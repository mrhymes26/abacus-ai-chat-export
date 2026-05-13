from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from starlette.status import HTTP_401_UNAUTHORIZED

from .abacus_client import AbacusService
from .config import get_settings
from .database import Database
from .exporters import create_backup_zip
from .local_settings import (
    has_supported_conversation_scope,
    merge_scope_summaries,
    read_conversation_scopes,
    summary_to_query_scopes,
    write_conversation_scopes,
)
from .models import (
    APP_NAME,
    APP_VERSION,
    BackupListResponse,
    ChatItem,
    ChatListResponse,
    ConnectRequest,
    ConnectionResult,
    ConversationScopes,
    ExportRequest,
    ExportStartResponse,
    StatusResponse,
)
from .security import (
    basic_auth_matches,
    delete_stored_api_key,
    get_api_key_from_env,
    get_api_key_from_file,
    has_stored_api_key,
    safe_error,
    store_api_key_locally,
)
from .utils import ensure_dir


settings = get_settings()
db = Database(settings.db_path)
abacus_service = AbacusService()


app = FastAPI(title=APP_NAME)
job_manager = None


@app.middleware("http")
async def optional_basic_auth(request: Request, call_next):
    if settings.basic_auth_enabled:
        if not basic_auth_matches(
            request.headers.get("authorization"),
            settings.basic_auth_user or "",
            settings.basic_auth_password or "",
        ):
            return Response(
                status_code=HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": "Basic"},
                content="Authentication required",
            )
    return await call_next(request)


@app.on_event("startup")
async def startup() -> None:
    global job_manager
    ensure_dir(settings.data_dir)
    ensure_dir(settings.backups_dir)
    ensure_dir(settings.secrets_dir)
    ensure_dir(settings.settings_dir)
    db.init()
    from .jobs import JobManager

    job_manager = JobManager(db, settings.data_dir, abacus_service)
    job_manager.startup()


@app.get("/api/health")
async def health() -> dict[str, object]:
    return {"ok": True, "app": APP_NAME, "version": APP_VERSION}


@app.post("/api/connect", response_model=ConnectionResult)
async def connect(payload: ConnectRequest | None = Body(default=None)) -> ConnectionResult:
    payload = payload or ConnectRequest()
    api_key = payload.api_key.strip() if payload.api_key else None
    if api_key and not settings.allow_ui_api_key:
        raise HTTPException(status_code=403, detail="UI API key entry is disabled.")
    if payload.remember_locally and not api_key:
        raise HTTPException(status_code=400, detail="remember_locally can only be used together with a UI API key.")
    if payload.remember_locally and not settings.allow_persistent_api_key:
        raise HTTPException(status_code=403, detail="Persistent API key storage is disabled.")
    try:
        result = abacus_service.connect_with_fallback(
            api_key=api_key,
            fallback_api_key=get_api_key_from_file(settings.api_key_file),
            fallback_source="stored",
        )
        if api_key and payload.remember_locally:
            store_api_key_locally(api_key, settings.api_key_file)
            result.persisted = True
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=safe_error(exc)) from exc


@app.get("/api/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    _try_connect_silently()
    stored_scopes = read_conversation_scopes(settings.conversation_scopes_file).model_dump(mode="json")
    merged_scopes = merge_scope_summaries(settings.conversation_scope_summary, stored_scopes)
    if abacus_service.connected and not has_supported_conversation_scope(merged_scopes):
        try:
            abacus_service.discover_conversation_scopes()
            merged_scopes = merge_scope_summaries(merged_scopes, abacus_service.discovered_conversation_scope_summary())
        except Exception:
            pass
    return StatusResponse(
        has_env_api_key=bool(get_api_key_from_env()),
        has_stored_api_key=has_stored_api_key(settings.api_key_file),
        allow_persistent_api_key=settings.allow_persistent_api_key,
        connected=abacus_service.connected,
        deployment_ids=settings.deployment_ids,
        conversation_scopes=merged_scopes,
        stored_conversation_scopes=stored_scopes,
        data_dir=str(settings.data_dir),
    )


@app.delete("/api/api-key")
async def forget_stored_api_key() -> dict[str, bool]:
    deleted = delete_stored_api_key(settings.api_key_file)
    return {"deleted": deleted}


@app.get("/api/conversation-scopes", response_model=ConversationScopes)
async def get_conversation_scopes() -> ConversationScopes:
    return read_conversation_scopes(settings.conversation_scopes_file)


@app.put("/api/conversation-scopes", response_model=ConversationScopes)
async def put_conversation_scopes(scopes: ConversationScopes) -> ConversationScopes:
    return write_conversation_scopes(settings.conversation_scopes_file, scopes)


@app.get("/api/chats", response_model=ChatListResponse)
async def list_chats(
    include_ai_chat: bool = Query(True),
    include_deployments: bool = Query(True),
    refresh: bool = Query(False),
) -> ChatListResponse:
    cached = [] if refresh else db.get_cached_chats()
    if cached:
        items = [ChatItem(**item) for item in cached]
        items = _filter_items(items, include_ai_chat, include_deployments)
        return ChatListResponse(items=items, counts=_counts(items), warnings=["Loaded from local cache."])

    _ensure_connected()
    try:
        items = abacus_service.list_all_chats(
            include_ai_chat=include_ai_chat,
            include_deployments=include_deployments,
            deployment_ids=settings.deployment_ids or None,
            conversation_scopes=_conversation_query_scopes(),
        )
        db.replace_cached_chats([item.model_dump(mode="json") for item in items])
        return ChatListResponse(items=items, counts=_counts(items), warnings=abacus_service.last_warnings)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=safe_error(exc)) from exc


