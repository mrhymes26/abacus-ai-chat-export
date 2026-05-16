from __future__ import annotations

import concurrent.futures
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

DETAIL_TIMEOUT_SECONDS = 120

T = TypeVar("T")


def _call_with_timeout(func: Callable[..., T], *args: Any, timeout: int = DETAIL_TIMEOUT_SECONDS) -> T:
    """Run a blocking SDK call with a timeout.

    Important: ThreadPoolExecutor context managers call shutdown(wait=True) on exit,
    which would block forever if the worker thread is stuck on a hung API call.
    On timeout we shut down with wait=False so the backup job can continue.
    """
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = pool.submit(func, *args)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        pool.shutdown(wait=True)

from .abacus_client import AbacusService
from .config import get_settings
from .database import Database
from .exporters import (
    conversation_export_stats,
    create_backup_zip,
    extract_messages_to_markdown,
    to_openwebui_chat,
    write_backup_index_html,
    write_conversation_readout_html,
    write_export_result,
    write_json,
    write_markdown,
    write_openwebui_import,
)
from .local_settings import merge_scope_summaries, read_conversation_scopes, summary_to_query_scopes
from .models import APP_NAME, APP_VERSION, ChatItem, ExportRequest
from .security import safe_error
from .utils import ensure_dir, now_utc_iso, relative_posix, safe_filename, short_id


def run_backup_job(
    job_id: str,
    request: ExportRequest,
    abacus_service: AbacusService,
    data_dir: str | Path,
    cancel_event: threading.Event | None = None,
) -> None:
    data_root = Path(data_dir)
    db = Database(data_root / "app.db")
    db.init()
    created_at = now_utc_iso()
    backup_id = f"abacus_{created_at[:19].replace(':', '-').replace('T', '_')}_{short_id(job_id)}"
    backup_dir = data_root / "backups" / backup_id
    ai_dir = backup_dir / "ai_chat_sessions"
    deployment_dir = backup_dir / "deployment_conversations"
    errors: list[str] = []
    timed_out_items: list[dict[str, Any]] = []
    manifest_items: list[dict[str, Any]] = []
    openwebui_chats: list[dict[str, Any]] = []

    try:
        ensure_dir(ai_dir)
        ensure_dir(deployment_dir)
        errors_log = backup_dir / "errors.log"
        errors_log.write_text("", encoding="utf-8")
        db.update_job(job_id, status="running", current_item="Loading chats")

        items = _resolve_items(request, abacus_service)
        db.update_job(job_id, total=len(items), done=0, failed=0)

        done = 0
        failed = 0
        for item in items:
            if cancel_event and cancel_event.is_set():
                break
            db.update_job(job_id, current_item=f"{item.type}:{item.id}")
            item_files: list[Path] = []
            item_errors: list[str] = []
            path_base = _path_base_for_item(item, ai_dir if item.type == "ai_chat" else deployment_dir)
            detail: Any = item.raw_preview or {}

            try:
                detail = _call_with_timeout(abacus_service.get_chat_detail, item)
            except concurrent.futures.TimeoutError:
                item_errors.append(
                    f"{item.type}:{item.id}: Failed to fetch detail: "
                    f"Timeout after {DETAIL_TIMEOUT_SECONDS}s — skipping this item."
                )
                timed_out_items.append(_timed_out_record(item, "detail"))
            except Exception as exc:
                item_errors.append(f"{item.type}:{item.id}: Failed to fetch detail: {safe_error(exc)}")
            export_stats = conversation_export_stats(detail)
            if export_stats.get("complete_by_total_events") is False:
                item_errors.append(
                    f"{item.type}:{item.id}: History may be incomplete "
                    f"(history_items={export_stats.get('history_items')}, total_events={export_stats.get('total_events')})."
                )

            if "json" in request.formats:
                try:
                    item_files.append(write_json(path_base.with_suffix(".json"), detail))
                except Exception as exc:
                    item_errors.append(f"{item.type}:{item.id}: JSON export failed: {safe_error(exc)}")

            if "markdown" in request.formats:
                try:
                    markdown = extract_messages_to_markdown(detail, item.title, item.type, item.id)
                    item_files.append(write_markdown(path_base.with_suffix(".md"), markdown))
                except Exception as exc:
                    item_errors.append(f"{item.type}:{item.id}: Markdown export failed: {safe_error(exc)}")

            if "openwebui" in request.formats:
                try:
                    openwebui_chat = to_openwebui_chat(
                        detail,
                        title=item.title,
                        source_type=item.type,
                        source_id=item.id,
                        deployment_id=item.deployment_id,
                    )
                    openwebui_chats.append(openwebui_chat)
                    item_files.append(
                        write_openwebui_import(
                            path_base.with_name(path_base.name + "_openwebui.json"),
                            [openwebui_chat],
                        )
                    )
                except Exception as exc:
                    item_errors.append(f"{item.type}:{item.id}: Open WebUI conversion failed: {safe_error(exc)}")

            if "html" in request.formats:
                # Nur Format „HTML“: ein einziges druckfähiges Konversationsdokument — ohne SDK-Roh-Export
                conversation_only = set(request.formats) == {"html"}
                # Transcript first (local, from detail already fetched) — do not block on SDK export_deployment_conversation
                try:
                    item_files.append(
                        write_conversation_readout_html(
                            path_base.with_name(path_base.name + "_Konversation.html"),
                            detail,
                            title=item.title,
                            source_type=item.type,
                            source_id=item.id,
                            deployment_id=item.deployment_id,
                            conversation_only_export=conversation_only,
                        )
                    )
                except Exception as exc:
                    item_errors.append(f"{item.type}:{item.id}: Conversation HTML (readout) failed: {safe_error(exc)}")
                if not conversation_only:
                    try:
                        export_result = _call_with_timeout(abacus_service.export_chat_html, item)
                        item_files.extend(write_export_result(export_result, path_base.with_name(path_base.name + "_html")))
                    except concurrent.futures.TimeoutError:
                        item_errors.append(
                            f"{item.type}:{item.id}: HTML export timed out after {DETAIL_TIMEOUT_SECONDS}s — skipped."
                        )
                        timed_out_items.append(_timed_out_record(item, "html_export"))
                    except AttributeError as exc:
                        item_errors.append(f"{item.type}:{item.id}: HTML export not available: {safe_error(exc)}")
                    except Exception as exc:
                        item_errors.append(f"{item.type}:{item.id}: HTML export failed: {safe_error(exc)}")

            if not item_files:
                failed += 1
            errors.extend(item_errors)
            manifest_items.append(
                {
                    "id": item.id,
                    "type": item.type,
                    "deployment_id": item.deployment_id,
                    "title": item.title,
                    "files": [relative_posix(path, backup_dir) for path in item_files],
                    "export_stats": export_stats,
                    "errors": item_errors,
                }
            )
            done += 1
            db.update_job(job_id, done=done, failed=failed, errors_json=errors)

        final_status = "cancelled" if cancel_event and cancel_event.is_set() else "completed"
        counts = _manifest_counts(manifest_items)
        counts["total"] = len(items)
        counts["processed"] = done
        counts["failed"] = failed
        manifest = {
            "backup_id": backup_id,
            "created_at": created_at,
            "app": APP_NAME,
            "app_version": APP_VERSION,
            "request": request.model_dump(mode="json"),
            "counts": counts,
            "items": manifest_items,
            "errors": errors,
            "timed_out_items": timed_out_items,
            "index_html": "index.html",
        }
        if "openwebui" in request.formats and openwebui_chats:
            openwebui_path = write_openwebui_import(backup_dir / "openwebui_import.json", openwebui_chats)
            manifest["openwebui_import"] = relative_posix(openwebui_path, backup_dir)
            manifest["counts"]["openwebui_chats"] = len(openwebui_chats)
        write_json(backup_dir / "manifest.json", manifest)
        errors_log.write_text("\n".join(errors) + ("\n" if errors else ""), encoding="utf-8")
        write_backup_index_html(manifest, backup_dir)

        zip_path: Path | None = None
        if request.zip:
            zip_path = create_backup_zip(backup_dir)

        db.insert_backup(
            backup_id=backup_id,
            created_at=created_at,
            path=str(backup_dir),
            zip_path=str(zip_path) if zip_path else None,
            manifest=manifest,
        )
        result = {
            "backup_id": backup_id,
            "backup_path": str(backup_dir),
            "zip_path": str(zip_path) if zip_path else None,
            "download_url": f"/api/backups/{backup_id}/download",
            "timed_out_items": timed_out_items,
        }
        db.update_job(job_id, status=final_status, current_item=None, result_json=result, errors_json=errors)
    except Exception as exc:
        errors.append(f"Backup job could not be started or completed: {safe_error(exc)}")
        db.update_job(job_id, status="failed", current_item=None, errors_json=errors)


