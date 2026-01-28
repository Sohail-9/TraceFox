"use client";

import { useMemo } from "react";
import clsx from "clsx";

import { FindingsFilter } from "@/components/analysis/findings-filter";
import { FindingsList } from "@/components/analysis/findings-list";
import { LoadingSpinner } from "@/components/common/loading-spinner";
import { useAnalysisStore } from "@/store/analysis-store";
import type { ReviewSummary } from "@/types/backend";

type Props = {
  review?: ReviewSummary;
  loading: boolean;
  onFeedback: (findingId: string, reaction: string) => void;
};

export function PRAnalysisPanel({ review, loading, onFeedback }: Props): JSX.Element {
  const severity = useAnalysisStore((state) => state.severity);
  const category = useAnalysisStore((state) => state.category);

  const findings = useMemo(() => {
    if (!review?.findings) return [];
    return review.findings.filter((finding) => {
      if (severity && finding.severity !== severity) return false;
      if (category && finding.type !== category) return false;
      return true;
    });
  }, [review?.findings, severity, category]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center rounded-3xl border border-slate-800">
        <LoadingSpinner label="Scanning findings" />
      </div>
    );
  }

  if (!review) {
    return (
      <div className="rounded-3xl border border-slate-800 p-6 text-sm text-slate-500">
        Select or analyze a pull request to view results.
      </div>
    );
  }

  const stats = {
    total: review.total_findings,
    mustFix: review.must_fix_count,
    shouldFix: review.should_fix_count,
    niceToFix: review.nice_to_fix_count,
  };

  return (
    <div className="animate-fade-in space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Findings" value={stats.total} />
        <StatCard label="Must Fix" value={stats.mustFix} tone="rose" />
        <StatCard label="Should Fix" value={stats.shouldFix} tone="amber" />
        <StatCard label="Nice to Fix" value={stats.niceToFix} tone="emerald" />
      </div>

      <div className="flex items-center gap-4 rounded-xl border border-white/5 bg-white/5 p-3 text-[11px] text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
          Model: <span className="font-medium text-slate-200">{review.primary_model}</span>
        </div>
        <div className="h-3 w-px bg-white/10" />
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          Duration: <span className="font-medium text-slate-200">{review.duration_ms} ms</span>
        </div>
      </div>

      <div className="space-y-4">
        <FindingsFilter />
        <FindingsList findings={findings} onFeedback={onFeedback} />
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  tone = "indigo",
}: {
  label: string;
  value: number;
  tone?: "indigo" | "rose" | "amber" | "emerald";
}) {
  const TONE_CLASSES = {
    indigo: "text-indigo-400 border-indigo-500/20 bg-indigo-500/5",
    rose: "text-rose-400 border-rose-500/20 bg-rose-500/5",
    amber: "text-amber-400 border-amber-500/20 bg-amber-500/5",
    emerald: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5",
  };

  return (
    <div className={clsx(
      "rounded-2xl border p-4 transition-all duration-300 hover:shadow-lg",
      TONE_CLASSES[tone]
    )}>
      <p className="text-[10px] font-bold uppercase tracking-[0.2em] opacity-60">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}
