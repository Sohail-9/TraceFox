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
  brand: "border-brand-500/60 bg-brand-500/5",
  emerald: "border-emerald-500/50 bg-emerald-500/5",
  amber: "border-amber-400/50 bg-amber-500/5",
  rose: "border-rose-400/50 bg-rose-500/5",
  slate: "border-slate-700/60 bg-slate-900/60",
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
        "rounded-3xl border p-6 shadow-xl backdrop-blur transition hover:-translate-y-0.5 hover:shadow-2xl",
        "bg-glass shadow-soft",
        ACCENT_CLASSES[accent],
        className
      )}
    >
      {(title || action) && (
        <header className="mb-5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {icon ? (
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-ui/10 bg-panel text-ui text-lg">
                {icon}
              </div>
            ) : null}
            {title ? (
              <h2 className="text-base font-semibold uppercase tracking-wide text-ui">
                {title}
              </h2>
            ) : null}
          </div>
          {action ? <div className="text-xs text-muted">{action}</div> : null}
        </header>
      )}
      <div className="space-y-4 text-sm leading-relaxed text-ui">{children}</div>
      {footer ? <footer className="mt-6 text-xs text-muted">{footer}</footer> : null}
    </section>
  );
}
