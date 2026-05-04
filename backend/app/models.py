from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


APP_NAME = "Abacus Backup Chat Export Manager"

ChatType = Literal["ai_chat", "deployment_conversation"]
ExportFormat = Literal["json", "html", "markdown"]
ExportMode = Literal["selected", "all"]
JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class ConnectRequest(BaseModel):
    api_key: str | None = None
    remember_locally: bool = False


class ConnectionResult(BaseModel):
    connected: bool
    source: Literal["ui", "env", "stored", "none"] = "none"
    persisted: bool = False
    available_methods: list[str] = Field(default_factory=list)
    missing_methods: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StatusResponse(BaseModel):
    has_env_api_key: bool
    has_stored_api_key: bool
    allow_persistent_api_key: bool
    connected: bool
    deployment_ids: list[str] = Field(default_factory=list)
    conversation_scopes: dict[str, list[str]] = Field(default_factory=dict)
    stored_conversation_scopes: dict[str, list[str]] = Field(default_factory=dict)
    data_dir: str


class ChatItem(BaseModel):
    id: str
    type: ChatType
    deployment_id: str | None = None
    title: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    last_event_created_at: str | None = None
    message_count: int | None = None
    raw_preview: dict[str, Any] | None = None
    exportable: bool = True
    selected: bool = False


class ChatListResponse(BaseModel):
    items: list[ChatItem]
    counts: dict[str, int]
    warnings: list[str] = Field(default_factory=list)


class ConversationScopes(BaseModel):
    deployment_ids: list[str] = Field(default_factory=list)
    external_application_ids: list[str] = Field(default_factory=list)
    conversation_types: list[str] = Field(default_factory=list)

    @field_validator(
        "deployment_ids",
        "external_application_ids",
        "conversation_types",
        mode="before",
    )
    @classmethod
    def normalize_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            import re

            return [part.strip() for part in re.split(r"[\s,;]+", value) if part.strip()]
        if isinstance(value, list):
            return [str(part).strip() for part in value if str(part).strip()]
        return []


class ExportRequest(BaseModel):
    mode: ExportMode
    chat_ids: list[str] = Field(default_factory=list)
    types: list[ChatType] = Field(default_factory=lambda: ["ai_chat", "deployment_conversation"])
    formats: list[ExportFormat] = Field(default_factory=lambda: ["json", "markdown", "html"])
    deployment_ids: list[str] = Field(default_factory=list)
    external_application_ids: list[str] = Field(default_factory=list)
    conversation_types: list[str] = Field(default_factory=list)
    zip: bool = True

    @field_validator(
        "chat_ids",
        "types",
        "formats",
        "deployment_ids",
        "external_application_ids",
        "conversation_types",
        mode="before",
    )
    @classmethod
    def none_to_empty_list(cls, value: Any) -> Any:
        if value is None:
            return []
        return value


class ExportStartResponse(BaseModel):
    job_id: str


class JobProgress(BaseModel):
    total: int = 0
    done: int = 0
    failed: int = 0
    percent: int = 0


class BackupJob(BaseModel):
    job_id: str
    status: JobStatus
    progress: JobProgress
    current_item: str | None = None
    errors: list[str] = Field(default_factory=list)
    result: dict[str, Any] | None = None


class BackupManifest(BaseModel):
    backup_id: str
    created_at: str
    app: str = APP_NAME
    request: dict[str, Any] = Field(default_factory=dict)
    counts: dict[str, int] = Field(default_factory=dict)
    items: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class BackupSummary(BaseModel):
    backup_id: str
    created_at: str
    counts: dict[str, int] = Field(default_factory=dict)
    path: str
    zip_available: bool = False
    download_url: str | None = None
    size_bytes: int | None = None


class BackupListResponse(BaseModel):
    items: list[BackupSummary]


class ExportResult(BaseModel):
    ok: bool = True
    data: Any = None
    content_type: str | None = None
    filename: str | None = None
