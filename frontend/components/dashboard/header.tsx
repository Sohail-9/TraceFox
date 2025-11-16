"use client";

import { useEffect, useState } from "react";

import { useToast } from "@/components/ToastProvider";
import { apiClient } from "@/lib/api-client";
import type { ManualAnalysisPayload } from "@/types/backend";

export function DashboardHeader({
  onAnalyzed,
  suggestedRepository,
  suggestedPrNumber,
}: {
  onAnalyzed: (prId: string) => void;
  suggestedRepository?: string | null;
  suggestedPrNumber?: number | null;
}): JSX.Element {
  const { addToast } = useToast();
  const [form, setForm] = useState<ManualAnalysisPayload>({
    repository: "",
    pr_number: NaN,
    diff: "",
    changed_files: [],
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!form.repository && suggestedRepository) {
      setForm((prev) => ({ ...prev, repository: suggestedRepository }));
    }
  }, [form.repository, suggestedRepository]);

  useEffect(() => {
    if ((Number.isNaN(form.pr_number) || !form.pr_number) && suggestedPrNumber) {
      setForm((prev) => ({ ...prev, pr_number: suggestedPrNumber }));
    }
  }, [form.pr_number, suggestedPrNumber]);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const response = await apiClient.analyzePullRequest(form);
      addToast({
        tone: "success",
        title: "Analysis queued",
        description: `Tracked as ${response.pr_id}`,
      });
      onAnalyzed(response.pr_id);
    } catch (error) {
      addToast({
        tone: "error",
        title: "Unable to analyze PR",
        description:
          error instanceof Error ? error.message : "Unexpected error occurred",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-950/60 px-6 py-5 shadow-xl shadow-black/40">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.4em] text-slate-500">
            Welcome back
          </p>
          <h1 className="text-3xl font-semibold text-white">Control Center</h1>
          <p className="text-sm text-slate-400">
            Monitor GitHub/GitLab pull requests, visualize AI reasoning, and push fixes faster.
          </p>
        </div>
        <form
          className="grid gap-2 text-xs text-slate-200 md:grid-cols-4"
          onSubmit={(event) => {
            event.preventDefault();
            handleSubmit();
          }}
        >
          <div className="flex flex-col">
            <label className="text-[10px] uppercase tracking-[0.35em] text-slate-500">
              Repository
            </label>
            <input
              className="rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2"
              placeholder="owner/repo"
              value={form.repository}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, repository: event.target.value }))
              }
            />
          </div>
          <div className="flex flex-col">
            <label className="text-[10px] uppercase tracking-[0.35em] text-slate-500">
              PR #
            </label>
            <input
              type="number"
              className="w-24 rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2"
              placeholder="#"
              value={Number.isNaN(form.pr_number) ? "" : form.pr_number}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  pr_number: Number(event.target.value),
                }))
              }
            />
          </div>
          <div className="flex flex-col md:col-span-2">
            <label className="text-[10px] uppercase tracking-[0.35em] text-slate-500">
              Changed Files (comma separated)
            </label>
            <input
              className="rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2"
              placeholder="src/app.ts, src/utils/logger.ts"
              value={form.changed_files?.join(", ") ?? ""}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  changed_files: event.target.value
                    .split(",")
                    .map((entry) => entry.trim())
                    .filter(Boolean),
                }))
              }
            />
          </div>
          <div className="flex flex-col md:col-span-3">
            <label className="text-[10px] uppercase tracking-[0.35em] text-slate-500">
              Diff Snippet
            </label>
            <textarea
              className="h-20 rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2"
              placeholder="Paste diff snippet or file content…"
              value={form.diff}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, diff: event.target.value }))
              }
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              className="w-full rounded-2xl bg-brand-500 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:bg-brand-400 disabled:opacity-50"
              disabled={loading}
            >
              {loading ? "Analyzing…" : "Analyze PR"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
