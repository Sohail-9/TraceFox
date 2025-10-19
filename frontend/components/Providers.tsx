"use client";

import { ToastProvider } from "@/components/ToastProvider";

export function Providers({ children }: { children: React.ReactNode }): JSX.Element {
  return <ToastProvider>{children}</ToastProvider>;
}
