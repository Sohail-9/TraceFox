"use client";

import clsx from "clsx";
import type { OperationsSnapshot } from "@/types/backend";

// Defined PRListProps type
type PRListProps = {
  registry: OperationsSnapshot["pr_registry"];
  loading: boolean;
  selectedPrId?: string | null;
  onSelect: (prId: string) => void;
};

export function PRList({ registry, loading, selectedPrId, onSelect }: PRListProps): JSX.Element {
  if (loading) {
    return (
      <div className="flex flex-col gap-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 w-full animate-pulse rounded-lg bg-white/5" />
        ))}
      </div>
    );
  }

  if (!registry.length) {
    return (
      <div className="flex aspect-video flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-white/[0.02] p-8 text-center">
        <div className="text-2xl mb-2 opacity-50">🔍</div>
        <p className="text-sm font-medium text-slate-400">No active reviews</p>
        <p className="mt-1 text-[11px] text-slate-500">Repos are quiet for now.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1.5" role="listbox" aria-label="Pull Requests">
      {registry.map((pr) => {
        const isActive = pr.pr_id === selectedPrId;
        return (
          <button
            key={pr.pr_id}
            onClick={() => onSelect(pr.pr_id)}
            role="option"
            aria-selected={isActive}
            className={clsx(
              "group flex flex-col gap-1 w-full rounded-lg px-4 py-3 text-left transition-all duration-200 outline-none",
              isActive
                ? "bg-brand-500/10 border-l-2 border-brand-500 shadow-[0_2px_12px_-4px_rgba(99,102,241,0.2)]"
                : "bg-transparent border-l-2 border-transparent hover:bg-white/[0.03] hover:border-white/20 focus:bg-white/[0.04]"
            )}
          >
            <div className="flex items-center justify-between gap-3 w-full">
              <span className={clsx(
                "truncate text-sm font-medium tracking-tight",
                isActive ? "text-brand-400" : "text-slate-300 group-hover:text-slate-200"
              )}>
                {pr.repository_name} <span className="opacity-50">#{pr.pull_request_number}</span>
              </span>
              <span className="shrink-0 text-[10px] font-mono text-slate-600 bg-black/20 px-1.5 py-0.5 rounded">
                {pr.pr_id.slice(0, 6)}
              </span>
            </div>

            <div className="flex items-center gap-2 text-[11px] text-slate-500 group-hover:text-slate-400">
              <div className={clsx(
                "w-1.5 h-1.5 rounded-full",
                pr.event_type === "pull_request" ? "bg-emerald-500/50" : "bg-blue-500/50"
              )} />
              <span className="uppercase tracking-wider font-semibold text-[10px]">
                {(pr.event_type || "unknown").replace("_", " ")}
              </span>
              <span className="opacity-30">|</span>
              <span>
                {pr.received_at ? new Date(pr.received_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "--:--"}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
