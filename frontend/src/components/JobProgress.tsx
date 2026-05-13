import { Download, Loader2, OctagonX } from "lucide-react";
import { useState } from "react";
import type { BackupJob } from "../types";

interface JobProgressProps {
  job: BackupJob | null;
  onCancel: (jobId: string) => void;
}

export default function JobProgress({ job, onCancel }: JobProgressProps) {
  const [showErrors, setShowErrors] = useState(false);
  if (!job) return null;
  const active = job.status === "queued" || job.status === "running";

  return (
    <section className="border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Job progress</h2>
          <p className="mt-1 text-sm text-zinc-600">Status: {job.status}</p>
        </div>
        {active && (
          <button onClick={() => onCancel(job.job_id)} className="inline-flex items-center justify-center gap-2 rounded-md border border-red-300 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50">
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
      {job.current_item && (
        <p className="mt-3 inline-flex items-center gap-2 text-sm text-zinc-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          {job.current_item}
        </p>
      )}

      {job.errors.length > 0 && (
        <div className="mt-4">
          <button onClick={() => setShowErrors(!showErrors)} className="text-sm font-semibold text-red-700">
            {showErrors ? "Hide" : "Show"} errors ({job.errors.length})
          </button>
          {showErrors && (
            <ul className="mt-2 space-y-2 text-sm text-red-800">
              {job.errors.map((error, index) => (
                <li key={`${error}-${index}`} className="rounded-md bg-red-50 p-2">{error}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {job.status === "completed" && job.result?.download_url && (
        <a href={job.result.download_url} className="mt-5 inline-flex items-center gap-2 rounded-md bg-zinc-950 px-4 py-2 text-sm font-semibold text-white hover:bg-zinc-800">
          <Download className="h-4 w-4" />
          Download ZIP
        </a>
      )}
    </section>
  );
}
