"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

type ToastTone = "success" | "error" | "info";

type Toast = {
  id: string;
  title: string;
  description?: string;
  tone: ToastTone;
};

type ToastContextValue = {
  addToast: (toast: Omit<Toast, "id"> & { id?: string }) => void;
};

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }): JSX.Element {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, "id"> & { id?: string }) => {
    const id = toast.id ?? generateId();
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id));
    }, 4000);
  }, []);

  const value = useMemo(() => ({ addToast }), [addToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 top-4 z-50 flex flex-col items-center gap-3 px-4">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={getToastClasses(toast.tone)}
          >
            <p className="text-sm font-semibold text-white">{toast.title}</p>
            {toast.description ? (
              <p className="text-xs text-white/80">{toast.description}</p>
            ) : null}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function getToastClasses(tone: ToastTone): string {
  const base = "pointer-events-auto w-full max-w-sm rounded-2xl border px-4 py-3 shadow-lg transition";
  if (tone === "success") {
    return `${base} border-emerald-500/40 bg-emerald-500/20 text-emerald-50 backdrop-blur`;
  }
  if (tone === "error") {
    return `${base} border-rose-500/40 bg-rose-500/20 text-rose-50 backdrop-blur`;
  }
  return `${base} border-brand-500/40 bg-brand-500/20 text-brand-50 backdrop-blur`;
}

function generateId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2);
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
