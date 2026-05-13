import { ArrowDownUp, CheckSquare, ChevronLeft, ChevronRight, RefreshCw, Search, Square } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
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

const PAGE_SIZE_OPTIONS = [10, 50, 100] as const;
type PageSize = (typeof PAGE_SIZE_OPTIONS)[number];

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
  const [pageSize, setPageSize] = useState<PageSize>(10);
  const [pageIndex, setPageIndex] = useState(0);

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

  const totalPages = Math.max(1, Math.ceil(visibleItems.length / pageSize));
  const safePageIndex = Math.min(pageIndex, totalPages - 1);
  const rangeStart = visibleItems.length === 0 ? 0 : safePageIndex * pageSize + 1;
  const rangeEnd = visibleItems.length === 0 ? 0 : Math.min(visibleItems.length, (safePageIndex + 1) * pageSize);
  const shownItems = visibleItems.slice(safePageIndex * pageSize, (safePageIndex + 1) * pageSize);
  const needsPagination = visibleItems.length > pageSize;

  useEffect(() => {
    setPageIndex((i) => Math.min(i, Math.max(0, totalPages - 1)));
  }, [totalPages]);

  useEffect(() => {
    setPageIndex(0);
  }, [query, filter, sortKey, visibleItems.length]);

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
          <p className="mt-1 text-sm text-zinc-600">{items.length} rows loaded, {selectedIds.size} selected</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={onLoad} disabled={loading} className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50 disabled:opacity-60">
            <Search className="h-4 w-4" />
            Load chats
          </button>
          <button onClick={onRefresh} disabled={loading} className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50 disabled:opacity-60">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button onClick={selectVisible} className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50">
            <CheckSquare className="h-4 w-4" />
            Select all
          </button>
          <button onClick={clearSelection} className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50">
            <Square className="h-4 w-4" />
            Clear selection
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
            placeholder="Search title, ID, deployment"
            className="min-h-10 w-full rounded-md border border-zinc-300 pl-9 pr-3 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100"
          />
        </div>
        <select value={filter} onChange={(event) => setFilter(event.target.value as Filter)} className="min-h-10 rounded-md border border-zinc-300 px-3 text-sm">
          <option value="all">All</option>
          <option value="ai_chat">AI chat</option>
          <option value="deployment_conversation">Deployment conversations</option>
        </select>
        <select value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)} className="min-h-10 rounded-md border border-zinc-300 px-3 text-sm">
          <option value="date">Date</option>
          <option value="title">Title</option>
          <option value="type">Type</option>
        </select>
      </div>

      {visibleItems.length > 0 && (
        <p className="mt-3 text-xs text-zinc-500">
          {needsPagination
            ? `Showing rows ${rangeStart}–${rangeEnd} of ${visibleItems.length} (page ${safePageIndex + 1} of ${totalPages}, ${pageSize} per page). "Select all" applies to all ${visibleItems.length} rows in this filtered view, not only the visible page.`
            : `Showing all ${visibleItems.length} rows in this view (up to ${pageSize} per page). "Select all" selects the entire filtered list.`}
        </p>
      )}

      <div className="mt-5 overflow-x-auto border border-zinc-200">
        <table className="min-w-full divide-y divide-zinc-200 text-sm">
          <thead className="bg-zinc-50 text-left text-xs font-semibold uppercase text-zinc-600">
            <tr>
              <th className="w-12 px-3 py-3"></th>
              <th className="px-3 py-3">Type</th>
              <th className="px-3 py-3">Title</th>
              <th className="px-3 py-3">ID</th>
              <th className="px-3 py-3">Deployment ID</th>
              <th className="px-3 py-3">
                <span className="inline-flex items-center gap-1"><ArrowDownUp className="h-3 w-3" />Date</span>
              </th>
              <th className="px-3 py-3">Exportable</th>
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
                      {item.type === "ai_chat" ? "AI chat" : "Deployment"}
                    </span>
                  </td>
                  <td className="max-w-xs px-3 py-3 font-medium text-zinc-900">
                    <span className="line-clamp-2">{item.title || "Untitled"}</span>
                  </td>
                  <td className="px-3 py-3 font-mono text-xs text-zinc-600" title={item.id}>{shorten(item.id)}</td>
                  <td className="px-3 py-3 font-mono text-xs text-zinc-600" title={item.deployment_id || ""}>{item.deployment_id ? shorten(item.deployment_id) : "-"}</td>
                  <td className="px-3 py-3 text-zinc-600">{formatDate(item.updated_at || item.created_at || item.last_event_created_at)}</td>
                  <td className="px-3 py-3">{item.exportable ? "Yes" : "No"}</td>
                </tr>
              );
            })}
            {!visibleItems.length && (
              <tr>
                <td colSpan={7} className="px-3 py-10 text-center text-zinc-500">
                  No chats in this view.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {visibleItems.length > 0 && (
        <div className="mt-3 flex flex-col gap-3 rounded-md border border-zinc-200 bg-zinc-50 px-3 py-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <label className="flex items-center gap-2 text-sm text-zinc-700">
            <span className="font-medium text-zinc-800">Rows per page</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value) as PageSize);
                setPageIndex(0);
              }}
              className="min-h-9 rounded-md border border-zinc-300 bg-white px-2 text-sm"
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          {needsPagination && (
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={safePageIndex <= 0}
                onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
                className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </button>
              <span className="text-sm text-zinc-600">
                Page {safePageIndex + 1} / {totalPages}
              </span>
              <button
                type="button"
                disabled={safePageIndex >= totalPages - 1}
                onClick={() => setPageIndex((p) => Math.min(totalPages - 1, p + 1))}
                className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      )}
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
