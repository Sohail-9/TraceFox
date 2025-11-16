"use client";

import { useMemo } from "react";

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
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        <StatCard label="Total Findings" value={stats.total} />
        <StatCard label="Must Fix" value={stats.mustFix} tone="text-rose-200" />
        <StatCard
          label="Should Fix"
          value={stats.shouldFix}
          tone="text-amber-200"
        />
        <StatCard
          label="Nice to Fix"
          value={stats.niceToFix}
          tone="text-emerald-200"
        />
      </div>
      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-xs text-slate-400">
        <p>
          Primary model: <span className="text-white">{review.primary_model}</span>
        </p>
        <p>
          Duration: <span className="text-white">{review.duration_ms} ms</span>
        </p>
      </div>
      <FindingsFilter />
      <FindingsList findings={findings} onFeedback={onFeedback} />
    </div>
  );
}

function StatCard({
  label,
  value,
  tone = "text-white",
}: {
  label: string;
  value: number;
  tone?: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm">
      <p className="text-xs uppercase tracking-[0.3em] text-slate-500">{label}</p>
      <p className={`text-2xl font-semibold ${tone}`}>{value}</p>
    </div>
  );
}
