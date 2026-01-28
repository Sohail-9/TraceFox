"use client";

import { useState } from "react";
import clsx from "clsx";
import type { ReviewSummary } from "@/types/backend";
import { GlassCard } from "@/components/ui/glass-card";

type FindingItemProps = {
  finding: ReviewSummary["findings"][number];
  onFeedback: (findingId: string, reaction: string) => void;
};

export function FindingItem({ finding, onFeedback }: FindingItemProps): JSX.Element {
  const [selectedReaction, setSelectedReaction] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  const severityConfig = {
    high: { color: "text-rose-400", bg: "bg-rose-500/10", border: "border-rose-500/20", icon: "🔴" },
    medium: { color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20", icon: "🟡" },
    low: { color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20", icon: "🟢" },
  }[finding.severity as "high" | "medium" | "low"] || {
    color: "text-slate-400", bg: "bg-slate-500/10", border: "border-slate-500/20", icon: "⚪"
  };

  return (
    <GlassCard
      intensity="low"
      className="group flex flex-col transition-all duration-300 hover:border-brand-500/30"
    >
      {/* Header Row */}
      <div
        className="flex cursor-pointer items-start justify-between gap-4 p-4"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex gap-4 flex-1">
          {/* Severity Icon */}
          <div className={clsx("mt-0.5 shrink-0 rounded-lg p-2 transition-colors", severityConfig.bg)}>
            <span className="text-lg">{severityConfig.icon}</span>
          </div>

          <div className="space-y-1.5 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className={clsx(
                "text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border",
                severityConfig.color, severityConfig.bg, severityConfig.border
              )}>
                {finding.severity}
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-2 py-0.5 rounded border border-white/5 bg-white/5">
                {finding.type.replace(/_/g, " ")}
              </span>
            </div>
            <h3 className="text-sm font-medium text-slate-200 leading-relaxed group-hover:text-brand-400 transition-colors">
              {finding.message}
            </h3>

            {/* Meta Info */}
            <div className="flex items-center gap-3 text-[11px] text-slate-500">
              <span className="font-mono text-indigo-400/80 hover:underline">{finding.file_path}:{finding.line_number}</span>
              <span className="opacity-30">•</span>
              <span>{Math.round(finding.confidence * 100)}% Confidence</span>
            </div>
          </div>
        </div>

        {/* Expand/Collapse Toggle */}
        <div className={clsx(
          "h-8 w-8 flex items-center justify-center rounded-full bg-white/5 transition-transform duration-300",
          expanded ? "rotate-180 bg-brand-500/20 text-brand-400" : "text-slate-500"
        )}>
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Expanded Content (Action Area) */}
      <div className={clsx(
        "bg-black/20 border-t border-white/5 transition-all duration-300 overflow-hidden",
        expanded ? "max-h-[500px] opacity-100" : "max-h-0 opacity-0"
      )}>
        <div className="p-4 space-y-4">
          {finding.suggested_fix && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Suggested Fix</span>
                <button className="text-[10px] text-brand-400 hover:text-brand-300">Apply Fix</button>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/40 p-3 overflow-x-auto">
                <pre className="font-mono text-xs text-emerald-400/90 whitespace-pre-wrap">
                  {finding.suggested_fix}
                </pre>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            <div className="text-[11px] text-slate-600">
              Is this finding helpful?
            </div>
            <div className="flex gap-2">
              {["helpful", "unhelpful"].map((reaction) => (
                <button
                  key={reaction}
                  onClick={(e) => { e.stopPropagation(); onFeedback(finding.id, reaction); setSelectedReaction(reaction); }}
                  className={clsx(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-all text-xs font-medium",
                    selectedReaction === reaction
                      ? reaction === "helpful" ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" : "bg-rose-500/10 border-rose-500/30 text-rose-400"
                      : "border-white/5 bg-white/5 text-slate-400 hover:bg-white/10"
                  )}
                >
                  <span>{reaction === "helpful" ? "👍" : "👎"}</span>
                  <span className="capitalize">{reaction}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}
