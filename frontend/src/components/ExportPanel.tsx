import { Archive, FileCode2, FileJson, FileText, PackageCheck } from "lucide-react";
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
  { value: "html", label: "HTML", icon: FileCode2 }
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
      <p className="mt-2 text-sm text-zinc-600">Backups enthalten vertrauliche Chat-Inhalte.</p>

      <div className="mt-4 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-700">
        <p className="font-medium text-zinc-900">Ablauf</p>
        <p className="mt-1">
          Nach Klick auf Export startet ein <strong>Server-Job</strong>: Für jeden Chat werden die gewählten Formate als <strong>Einzeldateien</strong> in einen neuen Backup-Ordner geschrieben (zusätzlich <span className="font-mono text-xs">manifest.json</span> und ggf.{" "}
          <span className="font-mono text-xs">errors.log</span>).
        </p>
        <p className="mt-2">
          Wenn <strong>ZIP erstellen</strong> aktiv ist, wird <strong>am Ende des Jobs</strong> eine Datei <span className="font-mono text-xs">backup.zip</span> im Backup-Ordner erzeugt. Die ZIP ist ein Archiv über dieselben Dateien (kein zusätzlicher Exportlauf). Ist die Option aus, werden nur Einzeldateien geschrieben; ein Klick auf <strong>Download</strong> in der Historie erzeugt die ZIP bei Bedarf beim ersten Abruf nachträglich.
        </p>
        <p className="mt-2 text-zinc-600">
          <strong>Alle exportieren</strong> verarbeitet alle <em>exportierbaren</em> Chats aus der geladenen Liste (unabhängig von Checkboxen). <strong>Auswahl exportieren</strong> nur die angehakten Zeilen.
        </p>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-3">
        <div>
          <p className="text-sm font-semibold text-zinc-900">Formate</p>
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
          <p className="text-sm font-semibold text-zinc-900">Modus</p>
          <div className="mt-2 grid grid-cols-2 overflow-hidden rounded-md border border-zinc-300">
            <button
              type="button"
              onClick={() => setMode("selected")}
              className={`px-3 py-2 text-sm font-medium ${mode === "selected" ? "bg-zinc-950 text-white" : "bg-white text-zinc-700"}`}
            >
              Auswahl exportieren
            </button>
            <button
              type="button"
              onClick={() => setMode("all")}
              className={`px-3 py-2 text-sm font-medium ${mode === "all" ? "bg-zinc-950 text-white" : "bg-white text-zinc-700"}`}
            >
              Alle exportieren
            </button>
          </div>
        </div>

        <div>
          <p className="text-sm font-semibold text-zinc-900">Paket</p>
          <label className="mt-2 inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={zip}
              onChange={(event) => setZip(event.target.checked)}
              className="h-4 w-4 rounded border-zinc-300 text-emerald-700"
            />
            <Archive className="h-4 w-4 text-zinc-600" />
            ZIP erstellen
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
        {mode === "all" ? "Alle exportieren" : "Ausgewählte exportieren"}
      </button>
    </section>
  );
}
