"use client";

import { useEffect, useState } from "react";
import { X, CheckCircle, AlertCircle, Info } from "lucide-react";
import { cn } from "../../lib/utils";

export type ToastVariant = "success" | "error" | "info";

export interface ToastMessage {
  id: string;
  message: string;
  variant: ToastVariant;
}

interface ToastItemProps {
  toast: ToastMessage;
  onDismiss: (id: string) => void;
}

function ToastItem({ toast, onDismiss }: ToastItemProps) {
  useEffect(() => {
    const t = setTimeout(() => onDismiss(toast.id), 4000);
    return () => clearTimeout(t);
  }, [toast.id, onDismiss]);

  const Icon = toast.variant === "success" ? CheckCircle : toast.variant === "error" ? AlertCircle : Info;
  const colors = {
    success: "bg-green-600 dark:bg-green-700",
    error: "bg-red-600 dark:bg-red-700",
    info: "bg-blue-600 dark:bg-blue-700",
  };

  return (
    <div
      className={cn(
        "flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-white min-w-72 max-w-sm",
        colors[toast.variant]
      )}
    >
      <Icon className="w-5 h-5 shrink-0" />
      <span className="flex-1 text-sm">{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        className="shrink-0 opacity-80 hover:opacity-100 transition-opacity"
        aria-label="Dismiss"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

// ─── Global toast state (module-level for simplicity) ──────────────────────
let _setToasts: React.Dispatch<React.SetStateAction<ToastMessage[]>> | null = null;

export function toast(message: string, variant: ToastVariant = "info") {
  const id = Math.random().toString(36).slice(2);
  _setToasts?.((prev) => [...prev, { id, message, variant }]);
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  _setToasts = setToasts;

  const dismiss = (id: string) => setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div key={t.id} className="pointer-events-auto">
          <ToastItem toast={t} onDismiss={dismiss} />
        </div>
      ))}
    </div>
  );
}
