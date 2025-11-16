"use client";

import { useEffect, useMemo, useState } from "react";

import { Card } from "@/components/Card";
import { DashboardHeader } from "@/components/dashboard/header";
import { AnalyticsPanel } from "@/components/dashboard/AnalyticsPanel";
import { LoadingSpinner } from "@/components/common/loading-spinner";
import { PRAnalysisPanel } from "@/components/pr/pr-analysis-panel";
import { PRList } from "@/components/pr/pr-list";
import {
  submitFindingFeedback,
  useOperations,
  useReview,
} from "@/hooks/usePRAnalysis";
import { GitHubRepositoriesPanel } from "@/components/dashboard/GitHubRepositoriesPanel";

export default function DashboardPage(): JSX.Element {
  const [selectedPrId, setSelectedPrId] = useState<string | null>(null);
  const {
    data: operations,
    isLoading: operationsLoading,
    mutate: mutateOperations,
  } = useOperations();
  const activePrId = selectedPrId ?? operations?.active_pr_id ?? null;

  useEffect(() => {
    if (!selectedPrId) return;
    const exists = operations?.pr_registry?.some((entry) => entry.pr_id === selectedPrId);
    if (!exists) {
      setSelectedPrId(null);
    }
  }, [operations?.pr_registry, selectedPrId]);
  const {
    data: review,
    isLoading: reviewLoading,
    isValidating: reviewFetching,
    mutate: mutateReview,
  } = useReview(activePrId);

  const summaryCards = useMemo(() => {
    if (!operations) {
      return [
        { label: "Tracked PRs", value: 0 },
        { label: "Total Findings", value: 0 },
        { label: "Must Fix", value: 0 },
        { label: "Tests Generated", value: 0 },
      ];
    }
    return [
      { label: "Tracked PRs", value: operations.total_prs },
      { label: "Total Findings", value: operations.summary.total_findings },
      { label: "Must Fix", value: operations.summary.must_fix },
      { label: "Tests Generated", value: operations.tests.total_cases },
    ];
  }, [operations]);

  return (
    <div className="space-y-6">
      <DashboardHeader
        suggestedRepository={operations?.pr_registry?.[0]?.repository_name}
        suggestedPrNumber={operations?.pr_registry?.[0]?.pull_request_number}
        onAnalyzed={(_prId) => {
          mutateOperations();
        }}
      />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {summaryCards.map((card) => (
          <Card
            key={card.label}
            className="border border-slate-800 bg-slate-950/70 p-4"
          >
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
              {card.label}
            </p>
            <p className="text-2xl font-semibold text-white">{card.value}</p>
          </Card>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border border-slate-800 bg-slate-950/60 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
                Pull Requests
              </p>
              <h2 className="text-lg font-semibold">Recent Activity</h2>
            </div>
            {operationsLoading ? <LoadingSpinner /> : null}
          </div>
          <PRList
            registry={operations?.pr_registry ?? []}
            loading={operationsLoading}
            selectedPrId={selectedPrId ?? operations?.active_pr_id ?? null}
            onSelect={(prId) => setSelectedPrId(prId)}
          />
        </Card>
        <Card className="border border-slate-800 bg-slate-950/60 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
                Analysis
              </p>
              <h2 className="text-lg font-semibold">
                Active PR · {activePrId ?? "N/A"}
              </h2>
            </div>
            {reviewFetching ? <LoadingSpinner /> : null}
          </div>
          <PRAnalysisPanel
            review={review}
            loading={reviewLoading}
            onFeedback={(id, reaction) =>
              submitFindingFeedback(id, reaction, mutateReview)
            }
          />
        </Card>
      </div>
      {operations?.summary ? (
        <AnalyticsPanel summary={operations.summary} totalPrs={operations.total_prs} />
      ) : null}
      <GitHubRepositoriesPanel />
    </div>
  );
}
