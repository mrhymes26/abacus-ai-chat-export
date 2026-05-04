import { Cable, CircleAlert, Server } from "lucide-react";
import type { ConnectionResult, StatusResponse } from "../types";

interface ConnectionStatusProps {
  status: StatusResponse | null;
  connection: ConnectionResult | null;
}

export default function ConnectionStatus({ status, connection }: ConnectionStatusProps) {
  const methods = connection?.available_methods || [];
  const missing = connection?.missing_methods || [];
  const scopeEntries = supportedScopeKeys
    .map((key) => [key, status?.conversation_scopes?.[key] || []] as const)
    .filter(([, values]) => values.length > 0);

  return (
    <section className="grid gap-4 border border-zinc-200 bg-white p-5 shadow-sm lg:grid-cols-3">
      <div>
        <div className="flex items-center gap-2">
          <Cable className="h-5 w-5 text-sky-700" />
          <h2 className="text-lg font-semibold">Status</h2>
        </div>
        <p className="mt-2 text-sm text-zinc-600">{status?.connected ? "Connected" : "Not connected"}</p>
        <p className="mt-1 text-sm text-zinc-600">
          Env API-Key: {status?.has_env_api_key ? "vorhanden" : "nicht gesetzt"}
        </p>
      </div>
      <div>
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
          <Server className="h-4 w-4" />
          Conversation Scopes
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {scopeEntries.length ? (
            scopeEntries.flatMap(([key, values]) =>
              values.map((value) => (
                <span key={`${key}:${value}`} className="rounded-md bg-sky-50 px-2 py-1 text-xs font-medium text-sky-800">
                  {key}: {value}
                </span>
              ))
            )
          ) : (
            <span className="text-sm text-zinc-500">Keine gesetzt</span>
          )}
        </div>
      </div>
      <div>
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
          <CircleAlert className="h-4 w-4" />
          SDK-Methoden
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {methods.length ? (
            methods.map((method) => (
              <span key={method} className="rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-800">
                {method}
              </span>
            ))
          ) : (
            <span className="text-sm text-zinc-500">Noch nicht geprueft</span>
          )}
        </div>
        {missing.length > 0 && <p className="mt-3 text-xs text-zinc-500">Fehlend: {missing.join(", ")}</p>}
      </div>
    </section>
  );
}

const supportedScopeKeys = ["deployment_ids", "external_application_ids", "conversation_types"];
