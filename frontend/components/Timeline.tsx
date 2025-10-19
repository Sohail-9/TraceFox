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
    <ol className="space-y-4">
      {items.map((item, idx) => (
        <Fragment key={`${item.title}-${idx}`}>
          <li className="relative pl-6">
            <span className="absolute left-0 top-1 h-3 w-3 rounded-full border border-brand-400 bg-brand-500 shadow shadow-brand-500/40" />
            <div>
              <p className="text-sm font-medium text-slate-100">{item.title}</p>
              {item.timestamp ? (
                <p className="text-xs uppercase tracking-wide text-slate-400">
                  {new Date(item.timestamp).toLocaleString()}
                </p>
              ) : null}
              {item.details?.map((detail) => (
                <p key={detail} className="mt-2 text-sm text-slate-300">
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

