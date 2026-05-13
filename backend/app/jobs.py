from __future__ import annotations

import asyncio
import threading
import uuid
from pathlib import Path

from .abacus_client import AbacusService
from .backup_engine import run_backup_job
from .database import Database
from .models import BackupJob, ExportRequest
from .security import safe_error


class JobManager:
    def __init__(self, db: Database, data_dir: str | Path, abacus_service: AbacusService) -> None:
        self.db = db
        self.data_dir = Path(data_dir)
        self.abacus_service = abacus_service
        self._cancel_flags: dict[str, threading.Event] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def startup(self) -> None:
        self.db.mark_interrupted_jobs()

    async def start_export(self, request: ExportRequest) -> str:
        job_id = str(uuid.uuid4())
        self.db.create_job(job_id, request.model_dump(mode="json"))
        cancel_event = threading.Event()
        self._cancel_flags[job_id] = cancel_event
        task = asyncio.create_task(self._run(job_id, request, cancel_event))
        self._tasks[job_id] = task
        return job_id

    async def _run(self, job_id: str, request: ExportRequest, cancel_event: threading.Event) -> None:
        try:
            await asyncio.to_thread(run_backup_job, job_id, request, self.abacus_service, self.data_dir, cancel_event)
        except Exception as exc:
            self.db.append_job_error(job_id, f"Job runtime error: {safe_error(exc)}")
            self.db.update_job(job_id, status="failed", current_item=None)
        finally:
            self._cancel_flags.pop(job_id, None)
            self._tasks.pop(job_id, None)

    def get_job(self, job_id: str) -> BackupJob | None:
        data = self.db.get_job(job_id)
        if not data:
            return None
        return BackupJob(**data)

    def cancel_job(self, job_id: str) -> bool:
        row = self.db.get_job(job_id)
        if not row:
            return False
        flag = self._cancel_flags.get(job_id)
        if flag:
            flag.set()
        if row["status"] in {"queued", "running"}:
            self.db.update_job(job_id, status="cancelled", current_item=None)
        return True
