"use client";

import clsx from "clsx";
import Link from "next/link";

import { Card } from "@/components/Card";

type StatusLevel = "operational" | "degraded" | "maintenance";

const statusTone: Record<StatusLevel, string> = {
  operational: "border-emerald-400/40 bg-emerald-500/10 text-emerald-100",
  degraded: "border-amber-400/40 bg-amber-500/10 text-amber-100",
  maintenance: "border-slate-600/60 bg-slate-900/60 text-slate-300",
};

const serviceStatuses = [
  {
    name: "API Gateway",
    status: "operational" as StatusLevel,
    lastUpdated: "5 minutes ago",
    detail: "Accepting webhooks, serving reviews, and orchestrating downstream workflows.",
  },
  {
    name: "Review Engine",
    status: "operational" as StatusLevel,
    lastUpdated: "12 minutes ago",
    detail: "AI model pool healthy. Latest review latency p95 at 2.1s.",
  },
  {
    name: "Test Generation",
    status: "operational" as StatusLevel,
    lastUpdated: "2 minutes ago",
    detail: "Queue depth 0.5x capacity. Deterministic prompt templates in sync (v3.0).",
  },
  {
    name: "Test Execution",
    status: "degraded" as StatusLevel,
    lastUpdated: "1 minute ago",
    detail: "Experiencing intermittent flaky runs on macOS executor pod TF-EXEC-04. Failover in progress.",
  },
  {
    name: "RCA Engine",
    status: "operational" as StatusLevel,
    lastUpdated: "9 minutes ago",
    detail: "Correlating failures with commit graph. No incident alerts.",
  },
  {
    name: "Observability Pipeline",
    status: "maintenance" as StatusLevel,
    lastUpdated: "Scheduled",
    detail: "Planned upgrade window 22:00-22:30 UTC. Metrics ingest paused; traces unaffected.",
  },
];

export default function StatusPage(): JSX.Element {
  return (
    <div className="space-y-8 pb-16">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.4em] text-slate-400">TraceFox Status</p>
        <h1 className="text-3xl font-semibold text-white">Platform Health</h1>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/60 px-3 py-1 text-xs uppercase tracking-wide text-slate-300 transition hover:border-brand-400/60 hover:text-brand-200"
        >
          ← Control Center
        </Link>
        <p className="max-w-3xl text-sm text-slate-300">
          Real-time snapshot of core TraceFox microservices. Subscribe to incident alerts from your
          observability stack or revisit this panel for the latest updates.
        </p>
      </header>

      <Card title="Service Overview" accent="brand" icon={<span>🩺</span>}>
        <ul className="space-y-3">
          {serviceStatuses.map((service) => (
            <li
              key={service.name}
              className={clsx(
                "rounded-2xl border px-4 py-3 shadow-inner shadow-black/30",
                statusTone[service.status]
              )}
            >
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs uppercase tracking-wide">
                <span className="text-white">{service.name}</span>
                <span className="font-semibold">
                  {service.status === "operational" && "Operational"}
                  {service.status === "degraded" && "Degraded"}
                  {service.status === "maintenance" && "Maintenance"}
                </span>
                <span className="text-slate-200">Updated {service.lastUpdated}</span>
              </div>
              <p className="mt-2 text-sm text-slate-100/90">{service.detail}</p>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="Next Steps" accent="emerald" icon={<span>🔔</span>}>
        <p className="text-sm text-slate-200/90">
          Tie this status page to your incident response tooling. Hook into Alertmanager or PagerDuty
          for automatic notifications, and publish the JSON feed directly from the observability
          gateway once wired.
        </p>
      </Card>
    </div>
  );
}
