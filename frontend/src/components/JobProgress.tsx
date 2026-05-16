import { AlertTriangle, Download, Loader2, OctagonX, RotateCcw } from "lucide-react";
import { useState } from "react";
import type { BackupJob, TimedOutItem } from "../types";

interface JobProgressProps {
  job: BackupJob | null;
  onCancel: (jobId: string) => void;
  onRetry?: (chatIds: string[]) => void;
  retryBusy?: boolean;
}

function canonicalChatId(item: TimedOutItem): string {
  return `${item.type}:${item.deployment_id || ""}:${item.id}`;
}

function stepLabel(step: TimedOutItem["step"]): string {
  if (step === "detail") return "Detail fetch (Abacus API)";
  return "SDK HTML export (Abacus API)";
}

export default function JobProgress({ job, onCancel, onRetry, retryBusy = false }: JobProgressProps) {
  const [showErrors, setShowErrors] = useState(false);
  if (!job) return null;
  const active = job.status === "queued" || job.status === "running";
  const terminal = job.status === "completed" || job.status === "cancelled" || job.status === "failed";

  const timeoutErrors = job.errors.filter((e) => /timeout/i.test(e) || /timed out/i.test(e));
  const skippedCount = timeoutErrors.length;

  const timedOutItems = job.result?.timed_out_items ?? [];
  const retryChatIds = [...new Set(timedOutItems.map(canonicalChatId))];

  return (
    <section className="border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Job progress</h2>
          <p className="mt-1 text-sm text-zinc-600">Status: {job.status}</p>
        </div>
        {active && (
          <button
            onClick={() => onCancel(job.job_id)}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-red-300 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50"
          >
            <OctagonX className="h-4 w-4" />
            Cancel job
          </button>
        )}
      </div>

      <div className="mt-5 h-3 overflow-hidden rounded-md bg-zinc-100">
        <div className="h-full bg-emerald-700 transition-all" style={{ width: `${job.progress.percent}%` }} />
      </div>
      <div className="mt-3 grid gap-2 text-sm text-zinc-700 md:grid-cols-4">
        <span>Done: {job.progress.done}</span>
        <span>Total: {job.progress.total}</span>
        <span>Failed: {job.progress.failed}</span>
        <span>{job.progress.percent}%</span>
      </div>
      {job.current_item && active && (
        <p className="mt-3 inline-flex items-center gap-2 text-sm text-zinc-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          {job.current_item}
        </p>
      )}

      {skippedCount > 0 && active && (
        <div className="mt-4 flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-none text-amber-600" />
          <div className="text-sm text-amber-900">
            <p className="font-semibold">
              {skippedCount} item{skippedCount > 1 ? "s" : ""} skipped due to API timeout
            </p>
            <p className="mt-1 text-amber-700">
              The Abacus API did not respond within the time limit for {skippedCount === 1 ? "this chat" : "these chats"}.
              They were skipped so the rest of the backup can continue.
            </p>
          </div>
        </div>
      )}

      {terminal && timedOutItems.length > 0 && (
        <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-4">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 flex-none text-amber-600" />
            <div className="min-w-0 flex-1 text-sm text-amber-900">
              <p className="font-semibold">
                {timedOutItems.length} item{timedOutItems.length > 1 ? "s" : ""} could not be fully exported (API
                timeout)
              </p>
              <p className="mt-1 text-amber-700">
                These chats were partially exported where possible (for example JSON/Markdown and the conversation
                transcript). The Abacus API did not respond in time for the step listed below.
              </p>
              <ul className="mt-3 space-y-2">
                {timedOutItems.map((item, index) => (
                  <li
                    key={`${canonicalChatId(item)}-${item.step}-${index}`}
                    className="rounded-md bg-amber-100/80 px-3 py-2"
                  >
                    <p className="font-medium text-amber-950">{item.title || item.id}</p>
                    <p className="mt-0.5 font-mono text-xs text-amber-800">
                      {item.type}:{item.deployment_id || "—"}:{item.id}
                    </p>
                    <p className="mt-1 text-xs text-amber-800">{stepLabel(item.step)}</p>
                  </li>
                ))}
              </ul>
              {onRetry && retryChatIds.length > 0 && (
                <button
                  type="button"
                  disabled={retryBusy}
                  onClick={() => onRetry(retryChatIds)}
                  className="mt-4 inline-flex items-center gap-2 rounded-md bg-amber-800 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-900 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <RotateCcw className="h-4 w-4" />
                  Retry timed-out items ({retryChatIds.length})
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {job.errors.length > 0 && (
        <div className="mt-4">
          <button onClick={() => setShowErrors(!showErrors)} className="text-sm font-semibold text-red-700">
            {showErrors ? "Hide" : "Show"} errors ({job.errors.length})
          </button>
          {showErrors && (
            <ul className="mt-2 space-y-2 text-sm text-red-800">
              {job.errors.map((error, index) => (
                <li key={`${error}-${index}`} className="rounded-md bg-red-50 p-2">
                  {error}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {job.status === "completed" && job.result?.download_url && (
        <a
          href={job.result.download_url}
          className="mt-5 inline-flex items-center gap-2 rounded-md bg-zinc-950 px-4 py-2 text-sm font-semibold text-white hover:bg-zinc-800"
        >
          <Download className="h-4 w-4" />
          Download ZIP
        </a>
      )}
    </section>
  );
}
