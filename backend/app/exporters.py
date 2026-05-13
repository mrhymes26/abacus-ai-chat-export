from __future__ import annotations

import base64
import hashlib
import html
import json
import re
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .models import ExportResult
from .security import redact_secrets, redact_secrets_from_text
from .utils import ensure_dir, first_present, safe_json_dumps


MESSAGE_LIST_KEYS = {
    "messages",
    "chat_messages",
    "chatMessages",
    "conversation",
    "conversations",
    "events",
    "history",
    "turns",
    "cells",
    "records",
    "responses",
    "thread",
}
ROLE_KEYS = ("role", "author", "sender", "user_type", "userType", "type")
CONTENT_KEYS = ("content", "text", "message", "response", "prompt", "output", "value")
TIME_KEYS = ("created_at", "createdAt", "timestamp", "time", "date")


def to_plain_data(obj: Any) -> Any:
    return _to_plain_data(obj, seen=set(), depth=0)


def _to_plain_data(obj: Any, seen: set[int], depth: int) -> Any:
    if depth > 30:
        return redact_secrets_from_text(str(obj))
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        return redact_secrets_from_text(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        try:
            return redact_secrets_from_text(obj.decode("utf-8"))
        except UnicodeDecodeError:
            return {"base64": base64.b64encode(obj).decode("ascii")}

    obj_id = id(obj)
    if obj_id in seen:
        return redact_secrets_from_text(str(obj))
    seen.add(obj_id)

    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            return _to_plain_data(obj.to_dict(), seen, depth + 1)
        except Exception:
            pass
    if isinstance(obj, dict):
        return {
            redact_secrets_from_text(str(key)): _to_plain_data(value, seen, depth + 1)
            for key, value in obj.items()
        }
    if isinstance(obj, (list, tuple, set)):
        return [_to_plain_data(item, seen, depth + 1) for item in obj]
    try:
        public_attrs = {key: value for key, value in vars(obj).items() if not key.startswith("_")}
        return _to_plain_data(public_attrs, seen, depth + 1)
    except Exception:
        return redact_secrets_from_text(str(obj))


def write_json(path: str | Path, data: Any) -> Path:
    file_path = Path(path)
    ensure_dir(file_path.parent)
    file_path.write_text(safe_json_dumps(redact_secrets(to_plain_data(data))), encoding="utf-8")
    return file_path


def extract_messages_to_markdown(data: Any, title: str | None, source_type: str, source_id: str) -> str:
    plain = to_plain_data(data)
    message_list = _best_message_list(plain)
    heading = title or source_id
    if not message_list:
        return (
            "# No markdown chat history could be extracted\n\n"
            "Raw data was saved as JSON.\n"
        )

    lines = [
        f"# {heading}",
        "",
        f"Source type: {source_type}",
        f"Source ID: {source_id}",
        "",
    ]
    for message in message_list:
        role = _string_value(_first_key(message, ROLE_KEYS)) or "Message"
        content = _content_value(message)
        timestamp = _string_value(_first_key(message, TIME_KEYS))
        role_label = _normalize_role(role)
        lines.append(f"## {role_label}")
        if timestamp:
            lines.append(f"Time: {timestamp}")
        lines.append("")
        body = _tidy_export_plaintext(content or "")
        lines.append(body or "_No text content detected._")
        lines.append("")
    return redact_secrets_from_text("\n".join(lines).rstrip() + "\n")


def conversation_export_stats(data: Any) -> dict[str, Any]:
    plain = to_plain_data(data)
    messages = _best_message_list(plain)
    history = plain.get("history") if isinstance(plain, dict) else None
    total_events = plain.get("total_events") if isinstance(plain, dict) else None
    fetch_meta = plain.get("_abacus_backup_fetch") if isinstance(plain, dict) else None
    stats = {
        "extracted_messages": len(messages),
        "history_items": len(history) if isinstance(history, list) else None,
        "total_events": total_events,
        "complete_by_total_events": None,
        "fetch": fetch_meta if isinstance(fetch_meta, dict) else None,
    }
    if isinstance(history, list) and total_events is not None:
        try:
            stats["complete_by_total_events"] = len(history) >= int(total_events)
        except (TypeError, ValueError):
            pass
    return stats


def to_openwebui_chat(
    data: Any,
    *,
    title: str | None,
    source_type: str,
    source_id: str,
    deployment_id: str | None = None,
) -> dict[str, Any]:
    plain = to_plain_data(data)
    message_list = _best_message_list(plain)
    if not message_list:
        raise ValueError("No messages could be extracted for Open WebUI conversion.")

    chat_messages: dict[str, dict[str, Any]] = {}
    ordered_ids: list[str] = []
    models: list[str] = []

    for index, message in enumerate(message_list):
        if not isinstance(message, dict):
            continue
        content = _tidy_export_plaintext(_content_value(message).strip())
        if not content:
            continue

        raw_role = _string_value(_first_key(message, ROLE_KEYS)) or "assistant"
        role = _openwebui_role(raw_role)
        normalized_role = _normalize_role(raw_role)
        if role == "assistant" and normalized_role not in {"Assistant", "User"}:
            content = f"[{normalized_role}]\n{content}"

        msg_id = _openwebui_message_id(source_id, index, role, content)
        parent_id = ordered_ids[-1] if ordered_ids else None
        if parent_id:
            chat_messages[parent_id]["childrenIds"] = [msg_id]

        timestamp = _unix_timestamp(_first_key(message, TIME_KEYS))
        model = _message_model(message)
        if model and model not in models:
            models.append(model)

        entry: dict[str, Any] = {
            "id": msg_id,
            "parentId": parent_id,
            "childrenIds": [],
            "role": role,
            "content": content,
        }
        if timestamp is not None:
            entry["timestamp"] = timestamp
        if role == "assistant":
            entry["done"] = True
            if model:
                entry["model"] = model

        chat_messages[msg_id] = entry
        ordered_ids.append(msg_id)

    if not ordered_ids:
        raise ValueError("No text-based messages could be extracted for Open WebUI conversion.")

    created_at = _unix_timestamp(first_present(plain, ("created_at", "createdAt", "created", "timestamp"))) if isinstance(plain, dict) else None
    updated_at = _unix_timestamp(
        first_present(plain, ("updated_at", "updatedAt", "last_event_created_at", "lastEventCreatedAt", "timestamp"))
    ) if isinstance(plain, dict) else None
    if created_at is None:
        created_at = min((msg.get("timestamp") for msg in chat_messages.values() if isinstance(msg.get("timestamp"), int)), default=None)
    if updated_at is None:
        updated_at = max((msg.get("timestamp") for msg in chat_messages.values() if isinstance(msg.get("timestamp"), int)), default=created_at)

    tags = ["abacus-ai", source_type]
    if deployment_id:
        tags.append("deployment")

    return {
        "chat": {
            "title": title or source_id or "Abacus Conversation",
            "models": models,
            "history": {
                "currentId": ordered_ids[-1],
                "messages": chat_messages,
            },
            "options": {},
        },
        "meta": {
            "tags": tags,
            "source": "abacus-ai",
            "source_type": source_type,
            "source_id": source_id,
            "deployment_id": deployment_id,
        },
        "pinned": False,
        "folder_id": None,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def write_openwebui_import(path: str | Path, chats: list[dict[str, Any]]) -> Path:
    file_path = Path(path)
    ensure_dir(file_path.parent)
    file_path.write_text(safe_json_dumps(redact_secrets(chats)), encoding="utf-8")
    return file_path


def write_markdown(path: str | Path, markdown: str) -> Path:
    file_path = Path(path)
    ensure_dir(file_path.parent)
    file_path.write_text(redact_secrets_from_text(markdown), encoding="utf-8")
    return file_path


def write_conversation_readout_html(
    path: str | Path,
    data: Any,
    *,
    title: str | None,
    source_type: str,
    source_id: str,
    deployment_id: str | None = None,
    conversation_only_export: bool = False,
) -> Path:
    """Readable conversation view in a messenger layout with print/PDF-oriented styles."""
    file_path = Path(path)
    ensure_dir(file_path.parent)

    def esc(s: Any) -> str:
        return html.escape(str(s) if s is not None else "", quote=True)

    plain = to_plain_data(data)
    messages = _best_message_list(plain)
    heading = title or source_id

    type_hint = ""
    if source_type == "ai_chat":
        type_hint = "Messages between you (user) and the AI assistant."
    elif source_type == "deployment_conversation":
        dep = deployment_id or "—"
        type_hint = (
            f"Deployment conversation: user and assistant in the context of this deployment "
            f"(deployment ID: {dep})."
        )
    else:
        type_hint = "Message history."

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8"/>',
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
        '<meta name="color-scheme" content="light"/>',
        f"<title>{esc('Conversation')} — {esc(heading)}</title>",
        "<style>",
        ":root { --wa-green:#075e54; --wa-green-2:#128c7e; --wa-user:#dcf8c6; --wa-peer:#ffffff; --wa-bg:#e5ddd5; --text:#111b21; --muted:#667781; --line:#d1d7db; }",
        "* { box-sizing: border-box; }",
        "body { font-family: system-ui, Segoe UI, Roboto, sans-serif; margin: 0; background: #d8d7d2; color: var(--text); line-height: 1.45; }",
        ".wrap { max-width: 860px; margin: 0 auto; padding: 1.25rem 1rem 2rem; }",
        ".phone { overflow: hidden; border: 1px solid #c9cfcc; background: var(--wa-bg); box-shadow: 0 10px 32px rgba(17,27,33,.12); }",
        ".chat-header { position: sticky; top: 0; z-index: 2; display: flex; align-items: center; gap: .75rem; min-height: 4rem; padding: .65rem .9rem; background: linear-gradient(90deg,var(--wa-green),var(--wa-green-2)); color: #fff; }",
        ".avatar { display: grid; place-items: center; width: 2.6rem; height: 2.6rem; flex: none; border-radius: 999px; background: rgba(255,255,255,.22); font-weight: 800; }",
        ".title { min-width: 0; flex: 1; }",
        "h1 { overflow: hidden; margin: 0; font-size: 1rem; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }",
        ".sub { overflow: hidden; margin: .12rem 0 0; color: rgba(255,255,255,.82); font-size: .78rem; text-overflow: ellipsis; white-space: nowrap; }",
        ".thread { min-height: 62vh; padding: 1rem .8rem 1.25rem; background-color: var(--wa-bg); background-image: radial-gradient(circle at 12px 12px, rgba(255,255,255,.23) 1.4px, transparent 1.4px), radial-gradient(circle at 38px 32px, rgba(7,94,84,.08) 1.1px, transparent 1.1px); background-size: 52px 52px; }",
        ".message-row { display: flex; margin: .28rem 0; }",
        ".msg-user { justify-content: flex-end; }",
        ".msg-assistant, .msg-other { justify-content: flex-start; }",
        ".msg-system { justify-content: center; }",
        ".bubble { position: relative; max-width: min(78%, 44rem); min-width: 0; padding: .45rem .62rem .35rem; border-radius: .48rem; box-shadow: 0 1px .5px rgba(17,27,33,.18); overflow-wrap: break-word; word-break: normal; font-size: .94rem; line-height: 1.5; overflow-x: hidden; overflow-y: visible; }",
        ".bubble .plain-body { white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; max-width: 100%; }",
        ".bubble .md-body { white-space: normal; min-width: 0; max-width: 100%; }",
        ".bubble .md-body > *:first-child { margin-top: 0; }",
        ".bubble .md-body .md-p { margin: 0.35rem 0; white-space: pre-line; overflow-wrap: break-word; }",
        ".bubble .md-body .md-h { margin: 0.55rem 0 0.25rem; font-weight: 700; line-height: 1.25; color: #0f172a; }",
        ".bubble .md-body h2.md-h { font-size: 1.05rem; }",
        ".bubble .md-body h3.md-h { font-size: 0.98rem; }",
        ".bubble .md-body h4.md-h, .bubble .md-body h5.md-h, .bubble .md-body h6.md-h { font-size: 0.9rem; }",
        ".bubble .md-body .tool-label { display: block; margin: 0.45rem 0 0.15rem; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: var(--wa-green-2); }",
        ".bubble .md-body .md-quote { margin: 0.35rem 0 0.45rem; padding: 0.35rem 0.5rem; border-left: 3px solid var(--wa-green-2); background: #ecfdf5; border-radius: 0 0.35rem 0.35rem 0; font-size: 0.84rem; color: #14532d; }",
        ".bubble .md-body .md-quote p { margin: 0; white-space: pre-line; overflow-wrap: break-word; }",
        ".bubble .md-body .md-quote.routing { background: #f0fdf4; }",
        ".bubble .md-body .md-list { margin: 0.35rem 0 0.45rem 1rem; padding-left: 0.35rem; }",
        ".bubble .md-body .md-list li { margin: 0.18rem 0; overflow-wrap: break-word; word-break: normal; }",
        ".bubble .md-body .md-table-wrap { margin: 0.45rem 0; overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100%; }",
        ".bubble .md-body table.md-table { border-collapse: collapse; width: 100%; font-size: 0.78rem; }",
        ".bubble .md-body .md-table th, .bubble .md-body .md-table td { border: 1px solid var(--line); padding: 0.28rem 0.38rem; vertical-align: top; text-align: left; overflow-wrap: break-word; word-break: normal; hyphens: auto; }",
        ".bubble .md-body .md-table th { background: #f4f4f5; font-weight: 600; }",
        ".bubble .md-body .md-hr { margin: 0.45rem 0; border: 0; border-top: 1px solid var(--line); }",
        ".bubble .md-body a { color: #0d9488; text-decoration: underline; text-underline-offset: 2px; }",
        ".bubble .md-body .md-code { font-family: ui-monospace, Consolas, monospace; font-size: 0.82em; background: #f4f4f5; padding: 0.08rem 0.22rem; border-radius: 0.2rem; }",
        ".msg-user .bubble { background: var(--wa-user); border-top-right-radius: .12rem; }",
        ".msg-assistant .bubble, .msg-other .bubble { background: var(--wa-peer); border-top-left-radius: .12rem; }",
        ".msg-user .bubble::after { content: ''; position: absolute; right: -.45rem; top: 0; width: 0; height: 0; border-top: .45rem solid var(--wa-user); border-right: .45rem solid transparent; }",
        ".msg-assistant .bubble::before, .msg-other .bubble::before { content: ''; position: absolute; left: -.45rem; top: 0; width: 0; height: 0; border-top: .45rem solid var(--wa-peer); border-left: .45rem solid transparent; }",
        ".msg-system .bubble { max-width: 72%; background: rgba(255,255,255,.76); color: var(--muted); text-align: center; font-size: .78rem; border-radius: .55rem; box-shadow: none; }",
        ".sender { display: block; margin: 0 0 .18rem; color: var(--wa-green); font-size: .73rem; font-weight: 700; }",
        ".msg-user .sender { color: #356b28; text-align: right; }",
        ".stamp { display: block; margin-top: .28rem; text-align: right; color: var(--muted); font-size: .68rem; line-height: 1.25; white-space: normal; overflow-wrap: anywhere; word-break: break-word; }",
        ".empty { margin: 1rem auto; max-width: 34rem; padding: .8rem 1rem; background: rgba(255,255,255,.86); border-radius: .55rem; color: #92400e; font-size: .9rem; text-align: center; }",
        "footer.note { padding: .8rem 1rem; background: #f0f2f5; border-top: 1px solid var(--line); color: var(--muted); font-size: .72rem; }",
        ".screen-only { margin: .75rem 0 0; color: rgba(255,255,255,.72); font-size: .75rem; }",
        ".phone > .screen-only { display: none; }",
        "@media print {",
        "  .screen-only { display: none !important; }",
        "  @page { size: A4; margin: 12mm 14mm; }",
        "  * { -webkit-print-color-adjust: economy; print-color-adjust: economy; box-shadow: none !important; }",
        "  body { background: #fff !important; color: #111 !important; }",
        "  .wrap { max-width: none; margin: 0; padding: 0; }",
        "  .phone { border: 0; background: #fff !important; box-shadow: none; }",
        "  .chat-header { position: static; min-height: auto; padding: 0 0 5mm; background: #fff !important; color: #111 !important; border-bottom: 1pt solid #bbb; }",
        "  .avatar { display: none !important; }",
        "  h1 { font-size: 14pt; page-break-after: avoid; }",
        "  .sub { color: #444 !important; font-size: 9pt; white-space: normal; }",
        "  .thread { min-height: auto; padding: 5mm 0; background: #fff !important; background-image: none !important; }",
        "  .message-row { break-inside: auto; page-break-inside: auto; margin: 0 0 3.5mm; }",
        "  .msg-user { justify-content: flex-end; }",
        "  .msg-assistant, .msg-other { justify-content: flex-start; }",
        "  .bubble { break-inside: auto; page-break-inside: auto; line-height: 1.5; overflow-wrap: break-word; word-break: normal; hyphens: auto; overflow-x: hidden; }",
        "  .bubble .plain-body { white-space: pre-wrap; overflow-wrap: anywhere; orphans: 2; widows: 2; }",
        "  .bubble .md-body .md-p { white-space: pre-line; line-height: 1.52; orphans: 3; widows: 3; overflow-wrap: break-word; word-break: normal; hyphens: auto; }",
        "  .bubble .md-body .md-quote p { white-space: pre-line; orphans: 2; widows: 2; }",
        "  .bubble .md-body .md-list li { orphans: 2; widows: 2; break-inside: avoid; page-break-inside: avoid; }",
        "  .bubble .md-body .md-table-wrap { break-inside: auto; }",
        "  .bubble .md-body table.md-table { break-inside: auto; width: 100%; }",
        "  .bubble .md-body .md-table thead { display: table-header-group; }",
        "  .bubble .md-body .md-table tr { break-inside: avoid; page-break-inside: avoid; }",
        "  .bubble .md-body .md-table th, .bubble .md-body .md-table td { font-size: 8pt; padding: 1.2mm 1.5mm; white-space: normal; overflow-wrap: break-word; word-break: normal; hyphens: auto; }",
        "  .bubble .md-body .md-h { page-break-after: avoid; break-after: avoid; }",
        "  .bubble .md-body .tool-label { page-break-after: avoid; break-after: avoid; }",
        "  .msg-user .bubble { border-left: 4pt solid #555; border-top-right-radius: 2mm; }",
        "  .msg-assistant .bubble, .msg-other .bubble { border-left: 4pt solid #999; border-top-left-radius: 2mm; }",
        "  .msg-system .bubble { max-width: 90%; border-style: dashed; text-align: center; }",
        "  .msg-user .bubble::after, .msg-assistant .bubble::before, .msg-other .bubble::before { display: none !important; }",
        "  .sender { color: #111 !important; font-size: 8pt; text-transform: uppercase; letter-spacing: .02em; }",
        "  .msg-user .sender { text-align: right; }",
        "  .stamp { float: none; color: #555 !important; font-size: 7pt; white-space: normal; overflow-wrap: anywhere; word-break: break-word; }",
        "  footer.note { background: #fff !important; border-top: 1pt solid #bbb; color: #444 !important; font-size: 8pt; }",
        "}",
        "</style>",
        "</head>",
        "<body>",
        '<div class="wrap">',
        '<section class="phone">',
        '<header class="chat-header">',
        f'<div class="avatar">{esc(_initials(heading))}</div>',
        '<div class="title">',
        f"<h1>{esc(heading)}</h1>",
        f'<p class="sub">{esc(type_hint)}</p>',
        '<p class="screen-only">Print or PDF: <strong>Ctrl+P</strong> (Mac: <strong>Cmd+P</strong>) — save as PDF or choose a printer. This page is tuned for A4.</p>',
        "</div>",
        "</header>",
        '<main class="thread">',
    ]

    if not messages:
        hint_tail = (
            "Try other export formats or inspect the raw data."
            if conversation_only_export
            else "Check the JSON file or the SDK HTML export."
        )
        parts.append(
            '<p class="empty">No individual messages with role and text could be detected from the raw data. '
            + esc(hint_tail)
            + "</p>"
        )
    else:
        for message in messages:
            raw_role = _string_value(_first_key(message, ROLE_KEYS)) or "message"
            normalized = _normalize_role(raw_role)
            ui_class = _role_ui_class(normalized)
            label_ui = _role_display_label(normalized)
            content = _content_value(message)
            timestamp = _string_value(_first_key(message, TIME_KEYS))
            raw_hint = raw_role if raw_role.lower() != normalized.lower() else ""
            sender = label_ui if not raw_hint or label_ui == raw_hint else f"{label_ui} ({raw_hint})"
            parts.append(f'<article class="message-row {ui_class}">')
            if content:
                rich = normalized == "Assistant"
                inner = _message_body_html_for_export(content, rich_markdown=rich)
                parts.append(f'<div class="bubble"><span class="sender">{esc(sender)}</span>{inner}')
                if timestamp:
                    parts.append(f'<span class="stamp">{esc(timestamp)}</span>')
                parts.append("</div>")
            else:
                parts.append('<div class="bubble"><em>No text content.</em></div>')
            parts.append("</article>")

    parts.append("</main>")
    parts.append(
        '<footer class="note">Technical IDs — chat: <code>'
        + esc(source_id)
        + "</code>"
        + (
            f' · Deployment: <code>{esc(deployment_id)}</code>'
            if deployment_id
            else ""
        )
        + "</footer>"
    )
    parts.append("</section>")
    parts.append("</div></body></html>")

    file_path.write_text(redact_secrets_from_text("\n".join(parts)), encoding="utf-8")
    return file_path


def _role_ui_class(normalized: str) -> str:
    if normalized == "User":
        return "msg-user"
    if normalized == "Assistant":
        return "msg-assistant"
    if normalized == "System":
        return "msg-system"
    return "msg-other"


def _initials(value: str | None) -> str:
    words = [part for part in str(value or "Chat").replace("_", " ").split() if part]
    if not words:
        return "C"
    return "".join(word[0].upper() for word in words[:2])[:2]


def _role_display_label(normalized: str) -> str:
    mapping = {
        "User": "You / user",
        "Assistant": "Assistant",
        "System": "System",
        "Message": "Message",
    }
    return mapping.get(normalized, normalized)


def _openwebui_role(raw_role: str) -> str:
    normalized = _normalize_role(raw_role)
    return "user" if normalized == "User" else "assistant"


def _openwebui_message_id(source_id: str, index: int, role: str, content: str) -> str:
    digest = hashlib.sha256(f"{source_id}:{index}:{role}:{content[:200]}".encode("utf-8")).hexdigest()[:16]
    return f"abacus-{index + 1}-{digest}"


def _unix_timestamp(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if number > 10_000_000_000:
            number = number / 1000
        return int(number)
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.isdigit():
            number = float(text)
            if number > 10_000_000_000:
                number = number / 1000
            return int(number)
        normalized = text.replace("Z", "+00:00")
        return int(datetime.fromisoformat(normalized).timestamp())
    except Exception:
        return None


def _message_model(message: dict[str, Any]) -> str | None:
    value = first_present(
        message,
        (
            "model",
            "model_id",
            "modelId",
            "model_version",
            "modelVersion",
            "llm_model",
            "llmModel",
        ),
    )
    if value is None:
        return None
    if isinstance(value, dict):
        value = first_present(value, ("name", "id", "model", "model_id", "modelId"))
    text = str(value).strip()
    return text or None


def write_export_result(result: Any, path_base: str | Path) -> list[Path]:
    base = Path(path_base)
    ensure_dir(base.parent)
    data = result.data if isinstance(result, ExportResult) else result
    written: list[Path] = []

    if isinstance(data, bytes):
        suffix = ".html" if _bytes_look_like_html(data) else ".bin"
        file_path = base.with_suffix(suffix)
        file_path.write_bytes(data)
        return [file_path]

    if isinstance(data, str):
        content = redact_secrets_from_text(data)
        suffix = ".html" if _looks_like_html(content) else ".txt"
        file_path = base.with_suffix(suffix)
        file_path.write_text(content, encoding="utf-8")
        return [file_path]

    plain = to_plain_data(data)
    # SDK liefert oft ein Objekt statt Roh-HTML: strukturierte Antwort als Sidecar-Metadaten
    # (kein ".export." im Dateinamen — nur .html bzw. .meta.json)
    metadata_path = base.with_suffix(".meta.json")
    metadata_path.write_text(safe_json_dumps(plain), encoding="utf-8")
    written.append(metadata_path)

    embedded = _first_key(plain, ("html", "content", "data", "file_content", "fileContent"))
    if isinstance(embedded, str) and _looks_like_html(embedded):
        html_path = base.with_suffix(".html")
        html_path.write_text(redact_secrets_from_text(embedded), encoding="utf-8")
        written.append(html_path)
    elif isinstance(embedded, bytes):
        embedded_path = base.with_suffix(".html" if _bytes_look_like_html(embedded) else ".bin")
        embedded_path.write_bytes(embedded)
        written.append(embedded_path)
    return written


def write_backup_index_html(
    manifest: dict[str, Any],
    backup_root: Path,
    *,
    filename: str = "index.html",
) -> Path:
    """Single-page overview with relative links to exported files (open index.html after unzip)."""
    root = Path(backup_root)
    ensure_dir(root)
    out = root / filename

    def esc(s: Any) -> str:
        return html.escape(str(s) if s is not None else "", quote=True)

    def href(rel: str) -> str:
        rel = rel.replace("\\", "/").strip("/")
        return "/".join(quote(part, safe="") for part in rel.split("/") if part)

    backup_id = manifest.get("backup_id") or ""
    created = esc(manifest.get("created_at") or "")
    app_name = esc(manifest.get("app") or "")
    app_version = manifest.get("app_version")
    app_line = app_name
    if app_version:
        app_line += f' · Version <code>{esc(app_version)}</code>'
    counts = manifest.get("counts") or {}
    req = manifest.get("request") or {}
    formats = req.get("formats") or []
    mode = req.get("mode") or ""

    global_errors = manifest.get("errors") or []

    lines: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8"/>',
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
        f"<title>{esc('Backup')} — {esc(backup_id)}</title>",
        "<style>",
        ":root { --bg:#fafafa; --card:#fff; --border:#e4e4e7; --text:#18181b; --muted:#71717a; --accent:#047857; --danger:#b91c1c; }",
        "* { box-sizing: border-box; }",
        "body { font-family: system-ui, Segoe UI, Roboto, sans-serif; margin: 0; background: var(--bg); color: var(--text); line-height: 1.5; }",
        ".wrap { max-width: 960px; margin: 0 auto; padding: 1.5rem; }",
        "header { margin-bottom: 1.5rem; }",
        "h1 { font-size: 1.35rem; margin: 0 0 0.35rem; }",
        ".meta { color: var(--muted); font-size: 0.875rem; }",
        ".badges { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1rem 0; }",
        ".badge { background: #ecfdf5; color: var(--accent); padding: 0.2rem 0.55rem; border-radius: 0.35rem; font-size: 0.75rem; font-weight: 600; }",
        ".err-box { background: #fef2f2; border: 1px solid #fecaca; color: var(--danger); padding: 0.75rem 1rem; border-radius: 0.35rem; margin: 1rem 0; font-size: 0.875rem; }",
        "table { width: 100%; border-collapse: collapse; background: var(--card); border: 1px solid var(--border); border-radius: 0.5rem; overflow: hidden; }",
        "th, td { text-align: left; padding: 0.65rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: top; }",
        "th { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); background: #fafafa; }",
        "tr:last-child td { border-bottom: none; }",
        ".files a { display: inline-block; margin: 0.15rem 0.35rem 0 0; padding: 0.15rem 0.45rem; background: #f4f4f5; border-radius: 0.25rem; font-size: 0.8rem; text-decoration: none; color: #27272a; }",
        ".files a:hover { background: #e4e4e7; }",
        ".files a.ft-konv::before { content: 'Conversation '; font-size: 0.65rem; color: var(--muted); }",
        ".files a.ft-md::before { content: 'MD '; font-size: 0.65rem; color: var(--muted); }",
        ".files a.ft-html::before { content: 'HTML '; font-size: 0.65rem; color: var(--muted); }",
        ".files a.ft-meta::before { content: 'Meta '; font-size: 0.65rem; color: var(--muted); }",
        ".files a.ft-bin::before { content: 'Bin '; font-size: 0.65rem; color: var(--muted); }",
        ".files a.ft-txt::before { content: 'Txt '; font-size: 0.65rem; color: var(--muted); }",
        "footer { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border); font-size: 0.8rem; color: var(--muted); }",
        "footer a { color: var(--accent); }",
        "</style>",
        "</head>",
        "<body>",
        '<div class="wrap">',
        "<header>",
        f"<h1>Backup overview</h1>",
        f'<p class="meta">{app_line}<br/>Backup ID: <code>{esc(backup_id)}</code><br/>Created: {created}</p>',
        "</header>",
        '<div class="badges">',
        f'<span class="badge">Mode: {esc(mode)}</span>',
        f'<span class="badge">Formats: {esc(", ".join(str(f) for f in formats))}</span>',
        f'<span class="badge">AI chats: {esc(counts.get("ai_chat", 0))}</span>',
        f'<span class="badge">Deployments: {esc(counts.get("deployment_conversation", 0))}</span>',
        f'<span class="badge">Processed: {esc(counts.get("processed", 0))}</span>',
        "</div>",
    ]

    if global_errors:
        lines.append('<div class="err-box"><strong>Notes / errors (job)</strong><ul>')
        for err in global_errors[:200]:
            lines.append(f"<li>{esc(err)}</li>")
        lines.append("</ul></div>")

    lines.append("<table><thead><tr>")
    for h in ("Title / chat", "Type", "Deployment", "ID", "Files and links"):
        lines.append(f"<th>{esc(h)}</th>")
    lines.append("</tr></thead><tbody>")

    items = manifest.get("items") or []
    if not items:
        lines.append(
            '<tr><td colspan="5" style="color:var(--muted)">No entries in this backup.</td></tr>'
        )
    for row in items:
        title = row.get("title") or row.get("id") or "—"
        ctype = row.get("type") or "—"
        dep = row.get("deployment_id") or "—"
        cid = row.get("id") or "—"
        item_errs = row.get("errors") or []
        files = row.get("files") or []

        lines.append("<tr>")
        lines.append(f"<td><strong>{esc(title)}</strong>")
        if item_errs:
            lines.append(f'<br/><span style="color:var(--danger);font-size:0.8rem">{esc("; ".join(item_errs[:5]))}</span>')
        lines.append("</td>")
        lines.append(f"<td><code>{esc(ctype)}</code></td>")
        lines.append(f"<td><code>{esc(dep)}</code></td>")
        lines.append(f"<td><code>{esc(cid)}</code></td>")
        lines.append('<td class="files">')
        for rel in files:
            rel_s = str(rel).replace("\\", "/")
            label = Path(rel_s).name
            css_classes = ["file-link"]
            lower = label.lower()
            if lower.endswith("_konversation.html"):
                css_classes.append("ft-konv")
            elif lower.endswith(".html"):
                css_classes.append("ft-html")
            elif lower.endswith(".md"):
                css_classes.append("ft-md")
            elif lower.endswith(".meta.json"):
                css_classes.append("ft-meta")
            elif lower.endswith(".json"):
                css_classes.append("ft-json")
            elif lower.endswith(".txt"):
                css_classes.append("ft-txt")
            else:
                css_classes.append("ft-bin")
            cls_attr = " ".join(css_classes)
            lines.append(f'<a class="{cls_attr}" href="{href(rel_s)}">{esc(label)}</a>')
        lines.append("</td></tr>")

    lines.append("</tbody></table>")

    lines.append("<footer>")
    lines.append("<p>Quick links:</p><ul>")
    lines.append(f'<li><a href="{href("manifest.json")}">manifest.json</a> — full metadata</li>')
    lines.append(f'<li><a href="{href("errors.log")}">errors.log</a></li>')
    lines.append("</ul>")
    lines.append(
        "<p>Tip: extract the folder and open this file (<code>index.html</code>) in a browser — links are relative.</p>"
    )
    lines.append("</footer>")
    lines.append("</div></body></html>")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def create_backup_zip(backup_dir: str | Path) -> Path:
    root = Path(backup_dir)
    zip_path = root / "backup.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in root.rglob("*"):
            if not file_path.is_file() or file_path == zip_path:
                continue
            archive.write(file_path, file_path.relative_to(root).as_posix())
    return zip_path


def _best_message_list(data: Any) -> list[Any]:
    candidates = list(_find_message_lists(data, depth=0))
    candidates.sort(key=lambda values: (_message_list_score(values), len(values)), reverse=True)
    return candidates[0] if candidates else []


def _find_message_lists(data: Any, depth: int) -> list[list[Any]]:
    if depth > 12:
        return []
    found: list[list[Any]] = []
    if isinstance(data, list):
        if _message_list_score(data) > 0:
            found.append(data)
        for item in data[:200]:
            found.extend(_find_message_lists(item, depth + 1))
    elif isinstance(data, dict):
        for key, value in data.items():
            if key in MESSAGE_LIST_KEYS and isinstance(value, list):
                found.append(value)
            found.extend(_find_message_lists(value, depth + 1))
    return found


def _message_list_score(values: list[Any]) -> int:
    if not values:
        return 0
    score = 0
    for item in values[:20]:
        if not isinstance(item, dict):
            continue
        if _content_value(item).strip():
            score += 2
        if _first_key(item, ROLE_KEYS) is not None:
            score += 1
        if _first_key(item, TIME_KEYS) is not None:
            score += 1
    return score


def _first_key(data: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(data, dict):
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
    return None


def _content_value(message: Any) -> str:
    """Plain text for one chat turn. Abacus deployment `history` often leaves BOT `text` empty and puts the body in `segments`."""
    if not isinstance(message, dict):
        return ""
    for key in CONTENT_KEYS:
        if key not in message or message[key] is None:
            continue
        val = message[key]
        if isinstance(val, str):
            if val.strip():
                return redact_secrets_from_text(val)
        else:
            return redact_secrets_from_text(json.dumps(val, ensure_ascii=False, indent=2, default=str))
    seg_text = _text_from_segments(message.get("segments"))
    if seg_text.strip():
        return seg_text
    for sk in ("streamed_data", "streamedData"):
        v = message.get(sk)
        if isinstance(v, str) and v.strip():
            return redact_secrets_from_text(v)
    return ""


def _text_from_segments(segments: Any, depth: int = 0) -> str:
    """Flatten Abacus `segments` (nested dicts, collapsible_component + text chunks)."""
    if depth > 32 or segments is None:
        return ""
    if isinstance(segments, str):
        s = segments.strip()
        return redact_secrets_from_text(s) if s else ""
    if isinstance(segments, dict):
        return _segment_node_to_text(segments, depth + 1)
    if not isinstance(segments, list):
        return ""
    parts: list[str] = []
    for item in segments:
        chunk = _text_from_segments(item, depth + 1)
        if chunk.strip():
            parts.append(chunk)
    return "\n\n".join(parts)


def _segment_node_to_text(node: dict, depth: int) -> str:
    if depth > 32:
        return ""
    parts: list[str] = []

    title = node.get("title")
    if isinstance(title, str) and title.strip():
        parts.append(redact_secrets_from_text(title.strip()))

    seg = node.get("segment")
    if isinstance(seg, str) and seg.strip():
        parts.append(redact_secrets_from_text(seg.strip()))
    elif isinstance(seg, dict):
        inner = _segment_node_to_text(seg, depth + 1)
        if inner.strip():
            parts.append(inner)

    for extra_key in ("text", "content", "body", "markdown"):
        v = node.get(extra_key)
        if isinstance(v, str) and v.strip():
            parts.append(redact_secrets_from_text(v.strip()))

    return "\n\n".join(parts)


_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")


def _tidy_export_plaintext(text: str) -> str:
    """Normalize whitespace and repair common segment-merge line breaks for Markdown/Open WebUI."""
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = _merge_paragraphs_after_unclosed_bold(t)
    return _join_soft_breaks_inside_bold_spans(t)


def _merge_paragraphs_after_unclosed_bold(text: str) -> str:
    """Join paragraphs when the previous block ends with odd ** count (broken bold across a blank line)."""
    parts = text.split("\n\n")
    out: list[str] = []
    i = 0
    while i < len(parts):
        block = parts[i]
        if i + 1 < len(parts):
            nxt = parts[i + 1]
            last_line = block.split("\n")[-1] if block else ""
            if last_line.count("**") % 2 == 1:
                nxt_strip = nxt.strip()
                if "\n" not in nxt_strip and len(nxt_strip) <= 8000:
                    out.append(block.rstrip() + " " + nxt_strip)
                    i += 2
                    continue
        out.append(block)
        i += 1
    return "\n\n".join(out)


def _join_soft_breaks_inside_bold_spans(text: str) -> str:
    """Join single newlines inside a paragraph when ** delimiters are unbalanced (split bold across lines)."""
    parts_out: list[str] = []
    for para in text.split("\n\n"):
        lines = para.split("\n")
        merged: list[str] = []
        for ln in lines:
            if not merged:
                merged.append(ln)
                continue
            prev = merged[-1]
            if prev.count("**") % 2 == 1 and ln.strip():
                st = ln.lstrip()
                if st.startswith(("#", "|", ">", "- ", "* ")):
                    merged.append(ln)
                    continue
                if re.match(r"^\d+\.\s", st):
                    merged.append(ln)
                    continue
                merged[-1] = prev.rstrip() + " " + ln.lstrip()
            else:
                merged.append(ln)
        parts_out.append("\n".join(merged))
    return "\n\n".join(parts_out)


def _message_body_html_for_export(text: str, *, rich_markdown: bool) -> str:
    """Turn plain export text into safe HTML (rich Markdown for assistant bubbles, escaped plain for users)."""
    if not text:
        return ""
    tidied = _tidy_export_plaintext(text)
    if not rich_markdown:
        return f'<div class="plain-body">{html.escape(tidied, quote=True)}</div>'
    return f'<div class="md-body">{_markdownish_to_html(tidied)}</div>'


def _markdownish_to_html(text: str) -> str:
    """Subset of Markdown used in Abacus BOT replies: headings, lists, blockquotes, tables, links, **bold**."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0

    def flush_paragraph(buf: list[str]) -> None:
        if not buf:
            return
        raw = "\n".join(buf).strip()
        if raw:
            out.append(f'<p class="md-p">{_inline_markdown_spans_to_html(raw)}</p>')
        buf.clear()

    para: list[str] = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_paragraph(para)
            i += 1
            continue

        if re.fullmatch(r"[-*]{3,}", stripped) or re.fullmatch(r"_{3,}", stripped):
            flush_paragraph(para)
            out.append('<hr class="md-hr"/>')
            i += 1
            continue

        if stripped in {"Web Search", "Search Results"} or stripped.lower() in {"web search", "search results"}:
            flush_paragraph(para)
            out.append(f'<div class="tool-label">{html.escape(stripped, quote=True)}</div>')
            i += 1
            continue

        if re.match(r"^>\s?", stripped):
            flush_paragraph(para)
            bq_lines: list[str] = []
            while i < len(lines) and lines[i].strip() and re.match(r"^>\s?", lines[i].strip()):
                bq_lines.append(re.sub(r"^>\s?", "", lines[i].strip()))
                i += 1
            inner = "\n".join(bq_lines)
            cls = "md-quote routing" if re.match(r"^routing\b", inner, re.I) else "md-quote"
            out.append(
                f'<blockquote class="{cls}"><p>{_inline_markdown_spans_to_html(inner)}</p></blockquote>'
            )
            continue

        m_heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m_heading:
            flush_paragraph(para)
            level = min(len(m_heading.group(1)), 6)
            title = m_heading.group(2).strip()
            tag = f"h{level}"
            out.append(f'<{tag} class="md-h">{html.escape(title, quote=True)}</{tag}>')
            i += 1
            continue

        if _md_row_looks_like_table(stripped):
            flush_paragraph(para)
            table_lines: list[str] = []
            while i < len(lines):
                cur_raw = lines[i]
                cur = cur_raw.strip()
                if not cur:
                    if not table_lines:
                        break
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    if j < len(lines):
                        peek = lines[j].strip()
                        if peek.startswith("|") or _md_is_table_continuation_line(peek) or (
                            table_lines and _md_merge_table_fragment_row(table_lines[-1], peek)
                        ):
                            i += 1
                            continue
                    break
                if "|" in cur:
                    if table_lines and _md_merge_table_fragment_row(table_lines[-1], cur):
                        table_lines[-1] = table_lines[-1].rstrip() + " " + cur.strip()
                    else:
                        table_lines.append(cur.strip())
                    i += 1
                    continue
                if table_lines and _md_is_table_continuation_line(cur):
                    table_lines[-1] = table_lines[-1].rstrip() + " " + cur.strip()
                    i += 1
                    continue
                break
            table_html = _md_table_to_html(table_lines)
            if table_html:
                out.append(table_html)
            continue

        list_match = re.match(r"^(\s*)([-*]|\d+\.)\s+(.+)$", line)
        if list_match:
            flush_paragraph(para)
            ordered = list_match.group(2).endswith(".")
            items: list[str] = []
            pattern = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.+)$")
            while i < len(lines):
                cur = lines[i]
                if not cur.strip():
                    break
                lm = pattern.match(cur)
                if not lm:
                    break
                items.append(lm.group(3).strip())
                i += 1
            tag = "ol" if ordered else "ul"
            lis = "".join(f"<li>{_inline_markdown_spans_to_html(it)}</li>" for it in items)
            out.append(f'<{tag} class="md-list">{lis}</{tag}>')
            continue

        para.append(line.rstrip())
        i += 1

    flush_paragraph(para)
    return "\n".join(out)


def _md_is_table_continuation_line(line: str) -> bool:
    """A non-| line that belongs to the previous table row (cell wrapped in source)."""
    s = line.strip()
    if not s or len(s) > 260:
        return False
    if s.startswith(("#", ">", "- ", "* ")):
        return False
    if re.match(r"^\d+\.\s", s):
        return False
    return "|" not in s


def _md_merge_table_fragment_row(prev_row: str, fragment: str) -> bool:
    """Single-| fragment that continues the last row (e.g. 'Standard sizes |' after '..., allergies,')."""
    if not prev_row.rstrip().endswith((",", ";")):
        return False
    frag = fragment.strip()
    if frag.count("|") != 1:
        return False
    cells = [c.strip() for c in frag.split("|")]
    while cells and cells[-1] == "":
        cells.pop()
    while cells and cells[0] == "":
        cells.pop(0)
    if len(cells) == 1 and frag.rstrip().endswith("|"):
        return len(cells[0]) < 80
    if len(cells) == 2:
        return (not cells[1]) or len(cells[1]) < 48
    return False


def _md_row_looks_like_table(line: str) -> bool:
    if "|" not in line or line.count("|") < 2:
        return False
    if _md_is_separator_row(line):
        return False
    return True


def _md_is_separator_row(line: str) -> bool:
    s = line.strip().strip("|")
    if "|" not in line:
        return False
    cells = [c.strip() for c in s.split("|")]
    if not cells:
        return False
    return all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells)


def _md_table_to_html(rows: list[str]) -> str:
    if len(rows) < 2:
        return ""
    header = rows[0]
    if _md_is_separator_row(rows[1]):
        body_rows = rows[2:]
    else:
        body_rows = rows[1:]

    def split_row(r: str) -> list[str]:
        return [c.strip() for c in r.strip().strip("|").split("|")]

    heads = split_row(header)
    if not heads:
        return ""

    thead = "".join(f"<th>{_inline_markdown_spans_to_html(h)}</th>" for h in heads)
    tbody_parts: list[str] = []
    for r in body_rows:
        if not r.strip() or _md_is_separator_row(r):
            continue
        cells = split_row(r)
        if len(cells) < len(heads):
            cells = cells + [""] * (len(heads) - len(cells))
        elif len(cells) > len(heads):
            cells = cells[: len(heads)]
        tbody_parts.append(
            "<tr>" + "".join(f"<td>{_inline_markdown_spans_to_html(c)}</td>" for c in cells) + "</tr>"
        )
    return (
        '<div class="md-table-wrap"><table class="md-table"><thead><tr>'
        f"{thead}</tr></thead><tbody>{''.join(tbody_parts)}</tbody></table></div>"
    )


def _inline_markdown_spans_to_html(text: str) -> str:
    """Escape-safe inline **bold**, `code`, and [label](https://...) links."""
    if not text:
        return ""
    parts: list[str] = []
    pos = 0
    for m in _MD_LINK_RE.finditer(text):
        parts.append(_inline_markdown_spans_no_links(text[pos : m.start()]))
        label = m.group(1)
        url = m.group(2).strip()
        if url.startswith(("http://", "https://")):
            safe_url = html.escape(url, quote=True)
            parts.append(
                f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">'
                f"{html.escape(label, quote=True)}</a>"
            )
        else:
            parts.append(html.escape(m.group(0), quote=True))
        pos = m.end()
    parts.append(_inline_markdown_spans_no_links(text[pos:]))
    return "".join(parts)


def _inline_markdown_spans_no_links(text: str) -> str:
    if not text:
        return ""
    chunks = re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)
    out: list[str] = []
    for ch in chunks:
        if ch.startswith("**") and ch.endswith("**") and len(ch) > 4:
            inner = html.escape(ch[2:-2], quote=True)
            out.append(f"<strong>{inner}</strong>")
        elif ch.startswith("`") and ch.endswith("`") and len(ch) > 2:
            inner = html.escape(ch[1:-1], quote=True)
            out.append(f'<code class="md-code">{inner}</code>')
        else:
            out.append(html.escape(ch, quote=True))
    return "".join(out)


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    return redact_secrets_from_text(str(value))


def _normalize_role(role: str) -> str:
    lowered = role.strip().lower()
    if lowered in {"assistant", "bot", "ai", "model", "assistent"}:
        return "Assistant"
    if lowered in {"system"}:
        return "System"
    if lowered in {"user", "human", "customer", "nutzer", "benutzer"}:
        return "User"
    return role.strip().title() or "Message"


def _looks_like_html(value: str) -> bool:
    lowered = value.lstrip()[:300].lower()
    return lowered.startswith("<!doctype html") or lowered.startswith("<html") or "<body" in lowered


def _bytes_look_like_html(value: bytes) -> bool:
    try:
        return _looks_like_html(value[:500].decode("utf-8", errors="ignore"))
    except Exception:
        return False
