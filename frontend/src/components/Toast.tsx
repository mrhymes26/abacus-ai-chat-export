import { CircleAlert, CircleCheck, Info, X } from "lucide-react";
import type { ToastMessage } from "../types";

interface ToastProps {
  messages: ToastMessage[];
  onDismiss: (id: number) => void;
}

export default function Toast({ messages, onDismiss }: ToastProps) {
  if (!messages.length) return null;
  return (
    <div className="fixed bottom-4 right-4 z-50 flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2">
      {messages.map((toast) => {
        const Icon = toast.type === "success" ? CircleCheck : toast.type === "error" ? CircleAlert : Info;
        const tone = toast.type === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-900" : toast.type === "error" ? "border-red-200 bg-red-50 text-red-900" : "border-sky-200 bg-sky-50 text-sky-900";
        return (
          <div key={toast.id} className={`flex items-start gap-3 rounded-md border p-3 shadow-sm ${tone}`}>
            <Icon className="mt-0.5 h-4 w-4 flex-none" />
            <p className="flex-1 text-sm font-medium">{toast.message}</p>
            <button onClick={() => onDismiss(toast.id)} title="Schließen" className="rounded p-0.5 hover:bg-white/70">
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
