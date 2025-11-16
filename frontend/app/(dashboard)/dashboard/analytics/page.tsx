"use client";

import { useMemo } from "react";

import { AnalyticsPanel } from "@/components/dashboard/AnalyticsPanel";
import { Card } from "@/components/Card";
import { LoadingSpinner } from "@/components/common/loading-spinner";
import { useOperations } from "@/hooks/usePRAnalysis";

export default function AnalyticsPage(): JSX.Element {
  const { data, isLoading } = useOperations();

  const perPrRows = useMemo(() => {
    if (!data?.summary?.per_pr) return [];
    const testsPerPr = data.tests?.per_pr ?? {};
    const executions = data.executions?.latest_per_pr ?? {};
    const rcaCounts = data.rca?.per_pr_counts ?? {};
    return Object.entries(data.summary.per_pr).map(([prId, snapshot]) => ({
      prId,
      summary: snapshot.summary,
      totalFindings: snapshot.total_findings,
      mustFix: snapshot.must_fix,
      shouldFix: snapshot.should_fix,
      niceToFix: snapshot.nice_to_fix,
      tests: testsPerPr[prId] ?? 0,
      executions: executions[prId]?.total_tests ?? 0,
      rca: rcaCounts[prId] ?? 0,
      createdAt: snapshot.created_at,
    }));
  }, [data]);

  const activity = data?.activity ?? [];

  if (isLoading && !data) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner label="Loading analytics" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Analytics</p>
        <h1 className="text-3xl font-semibold text-white">Operational Intelligence</h1>
        <p className="text-sm text-slate-400">
          Deep dive into review throughput, severity mix, and traceability powered by the TraceFox control center.
        </p>
      </header>

      {data?.summary ? (
        <AnalyticsPanel summary={data.summary} totalPrs={data.total_prs} />
      ) : null}

      <Card className="space-y-4 border border-slate-800 bg-slate-950/70 p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Per-PR Overview</p>
            <h2 className="text-lg font-semibold">Findings &amp; Signal Mix</h2>
          </div>
          <span className="text-sm text-slate-400">{perPrRows.length} tracked PRs</span>
        </div>
        {perPrRows.length === 0 ? (
          <p className="text-sm text-slate-500">No PRs have completed analysis yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-slate-800">
            <table className="min-w-full divide-y divide-slate-800 text-sm">
              <thead className="bg-slate-900/80 text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 text-left">PR</th>
                  <th className="px-4 py-3 text-left">Findings</th>
                  <th className="px-4 py-3 text-left">Tests</th>
                  <th className="px-4 py-3 text-left">Executions</th>
                  <th className="px-4 py-3 text-left">RCA</th>
                  <th className="px-4 py-3 text-left">Updated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900">
                {perPrRows.map((row) => (
                  <tr key={row.prId} className="text-slate-200">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-white">{row.prId}</div>
                      <p className="text-xs text-slate-500 line-clamp-2">{row.summary}</p>
                    </td>
                    <td className="px-4 py-3">
                      <p>Total: {row.totalFindings}</p>
                      <p className="text-xs text-rose-200">Must fix: {row.mustFix}</p>
                      <p className="text-xs text-amber-200">Should fix: {row.shouldFix}</p>
                      <p className="text-xs text-emerald-200">Nice to fix: {row.niceToFix}</p>
                    </td>
                    <td className="px-4 py-3">{row.tests}</td>
                    <td className="px-4 py-3">{row.executions}</td>
                    <td className="px-4 py-3">{row.rca}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">{row.createdAt ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card className="space-y-4 border border-slate-800 bg-slate-950/70 p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Activity Timeline</p>
            <h2 className="text-lg font-semibold">Recent Events</h2>
          </div>
          <span className="text-sm text-slate-400">{activity.length} events</span>
        </div>
        {activity.length === 0 ? (
          <p className="text-sm text-slate-500">No notable workflow events yet.</p>
        ) : (
          <ul className="space-y-3">
            {activity.map((item) => (
              <li
                key={item.id}
                className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-sm text-slate-200"
              >
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-slate-500">
                  <span>{item.tone}</span>
                  <span>{item.timestamp ?? "—"}</span>
                </div>
                <p className="mt-1 font-semibold text-white">{item.title}</p>
                <p className="text-xs text-slate-400">{item.detail}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
