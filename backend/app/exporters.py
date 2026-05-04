from __future__ import annotations

import base64
import html
import json
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .models import ExportResult
from .security import redact_secrets, redact_secrets_from_text
from .utils import ensure_dir, safe_json_dumps


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
            "# Kein Markdown-Chatverlauf extrahierbar\n\n"
            "Die Rohdaten wurden als JSON gespeichert.\n"
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
            lines.append(f"Zeit: {timestamp}")
        lines.append("")
        lines.append(content or "_Kein Textinhalt erkannt._")
        lines.append("")
    return redact_secrets_from_text("\n".join(lines).rstrip() + "\n")


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
    """Lesbare Konversationsansicht: Rollen (Benutzer / Assistent), Zeitstempel; inkl. Druck/PDF-Styles."""
    file_path = Path(path)
    ensure_dir(file_path.parent)

    def esc(s: Any) -> str:
        return html.escape(str(s) if s is not None else "", quote=True)

    plain = to_plain_data(data)
    messages = _best_message_list(plain)
    heading = title or source_id

    type_hint = ""
    if source_type == "ai_chat":
        type_hint = "Nachrichten zwischen dir (Benutzer) und dem KI-Assistenten."
    elif source_type == "deployment_conversation":
        dep = deployment_id or "—"
        type_hint = (
            f"Deployment-Konversation: Nutzer und Assistent im Kontext dieses Deployments "
            f"(Deployment-ID: {dep})."
        )
    else:
        type_hint = "Nachrichtenverlauf."

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="de">',
        "<head>",
        '<meta charset="utf-8"/>',
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>',
        '<meta name="color-scheme" content="light"/>',
        f"<title>{esc('Konversation')} — {esc(heading)}</title>",
        "<style>",
        ":root { --user-bg:#ecfdf5; --user-accent:#047857; --asst-bg:#f4f4f5; --asst-accent:#52525b; --muted:#71717a; }",
        "* { box-sizing: border-box; }",
        "body { font-family: system-ui, Segoe UI, Roboto, sans-serif; margin: 0; background: #fafafa; color: #18181b; line-height: 1.55; }",
        ".wrap { max-width: 720px; margin: 0 auto; padding: 1.25rem 1rem 2rem; }",
        "header.page { margin-bottom: 1.25rem; padding-bottom: 1rem; border-bottom: 1px solid #e4e4e7; }",
        "h1 { font-size: 1.25rem; margin: 0 0 0.35rem; font-weight: 700; }",
        ".sub { font-size: 0.9rem; color: var(--muted); margin: 0 0 0.5rem; }",
        ".legend { display: flex; flex-wrap: wrap; gap: 0.75rem; font-size: 0.78rem; margin-top: 0.75rem; }",
        ".legend span { display: inline-flex; align-items: center; gap: 0.35rem; }",
        ".dot { width: 0.55rem; height: 0.55rem; border-radius: 999px; }",
        ".dot-user { background: var(--user-accent); }",
        ".dot-asst { background: var(--asst-accent); }",
        ".dot-sys { background: #a1a1aa; }",
        ".thread { margin-top: 1rem; }",
        ".turn { margin-bottom: 1rem; }",
        ".meta-row { display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.5rem 0.75rem; margin-bottom: 0.35rem; }",
        ".who { font-weight: 700; font-size: 0.82rem; letter-spacing: 0.02em; }",
        ".who-user { color: var(--user-accent); }",
        ".who-assistant { color: #27272a; }",
        ".who-system { color: #71717a; }",
        ".who-other { color: #3f3f46; }",
        "time { font-size: 0.72rem; color: var(--muted); }",
        ".bubble { padding: 0.65rem 0.85rem; border-radius: 0.5rem; white-space: pre-wrap; word-break: break-word; font-size: 0.95rem; }",
        ".turn-user .bubble { background: var(--user-bg); border-left: 4px solid var(--user-accent); margin-right: 8%; }",
        ".turn-assistant .bubble { background: var(--asst-bg); border-left: 4px solid var(--asst-accent); margin-left: 8%; }",
        ".turn-system .bubble { background: #fafafa; border: 1px dashed #d4d4d8; font-size: 0.85rem; color: #52525b; }",
        ".turn-other .bubble { background: #fff; border: 1px solid #e4e4e7; }",
        ".empty { padding: 1rem; background: #fffbeb; border: 1px solid #fde68a; border-radius: 0.35rem; font-size: 0.9rem; color: #92400e; }",
        "footer.note { margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e4e4e7; font-size: 0.75rem; color: var(--muted); }",
        ".screen-only { font-size: 0.8rem; color: var(--muted); margin: 0.75rem 0 0; }",
        "@media print {",
        "  .screen-only { display: none !important; }",
        "  @page { size: A4; margin: 12mm 14mm; }",
        "  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }",
        "  body { background: #fff !important; color: #111 !important; }",
        "  .wrap { max-width: none; margin: 0; padding: 0; }",
        "  header.page { margin-bottom: 8mm; padding-bottom: 5mm; border-bottom: 1pt solid #ccc; }",
        "  h1 { font-size: 14pt; page-break-after: avoid; }",
        "  .sub { font-size: 10pt; }",
        "  .legend { font-size: 8pt; margin-top: 4mm; }",
        "  .thread { margin-top: 5mm; }",
        "  article.turn { break-inside: avoid; page-break-inside: avoid; margin-bottom: 4mm; }",
        "  .meta-row { margin-bottom: 2mm; }",
        "  .bubble { font-size: 10pt; line-height: 1.45; padding: 3mm 4mm; border-radius: 2mm; }",
        "  .turn-user .bubble { margin-right: 12%; border-left-width: 3pt; }",
        "  .turn-assistant .bubble { margin-left: 12%; border-left-width: 3pt; }",
        "  footer.note { margin-top: 8mm; padding-top: 4mm; border-top: 1pt solid #ccc; font-size: 8pt; }",
        "  time { font-size: 8pt; }",
        "}",
        "</style>",
        "</head>",
        "<body>",
        '<div class="wrap">',
        '<header class="page">',
        f"<h1>{esc(heading)}</h1>",
        f'<p class="sub">{esc(type_hint)}</p>',
        '<div class="legend">',
        '<span><i class="dot dot-user"></i> Du / Benutzer</span>',
        '<span><i class="dot dot-asst"></i> Assistent</span>',
        '<span><i class="dot dot-sys"></i> System</span>',
        "</div>",
        "</header>",
        '<p class="screen-only">PDF oder Druck: <strong>Strg+P</strong> (Mac: ⌘+P) → „Als PDF speichern“ oder Drucker wählen. '
        "Diese Seite ist für A4 optimiert.</p>",
        '<main class="thread">',
    ]

    if not messages:
        hint_tail = (
            "Optional andere Exportformate wählen oder Rohdaten prüfen."
            if conversation_only_export
            else "Bitte die JSON-Datei oder den SDK-HTML-Export prüfen."
        )
        parts.append(
            '<p class="empty">Aus den Rohdaten konnten keine einzelnen Nachrichten mit Rolle und Text erkannt werden. '
            + esc(hint_tail)
            + "</p>"
        )
    else:
        for message in messages:
            raw_role = _string_value(_first_key(message, ROLE_KEYS)) or "message"
            normalized = _normalize_role(raw_role)
            ui_class = _role_ui_class(normalized)
            label_de = _role_label_de(normalized)
            content = _content_value(message)
            timestamp = _string_value(_first_key(message, TIME_KEYS))
            raw_hint = raw_role if raw_role.lower() != normalized.lower() else ""
            parts.append(f'<article class="turn {ui_class}">')
            parts.append('<div class="meta-row">')
            parts.append(f'<span class="who who-{ui_class.replace("turn-", "")}">{esc(label_de)}</span>')
            if timestamp:
                parts.append(f"<time>{esc(timestamp)}</time>")
            if raw_hint and label_de != raw_hint:
                parts.append(f'<span style="font-size:0.72rem;color:var(--muted)">({esc(raw_hint)})</span>')
            parts.append("</div>")
            if content:
                parts.append(f'<div class="bubble">{esc(content)}</div>')
            else:
                parts.append('<div class="bubble"><em>Kein Textinhalt.</em></div>')
            parts.append("</article>")

    parts.append("</main>")
    parts.append(
        '<footer class="note">Technische IDs — Chat: <code>'
        + esc(source_id)
        + "</code>"
        + (
            f' · Deployment: <code>{esc(deployment_id)}</code>'
            if deployment_id
            else ""
        )
        + "</footer>"
    )
    parts.append("</div></body></html>")

    file_path.write_text(redact_secrets_from_text("\n".join(parts)), encoding="utf-8")
    return file_path


