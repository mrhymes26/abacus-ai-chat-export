import { Save, Settings } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import type { ConversationScopes, StatusResponse } from "../types";

interface ConversationScopesPanelProps {
  status: StatusResponse | null;
  scopes: ConversationScopes | null;
  onSave: (scopes: ConversationScopes) => Promise<void>;
}

const emptyScopes: ConversationScopes = {
  deployment_ids: [],
  external_application_ids: [],
  conversation_types: []
};

export default function ConversationScopesPanel({ status, scopes, onSave }: ConversationScopesPanelProps) {
  const [draft, setDraft] = useState<ConversationScopes>(emptyScopes);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(scopes || emptyScopes);
  }, [scopes]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await onSave(toSupportedScopes(draft));
      setMessage("Conversation Scopes gespeichert.");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Scopes konnten nicht gespeichert werden.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section id="settings" className="border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <Settings className="h-5 w-5 text-sky-700" />
        <h2 className="text-lg font-semibold">Einstellungen</h2>
      </div>

      <div className="mt-3 grid gap-3 text-sm text-zinc-700 md:grid-cols-2">
        <p>Docker Volume: <span className="font-mono">{status?.data_dir || "/data"}</span></p>
        <p>API-Key im Browser: nicht gespeichert</p>
        <p>UI/API Auth: optional ueber <span className="font-mono">APP_BASIC_AUTH_USER</span></p>
        <p>Scope-Datei: <span className="font-mono">/data/settings/conversation_scopes.json</span></p>
        <p>Aktive Scopes: {countScopes(status?.conversation_scopes || {})}</p>
        <p>Lokal gespeicherte Scopes: {countScopes(status?.stored_conversation_scopes || {})}</p>
      </div>

      <form onSubmit={handleSubmit} className="mt-5 grid gap-4 lg:grid-cols-2">
        <ScopeInput
          label="Deployment IDs"
          value={draft.deployment_ids}
          onChange={(value) => setDraft((current) => ({ ...current, deployment_ids: value }))}
        />
        <ScopeInput
          label="External Application IDs"
          value={draft.external_application_ids}
          onChange={(value) => setDraft((current) => ({ ...current, external_application_ids: value }))}
        />
        <ScopeInput
          label="Conversation Types"
          value={draft.conversation_types}
          onChange={(value) => setDraft((current) => ({ ...current, conversation_types: value }))}
        />

        <div className="flex items-end">
          <button
            type="submit"
            disabled={busy}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-zinc-950 px-4 text-sm font-semibold text-white hover:bg-zinc-800 disabled:bg-zinc-400"
          >
            <Save className="h-4 w-4" />
            Scopes speichern
          </button>
        </div>
      </form>

      <p className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900">
        Deployment Conversation Scopes werden automatisch ueber das Abacus SDK ermittelt, wenn sie hier leer sind.
        Manuell unterstuetzt werden Deployment ID, External Application ID und Conversation Type; Werte koennen
        kommasepariert, mit Semikolon oder zeilenweise eingetragen werden.
      </p>
      {message && <p className="mt-3 text-sm font-medium text-emerald-700">{message}</p>}
      {error && <p className="mt-3 text-sm font-medium text-red-700">{error}</p>}
    </section>
  );
}

function countScopes(scopes: Record<string, string[]>): number {
  return supportedScopeKeys.reduce((total, key) => total + (scopes[key]?.length || 0), 0);
}

const supportedScopeKeys = ["deployment_ids", "external_application_ids", "conversation_types"];

function toSupportedScopes(scopes: ConversationScopes): ConversationScopes {
  return {
    deployment_ids: scopes.deployment_ids,
    external_application_ids: scopes.external_application_ids,
    conversation_types: scopes.conversation_types
  };
}

function ScopeInput({
  label,
  value,
  onChange
}: {
  label: string;
  value: string[];
  onChange: (value: string[]) => void;
}) {
  return (
    <label className="block text-sm">
      <span className="font-semibold text-zinc-900">{label}</span>
      <textarea
        value={value.join("\n")}
        onChange={(event) => onChange(splitValues(event.target.value))}
        rows={3}
        className="mt-2 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
        placeholder="ein Wert pro Zeile oder kommasepariert"
      />
    </label>
  );
}

function splitValues(value: string): string[] {
  return value
    .split(/[\n,;]+/)
    .map((part) => part.trim())
    .filter(Boolean);
}
