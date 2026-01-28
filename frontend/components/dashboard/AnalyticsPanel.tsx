"use client";

import clsx from "clsx";
import type { OperationsSnapshot } from "@/types/backend";

function metric(value: number): string {
  if (!Number.isFinite(value)) return "0";
  return value.toFixed(value >= 10 ? 1 : 2);
}

export function AnalyticsPanel({
  summary,
  totalPrs,
}: {
  summary: OperationsSnapshot["summary"];
  totalPrs?: number | null;
}): JSX.Element {
  const totalReviews = summary?.total_reviews || 0;
  const totalFindings = summary?.total_findings || 0;
  const avgFindings = totalReviews ? totalFindings / totalReviews : 0;
  const detectionRate = totalPrs ? (totalReviews / totalPrs) * 100 : 0;
  const mustFixRatio = totalFindings ? ((summary?.must_fix ?? 0) / totalFindings) * 100 : 0;
  const shouldFixRatio = totalFindings ? ((summary?.should_fix ?? 0) / totalFindings) * 100 : 0;
  const niceToFixRatio = totalFindings ? ((summary?.nice_to_fix ?? 0) / totalFindings) * 100 : 0;

  return (
    <div className="rounded-3xl border border-white/5 bg-slate-900/40 p-8 shadow-premium backdrop-blur-md">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-1">
          <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-indigo-400/80">Analytics</p>
          <h2 className="text-2xl font-bold tracking-tight text-slate-100">Review Effectiveness</h2>
          <p className="text-sm text-slate-500 max-w-md">
            Real-time snapshot of detection quality and severity distribution across every PR.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <MiniStat label="Avg Findings / PR" value={metric(avgFindings)} />
          <MiniStat label="Detection Rate" value={`${metric(detectionRate)}%`} />
        </div>
      </div>
      <div className="mt-8 grid gap-8 md:grid-cols-3">
        <SeverityBar
          label="Must Fix"
          percentage={mustFixRatio}
          tone="bg-rose-500/30 ring-1 ring-rose-500/50"
          value={summary?.must_fix ?? 0}
        />
        <SeverityBar
          label="Should Fix"
          percentage={shouldFixRatio}
          tone="bg-amber-500/30 ring-1 ring-amber-500/50"
          value={summary?.should_fix ?? 0}
        />
        <SeverityBar
          label="Nice to Fix"
          percentage={niceToFixRatio}
          tone="bg-emerald-500/30 ring-1 ring-emerald-500/50"
          value={summary?.nice_to_fix ?? 0}
        />
      </div>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="rounded-2xl border border-white/5 bg-black/20 p-5 min-w-[180px]">
      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-100">{value}</p>
    </div>
  );
}

function SeverityBar({
  label,
  percentage,
  tone,
  value,
}: {
  label: string;
  percentage: number;
  tone: string;
  value: number;
}) {
  const safePercent = Number.isFinite(percentage) ? Math.min(Math.max(percentage, 0), 100) : 0;
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-[0.15em] text-slate-500">
        <span>{label}</span>
        <span className="text-slate-300">
          {value} · {safePercent.toFixed(1)}%
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-white/5 ring-1 ring-white/5">
        <div
          className={clsx("h-full rounded-full transition-all duration-500", tone)}
          style={{ width: `${safePercent}%` }}
        />
      </div>
    </div>
  );
}
