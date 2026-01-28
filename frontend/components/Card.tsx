"use client";

import clsx from "clsx";
import { ReactNode } from "react";

type CardProps = {
  title?: string;
  accent?: "brand" | "emerald" | "amber" | "rose" | "slate";
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
};

const ACCENT_CLASSES: Record<NonNullable<CardProps["accent"]>, string> = {
  brand: "border-indigo-500/40 bg-indigo-500/5",
  emerald: "border-emerald-500/40 bg-emerald-500/5",
  amber: "border-amber-500/40 bg-amber-500/5",
  rose: "border-rose-500/40 bg-rose-500/5",
  slate: "border-white/5 bg-slate-900/40",
};

export function Card({
  title,
  accent = "slate",
  icon,
  action,
  children,
  footer,
  className,
}: CardProps) {
  return (
    <section
      className={clsx(
        "rounded-3xl border p-6 backdrop-blur-md transition-all duration-300",
        "bg-glass shadow-premium hover:shadow-2xl hover:-translate-y-1",
        ACCENT_CLASSES[accent],
        className
      )}
    >
      {(title || action) && (
        <header className="mb-5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {icon ? (
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/5 bg-panel shadow-inner text-lg">
                {icon}
              </div>
            ) : null}
            {title ? (
              <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">
                {title}
              </h2>
            ) : null}
          </div>
          {action ? <div className="text-xs text-slate-500">{action}</div> : null}
        </header>
      )}
      <div className="animate-fade-in space-y-4 text-sm leading-relaxed text-slate-300">
        {children}
      </div>
      {footer ? (
        <footer className="mt-6 border-t border-white/5 pt-4 text-xs text-slate-500">
          {footer}
        </footer>
      ) : null}
    </section>
  );
}
