import { ArrowDownUp, CheckSquare, ChevronDown, ChevronUp, RefreshCw, Search, Square } from "lucide-react";
import { useMemo, useState } from "react";
import type { ChatItem } from "../types";

interface ChatTableProps {
  items: ChatItem[];
  warnings: string[];
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
  onLoad: () => void;
  onRefresh: () => void;
  loading: boolean;
}

type Filter = "all" | "ai_chat" | "deployment_conversation";
type SortKey = "title" | "date" | "type";

const INITIAL_TABLE_ROWS = 10;

export function chatSelectionKey(item: ChatItem): string {
  return `${item.type}:${item.deployment_id || ""}:${item.id}`;
}

export default function ChatTable({
  items,
  warnings,
  selectedIds,
  onSelectionChange,
  onLoad,
  onRefresh,
  loading
}: ChatTableProps) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [tableExpanded, setTableExpanded] = useState(false);

  const visibleItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return [...items]
      .filter((item) => filter === "all" || item.type === filter)
      .filter((item) => {
        if (!normalizedQuery) return true;
        return [item.title, item.id, item.deployment_id, item.type].some((value) =>
          String(value || "").toLowerCase().includes(normalizedQuery)
        );
      })
      .sort((a, b) => {
        if (sortKey === "type") return a.type.localeCompare(b.type);
        if (sortKey === "title") return String(a.title || a.id).localeCompare(String(b.title || b.id));
        return String(b.updated_at || b.created_at || "").localeCompare(String(a.updated_at || a.created_at || ""));
      });
  }, [filter, items, query, sortKey]);

  const hasLongList = visibleItems.length > INITIAL_TABLE_ROWS;
  const shownItems = tableExpanded || !hasLongList ? visibleItems : visibleItems.slice(0, INITIAL_TABLE_ROWS);
  const hiddenCount = hasLongList ? visibleItems.length - INITIAL_TABLE_ROWS : 0;

  function toggleItem(item: ChatItem) {
    const next = new Set(selectedIds);
    const key = chatSelectionKey(item);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    onSelectionChange(next);
  }

  function selectVisible() {
    const next = new Set(selectedIds);
    visibleItems.filter((item) => item.exportable).forEach((item) => next.add(chatSelectionKey(item)));
    onSelectionChange(next);
  }

  function clearSelection() {
    onSelectionChange(new Set());
  }

  return (
    <section id="chats" className="border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Chats</h2>
          <p className="mt-1 text-sm text-zinc-600">{items.length} Einträge geladen, {selectedIds.size} ausgewählt</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={onLoad} disabled={loading} className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50 disabled:opacity-60">
            <Search className="h-4 w-4" />
            Chats laden
          </button>
          <button onClick={onRefresh} disabled={loading} className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50 disabled:opacity-60">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button onClick={selectVisible} className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50">
            <CheckSquare className="h-4 w-4" />
            Alle auswählen
          </button>
          <button onClick={clearSelection} className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50">
            <Square className="h-4 w-4" />
            Auswahl aufheben
          </button>
        </div>
      </div>

      {warnings.length > 0 && (
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          {warnings.join(" ")}
        </div>
      )}

      <div className="mt-5 grid gap-3 lg:grid-cols-[1fr_auto_auto]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-zinc-400" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Suche nach Titel, ID, Deployment"
            className="min-h-10 w-full rounded-md border border-zinc-300 pl-9 pr-3 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
          />
        </div>
        <select value={filter} onChange={(event) => setFilter(event.target.value as Filter)} className="min-h-10 rounded-md border border-zinc-300 px-3 text-sm">
          <option value="all">Alle</option>
          <option value="ai_chat">AI Chat</option>
          <option value="deployment_conversation">Deployment Conversations</option>
        </select>
        <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)} className="min-h-10 rounded-md border border-zinc-300 px-3 text-sm">
          <option value="date">Datum</option>
          <option value="title">Titel</option>
          <option value="type">Typ</option>
        </select>
      </div>

      {hasLongList && !tableExpanded && (
        <p className="mt-3 text-xs text-zinc-500">
          Es werden die ersten {INITIAL_TABLE_ROWS} Zeilen angezeigt. „Alle auswählen“ bezieht sich auf alle {visibleItems.length} Einträge in dieser gefilterten Ansicht, nicht nur auf die sichtbaren Zeilen.
        </p>
      )}

      <div className="mt-5 overflow-x-auto border border-zinc-200">
        <table className="min-w-full divide-y divide-zinc-200 text-sm">
          <thead className="bg-zinc-50 text-left text-xs font-semibold uppercase text-zinc-600">
            <tr>
              <th className="w-12 px-3 py-3"></th>
              <th className="px-3 py-3">Typ</th>
              <th className="px-3 py-3">Titel</th>
              <th className="px-3 py-3">ID</th>
              <th className="px-3 py-3">Deployment ID</th>
              <th className="px-3 py-3">
                <span className="inline-flex items-center gap-1"><ArrowDownUp className="h-3 w-3" />Datum</span>
              </th>
              <th className="px-3 py-3">Exportierbar</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 bg-white">
            {shownItems.map((item) => {
              const key = chatSelectionKey(item);
              return (
                <tr key={key} className="hover:bg-zinc-50">
                  <td className="px-3 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(key)}
                      disabled={!item.exportable}
                      onChange={() => toggleItem(item)}
                      className="h-4 w-4 rounded border-zinc-300 text-emerald-700"
                    />
                  </td>
                  <td className="px-3 py-3">
                    <span className={`rounded-md px-2 py-1 text-xs font-semibold ${item.type === "ai_chat" ? "bg-emerald-50 text-emerald-800" : "bg-sky-50 text-sky-800"}`}>
                      {item.type === "ai_chat" ? "AI Chat" : "Deployment"}
                    </span>
                  </td>
                  <td className="max-w-xs px-3 py-3 font-medium text-zinc-900">
                    <span className="line-clamp-2">{item.title || "Ohne Titel"}</span>
                  </td>
                  <td className="px-3 py-3 font-mono text-xs text-zinc-600" title={item.id}>{shorten(item.id)}</td>
                  <td className="px-3 py-3 font-mono text-xs text-zinc-600" title={item.deployment_id || ""}>{item.deployment_id ? shorten(item.deployment_id) : "-"}</td>
                  <td className="px-3 py-3 text-zinc-600">{formatDate(item.updated_at || item.created_at || item.last_event_created_at)}</td>
                  <td className="px-3 py-3">{item.exportable ? "Ja" : "Nein"}</td>
                </tr>
              );
            })}
            {!visibleItems.length && (
              <tr>
                <td colSpan={7} className="px-3 py-10 text-center text-zinc-500">
                  Keine Chats in dieser Ansicht.
                </td>
              </tr>
            )}
            {hasLongList && (
              <tr className="bg-zinc-50">
                <td colSpan={7} className="px-3 py-3">
                  <button
                    type="button"
                    onClick={() => setTableExpanded((v) => !v)}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-50"
                  >
                    {tableExpanded ? (
                      <>
                        <ChevronUp className="h-4 w-4" />
                        Liste einklappen (nur {INITIAL_TABLE_ROWS} Zeilen)
                      </>
                    ) : (
                      <>
                        <ChevronDown className="h-4 w-4" />
                        Weitere {hiddenCount} Einträge anzeigen ({visibleItems.length} in dieser Ansicht)
                      </>
                    )}
                  </button>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function shorten(value: string): string {
  return value.length > 14 ? `${value.slice(0, 6)}...${value.slice(-5)}` : value;
}

function formatDate(value?: string | null): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}
