"use client";

import Link from "next/link";

import { Card } from "@/components/Card";

const sections = [
  {
    title: "Getting Started",
    accent: "brand" as const,
    description:
      "Bootstrap a local TraceFox environment, seed configuration, and explore the mission-control dashboard.",
    items: [
      {
        heading: "1. Configure",
        body: "Copy .env.example to .env and tailor environment variables for your stack.",
      },
      {
        heading: "2. Launch",
        body: "Run docker-compose for Redis, Neo4j, and Qdrant, then start the API gateway via uvicorn.",
      },
      {
        heading: "3. Explore",
        body: "Fire a sample webhook from the dashboard to trigger indexing, reviews, and test orchestration.",
      },
    ],
  },
  {
    title: "API Reference",
    accent: "emerald" as const,
    description:
      "Primary endpoints powering TraceFox automation. All responses are JSON and secured via auth middleware in production modes.",
    items: [
      {
        heading: "POST /webhooks/{provider}",
        body: "Queue repository indexing and AI review from a Git provider payload.",
      },
      {
        heading: "POST /tests/generate",
        body: "Produce deterministic tests mapped to review findings by type.",
      },
      {
        heading: "POST /tests/execute",
        body: "Execute generated suites and stream execution summaries for RCA.",
      },
    ],
  },
  {
    title: "Observability & Resilience",
    accent: "amber" as const,
    description:
      "End-to-end telemetry baked into the 3.0 architecture. Tune thresholds via centralized configuration.",
    items: [
      {
        heading: "Distributed Tracing",
        body: "OpenTelemetry collectors receive spans from every service via the observability gateway.",
      },
      {
        heading: "Circuit Breaking",
        body: "Resilience orchestrator wraps external calls with backoff, jitter, and breaker thresholds set in TRACEFOX_* vars.",
      },
      {
        heading: "Learning Feedback",
        body: "Feedback endpoints update quality scoring, feeding the learning service and dashboard analytics.",
      },
    ],
  },
];

export default function DocsPage(): JSX.Element {
  return (
    <div className="space-y-8 pb-16">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.35em] text-slate-400">TraceFox Docs</p>
        <h1 className="text-3xl font-semibold text-white">Operational Handbook</h1>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/60 px-3 py-1 text-xs uppercase tracking-wide text-slate-300 transition hover:border-brand-400/60 hover:text-brand-200"
        >
          ← Control Center
        </Link>
        <p className="max-w-3xl text-sm text-slate-300">
          Your quick-start guide for orchestrating the TraceFox microservices platform. Pair this
          with the configuration article inside the repo&apos;s <code>docs/</code> directory for deeper
          operational playbooks.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-3">
        {sections.map((section) => (
          <Card key={section.title} title={section.title} accent={section.accent}>
            <p className="text-sm text-slate-200/90">{section.description}</p>
            <ul className="space-y-3 text-sm text-slate-100/90">
              {section.items.map((item) => (
                <li key={item.heading}>
                  <p className="font-semibold text-white">{item.heading}</p>
                  <p className="text-slate-300">{item.body}</p>
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </div>

      <footer className="rounded-3xl border border-slate-800/70 bg-slate-950/70 p-6 text-sm text-slate-200">
        Need more detail? Visit the in-repo <code>docs/configuration.md</code> or open a question in the
        TraceFox workspace. Return to the dashboard via the
        <Link href="/" className="ml-1 text-brand-300 underline underline-offset-4 hover:text-brand-200">
          control center
        </Link>
        .
      </footer>
    </div>
  );
}
