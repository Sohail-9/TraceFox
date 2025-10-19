"use client";

type InsightListProps = {
  insights: string[];
};

export function InsightList({ insights }: InsightListProps) {
  if (!insights.length) {
    return <p className="text-sm text-slate-400">Insights will populate after the first pipeline run.</p>;
  }

  return (
    <ul className="space-y-3">
      {insights.map((insight) => (
        <li
          key={insight}
          className="rounded-2xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100 shadow shadow-emerald-900/30"
        >
          {insight}
        </li>
      ))}
    </ul>
  );
}

