"use client";

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
    <div className="rounded-3xl border border-slate-800 bg-slate-950/70 p-6 shadow-xl shadow-black/40">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Analytics</p>
          <h2 className="text-2xl font-semibold text-white">Review Effectiveness</h2>
          <p className="text-sm text-slate-400">
            Real-time snapshot of detection quality and severity distribution across every PR.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <MiniStat label="Avg Findings / PR" value={metric(avgFindings)} />
          <MiniStat label="Detection Rate" value={`${metric(detectionRate)}%`} />
        </div>
      </div>
      <div className="mt-6 space-y-5">
        <SeverityBar
          label="Must Fix"
          percentage={mustFixRatio}
          tone="bg-rose-500/60"
          value={summary?.must_fix ?? 0}
        />
        <SeverityBar
          label="Should Fix"
          percentage={shouldFixRatio}
          tone="bg-amber-500/60"
          value={summary?.should_fix ?? 0}
        />
        <SeverityBar
          label="Nice to Fix"
          percentage={niceToFixRatio}
          tone="bg-emerald-500/60"
          value={summary?.nice_to_fix ?? 0}
        />
      </div>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-left">
      <p className="text-[10px] uppercase tracking-[0.4em] text-slate-500">{label}</p>
      <p className="text-xl font-semibold text-white">{value}</p>
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
}): JSX.Element {
  const safePercent = Number.isFinite(percentage) ? Math.min(Math.max(percentage, 0), 100) : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-slate-400">
        <span>{label}</span>
        <span>
          {value} · {safePercent.toFixed(1)}%
        </span>
      </div>
      <div className="mt-2 h-2 rounded-full bg-slate-800">
        <div
          className={`h-2 rounded-full ${tone}`}
          style={{ width: `${safePercent}%` }}
        />
      </div>
    </div>
  );
}
