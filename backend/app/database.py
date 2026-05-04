from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any

from .models import BackupSummary
from .utils import directory_size, ensure_dir, now_utc_iso, safe_json_dumps, safe_json_loads


class Database:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._lock = RLock()

    def init(self) -> None:
        ensure_dir(self.db_path.parent)
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY,
                  status TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  total INTEGER NOT NULL DEFAULT 0,
                  done INTEGER NOT NULL DEFAULT 0,
                  failed INTEGER NOT NULL DEFAULT 0,
                  current_item TEXT,
                  request_json TEXT NOT NULL,
                  result_json TEXT,
                  errors_json TEXT NOT NULL DEFAULT '[]'
                );

                CREATE TABLE IF NOT EXISTS backups (
                  id TEXT PRIMARY KEY,
                  created_at TEXT NOT NULL,
                  path TEXT NOT NULL,
                  zip_path TEXT,
                  manifest_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS cached_chats (
                  id TEXT NOT NULL,
                  type TEXT NOT NULL,
                  deployment_id TEXT NOT NULL DEFAULT '',
                  title TEXT,
                  created_at TEXT,
                  updated_at TEXT,
                  last_event_created_at TEXT,
                  raw_preview_json TEXT,
                  refreshed_at TEXT NOT NULL,
                  PRIMARY KEY (id, type, deployment_id)
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def mark_interrupted_jobs(self) -> None:
        now = now_utc_iso()
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT id, errors_json FROM jobs WHERE status IN ('queued', 'running')"
            ).fetchall()
            for row in rows:
                errors = safe_json_loads(row["errors_json"], [])
                errors.append("Job wurde durch Container-Neustart oder Prozessende unterbrochen.")
                conn.execute(
                    """
                    UPDATE jobs
                    SET status='failed', updated_at=?, current_item=NULL, errors_json=?
                    WHERE id=?
                    """,
                    (now, safe_json_dumps(errors), row["id"]),
                )

    def create_job(self, job_id: str, request_json: dict[str, Any]) -> None:
        now = now_utc_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, status, created_at, updated_at, request_json, errors_json)
                VALUES (?, 'queued', ?, ?, ?, '[]')
                """,
                (job_id, now, now, safe_json_dumps(request_json)),
            )

    def update_job(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = now_utc_iso()
        json_fields = {"request_json", "result_json", "errors_json"}
        assignments = []
        values = []
        for key, value in fields.items():
            assignments.append(f"{key}=?")
            if key in json_fields and not isinstance(value, str):
                value = safe_json_dumps(value)
            values.append(value)
        values.append(job_id)
        with self._lock, self._connect() as conn:
            conn.execute(f"UPDATE jobs SET {', '.join(assignments)} WHERE id=?", values)

    def append_job_error(self, job_id: str, message: str) -> None:
        row = self.get_job_row(job_id)
        errors = safe_json_loads(row["errors_json"] if row else None, [])
        errors.append(message)
        self.update_job(job_id, errors_json=errors)

    def get_job_row(self, job_id: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        row = self.get_job_row(job_id)
        if not row:
            return None
        total = int(row["total"] or 0)
        done = int(row["done"] or 0)
        percent = int((done / total) * 100) if total else (100 if row["status"] == "completed" else 0)
        return {
            "job_id": row["id"],
            "status": row["status"],
            "progress": {
                "total": total,
                "done": done,
                "failed": int(row["failed"] or 0),
                "percent": max(0, min(100, percent)),
            },
            "current_item": row["current_item"],
            "errors": safe_json_loads(row["errors_json"], []),
            "result": safe_json_loads(row["result_json"], None),
        }

    def insert_backup(
        self,
        backup_id: str,
        created_at: str,
        path: str,
        zip_path: str | None,
        manifest: dict[str, Any],
    ) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO backups (id, created_at, path, zip_path, manifest_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (backup_id, created_at, path, zip_path, safe_json_dumps(manifest)),
            )

    def list_backups(self) -> list[BackupSummary]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM backups ORDER BY created_at DESC").fetchall()
        items: list[BackupSummary] = []
        for row in rows:
            manifest = safe_json_loads(row["manifest_json"], {})
            zip_path = row["zip_path"]
            zip_available = bool(zip_path and Path(zip_path).exists())
            items.append(
                BackupSummary(
                    backup_id=row["id"],
                    created_at=row["created_at"],
                    counts=manifest.get("counts", {}),
                    path=row["path"],
                    zip_available=zip_available,
                    download_url=f"/api/backups/{row['id']}/download",
                    size_bytes=directory_size(row["path"]),
                )
            )
        return items

    def get_backup(self, backup_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM backups WHERE id=?", (backup_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "path": row["path"],
            "zip_path": row["zip_path"],
            "manifest": safe_json_loads(row["manifest_json"], {}),
        }

    def update_backup_zip(self, backup_id: str, zip_path: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("UPDATE backups SET zip_path=? WHERE id=?", (zip_path, backup_id))

    def delete_backup_record(self, backup_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM backups WHERE id=?", (backup_id,))

    def replace_cached_chats(self, items: list[dict[str, Any]]) -> None:
        refreshed_at = now_utc_iso()
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM cached_chats")
            for item in items:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cached_chats
                    (id, type, deployment_id, title, created_at, updated_at, last_event_created_at, raw_preview_json, refreshed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.get("id"),
                        item.get("type"),
                        item.get("deployment_id") or "",
                        item.get("title"),
                        item.get("created_at"),
                        item.get("updated_at"),
                        item.get("last_event_created_at"),
                        safe_json_dumps(item.get("raw_preview") or {}),
                        refreshed_at,
                    ),
                )

    def get_cached_chats(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM cached_chats ORDER BY updated_at DESC, created_at DESC").fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            items.append(
                {
                    "id": row["id"],
                    "type": row["type"],
                    "deployment_id": row["deployment_id"] or None,
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "last_event_created_at": row["last_event_created_at"],
                    "raw_preview": safe_json_loads(row["raw_preview_json"], {}),
                    "exportable": True,
                    "selected": False,
                }
            )
        return items
