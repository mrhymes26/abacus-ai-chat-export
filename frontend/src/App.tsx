import { useCallback, useEffect, useMemo, useState } from "react";
import {
  cancelJob,
  connect as connectApi,
  deleteBackup,
  forgetStoredApiKey,
  getConversationScopes,
  getJob,
  getManifest,
  getStatus,
  listBackups,
  listChats,
  saveConversationScopes,
  startExport
} from "./api";
import ApiKeyPanel from "./components/ApiKeyPanel";
import BackupHistory from "./components/BackupHistory";
import ChatTable from "./components/ChatTable";
import ConnectionStatus from "./components/ConnectionStatus";
import ConversationScopesPanel from "./components/ConversationScopesPanel";
import ExportPanel from "./components/ExportPanel";
import JobProgress from "./components/JobProgress";
import Layout, { AppView } from "./components/Layout";
import Toast from "./components/Toast";
import type {
  BackupJob,
  BackupSummary,
  ChatItem,
  ConnectionResult,
  ConversationScopes,
  ExportFormat,
  ExportMode,
  StatusResponse,
  ToastMessage
} from "./types";

const terminalStatuses = new Set(["completed", "failed", "cancelled"]);

export default function App() {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [connection, setConnection] = useState<ConnectionResult | null>(null);
  const [conversationScopes, setConversationScopes] = useState<ConversationScopes | null>(null);
  const [chats, setChats] = useState<ChatItem[]>([]);
  const [chatWarnings, setChatWarnings] = useState<string[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [job, setJob] = useState<BackupJob | null>(null);
  const [backups, setBackups] = useState<BackupSummary[]>([]);
  const [loadingChats, setLoadingChats] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [activeView, setActiveView] = useState<AppView>("chats");

  const addToast = useCallback((type: ToastMessage["type"], message: string) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((current) => [...current, { id, type, message }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 5200);
  }, []);

  const refreshStatus = useCallback(async () => {
    const data = await getStatus();
    setStatus(data);
  }, []);

  const refreshBackups = useCallback(async () => {
    const data = await listBackups();
    setBackups(data.items);
  }, []);

  const refreshConversationScopes = useCallback(async () => {
    const data = await getConversationScopes();
    setConversationScopes(data);
  }, []);

  useEffect(() => {
    void refreshStatus().catch((exc) => addToast("error", exc instanceof Error ? exc.message : "Status konnte nicht geladen werden."));
    void refreshBackups().catch((exc) => addToast("error", exc instanceof Error ? exc.message : "Backups konnten nicht geladen werden."));
    void refreshConversationScopes().catch((exc) => addToast("error", exc instanceof Error ? exc.message : "Conversation Scopes konnten nicht geladen werden."));
  }, [addToast, refreshBackups, refreshConversationScopes, refreshStatus]);

  useEffect(() => {
    if (!job || terminalStatuses.has(job.status)) return;
    let stopped = false;
    const interval = window.setInterval(() => {
      void getJob(job.job_id)
        .then(async (next) => {
          if (stopped) return;
          setJob(next);
          if (terminalStatuses.has(next.status)) {
            window.clearInterval(interval);
            await refreshBackups();
            addToast(next.status === "completed" ? "success" : "info", `Export-Job ${next.status}.`);
          }
        })
        .catch((exc) => addToast("error", exc instanceof Error ? exc.message : "Job-Status konnte nicht geladen werden."));
    }, 1000);
    return () => {
      stopped = true;
      window.clearInterval(interval);
    };
  }, [addToast, job, refreshBackups]);

  const selectedCount = useMemo(() => selectedIds.size, [selectedIds]);
  const exporting = Boolean(job && !terminalStatuses.has(job.status));

  async function handleConnect(apiKey?: string, rememberLocally = false) {
    const result = await connectApi(apiKey, rememberLocally);
    setConnection(result);
    await refreshStatus();
    addToast("success", result.persisted ? "Abacus.AI Verbindung steht, API-Key wurde lokal gespeichert." : "Abacus.AI Verbindung steht.");
  }

  async function handleForgetStoredKey() {
    await forgetStoredApiKey();
    await refreshStatus();
    addToast("success", "Lokal gespeicherter API-Key geloescht.");
  }

  async function handleSaveConversationScopes(scopes: ConversationScopes) {
    const saved = await saveConversationScopes(scopes);
    setConversationScopes(saved);
    await refreshStatus();
    addToast("success", "Conversation Scopes gespeichert.");
  }

  async function loadChats(refresh = false) {
    setLoadingChats(true);
    try {
      const latestStatus = await getStatus();
      setStatus(latestStatus);
      const result = await listChats(refresh, true);
      setChats(result.items);
      setChatWarnings(result.warnings || []);
      setSelectedIds(new Set());
      addToast("success", `${result.items.length} Chats geladen.`);
    } catch (exc) {
      addToast("error", exc instanceof Error ? exc.message : "Chats konnten nicht geladen werden.");
      throw exc;
    } finally {
      setLoadingChats(false);
    }
  }

  async function handleStartExport(mode: ExportMode, formats: ExportFormat[], zip: boolean) {
    try {
      const result = await startExport({
        mode,
        chatIds: mode === "selected" ? [...selectedIds] : [],
        formats,
        zip
      });
      const nextJob = await getJob(result.job_id);
      setJob(nextJob);
      addToast("success", "Export-Job gestartet.");
    } catch (exc) {
      addToast("error", exc instanceof Error ? exc.message : "Export konnte nicht gestartet werden.");
      throw exc;
    }
  }

  async function handleCancel(jobId: string) {
    try {
      await cancelJob(jobId);
      const nextJob = await getJob(jobId);
      setJob(nextJob);
      addToast("info", "Job-Abbruch angefordert.");
    } catch (exc) {
      addToast("error", exc instanceof Error ? exc.message : "Job konnte nicht abgebrochen werden.");
    }
  }

  async function handleDeleteBackup(backupId: string) {
    await deleteBackup(backupId);
    await refreshBackups();
    addToast("success", "Backup gelöscht.");
  }

  return (
    <>
      <Layout status={status} activeView={activeView} onViewChange={setActiveView}>
        <div className="border border-zinc-200 bg-white p-4 shadow-sm lg:hidden">
          <p className="text-sm font-semibold uppercase text-emerald-700">Abacus Backup</p>
          <h1 className="mt-1 text-2xl font-semibold">Chat Export Manager</h1>
        </div>

        {activeView === "chats" && (
          <>
            <ChatTable
              items={chats}
              warnings={chatWarnings}
              selectedIds={selectedIds}
              onSelectionChange={setSelectedIds}
              onLoad={() => void loadChats(false)}
              onRefresh={() => void loadChats(true)}
              loading={loadingChats}
            />
            <ExportPanel selectedCount={selectedCount} busy={exporting} onStart={handleStartExport} />
            <JobProgress job={job} onCancel={handleCancel} />
          </>
        )}

        {activeView === "backups" && (
          <BackupHistory backups={backups} onRefresh={() => void refreshBackups()} onManifest={getManifest} onDelete={handleDeleteBackup} />
        )}

        {activeView === "settings" && (
          <section id="settings" className="grid gap-6">
            <div className="border border-zinc-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-semibold uppercase text-emerald-700">Einstellungen</p>
              <h2 className="mt-1 text-xl font-semibold">Verbindung und Scopes</h2>
              <p className="mt-2 text-sm text-zinc-600">
                API-Key, SDK-Status und Conversation-Scopes sind hier gebündelt, damit die Arbeitsansicht kompakt bleibt.
              </p>
            </div>
            <ApiKeyPanel
              status={status}
              connection={connection}
              onConnect={handleConnect}
              onForgetStoredKey={handleForgetStoredKey}
            />
            <ConnectionStatus status={status} connection={connection} />
            <ConversationScopesPanel status={status} scopes={conversationScopes} onSave={handleSaveConversationScopes} />
          </section>
        )}
      </Layout>
      <Toast messages={toasts} onDismiss={(id) => setToasts((current) => current.filter((toast) => toast.id !== id))} />
    </>
  );
}
