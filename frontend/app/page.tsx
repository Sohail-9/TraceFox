import { fetchJson } from "@/lib/api";
import { Card } from "@/components/Card";
import { KPIGrid } from "@/components/Kpis";
import { Timeline } from "@/components/Timeline";
import { NotificationList } from "@/components/Notifications";
import type { AnalyticsReport, PipelineState } from "@/types/pipeline";

async function getPipelineState(): Promise<PipelineState> {
  try {
    return await fetchJson<PipelineState>("/state");
  } catch (error) {
    console.error(error);
    return {
      latest_report: null,
      last_commit: null,
      last_deployment: null,
    };
  }
}

async function getLatestAnalytics(): Promise<AnalyticsReport | null> {
  try {
    return await fetchJson<AnalyticsReport>("/analytics/latest");
  } catch (error) {
    console.warn("No analytics report yet", error);
    return null;
  }
}

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

function timelineFromState(state: PipelineState) {
  const items: { title: string; timestamp?: string; details?: string[] }[] = [];

  const commit = state.last_commit as Record<string, any> | null;
  if (commit) {
    items.push({
      title: `Commit ${commit.event?.repository ?? "repository"}`,
      timestamp: commit.event?.timestamp,
      details: [
        `Overall risk: ${commit.code_analysis?.summary?.overall_risk ?? "unknown"}`,
        `Generated tests: ${commit.test_generation?.tests?.length ?? 0}`,
      ].filter(Boolean),
    });
  }

  const deployment = state.last_deployment as Record<string, any> | null;
  if (deployment) {
    items.push({
      title: `Deployment ${deployment.deployment?.deployment_id ?? "event"}`,
      timestamp: deployment.deployment?.timestamp,
      details: (deployment.alerts as Array<Record<string, any>> | undefined)?.map(
        (alert) => `${alert.metric}: ${alert.observed} (baseline ${alert.baseline})`
      ),
    });
  }

  return items;
}

export default async function DashboardPage() {
  const [state, latestAnalytics] = await Promise.all([
    getPipelineState(),
    getLatestAnalytics(),
  ]);

  const report = latestAnalytics ?? state.latest_report;
  const kpis = buildKpis(report ?? null);
  const insights = report?.insights ?? [];
  const notifications = (state.last_commit as Record<string, any> | null)?.notification ??
    (state.last_deployment as Record<string, any> | null)?.notification ?? null;
  const timeline = timelineFromState(state);

  return (
    <main className="space-y-10">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white">DevGuardian Control Center</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-300">
            Observe code intelligence, testing, and production telemetry in one place. The dashboard
            auto-refreshes every few seconds to surface the most recent commit and deployment signals.
          </p>
        </div>
        <div className="rounded-full border border-brand-400/40 bg-brand-500/10 px-4 py-2 text-xs uppercase tracking-wide text-brand-100">
          API Source: {process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}
        </div>
      </header>

      <KPIGrid metrics={kpis} />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Latest Insights" accent="emerald">
          {insights.length ? (
            <ul className="list-disc space-y-2 pl-5">
              {insights.map((insight) => (
                <li key={insight} className="text-sm text-slate-200">
                  {insight}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-400">Insights appear once the pipeline has analyzed a commit.</p>
          )}
        </Card>

        <Card title="Notifications" accent="rose">
          <NotificationList notifications={notifications} />
        </Card>

        <Card title="Production Alerts" accent="amber">
          {timeline.filter((item) => item.title.startsWith("Deployment")).flatMap((item) => item.details ?? []).length ? (
            <ul className="list-disc space-y-2 pl-5 text-sm text-slate-100">
              {timeline
                .filter((item) => item.title.startsWith("Deployment"))
                .flatMap((item) => item.details ?? [])
                .map((detail) => (
                  <li key={detail}>{detail}</li>
                ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-400">No anomalies detected in the last deployment.</p>
          )}
        </Card>
      </div>

      <Card title="Lifecycle Timeline" accent="brand" footer="Trace commits through tests, debugging, and deployments.">
        <Timeline items={timeline} />
      </Card>
    </main>
  );
}

