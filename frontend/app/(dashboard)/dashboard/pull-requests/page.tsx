"use client";

import { Card } from "@/components/Card";
import { LoadingSpinner } from "@/components/common/loading-spinner";
import { PRList } from "@/components/pr/pr-list";
import { useOperations } from "@/hooks/usePRAnalysis";

export default function PullRequestsPage(): JSX.Element {
  const { data: operations, isLoading } = useOperations();
  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
          TraceFox
        </p>
        <h1 className="text-3xl font-semibold text-white">Pull Requests</h1>
        <p className="text-sm text-slate-400">
          Every webhook, analysis, and developer reaction flowing through TraceFox.
        </p>
      </div>
      <Card className="border border-slate-800 bg-slate-950/60 p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Tracked PRs</h2>
          {isLoading ? <LoadingSpinner /> : null}
        </div>
        <PRList
          registry={operations?.pr_registry ?? []}
          loading={isLoading}
        />
      </Card>
    </div>
  );
}
