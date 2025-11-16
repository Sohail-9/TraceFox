"use client";

import { ReactNode } from "react";

import { ToastProvider } from "@/components/ToastProvider";

export function Providers({ children }: { children: ReactNode }): JSX.Element {
  return <ToastProvider>{children}</ToastProvider>;
}
