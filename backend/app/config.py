from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .utils import split_env_list


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    backups_dir: Path
    db_path: Path
    secrets_dir: Path
    settings_dir: Path
    api_key_file: Path
    conversation_scopes_file: Path
    static_dir: Path
    allow_ui_api_key: bool
    allow_persistent_api_key: bool
    deployment_ids: list[str]
    external_application_ids: list[str]
    conversation_types: list[str]
    basic_auth_user: str | None
    basic_auth_password: str | None

    @property
    def basic_auth_enabled(self) -> bool:
        return bool(self.basic_auth_user and self.basic_auth_password)

    @property
    def deployment_conversation_scopes(self) -> list[dict[str, str]]:
        scopes: list[dict[str, str]] = []
        scopes.extend({"deployment_id": value} for value in self.deployment_ids)
        scopes.extend({"external_application_id": value} for value in self.external_application_ids)
        scopes.extend({"conversation_type": value} for value in self.conversation_types)
        return scopes

    @property
    def conversation_scope_summary(self) -> dict[str, list[str]]:
        return {
            "deployment_ids": self.deployment_ids,
            "external_application_ids": self.external_application_ids,
            "conversation_types": self.conversation_types,
        }


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    data_dir = Path(os.getenv("APP_DATA_DIR", "/data"))
    return Settings(
        data_dir=data_dir,
        backups_dir=data_dir / "backups",
        db_path=data_dir / "app.db",
        secrets_dir=data_dir / "secrets",
        settings_dir=data_dir / "settings",
        api_key_file=data_dir / "secrets" / "abacus_api_key.local",
        conversation_scopes_file=data_dir / "settings" / "conversation_scopes.json",
        static_dir=Path(os.getenv("APP_STATIC_DIR", "/app/static")),
        allow_ui_api_key=_env_bool("APP_ALLOW_UI_API_KEY", True),
        allow_persistent_api_key=_env_bool("APP_ALLOW_PERSISTENT_API_KEY", True),
        deployment_ids=split_env_list(os.getenv("ABACUS_DEPLOYMENT_IDS")),
        external_application_ids=split_env_list(os.getenv("ABACUS_EXTERNAL_APPLICATION_IDS")),
        conversation_types=split_env_list(os.getenv("ABACUS_CONVERSATION_TYPES")),
        basic_auth_user=os.getenv("APP_BASIC_AUTH_USER") or None,
        basic_auth_password=os.getenv("APP_BASIC_AUTH_PASSWORD") or None,
    )