def _resolve_items(request: ExportRequest, abacus_service: AbacusService) -> list[ChatItem]:
    include_ai = "ai_chat" in request.types
    include_deployments = "deployment_conversation" in request.types
    settings = get_settings()
    stored_scope_summary = read_conversation_scopes(settings.conversation_scopes_file).model_dump(mode="json")
    merged_scope_summary = merge_scope_summaries(settings.conversation_scope_summary, stored_scope_summary)
    items = abacus_service.list_all_chats(
        include_ai_chat=include_ai,
        include_deployments=include_deployments,
        deployment_ids=request.deployment_ids or settings.deployment_ids or None,
        conversation_scopes=_request_conversation_scopes(request) or summary_to_query_scopes(merged_scope_summary),
    )
    if request.mode == "all":
        return [item for item in items if item.exportable]

    wanted = set(request.chat_ids)
    if not wanted:
        return []
    selected: list[ChatItem] = []
    for item in items:
        # Nur noch kanonischer Schlüssel wie im Frontend (chatSelectionKey):
        # type + ":" + (deployment_id oder "") + ":" + id.
        # NICHT item.id allein matchen — dieselbe ID kann in mehreren Deployments/Scopes vorkommen,
        # dann würde eine Einzelauswahl fälschlich alle Treffer exportieren.
        canonical = f"{item.type}:{item.deployment_id or ''}:{item.id}"
        if canonical in wanted and item.exportable:
            selected.append(item)
    return selected


def _request_conversation_scopes(request: ExportRequest) -> list[dict[str, str]]:
    scopes: list[dict[str, str]] = []
    scopes.extend({"deployment_id": value} for value in request.deployment_ids if value)
    scopes.extend({"external_application_id": value} for value in request.external_application_ids if value)
    scopes.extend({"conversation_type": value} for value in request.conversation_types if value)
    return scopes


def _timed_out_record(item: ChatItem, step: str) -> dict[str, Any]:
    return {
        "id": item.id,
        "type": item.type,
        "title": item.title,
        "deployment_id": item.deployment_id,
        "step": step,
    }


def _path_base_for_item(item: ChatItem, directory: Path) -> Path:
    title = item.title or item.id
    filename = f"{safe_filename(title, fallback=item.type)}_{short_id(item.id)}"
    return directory / filename


def _manifest_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"ai_chat": 0, "deployment_conversation": 0}
    for item in items:
        item_type = item.get("type")
        if item_type in counts:
            counts[item_type] += 1
    return counts
