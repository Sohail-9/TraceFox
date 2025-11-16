"use client";

import type { OperationsSnapshot } from "@/types/backend";

import { PRCard } from "@/components/pr/pr-card";
import { LoadingSpinner } from "@/components/common/loading-spinner";

type DashboardPR = {
  prId: string;
  repository?: string;
  title?: string;
  author?: string;
  action?: string;
  status?: string;
  updatedAt?: string;
};

function mapRegistry(prRegistry: OperationsSnapshot["pr_registry"]): DashboardPR[] {
  return prRegistry.map((entry) => ({
    prId: entry.pr_id,
    repository: entry.repository_name,
    title: entry.pull_request_title,
    author: entry.pull_request_author,
    action: entry.action,
    status: entry.event_type,
    updatedAt: entry.received_at,
  }));
}

export function PRList({
  registry,
  loading,
}: {
  registry: OperationsSnapshot["pr_registry"];
  loading: boolean;
}): JSX.Element {
  if (loading) {
    return (
      <div className="flex justify-center py-10">
        <LoadingSpinner label="Loading pull requests" />
      </div>
    );
  }

  const items = mapRegistry(registry);
  if (!items.length) {
    return <p className="text-sm text-slate-500">No pull requests tracked yet.</p>;
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {items.map((pr) => (
        <PRCard key={pr.prId} pr={pr} />
      ))}
    </div>
  );
}