@app.post("/api/export", response_model=ExportStartResponse)
async def start_export(request: ExportRequest) -> ExportStartResponse:
    if request.mode == "selected" and not request.chat_ids:
        raise HTTPException(status_code=400, detail="For mode=selected, chat_ids must be provided.")
    if not request.formats:
        raise HTTPException(status_code=400, detail="Select at least one export format.")
    _ensure_connected()
    manager = _job_manager()
    job_id = await manager.start_export(request)
    return ExportStartResponse(job_id=job_id)


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = _job_manager().get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict[str, bool]:
    cancelled = _job_manager().cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"cancelled": True}


@app.get("/api/backups", response_model=BackupListResponse)
async def list_backups() -> BackupListResponse:
    return BackupListResponse(items=db.list_backups())


@app.get("/api/backups/{backup_id}/manifest")
async def get_manifest(backup_id: str):
    backup = _backup_or_404(backup_id)
    manifest_path = Path(backup["path"]) / "manifest.json"
    if manifest_path.exists():
        return JSONResponse(content=_read_json_file(manifest_path))
    return JSONResponse(content=backup["manifest"])


@app.get("/api/backups/{backup_id}/download")
async def download_backup(backup_id: str):
    backup = _backup_or_404(backup_id)
    backup_path = _safe_backup_path(backup["path"])
    zip_path = Path(backup.get("zip_path") or backup_path / "backup.zip")
    if not zip_path.exists():
        zip_path = create_backup_zip(backup_path)
        db.update_backup_zip(backup_id, str(zip_path))
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"{backup_id}.zip",
    )


@app.delete("/api/backups/{backup_id}")
async def delete_backup(backup_id: str, confirm: bool = Query(False)) -> dict[str, bool]:
    if not confirm:
        raise HTTPException(status_code=400, detail="Delete requires ?confirm=true.")
    backup = _backup_or_404(backup_id)
    backup_path = _safe_backup_path(backup["path"])
    if backup_path.exists():
        shutil.rmtree(backup_path)
    db.delete_backup_record(backup_id)
    return {"deleted": True}


def _ensure_connected() -> None:
    if abacus_service.connected:
        return
    try:
        abacus_service.connect_with_fallback(
            None,
            fallback_api_key=get_api_key_from_file(settings.api_key_file),
            fallback_source="stored",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=safe_error(exc)) from exc


def _try_connect_silently() -> None:
    if abacus_service.connected:
        return
    if not get_api_key_from_env() and not has_stored_api_key(settings.api_key_file):
        return
    try:
        abacus_service.connect_with_fallback(
            None,
            fallback_api_key=get_api_key_from_file(settings.api_key_file),
            fallback_source="stored",
        )
    except Exception:
        return


def _conversation_scope_summary() -> dict[str, list[str]]:
    stored = read_conversation_scopes(settings.conversation_scopes_file).model_dump(mode="json")
    return merge_scope_summaries(settings.conversation_scope_summary, stored)


def _conversation_query_scopes() -> list[dict[str, str]]:
    return summary_to_query_scopes(_conversation_scope_summary())


def _job_manager():
    if job_manager is None:
        raise HTTPException(status_code=503, detail="Job manager is not ready yet.")
    return job_manager


def _counts(items: list[ChatItem]) -> dict[str, int]:
    ai = sum(1 for item in items if item.type == "ai_chat")
    deployments = sum(1 for item in items if item.type == "deployment_conversation")
    return {"ai_chat": ai, "deployment_conversation": deployments, "total": len(items)}


def _filter_items(items: list[ChatItem], include_ai_chat: bool, include_deployments: bool) -> list[ChatItem]:
    return [
        item
        for item in items
        if (include_ai_chat and item.type == "ai_chat")
        or (include_deployments and item.type == "deployment_conversation")
    ]


def _backup_or_404(backup_id: str) -> dict:
    backup = db.get_backup(backup_id)
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found.")
    _safe_backup_path(backup["path"])
    return backup


def _safe_backup_path(path: str | Path) -> Path:
    candidate = Path(path).resolve()
    root = settings.backups_dir.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid backup path.") from exc
    return candidate


def _read_json_file(path: Path) -> dict:
    import json

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


if settings.static_dir.exists():
    assets_dir = settings.static_dir / "assets"
    if assets_dir.exists():
        from fastapi.staticfiles import StaticFiles

        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        requested = (settings.static_dir / full_path).resolve()
        static_root = settings.static_dir.resolve()
        if requested.exists() and requested.is_file():
            try:
                requested.relative_to(static_root)
            except ValueError:
                raise HTTPException(status_code=404, detail="Not found")
            return FileResponse(requested)
        return FileResponse(settings.static_dir / "index.html")
