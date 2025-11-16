"use client";

type DashboardPR = {
  prId: string;
  repository?: string;
  title?: string;
  author?: string;
  action?: string;
  status?: string;
  updatedAt?: string;
};

export function PRCard({ pr }: { pr: DashboardPR }): JSX.Element {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 shadow-inner shadow-black/30">
      <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
        <span>{pr.repository ?? "Repository"}</span>
        <span>{pr.status ?? pr.action ?? "pending"}</span>
      </div>
      <p className="mt-2 text-sm font-semibold text-white">
        {pr.title ?? pr.prId}
      </p>
      <p className="text-xs text-slate-500">
        #{pr.prId} · {pr.author ?? "unknown"}
      </p>
      <p className="text-[10px] text-slate-600">
        Updated {pr.updatedAt ?? "—"}
      </p>
    </div>
  );
}