def _role_ui_class(normalized: str) -> str:
    if normalized == "User":
        return "turn-user"
    if normalized == "Assistant":
        return "turn-assistant"
    if normalized == "System":
        return "turn-system"
    return "turn-other"


def _role_label_de(normalized: str) -> str:
    mapping = {
        "User": "Du / Benutzer",
        "Assistant": "Assistent",
        "System": "System",
        "Message": "Nachricht",
    }
    return mapping.get(normalized, normalized)


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
    counts = manifest.get("counts") or {}
    req = manifest.get("request") or {}
    formats = req.get("formats") or []
    mode = req.get("mode") or ""

    global_errors = manifest.get("errors") or []

    lines: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="de">',
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
        ".files a.ft-konv::before { content: 'Konversation '; font-size: 0.65rem; color: var(--muted); }",
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
        f"<h1>Backup-Übersicht</h1>",
        f'<p class="meta">{app_name}<br/>Backup-ID: <code>{esc(backup_id)}</code><br/>Erstellt: {created}</p>',
        "</header>",
        '<div class="badges">',
        f'<span class="badge">Modus: {esc(mode)}</span>',
        f'<span class="badge">Formate: {esc(", ".join(str(f) for f in formats))}</span>',
        f'<span class="badge">AI-Chats: {esc(counts.get("ai_chat", 0))}</span>',
        f'<span class="badge">Deployments: {esc(counts.get("deployment_conversation", 0))}</span>',
        f'<span class="badge">Verarbeitet: {esc(counts.get("processed", 0))}</span>',
        "</div>",
    ]

    if global_errors:
        lines.append('<div class="err-box"><strong>Hinweise/Fehler (Job)</strong><ul>')
        for err in global_errors[:200]:
            lines.append(f"<li>{esc(err)}</li>")
        lines.append("</ul></div>")

    lines.append("<table><thead><tr>")
    for h in ("Titel / Chat", "Typ", "Deployment", "ID", "Dateien & Links"):
        lines.append(f"<th>{esc(h)}</th>")
    lines.append("</tr></thead><tbody>")

    items = manifest.get("items") or []
    if not items:
        lines.append(
            '<tr><td colspan="5" style="color:var(--muted)">Keine Einträge in diesem Backup.</td></tr>'
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
    lines.append("<p>Schnellzugriff:</p><ul>")
    lines.append(f'<li><a href="{href("manifest.json")}">manifest.json</a> — vollständige Metadaten</li>')
    lines.append(f'<li><a href="{href("errors.log")}">errors.log</a></li>')
    lines.append("</ul>")
    lines.append(
        "<p>Tipp: Ordner entpacken und diese Datei (<code>index.html</code>) im Browser öffnen — Links sind relativ.</p>"
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
        if _first_key(item, CONTENT_KEYS) is not None:
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
    value = _first_key(message, CONTENT_KEYS)
    if value is None:
        return ""
    if isinstance(value, str):
        return redact_secrets_from_text(value)
    return redact_secrets_from_text(json.dumps(value, ensure_ascii=False, indent=2, default=str))


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
