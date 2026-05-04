import { Cable, ChevronDown, ChevronUp, CircleAlert, Server } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ConnectionResult, StatusResponse } from "../types";

const supportedScopeKeys = ["deployment_ids", "external_application_ids", "conversation_types"];

const PREVIEW_SCOPE_CHIPS = 10;

interface ConnectionStatusProps {
  status: StatusResponse | null;
  connection: ConnectionResult | null;
}

export default function ConnectionStatus({ status, connection }: ConnectionStatusProps) {
  const methods = connection?.available_methods || [];
  const missing = connection?.missing_methods || [];
  const [scopesExpanded, setScopesExpanded] = useState(false);

  const scopeChips = useMemo(() => {
    const entries = supportedScopeKeys
      .map((key) => [key, status?.conversation_scopes?.[key] || []] as const)
      .filter(([, values]) => values.length > 0);
    return entries.flatMap(([key, values]) =>
      values.map((value, index) => ({
        key,
        value,
        id: `${key}:${value}:${index}`
      }))
    );
  }, [status?.conversation_scopes]);

  const longScopeList = scopeChips.length > PREVIEW_SCOPE_CHIPS;
  const visibleChips = longScopeList && !scopesExpanded ? scopeChips.slice(0, PREVIEW_SCOPE_CHIPS) : scopeChips;
  const hiddenScopeCount = longScopeList ? scopeChips.length - PREVIEW_SCOPE_CHIPS : 0;

  useEffect(() => {
    if (scopeChips.length <= PREVIEW_SCOPE_CHIPS) {
      setScopesExpanded(false);
    }
  }, [scopeChips.length]);

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
        <div className="mt-2 space-y-2">
          {scopeChips.length ? (
            <>
              {longScopeList && !scopesExpanded && (
                <p className="text-xs text-zinc-500">
                  Vorschau: {PREVIEW_SCOPE_CHIPS} von {scopeChips.length} Einträgen — alle Scopes ausklappen für die volle Liste.
                </p>
              )}
              <div
                className={`flex flex-wrap gap-2 ${longScopeList && scopesExpanded ? "max-h-96 overflow-y-auto pr-1" : longScopeList ? "max-h-48 overflow-y-auto pr-1" : ""}`}
              >
                {visibleChips.map(({ key, value, id }) => (
                  <span key={id} className="max-w-full truncate rounded-md bg-sky-50 px-2 py-1 text-xs font-medium text-sky-800" title={`${key}: ${value}`}>
                    {key}: {value}
                  </span>
                ))}
              </div>
              {longScopeList && (
                <button
                  type="button"
                  onClick={() => setScopesExpanded((v) => !v)}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-50"
                >
                  {scopesExpanded ? (
                    <>
                      <ChevronUp className="h-4 w-4 shrink-0" />
                      Liste einklappen (nur {PREVIEW_SCOPE_CHIPS} Chips)
                    </>
                  ) : (
                    <>
                      <ChevronDown className="h-4 w-4 shrink-0" />
                      Weitere {hiddenScopeCount} Einträge anzeigen ({scopeChips.length} gesamt)
                    </>
                  )}
                </button>
              )}
            </>
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
