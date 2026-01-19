"use client";

import type { ReviewSummary } from "@/types/backend";

import { FindingItem } from "@/components/analysis/finding-item";

type FindingsListProps = {
  findings: ReviewSummary["findings"];
  onFeedback: (findingId: string, reaction: string) => void;
};

export function FindingsList({ findings, onFeedback }: FindingsListProps): JSX.Element {
  if (!findings.length) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted">No findings available for this PR.</p>
        <p className="text-sm text-muted">Run an analysis to generate findings for this pull request.</p>
      </div>
    );
  }
  return (
    <div className="space-y-3" data-testid="findings-list">
      {findings.map((finding) => (
        <FindingItem key={finding.id} finding={finding} onFeedback={onFeedback} />
      ))}
    </div>
  );
}
