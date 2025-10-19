"use client";

import clsx from "clsx";
import { ReactNode } from "react";

type CardProps = {
  title: string;
  accent?: "brand" | "emerald" | "amber" | "rose";
  children: ReactNode;
  footer?: ReactNode;
};

const ACCENT_CLASSES: Record<NonNullable<CardProps["accent"]>, string> = {
  brand: "border-brand-500/60",
  emerald: "border-emerald-500/50",
  amber: "border-amber-400/50",
  rose: "border-rose-400/50",
};

export function Card({ title, accent = "brand", children, footer }: CardProps) {
  return (
    <section
      className={clsx(
        "rounded-2xl border bg-slate-900/60 p-6 shadow-lg shadow-slate-950/40 backdrop-blur",
        ACCENT_CLASSES[accent]
      )}
    >
      <header className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
      </header>
      <div className="space-y-4 text-sm text-slate-200">{children}</div>
      {footer ? <footer className="mt-6 text-xs text-slate-400">{footer}</footer> : null}
    </section>
  );
}

