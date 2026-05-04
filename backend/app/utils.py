from __future__ import annotations

import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


def now_utc_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def ensure_dir(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def short_id(value: str, length: int = 8) -> str:
    safe = str(value or "").replace("-", "")
    return safe[:length] or "unknown"


def safe_filename(value: str | None, fallback: str = "chat") -> str:
    text = (value or fallback).strip() or fallback
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._")
    return (text[:90] or fallback).strip()


def safe_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def safe_json_loads(value: str | bytes | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def split_env_list(value: str | None) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[\s,;]+", value)
    return [part.strip() for part in parts if part.strip()]


def first_present(mapping: Any, keys: Iterable[str]) -> Any:
    for key in keys:
        value = get_value(mapping, key)
        if value is not None:
            return value
    return None


def get_value(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def shallow_preview(data: Any, max_keys: int = 24) -> dict[str, Any]:
    if isinstance(data, dict):
        items = list(data.items())[:max_keys]
        return {str(k): _preview_value(v) for k, v in items}
    try:
        attrs = vars(data)
    except Exception:
        return {"value": _preview_value(data)}
    return {str(k): _preview_value(v) for k, v in list(attrs.items())[:max_keys]}


def _preview_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        text = value
        if isinstance(text, str) and len(text) > 300:
            return text[:297] + "..."
        return text
    if isinstance(value, (list, tuple)):
        return f"{len(value)} items"
    if isinstance(value, dict):
        return f"{len(value)} keys"
    return str(type(value).__name__)


def directory_size(path: str | Path) -> int:
    root = Path(path)
    if not root.exists():
        return 0
    total = 0
    for file_path in root.rglob("*"):
        if file_path.is_file():
            try:
                total += file_path.stat().st_size
            except OSError:
                continue
    return total


def relative_posix(path: str | Path, base: str | Path) -> str:
    try:
        return Path(path).relative_to(base).as_posix()
    except ValueError:
        return Path(path).name
