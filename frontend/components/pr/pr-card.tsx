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

export function PRCard({
  pr,
  selected,
  onSelect,
}: {
  pr: DashboardPR;
  selected?: boolean;
  onSelect?: (id: string) => void;
}): JSX.Element {
  return (
    <button
      type="button"
      onClick={() => onSelect?.(pr.prId)}
      className={`w-full rounded-2xl border p-4 text-left shadow-inner shadow-black/30 transition ${
        selected
          ? "border-brand-400 bg-brand-500/20"
          : "border-slate-800 bg-slate-950/70 hover:border-brand-500/30 hover:bg-slate-950"
      }`}
    >
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
    </button>
  );
}
