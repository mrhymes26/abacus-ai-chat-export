import { Archive, Coffee, MessageSquare, Settings } from "lucide-react";
import type { ReactNode } from "react";
import type { StatusResponse } from "../types";

export type AppView = "chats" | "backups" | "settings";

interface LayoutProps {
  status: StatusResponse | null;
  activeView: AppView;
  onViewChange: (view: AppView) => void;
  children: ReactNode;
}

const navItems = [
  { label: "Chats", view: "chats" as const, icon: MessageSquare },
  { label: "Backups", view: "backups" as const, icon: Archive },
  { label: "Einstellungen", view: "settings" as const, icon: Settings }
];

const supportUrl = "https://buymeacoffee.com/mrhymes";

export default function Layout({ status, activeView, onViewChange, children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-stone-100 text-zinc-900">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 border-r border-zinc-200 bg-white lg:block">
        <div className="flex h-full flex-col">
          <div className="border-b border-zinc-200 px-6 py-6">
            <p className="text-sm font-semibold uppercase text-emerald-700">Abacus Backup</p>
            <h1 className="mt-2 text-2xl font-semibold leading-tight">Chat Export Manager</h1>
          </div>
          <nav className="flex-1 space-y-1 px-3 py-4">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = item.view === activeView;
              return (
                <button
                  key={item.view}
                  type="button"
                  onClick={() => onViewChange(item.view)}
                  className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm font-medium ${
                    active ? "bg-emerald-50 text-emerald-900" : "text-zinc-700 hover:bg-zinc-100 hover:text-zinc-950"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>
          <div className="border-t border-zinc-200 px-6 py-5 text-sm text-zinc-600">
            <p className="font-medium text-zinc-900">Speicherort</p>
            <p className="mt-1 break-all">{status?.data_dir || "/data"}</p>
            <a
              href={supportUrl}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md bg-amber-300 px-3 py-2 text-sm font-semibold text-zinc-950 hover:bg-amber-200"
            >
              <Coffee className="h-4 w-4" />
              Buy Me a Coffee
            </a>
          </div>
        </div>
      </aside>
      <main className="lg:pl-72">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex gap-2 overflow-x-auto border border-zinc-200 bg-white p-2 shadow-sm lg:hidden">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = item.view === activeView;
              return (
                <button
                  key={item.view}
                  type="button"
                  onClick={() => onViewChange(item.view)}
                  className={`inline-flex min-h-10 flex-none items-center gap-2 rounded-md px-3 text-sm font-semibold ${
                    active ? "bg-emerald-700 text-white" : "bg-zinc-50 text-zinc-700 hover:bg-zinc-100"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}
