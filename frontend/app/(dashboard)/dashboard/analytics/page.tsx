"use client";

import dynamic from "next/dynamic";

import { Card } from "@/components/Card";

const LazyChart = dynamic(
  () => import("@/components/analytics/chart").then((mod) => mod.AnalyticsChart),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-48 items-center justify-center text-xs uppercase tracking-[0.3em] text-slate-500">
        Loading chart…
      </div>
    ),
  }
);

export default function AnalyticsPage(): JSX.Element {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">TraceFox</p>
        <h1 className="text-3xl font-semibold text-white">Analytics</h1>
        <p className="text-sm text-slate-400">
          View trendlines for findings, confidence scores, and feedback adoption.
        </p>
      </div>
      <Card className="border border-slate-800 bg-slate-950/60 p-5">
        <LazyChart />
      </Card>
    </div>
  );
}
