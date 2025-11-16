"use client";

import { useState } from "react";

import { ConfidenceBadge } from "@/components/analysis/confidence-badge";
import { SeverityIndicator } from "@/components/analysis/severity-indicator";
import type { ReviewSummary } from "@/types/backend";

type FindingItemProps = {
  finding: ReviewSummary["findings"][number];
  onFeedback: (findingId: string, reaction: string) => void;
};

export function FindingItem({ finding, onFeedback }: FindingItemProps): JSX.Element {
  const [selectedReaction, setSelectedReaction] = useState<string | null>(null);

  const handleClick = (reaction: string) => {
    setSelectedReaction(reaction);
    onFeedback(finding.id, reaction);
  };

  return (
    <div
      data-testid="finding-item"
      className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 shadow-inner shadow-black/30"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">{finding.message}</p>
          <p className="text-xs text-slate-500">
            {finding.file_path}:{finding.line_number} · {finding.type}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <SeverityIndicator severity={finding.severity} />
          <ConfidenceBadge confidence={finding.confidence} />
        </div>
      </div>
      {finding.suggested_fix ? (
        <p className="mt-3 text-xs text-emerald-200/80">
          Suggestion: {finding.suggested_fix}
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2 text-xs">
          {["implemented", "dismissed", "modified"].map((reaction) => (
            <button
              key={reaction}
              type="button"
              onClick={() => handleClick(reaction)}
              className={`rounded-full px-3 py-1 uppercase tracking-wide transition ${
                selectedReaction === reaction
                  ? "bg-brand-500/30 text-white"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {reaction}
            </button>
          ))}
      </div>
    </div>
  );
}
