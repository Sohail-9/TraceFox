"use client";

import { Fragment } from "react";

type TimelineItem = {
  title: string;
  timestamp?: string;
  details?: string[];
};

type TimelineProps = {
  items: TimelineItem[];
  emptyLabel?: string;
};

export function Timeline({ items, emptyLabel = "No activity recorded yet." }: TimelineProps) {
  if (!items.length) {
    return <p className="text-sm text-slate-400">{emptyLabel}</p>;
  }

  return (
    <ol className="relative space-y-6">
      <span className="absolute left-[11px] top-2 h-full w-px bg-gradient-to-b from-brand-400/60 via-slate-700/50 to-transparent" />
      {items.map((item, idx) => (
        <Fragment key={`${item.title}-${idx}`}>
          <li className="relative pl-8">
            <span className="absolute left-0 top-1 h-3 w-3 rounded-full border border-brand-400 bg-brand-500 shadow shadow-brand-500/40" />
            <div>
              <p className="text-sm font-medium text-slate-100">{item.title}</p>
              {item.timestamp ? (
                <p className="text-xs uppercase tracking-wide text-slate-400/80">
                  {new Date(item.timestamp).toLocaleString()}
                </p>
              ) : null}
              {item.details?.map((detail) => (
                <p key={detail} className="mt-2 rounded-xl border border-slate-700/60 bg-slate-900/60 px-3 py-2 text-sm text-slate-200 shadow-inner shadow-slate-950/40">
                  {detail}
                </p>
              ))}
            </div>
          </li>
        </Fragment>
      ))}
    </ol>
  );
}
