from __future__ import annotations

import hmac
import os
from pathlib import Path
from threading import RLock
from typing import Any


_SECRET_LOCK = RLock()
_SECRET_VALUES: set[str] = set()


def get_api_key_from_env() -> str | None:
    value = os.getenv("ABACUS_API_KEY")
    if value:
        register_secret(value)
    return value or None


def has_stored_api_key(path: str | Path) -> bool:
    return Path(path).is_file()


def get_api_key_from_file(path: str | Path) -> str | None:
    file_path = Path(path)
    if not file_path.is_file():
        return None
    value = file_path.read_text(encoding="utf-8").strip()
    if value:
        register_secret(value)
    return value or None


def store_api_key_locally(api_key: str, path: str | Path) -> None:
    register_secret(api_key)
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(api_key.strip(), encoding="utf-8")
    try:
        file_path.chmod(0o600)
    except OSError:
        pass


def delete_stored_api_key(path: str | Path) -> bool:
    file_path = Path(path)
    if not file_path.exists():
        return False
    file_path.unlink()
    return True


def register_secret(secret: str | None) -> None:
    if not secret:
        return
    with _SECRET_LOCK:
        _SECRET_VALUES.add(secret)


def mask_secret(secret: str | None) -> str:
    if not secret:
        return ""
    if len(secret) <= 4:
        return "****"
    return f"{'*' * max(len(secret) - 4, 4)}{secret[-4:]}"


def create_client(api_key: str):
    register_secret(api_key)
    from abacusai import ApiClient

    return ApiClient(api_key)


def redact_secrets_from_text(value: str) -> str:
    text = value
    with _SECRET_LOCK:
        for secret in _SECRET_VALUES:
            if secret:
                text = text.replace(secret, "[REDACTED_SECRET]")
    return text


def redact_secrets(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets_from_text(value)
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [redact_secrets(item) for item in value]
    if isinstance(value, dict):
        return {redact_secrets_from_text(str(key)): redact_secrets(item) for key, item in value.items()}
    return value


def safe_error(exc: BaseException) -> str:
    return redact_secrets_from_text(str(exc) or exc.__class__.__name__)


def basic_auth_matches(header: str | None, expected_user: str, expected_password: str) -> bool:
    if not header or not header.lower().startswith("basic "):
        return False
    import base64

    try:
        decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        user, password = decoded.split(":", 1)
    except Exception:
        return False
    return hmac.compare_digest(user, expected_user) and hmac.compare_digest(password, expected_password)
