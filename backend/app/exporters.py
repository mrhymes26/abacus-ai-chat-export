from __future__ import annotations

import base64
import json
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

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
    metadata_path = base.with_suffix(".export.json")
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
    if lowered in {"assistant", "bot", "ai", "model", "system"}:
        return "Assistant" if lowered != "system" else "System"
    if lowered in {"user", "human", "customer"}:
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
