import { Archive, FileCode2, FileJson, FileText, PackageCheck, Upload } from "lucide-react";
import { useState } from "react";
import type { ExportFormat, ExportMode } from "../types";

interface ExportPanelProps {
  selectedCount: number;
  busy: boolean;
  onStart: (mode: ExportMode, formats: ExportFormat[], zip: boolean) => Promise<void>;
}

const formatOptions: Array<{ value: ExportFormat; label: string; icon: typeof FileJson }> = [
  { value: "json", label: "JSON", icon: FileJson },
  { value: "markdown", label: "Markdown", icon: FileText },
  { value: "html", label: "HTML", icon: FileCode2 },
  { value: "openwebui", label: "Open WebUI", icon: Upload }
];

export default function ExportPanel({ selectedCount, busy, onStart }: ExportPanelProps) {
  const [formats, setFormats] = useState<Set<ExportFormat>>(new Set(["json", "markdown", "html"]));
  const [mode, setMode] = useState<ExportMode>("selected");
  const [zip, setZip] = useState(true);

  function toggleFormat(format: ExportFormat) {
    const next = new Set(formats);
    if (next.has(format)) next.delete(format);
    else next.add(format);
    setFormats(next);
  }

  const disabled = busy || formats.size === 0 || (mode === "selected" && selectedCount === 0);

  return (
    <section className="border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <PackageCheck className="h-5 w-5 text-emerald-700" />
        <h2 className="text-lg font-semibold">Export</h2>
      </div>
      <p className="mt-2 text-sm text-zinc-600">Backups contain confidential chat content.</p>

      <div className="mt-4 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-700">
        <p className="font-medium text-zinc-900">How it works</p>
        <p className="mt-1">
          After you click export, a <strong>server job</strong> runs: for each chat, the selected formats are written as{" "}
          <strong>separate files</strong> into a new backup folder (plus <span className="font-mono text-xs">manifest.json</span> and optionally{" "}
          <span className="font-mono text-xs">errors.log</span>).
        </p>
        <p className="mt-2">
          If <strong>Create ZIP</strong> is enabled, a <span className="font-mono text-xs">backup.zip</span> file is built
          <strong> at the end of the job</strong> in the backup folder. The ZIP is an archive of the same files (no extra export pass). If the option is off, only individual files are written; a click on <strong>Download</strong> in the history creates the ZIP on first download if needed.
        </p>
        <p className="mt-2 text-zinc-600">
          <strong>Export all</strong> processes every <em>exportable</em> chat in the loaded list (regardless of checkboxes). <strong>Export selection</strong> only the checked rows.
        </p>
        <p className="mt-2 text-zinc-600">
          Enable <strong>HTML only</strong> (deselect other formats): one file per chat{" "}
          <span className="font-mono text-xs">*_Konversation.html</span> — no extra SDK artifacts, tuned for{" "}
          <strong>Save as PDF or print</strong> in the browser (A4 print layout; note inside the file). With multiple formats, you also get the chosen files and still{" "}
          <span className="font-mono text-xs">*_Konversation.html</span>, plus the raw SDK HTML export under{" "}
          <span className="font-mono text-xs">*_html.*</span> when applicable.
        </p>
        <p className="mt-2 text-zinc-600">
          <strong>Open WebUI</strong> adds importable JSON in Open WebUI chat format: one file per chat and{" "}
          <span className="font-mono text-xs">openwebui_import.json</span> in the backup folder for bulk import.
        </p>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-3">
        <div>
          <p className="text-sm font-semibold text-zinc-900">Formats</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {formatOptions.map((option) => {
              const Icon = option.icon;
              return (
                <label key={option.value} className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm">
                  <input
                    type="checkbox"
                    checked={formats.has(option.value)}
                    onChange={() => toggleFormat(option.value)}
                    className="h-4 w-4 rounded border-zinc-300 text-emerald-700"
                  />
                  <Icon className="h-4 w-4 text-zinc-600" />
                  {option.label}
                </label>
              );
            })}
          </div>
        </div>

        <div>
          <p className="text-sm font-semibold text-zinc-900">Mode</p>
          <div className="mt-2 grid grid-cols-2 overflow-hidden rounded-md border border-zinc-300">
            <button
              type="button"
              onClick={() => setMode("selected")}
              className={`px-3 py-2 text-sm font-medium ${mode === "selected" ? "bg-zinc-950 text-white" : "bg-white text-zinc-700"}`}
            >
              Export selection
            </button>
            <button
              type="button"
              onClick={() => setMode("all")}
              className={`px-3 py-2 text-sm font-medium ${mode === "all" ? "bg-zinc-950 text-white" : "bg-white text-zinc-700"}`}
            >
              Export all
            </button>
          </div>
        </div>

        <div>
          <p className="text-sm font-semibold text-zinc-900">Package</p>
          <label className="mt-2 inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={zip}
              onChange={(event) => setZip(event.target.checked)}
              className="h-4 w-4 rounded border-zinc-300 text-emerald-700"
            />
            <Archive className="h-4 w-4 text-zinc-600" />
            Create ZIP
          </label>
        </div>
      </div>

      <button
        type="button"
        disabled={disabled}
        onClick={() => onStart(mode, [...formats], zip)}
        className="mt-5 inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
      >
        <PackageCheck className="h-4 w-4" />
        {mode === "all" ? "Export all" : "Export selected"}
      </button>
    </section>
  );
}
