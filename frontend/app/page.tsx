"use client";

import useSWR from "swr";
import { swrFetcher, getApiBaseUrl } from "@/lib/api";
import { Card } from "@/components/Card";
import { KPIGrid } from "@/components/Kpis";
import { Timeline } from "@/components/Timeline";
import { NotificationList } from "@/components/Notifications";
import { InsightList } from "@/components/InsightList";
import type { AnalyticsReport, PipelineState } from "@/types/pipeline";

type TimelineItem = { title: string; timestamp?: string; details?: string[] };

const refreshIntervals = {
  state: 5000,
  analytics: 10000,
};

function buildKpis(report: AnalyticsReport | null) {
  if (!report) {
    return [
      { label: "Tests Generated", value: 0, caption: "Awaiting first commit" },
      { label: "Tests Failed", value: 0 },
      { label: "Notifications Sent", value: 0 },
      { label: "Anomalies Detected", value: 0 },
    ];
  }

  return [
    { label: "Tests Generated", value: report.tests_generated },
    { label: "Tests Failed", value: report.tests_failed },
    { label: "Notifications Sent", value: report.notifications_sent },
    {
      label: "Anomalies Detected",
      value: report.anomalies_detected,
      caption:
        report.anomalies_detected > 0
          ? "Investigate production telemetry before rollout continues."
          : "Production signals nominal.",
    },
  ];
}

function timelineFromState(state?: PipelineState | null): TimelineItem[] {
  if (!state) {
    return [];
  }

  const items: TimelineItem[] = [];
  const commit = state.last_commit as Record<string, any> | null;
  if (commit) {
    items.push({
      title: `Commit · ${commit.event?.repository ?? "repository"}`,
      timestamp: commit.event?.timestamp,
      details: [
        `Overall risk: ${commit.code_analysis?.summary?.overall_risk ?? "unknown"}`,
        `Generated tests: ${commit.test_generation?.tests?.length ?? 0}`,
        `Model routing: ${commit.code_analysis?.summary?.model_used ?? "n/a"}`,
      ].filter(Boolean),
    });
  }

  const deployment = state.last_deployment as Record<string, any> | null;
  if (deployment) {
    items.push({
      title: `Deployment · ${deployment.deployment?.deployment_id ?? "event"}`,
      timestamp: deployment.deployment?.timestamp,
      details: (deployment.alerts as Array<Record<string, any>> | undefined)?.map(
        (alert) => `${alert.metric}: ${alert.observed} (baseline ${alert.baseline})`
      ),
    });
  }

  return items;
}

export default function DashboardPage() {
  const {
    data: state,
    isLoading: stateLoading,
    error: stateError,
  } = useSWR<PipelineState>("/state", swrFetcher, {
    refreshInterval: refreshIntervals.state,
  });

  const { data: analytics } = useSWR<AnalyticsReport>("/analytics/latest", swrFetcher, {
    refreshInterval: refreshIntervals.analytics,
  });

  const report = analytics ?? state?.latest_report ?? null;
  const kpis = buildKpis(report);
  const insights = report?.insights ?? [];
  const notifications = (state?.last_commit as Record<string, any> | null)?.notification ??
    (state?.last_deployment as Record<string, any> | null)?.notification ?? null;
  const timeline = timelineFromState(state);
  const apiSource = getApiBaseUrl();

  return (
    <div className="space-y-10">
      <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-start">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Live overview</p>
          <h2 className="text-2xl font-semibold text-white md:text-3xl">
            Real-time intelligence across code, tests, and production
          </h2>
        </div>
        <div className="flex items-center gap-3 rounded-full border border-slate-700/70 bg-slate-900/60 px-4 py-2 text-xs uppercase tracking-wide text-slate-300">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
          API Source: {apiSource}
        </div>
      </div>

      {stateError ? (
        <div className="rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-100">
          Unable to connect to the DevGuardian API. Check that the backend is running at {apiSource}.
        </div>
      ) : null}

      <KPIGrid metrics={kpis} />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card
          title="Latest Insights"
          accent="emerald"
          icon={<span>✨</span>}
          action={<span>{report ? "Updated" : "Awaiting"}</span>}
        >
          <InsightList insights={insights} />
        </Card>

        <Card
          title="Notifications"
          accent="rose"
          icon={<span>🔔</span>}
          action={<span>Auto refresh: {refreshIntervals.state / 1000}s</span>}
        >
          <NotificationList notifications={notifications} />
        </Card>

        <Card
          title="Production Alerts"
          accent="amber"
          icon={<span>🚨</span>}
          action={<span>{report?.anomalies_detected ?? 0} active</span>}
        >
          {timeline
            .filter((item) => item.title.startsWith("Deployment"))
            .flatMap((item) => item.details ?? []).length ? (
              <ul className="space-y-2 text-sm text-slate-100">
                {timeline
                  .filter((item) => item.title.startsWith("Deployment"))
                  .flatMap((item) => item.details ?? [])
                  .map((detail) => (
                    <li
                      key={detail}
                      className="rounded-xl border border-amber-400/40 bg-amber-500/10 px-3 py-2 text-amber-100"
                    >
                      {detail}
                    </li>
                  ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-400">No anomalies detected in the last deployment.</p>
            )}
        </Card>
      </div>

      <Card
        title="Lifecycle Timeline"
        accent="brand"
        icon={<span>🛠️</span>}
        action={<span>{timeline.length || 0} events</span>}
        footer="Trace commits through tests, debugging, and deployments."
      >
        {stateLoading && !state ? (
          <p className="animate-pulse text-sm text-slate-400">Loading latest pipeline events…</p>
        ) : (
          <Timeline items={timeline} />
        )}
      </Card>
    </div>
  );
}
