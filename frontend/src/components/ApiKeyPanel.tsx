import { CheckCircle2, KeyRound, Loader2, ShieldAlert } from "lucide-react";
import { FormEvent, useState } from "react";
import type { ConnectionResult, StatusResponse } from "../types";

interface ApiKeyPanelProps {
  status: StatusResponse | null;
  connection: ConnectionResult | null;
  onConnect: (apiKey?: string, rememberLocally?: boolean) => Promise<void>;
  onForgetStoredKey: () => Promise<void>;
}

export default function ApiKeyPanel({ status, connection, onConnect, onForgetStoredKey }: ApiKeyPanelProps) {
  const [apiKey, setApiKey] = useState("");
  const [overrideKey, setOverrideKey] = useState(false);
  const [rememberLocally, setRememberLocally] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hasEnvKey = Boolean(status?.has_env_api_key);
  const hasStoredKey = Boolean(status?.has_stored_api_key);
  const showInput = (!hasEnvKey && !hasStoredKey) || overrideKey;
  const canUseExistingKey = hasEnvKey || hasStoredKey;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await onConnect(showInput ? apiKey : undefined, showInput ? rememberLocally : false);
      setApiKey("");
      setRememberLocally(false);
      setMessage("Verbindung erfolgreich getestet.");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Verbindung fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  }

  async function handleForget() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await onForgetStoredKey();
      setMessage("Lokal gespeicherter API-Key wurde geloescht.");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "API-Key konnte nicht geloescht werden.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section id="connection" className="border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-emerald-700" />
            <h2 className="text-lg font-semibold">API-Key</h2>
          </div>
          <p className="mt-2 text-sm text-zinc-600">
            Standard: API-Key nur im Server-RAM. Optional kann er lokal im Docker Volume gespeichert werden.
          </p>
          {hasStoredKey && (
            <p className="mt-1 text-sm font-medium text-amber-800">
              Ein lokal gespeicherter API-Key ist vorhanden.
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 text-sm">
          {connection?.connected ? (
            <span className="inline-flex items-center gap-2 rounded-md bg-emerald-50 px-3 py-1.5 font-medium text-emerald-800">
              <CheckCircle2 className="h-4 w-4" />
              Verbunden ueber {connection.source === "env" ? ".env" : connection.source === "stored" ? "lokalen Speicher" : "UI"}
            </span>
          ) : (
            <span className="inline-flex items-center gap-2 rounded-md bg-amber-50 px-3 py-1.5 font-medium text-amber-900">
              <ShieldAlert className="h-4 w-4" />
              Nicht verbunden
            </span>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="mt-5 grid gap-3 md:grid-cols-[1fr_auto]">
        {showInput ? (
          <input
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            autoComplete="off"
            placeholder="Abacus.AI API-Key eingeben"
            className="min-h-11 rounded-md border border-zinc-300 px-3 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
          />
        ) : (
          <div className="flex min-h-11 items-center rounded-md border border-zinc-300 px-3 text-sm text-zinc-700">
            {hasEnvKey ? "Environment API-Key vorhanden" : "Lokaler API-Key vorhanden"}
          </div>
        )}
        <button
          type="submit"
          disabled={busy || (showInput && !apiKey.trim()) || (!showInput && !canUseExistingKey)}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-zinc-950 px-4 text-sm font-semibold text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
          Verbinden testen
        </button>
      </form>

      {canUseExistingKey && (
        <label className="mt-3 flex items-center gap-2 text-sm text-zinc-700">
          <input
            type="checkbox"
            checked={overrideKey}
            onChange={(event) => setOverrideKey(event.target.checked)}
            className="h-4 w-4 rounded border-zinc-300 text-emerald-700"
          />
          Mit anderem UI-Key verbinden
        </label>
      )}

      {showInput && status?.allow_persistent_api_key && (
        <label className="mt-3 flex items-start gap-2 text-sm text-amber-900">
          <input
            type="checkbox"
            checked={rememberLocally}
            onChange={(event) => setRememberLocally(event.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-zinc-300 text-amber-700"
          />
          <span>
            Dauerhaft lokal speichern. Unsicher/lokal: Der Key wird im Docker Volume unter{" "}
            <span className="font-mono">/data/secrets</span> abgelegt.
          </span>
        </label>
      )}

      {hasStoredKey && (
        <button
          type="button"
          disabled={busy}
          onClick={() => void handleForget()}
          className="mt-3 text-sm font-semibold text-red-700 hover:text-red-800 disabled:opacity-60"
        >
          Gespeicherten API-Key loeschen
        </button>
      )}
      {message && <p className="mt-3 text-sm font-medium text-emerald-700">{message}</p>}
      {error && <p className="mt-3 text-sm font-medium text-red-700">{error}</p>}
    </section>
  );
}
