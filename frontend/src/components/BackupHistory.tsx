import { Download, Eye, RefreshCw, Trash2 } from "lucide-react";
import { useState } from "react";
import type { BackupSummary } from "../types";

interface BackupHistoryProps {
  backups: BackupSummary[];
  onRefresh: () => void;
  onManifest: (backupId: string) => Promise<unknown>;
  onDelete: (backupId: string) => Promise<void>;
}

export default function BackupHistory({ backups, onRefresh, onManifest, onDelete }: BackupHistoryProps) {
  const [manifest, setManifest] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function showManifest(backupId: string) {
    setBusyId(backupId);
    try {
      const data = await onManifest(backupId);
      setManifest(JSON.stringify(data, null, 2));
    } finally {
      setBusyId(null);
    }
  }

  async function deleteItem(backupId: string) {
    if (!window.confirm("Dieses lokale Backup wirklich löschen?")) return;
    setBusyId(backupId);
    try {
      await onDelete(backupId);
      setManifest(null);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section id="backups" className="border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Backup-Historie</h2>
          <p className="mt-1 text-sm text-zinc-600">{backups.length} lokale Backups</p>
        </div>
        <button onClick={onRefresh} className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50">
          <RefreshCw className="h-4 w-4" />
          Aktualisieren
        </button>
      </div>

      <div className="mt-5 divide-y divide-zinc-200 border border-zinc-200">
        {backups.map((backup) => (
          <div key={backup.backup_id} className="grid gap-3 p-4 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <p className="font-semibold text-zinc-900">{backup.backup_id}</p>
              <p className="mt-1 text-sm text-zinc-600">
                {formatDate(backup.created_at)} · Chats: {backup.counts?.processed ?? backup.counts?.total ?? 0} · Fehler: {backup.counts?.failed ?? 0} · {formatSize(backup.size_bytes)}
              </p>
              <p className="mt-1 break-all font-mono text-xs text-zinc-500">{backup.path}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button disabled={busyId === backup.backup_id} onClick={() => showManifest(backup.backup_id)} className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50 disabled:opacity-60">
                <Eye className="h-4 w-4" />
                Manifest
              </button>
              <a href={backup.download_url || `/api/backups/${backup.backup_id}/download`} className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50">
                <Download className="h-4 w-4" />
                ZIP
              </a>
              <button disabled={busyId === backup.backup_id} onClick={() => deleteItem(backup.backup_id)} className="inline-flex items-center gap-2 rounded-md border border-red-300 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-60">
                <Trash2 className="h-4 w-4" />
                Löschen
              </button>
            </div>
          </div>
        ))}
        {!backups.length && <div className="p-8 text-center text-sm text-zinc-500">Noch keine Backups vorhanden.</div>}
      </div>

      {manifest && (
        <div className="mt-5">
          <p className="mb-2 text-sm font-semibold text-zinc-900">Manifest</p>
          <pre className="max-h-96 overflow-auto rounded-md bg-zinc-950 p-4 text-xs text-zinc-100">{manifest}</pre>
        </div>
      )}
    </section>
  );
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function formatSize(value?: number | null): string {
  if (!value) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let current = value;
  let unitIndex = 0;
  while (current >= 1024 && unitIndex < units.length - 1) {
    current /= 1024;
    unitIndex += 1;
  }
  return `${current.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}
