"use client";

import clsx from "clsx";
import { FormEvent, useEffect, useMemo, useState } from "react";
import useSWR from "swr";

import { Card } from "@/components/Card";
import { getApiBaseUrl, postJson, swrFetcher } from "@/lib/api";
import type {
  GenerateTestsResponse,
  ReviewSummary,
  TestExecutionSummary,
  TestResultsResponse,
  RCAResponse,
  WebhookResponse,
} from "@/types/backend";

const defaultWebhookPayload = {
  event_type: "pull_request",
  action: "opened",
  repository: {
    id: "repo-123",
    name: "tracefox/backend",
    url: "https://github.com/tracefox/backend",
    default_branch: "main",
  },
  pull_request: {
    number: 42,
    title: "Add compliance checks",
    author: "sohail",
    source_branch: "feature/compliance",
    target_branch: "main",
    diff_url: "https://github.com/tracefox/backend/pull/42.diff",
  },
  files: [],
};

const severityStyles: Record<string, string> = {
  critical: "border-rose-400/50 bg-rose-500/10 text-rose-100",
  major: "border-amber-400/50 bg-amber-500/10 text-amber-100",
  minor: "border-emerald-400/50 bg-emerald-500/10 text-emerald-100",
};

const statusStyles: Record<string, string> = {
  passed: "border-emerald-400/40 bg-emerald-500/10 text-emerald-100",
  failed: "border-rose-400/40 bg-rose-500/10 text-rose-100",
  flaky: "border-amber-400/40 bg-amber-500/10 text-amber-100",
  skipped: "border-slate-500/40 bg-slate-500/10 text-slate-200",
  running: "border-brand-400/40 bg-brand-500/10 text-brand-100",
};

const pipelineStatusStyles: Record<PipelineStatus, string> = {
  done: "border-emerald-400/40 bg-emerald-500/10 text-emerald-100",
  active: "border-brand-400/50 bg-brand-500/10 text-brand-50",
  pending: "border-slate-700/60 bg-slate-900/60 text-slate-300",
};

const statToneStyles: Record<StatTone, string> = {
  rose: "border-rose-400/30 bg-rose-500/10",
  amber: "border-amber-400/30 bg-amber-500/10",
  emerald: "border-emerald-400/30 bg-emerald-500/10",
  brand: "border-brand-400/30 bg-brand-500/10",
  slate: "border-slate-600/60 bg-slate-900/60",
};

const activityToneStyles: Record<ActivityTone, string> = {
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-100",
  error: "border-rose-500/40 bg-rose-500/10 text-rose-100",
  info: "border-brand-400/40 bg-brand-500/10 text-brand-100",
  neutral: "border-slate-700/60 bg-slate-900/60 text-slate-300",
};

const executionToneBars: Record<string, string> = {
  Passed: "bg-emerald-400",
  Failed: "bg-rose-400",
  Flaky: "bg-amber-400",
  Skipped: "bg-slate-500",
};

type PipelineStatus = "done" | "active" | "pending";

type PipelineStep = {
  id: string;
  label: string;
  description: string;
  status: PipelineStatus;
};

type StatTone = "rose" | "amber" | "emerald" | "brand" | "slate";

type SummaryStat = {
  id: string;
  label: string;
  value: string;
  description: string;
  tone: StatTone;
};

type InsightTab = "findings" | "tests" | "rca";

type ActivityTone = "success" | "error" | "info" | "neutral";

type ActivityItem = {
  id: string;
  title: string;
  detail: string;
  tone: ActivityTone;
};

function formatTimestamp(value?: string) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function DashboardPage() {
  const [provider, setProvider] = useState("github");
  const [webhookBody, setWebhookBody] = useState(() =>
    JSON.stringify(defaultWebhookPayload, null, 2)
  );
  const [webhookStatus, setWebhookStatus] = useState<string | null>(null);
  const [webhookError, setWebhookError] = useState<string | null>(null);
  const [activePrId, setActivePrId] = useState<string | null>(null);
  const [prInput, setPrInput] = useState("repo-123:42");
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<
    "webhook" | "load" | "generate" | "execute" | null
  >(null);
  const [insightTab, setInsightTab] = useState<InsightTab>("findings");

  useEffect(() => {
    if (activePrId) {
      setPrInput(activePrId);
    }
  }, [activePrId]);

  const reviewKey = activePrId
    ? `/reviews/pr/${encodeURIComponent(activePrId)}?include_tests=true&include_rca=true`
    : null;

  const {
    data: review,
    error: reviewError,
    isLoading: reviewLoading,
    mutate: mutateReview,
  } = useSWR<ReviewSummary>(reviewKey, swrFetcher, {
    revalidateOnFocus: false,
  });

  const {
    data: executionResults,
    isLoading: executionLoading,
  } = useSWR<TestResultsResponse>(
    executionId ? `/tests/results/${executionId}` : null,
    swrFetcher,
    {
      refreshInterval: executionId ? 4000 : 0,
      revalidateOnFocus: false,
    }
  );

  const { data: rca } = useSWR<RCAResponse>(
    executionId ? `/rca/${executionId}` : null,
    swrFetcher,
    {
      refreshInterval: executionId ? 6000 : 0,
      revalidateOnFocus: false,
    }
  );

  const apiSource = getApiBaseUrl();
  const findings = review?.findings ?? [];
  const tests = review?.tests ?? [];

  const rcaItems = useMemo(() => {
    const map = new Map<string, RCAResponse>();
    (review?.rca ?? []).forEach((item) => map.set(item.id, item));
    if (rca) {
      map.set(rca.id, rca);
    }
    return Array.from(map.values());
  }, [review?.rca, rca]);

  const pipelineSteps = useMemo<PipelineStep[]>(() => {
    const steps = [
      {
        id: "webhook",
        label: "Webhook Received",
        description: "Ingest PR metadata and queue indexing jobs",
        complete: Boolean(activePrId || webhookStatus),
      },
      {
        id: "review",
        label: "AI Review",
        description: "Generate review summary and actionable findings",
        complete: Boolean(review),
      },
      {
        id: "tests",
        label: "Test Generation",
        description: "Produce deterministic tests mapped to findings",
        complete: tests.length > 0,
      },
      {
        id: "execution",
        label: "Test Execution",
        description: "Run prioritized suites and capture telemetry",
        complete: Boolean(executionResults),
      },
      {
        id: "rca",
        label: "Root Cause Analysis",
        description: "Synthesize failures into remediation guidance",
        complete: rcaItems.length > 0,
      },
    ];

    const firstIncomplete = steps.findIndex((step) => !step.complete);
    return steps.map((step, index) => ({
      id: step.id,
      label: step.label,
      description: step.description,
      status: step.complete
        ? "done"
        : index === firstIncomplete || firstIncomplete === -1
        ? "active"
        : "pending",
    }));
  }, [activePrId, executionResults, review, rcaItems.length, tests.length, webhookStatus]);

  const summaryStats = useMemo<SummaryStat[]>(() => {
    const passRate = executionResults && executionResults.total_tests > 0
      ? Math.round((executionResults.passed / executionResults.total_tests) * 100)
      : null;

    const passTone: StatTone = passRate === null
      ? "slate"
      : passRate >= 90
      ? "emerald"
      : passRate >= 70
      ? "amber"
      : "rose";

    return [
      {
        id: "critical",
        label: "Critical",
        value: String(review?.critical_count ?? 0),
        description: "Blocking issues that must be resolved before merge",
        tone: "rose",
      },
      {
        id: "major",
        label: "Major",
        value: String(review?.major_count ?? 0),
        description: "High-impact findings affecting reliability or security",
        tone: "amber",
      },
      {
        id: "tests",
        label: "Generated Tests",
        value: String(tests.length),
        description: "Ready-to-run suites mapped to review findings",
        tone: "brand",
      },
      {
        id: "pass-rate",
        label: "Pass Rate",
        value: passRate !== null ? `${passRate}%` : "—",
        description: executionResults
          ? `Latest run of ${executionResults.total_tests} tests`
          : "Awaiting the next execution",
        tone: passTone,
      },
    ];
  }, [executionResults, review, tests.length]);

  const insightNav = useMemo(
    () => [
      { id: "findings" as const, label: "Findings", count: findings.length },
      { id: "tests" as const, label: "Tests", count: tests.length },
      { id: "rca" as const, label: "RCA", count: rcaItems.length },
    ],
    [findings.length, rcaItems.length, tests.length]
  );

  const activityItems = useMemo<ActivityItem[]>(() => {
    const items: ActivityItem[] = [];
    if (webhookStatus) {
      items.push({
        id: "webhook-success",
        title: "Webhook accepted",
        detail: webhookStatus,
        tone: "success",
      });
    }
    if (webhookError) {
      items.push({
        id: "webhook-error",
        title: "Webhook failed",
        detail: webhookError,
        tone: "error",
      });
    }
    if (actionMessage) {
      items.push({
        id: "action-success",
        title: "Workflow updated",
        detail: actionMessage,
        tone: "success",
      });
    }
    if (actionError) {
      items.push({
        id: "action-error",
        title: "Action required",
        detail: actionError,
        tone: "error",
      });
    }
    if (reviewLoading) {
      items.push({
        id: "review-loading",
        title: "Review loading",
        detail: "Fetching AI insights for the selected pull request…",
        tone: "info",
      });
    }
    if (review) {
      items.push({
        id: `review-${review.review_id}`,
        title: "Review ready",
        detail: `${review.total_findings} findings surfaced for PR ${review.pr_id}`,
        tone: "success",
      });
    }
    if (executionResults) {
      const failed = executionResults.failed > 0;
      items.push({
        id: `execution-${executionResults.execution_id}`,
        title: "Execution update",
        detail: `${executionResults.status} · Passed ${executionResults.passed}/${executionResults.total_tests}`,
        tone: failed ? "info" : "success",
      });
    }
    if (rcaItems.length) {
      items.push({
        id: `rca-${rcaItems[0].id}`,
        title: "RCA insights ready",
        detail: `${rcaItems.length} remediation recommendations generated`,
        tone: "info",
      });
    }
    return items;
  }, [actionError, actionMessage, executionResults, review, reviewLoading, rcaItems, webhookError, webhookStatus]);

  const nextPipelineAction = pipelineSteps.find((step) => step.status === "active");

  function resetMessages() {
    setActionMessage(null);
    setActionError(null);
  }

  const handleWebhookSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    resetMessages();
    setLoadingAction("webhook");
    setWebhookStatus(null);
    setWebhookError(null);

    try {
      const payload = JSON.parse(webhookBody);
      const response = await postJson<WebhookResponse>(
        `/webhooks/${provider}`,
        payload
      );
      setWebhookStatus(response.message ?? "Webhook accepted.");
      const newPrId = payload?.repository?.id && payload?.pull_request?.number
        ? `${payload.repository.id}:${payload.pull_request.number}`
        : null;
      if (newPrId) {
        setActivePrId(newPrId);
        setExecutionId(null);
      }
    } catch (error) {
      setWebhookError(
        error instanceof Error ? error.message : "Unable to submit webhook payload."
      );
    } finally {
      setLoadingAction(null);
    }
  };

  const handleLoadReview = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    resetMessages();
    setWebhookStatus(null);
    setWebhookError(null);

    if (!prInput.trim()) {
      setActionError("Enter a PR identifier in the form <repository-id>:<pr-number>.");
      return;
    }

    setLoadingAction("load");
    setActivePrId(prInput.trim());
    setExecutionId(null);
    setTimeout(() => setLoadingAction(null), 0);
  };

  const handleGenerateTests = async () => {
    if (!review) {
      setActionError("Load a review before generating tests.");
      return;
    }
    resetMessages();
    setLoadingAction("generate");

    try {
      const body = {
        pr_id: review.pr_id,
        finding_ids: review.findings.map((finding) => finding.id),
        test_types: ["unit", "integration"],
        prioritize: true,
      };
      const response = await postJson<GenerateTestsResponse>(
        "/tests/generate",
        body
      );
      setActionMessage(
        `Queued ${response.total_generated ?? response.test_cases.length} tests for generation.`
      );
      await mutateReview();
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Unable to queue test generation."
      );
    } finally {
      setLoadingAction(null);
    }
  };

  const handleExecuteTests = async () => {
    if (!review) {
      setActionError("Load a review before executing tests.");
      return;
    }
    const testIds = (review.tests ?? []).map((test) => test.id);
    if (!testIds.length) {
      setActionError("Generate tests before executing them.");
      return;
    }

    resetMessages();
    setLoadingAction("execute");

    try {
      const summary = await postJson<TestExecutionSummary>("/tests/execute", {
        pr_id: review.pr_id,
        test_case_ids: testIds,
        parallel: true,
        timeout_seconds: 300,
      });
      setExecutionId(summary.execution_id);
      setActionMessage(
        `Execution ${summary.execution_id} started for ${summary.total_tests} tests.`
      );
      await mutateReview();
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Unable to execute tests."
      );
    } finally {
      setLoadingAction(null);
    }
  };

  const executionBreakdown = useMemo(() => {
    if (!executionResults) {
      return [] as Array<{ label: string; value: number }>;
    }
    return [
      { label: "Passed", value: executionResults.passed },
      { label: "Failed", value: executionResults.failed },
      { label: "Flaky", value: executionResults.flaky },
      { label: "Skipped", value: executionResults.skipped },
    ];
  }, [executionResults]);

  const executionTotal = executionResults?.total_tests ?? 0;

  return (
    <div className="space-y-10 pb-16">
      <section className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/60 p-8 shadow-[0_0_80px_-32px_rgba(79,70,229,0.45)]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(79,70,229,0.35),transparent)]" />
        <div className="relative z-10 flex flex-col gap-8 md:flex-row md:items-center md:justify-between">
          <div className="max-w-2xl space-y-4">
            <p className="text-xs uppercase tracking-[0.4em] text-slate-400">
              TraceFox Mission Control
            </p>
            <h1 className="text-3xl font-semibold text-white md:text-4xl">
              Orchestrate reviews, testing, and RCA with confidence
            </h1>
            <p className="text-sm text-slate-300 md:text-base">
              Drive resilient delivery by coordinating AI reviews, deterministic tests, and
              automated remediation. Everything you need to evaluate a pull request lives in one
              adaptive workspace.
            </p>
          </div>
          <div className="flex w-full flex-col gap-4 md:max-w-xs">
            <div className="rounded-2xl border border-slate-700/70 bg-slate-900/70 px-4 py-3 text-xs uppercase tracking-wide text-slate-300">
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-400">API Source</span>
                <span className="inline-flex items-center gap-2 text-white">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
                  {apiSource}
                </span>
              </div>
            </div>
            <div className="rounded-2xl border border-slate-700/70 bg-slate-900/70 px-4 py-3 text-xs uppercase tracking-wide text-slate-300">
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-400">Next Action</span>
                <span className="text-white">
                  {nextPipelineAction ? nextPipelineAction.label : "Awaiting webhook"}
                </span>
              </div>
            </div>
            {activePrId ? (
              <div className="rounded-2xl border border-brand-500/40 bg-brand-500/10 px-4 py-3 text-xs uppercase tracking-wide text-brand-100">
                <div className="flex items-center justify-between gap-2">
                  <span>Active PR</span>
                  <span>{activePrId}</span>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card title="Pipeline Overview" accent="brand" icon={<span>🛰️</span>}>
          <ol className="space-y-4">
            {pipelineSteps.map((step) => (
              <li
                key={step.id}
                className={clsx(
                  "flex flex-col gap-1 rounded-2xl border px-4 py-3 text-sm shadow",
                  pipelineStatusStyles[step.status]
                )}
              >
                <div className="flex items-center justify-between text-xs uppercase tracking-wide">
                  <span>{step.label}</span>
                  <span className="text-slate-200">
                    {step.status === "done"
                      ? "Complete"
                      : step.status === "active"
                      ? "In progress"
                      : "Queued"}
                  </span>
                </div>
                <p className="text-slate-100/90">{step.description}</p>
              </li>
            ))}
          </ol>
        </Card>

        <Card title="Live Status" accent="emerald" icon={<span>📊</span>}>
          <dl className="grid gap-4 sm:grid-cols-2">
            {summaryStats.map((stat) => (
              <div
                key={stat.id}
                className={clsx(
                  "rounded-2xl border px-4 py-3 shadow-inner shadow-black/20",
                  statToneStyles[stat.tone]
                )}
              >
                <dt className="text-xs uppercase tracking-wide text-slate-300">{stat.label}</dt>
                <dd className="mt-1 text-2xl font-semibold text-white">{stat.value}</dd>
                <p className="mt-1 text-xs text-slate-300/90">{stat.description}</p>
              </div>
            ))}
          </dl>
        </Card>
      </div>

      <Card title="Operations Console" accent="brand" icon={<span>🛠️</span>} footer="Use sample payloads to iterate quickly, then replay real PR webhooks from your Git provider for full-fidelity validation.">
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
          <form className="space-y-4" onSubmit={handleWebhookSubmit}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <label className="text-xs uppercase tracking-wide text-slate-300">Provider</label>
                <select
                  value={provider}
                  onChange={(event) => setProvider(event.target.value)}
                  className="w-32 rounded-xl border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-200 focus:border-brand-400 focus:outline-none"
                >
                  <option value="github">github</option>
                  <option value="gitlab">gitlab</option>
                  <option value="bitbucket">bitbucket</option>
                </select>
              </div>
              <button
                type="button"
                onClick={() => setWebhookBody(JSON.stringify(defaultWebhookPayload, null, 2))}
                className="rounded-xl border border-slate-700 bg-slate-950 px-3 py-1 text-xs font-semibold text-slate-300 transition hover:border-brand-400 hover:text-white"
              >
                Reset payload
              </button>
            </div>
            <textarea
              value={webhookBody}
              onChange={(event) => setWebhookBody(event.target.value)}
              spellCheck={false}
              rows={16}
              className="w-full rounded-2xl border border-slate-800 bg-slate-950/80 p-4 font-mono text-xs leading-relaxed text-slate-200 shadow-inner shadow-black/40 focus:border-brand-400 focus:outline-none"
            />
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={loadingAction === "webhook"}
                className="inline-flex items-center justify-center rounded-xl bg-brand-500 px-4 py-2 text-sm font-semibold text-white shadow transition hover:bg-brand-400 disabled:cursor-not-allowed disabled:bg-brand-700"
              >
                {loadingAction === "webhook" ? "Submitting…" : "Send Webhook"}
              </button>
              {webhookStatus ? (
                <span className="text-xs text-emerald-300">{webhookStatus}</span>
              ) : null}
              {webhookError ? (
                <span className="text-xs text-rose-300">{webhookError}</span>
              ) : null}
            </div>
          </form>

          <div className="space-y-6">
            <form className="space-y-4" onSubmit={handleLoadReview}>
              <label className="flex flex-col gap-2 text-xs uppercase tracking-wide text-slate-300">
                Pull Request Identifier
                <input
                  value={prInput}
                  onChange={(event) => setPrInput(event.target.value)}
                  placeholder="repo-id:pr-number"
                  className="rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-emerald-400 focus:outline-none"
                />
              </label>
              <button
                type="submit"
                disabled={loadingAction === "load"}
                className="inline-flex items-center justify-center rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-emerald-700"
              >
                {loadingAction === "load" ? "Loading…" : "Load Review"}
              </button>
            </form>

            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 shadow-inner shadow-black/30">
              <p className="text-xs uppercase tracking-wide text-slate-400">Quick actions</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={handleGenerateTests}
                  disabled={loadingAction === "generate" || !review}
                  className="inline-flex items-center justify-center rounded-xl border border-emerald-400/60 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-100 shadow transition hover:border-emerald-300 hover:text-emerald-50 disabled:cursor-not-allowed disabled:border-slate-700 disabled:text-slate-500"
                >
                  {loadingAction === "generate" ? "Generating…" : "Generate Tests"}
                </button>
                <button
                  type="button"
                  onClick={handleExecuteTests}
                  disabled={loadingAction === "execute" || !review}
                  className="inline-flex items-center justify-center rounded-xl border border-brand-400/60 bg-brand-500/10 px-4 py-2 text-sm font-semibold text-brand-100 shadow transition hover:border-brand-300 hover:text-brand-50 disabled:cursor-not-allowed disabled:border-slate-700 disabled:text-slate-500"
                >
                  {loadingAction === "execute" ? "Executing…" : "Execute Tests"}
                </button>
              </div>
              {actionMessage ? (
                <p className="mt-3 text-xs text-emerald-300">{actionMessage}</p>
              ) : null}
              {actionError ? (
                <p className="mt-3 text-xs text-rose-300">{actionError}</p>
              ) : null}
              {reviewError ? (
                <p className="mt-3 text-xs text-rose-300">
                  {reviewError instanceof Error ? reviewError.message : "Unable to load review."}
                </p>
              ) : null}
              {reviewLoading && !review ? (
                <p className="mt-3 text-xs text-slate-400">Fetching review details…</p>
              ) : null}
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-xs uppercase tracking-wide text-slate-300">
                <div className="flex items-center justify-between">
                  <span>Review Status</span>
                  <span className="text-white">
                    {review ? "Ready" : reviewLoading ? "Loading…" : "Awaiting load"}
                  </span>
                </div>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-xs uppercase tracking-wide text-slate-300">
                <div className="flex items-center justify-between">
                  <span>Execution Status</span>
                  <span className="text-white">
                    {executionResults ? executionResults.status : executionId ? "Awaiting results" : "Idle"}
                  </span>
                </div>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-xs uppercase tracking-wide text-slate-300 md:col-span-2">
                <div className="flex items-center justify-between">
                  <span>RCA Insights</span>
                  <span className="text-white">
                    {rcaItems.length ? `${rcaItems.length} available` : "Pending execution"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card title="Insights" accent="rose" icon={<span>🧠</span>}>
          <div className="inline-flex rounded-full border border-rose-400/40 bg-rose-500/10 p-1 text-xs font-semibold text-rose-100">
            {insightNav.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setInsightTab(tab.id)}
                className={clsx(
                  "flex items-center gap-2 rounded-full px-4 py-1.5 transition",
                  insightTab === tab.id
                    ? "bg-slate-950/80 text-white"
                    : "text-rose-100/70 hover:text-white"
                )}
              >
                {tab.label}
                <span className="rounded-full bg-rose-500/40 px-2 py-0.5 text-[10px] uppercase tracking-wide">
                  {tab.count}
                </span>
              </button>
            ))}
          </div>

          {insightTab === "findings" ? (
            <div className="space-y-4">
              {review?.summary ? (
                <div className="rounded-2xl border border-rose-400/40 bg-rose-500/10 p-4 text-sm text-rose-100 shadow-inner shadow-rose-900/40">
                  <p className="font-semibold">{review.summary}</p>
                  <p className="mt-2 text-xs text-rose-100/80">
                    Last updated {formatTimestamp(review.created_at)}
                  </p>
                </div>
              ) : null}
              {findings.length ? (
                <ul className="space-y-3">
                  {findings.map((finding) => {
                    const severity = finding.severity?.toLowerCase() ?? "minor";
                    const severityClass = severityStyles[severity] ?? severityStyles.minor;
                    return (
                      <li
                        key={finding.id}
                        className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 shadow-inner shadow-black/40"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <h3 className="text-sm font-semibold text-slate-100">
                            {finding.file_path}:{finding.line_number}
                          </h3>
                          <span
                            className={clsx(
                              "rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider",
                              severityClass
                            )}
                          >
                            {finding.severity.toUpperCase()} · {finding.category}
                          </span>
                        </div>
                        <p className="mt-3 text-sm text-slate-200">{finding.description}</p>
                        {finding.suggested_fix ? (
                          <p className="mt-2 text-xs text-emerald-200/80">
                            Suggestion: {finding.suggested_fix}
                          </p>
                        ) : null}
                        <p className="mt-2 text-xs text-slate-400">
                          Confidence: {(finding.confidence_score * 100).toFixed(0)}%
                        </p>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="text-sm text-slate-400">No findings recorded yet.</p>
              )}
            </div>
          ) : null}

          {insightTab === "tests" ? (
            <div className="space-y-3">
              {tests.length ? (
                <ul className="space-y-3">
                  {tests.map((test) => (
                    <li
                      key={test.id}
                      className="rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4 text-amber-50 shadow-inner shadow-amber-900/40"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs uppercase tracking-wide">
                        <span>{test.test_name}</span>
                        <span>{test.test_type}</span>
                        <span>Priority P{test.priority}</span>
                      </div>
                      <pre className="mt-3 max-h-48 overflow-auto rounded-xl bg-black/40 p-3 text-xs text-amber-100">
                        <code>{test.test_code}</code>
                      </pre>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-400">
                  No generated tests yet. Queue test generation to seed execution.
                </p>
              )}
            </div>
          ) : null}

          {insightTab === "rca" ? (
            <div className="space-y-4">
              {rcaItems.length ? (
                <ul className="space-y-4">
                  {rcaItems.map((item) => (
                    <li
                      key={item.id}
                      className="rounded-2xl border border-rose-400/40 bg-rose-500/10 p-4 text-rose-100 shadow-inner shadow-rose-900/40"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3 text-xs uppercase tracking-wide">
                        <span>Execution: {item.test_execution_id}</span>
                        <span>Category: {item.category}</span>
                        <span>Confidence: {(item.confidence_score * 100).toFixed(0)}%</span>
                      </div>
                      <p className="mt-3 text-sm font-medium">{item.root_cause_summary}</p>
                      <pre className="mt-2 whitespace-pre-wrap text-xs text-rose-100/80">
{JSON.stringify(item.root_cause_details, null, 2)}
                      </pre>
                      {item.suggested_fixes.length ? (
                        <div className="mt-3 space-y-2 text-xs text-rose-100/80">
                          <p className="font-semibold uppercase tracking-wide text-rose-200/80">
                            Suggested fixes
                          </p>
                          {item.suggested_fixes.map((fix, idx) => (
                            <pre key={idx} className="rounded-xl bg-black/30 p-3">
                              {JSON.stringify(fix, null, 2)}
                            </pre>
                          ))}
                        </div>
                      ) : null}
                      {item.prevention_recommendations.length ? (
                        <div className="mt-3 space-y-1 text-xs text-rose-100/80">
                          <p className="font-semibold uppercase tracking-wide text-rose-200/80">
                            Prevention recommendations
                          </p>
                          <ul className="list-disc space-y-1 pl-5">
                            {item.prevention_recommendations.map((rec) => (
                              <li key={rec}>{rec}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-400">
                  RCA insights will appear as soon as a test execution produces failures.
                </p>
              )}
            </div>
          ) : null}
        </Card>

        <Card title="Activity Feed" accent="amber" icon={<span>📡</span>}>
          {activityItems.length ? (
            <ul className="space-y-3 text-sm">
              {activityItems.map((item) => (
                <li
                  key={item.id}
                  className={clsx(
                    "rounded-2xl border px-4 py-3 shadow-inner shadow-black/30",
                    activityToneStyles[item.tone]
                  )}
                >
                  <p className="text-xs uppercase tracking-wide text-slate-200/80">{item.title}</p>
                  <p className="mt-1 text-slate-100/90">{item.detail}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-400">
              Initiate a webhook or load an existing PR to populate the activity feed.
            </p>
          )}
        </Card>
      </div>

      {executionId ? (
        <Card
          title="Test Execution"
          accent="brand"
          icon={<span>🚀</span>}
          action={<span>ID: {executionId}</span>}
          footer="Execution results refresh automatically while in progress."
        >
          {executionLoading && !executionResults ? (
            <p className="text-sm text-slate-400">Awaiting execution results…</p>
          ) : null}
          {executionResults ? (
            <div className="space-y-6">
              <div className="space-y-3">
                <div className="grid gap-3 text-sm text-slate-200 md:grid-cols-2">
                  <span>Status: {executionResults.status}</span>
                  <span>Total: {executionResults.total_tests}</span>
                  <span>Passed: {executionResults.passed}</span>
                  <span>Failed: {executionResults.failed}</span>
                  <span>Flaky: {executionResults.flaky}</span>
                  <span>Duration: {(executionResults.execution_time_ms / 1000).toFixed(1)}s</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                  <div className="flex h-full">
                    {executionBreakdown.map((part) => {
                      const toneClass = executionToneBars[part.label] ?? "bg-slate-700";
                      return (
                        <div
                          key={part.label}
                          className={clsx("h-full", toneClass)}
                          style={{
                            width: executionTotal
                              ? `${(part.value / executionTotal) * 100}%`
                              : "0%",
                          }}
                        />
                      );
                    })}
                  </div>
                </div>
              </div>
              <ul className="space-y-3">
                {executionResults.results.map((result) => {
                  const style = statusStyles[result.status] ?? statusStyles.running;
                  return (
                    <li
                      key={result.execution_id}
                      className={clsx("rounded-2xl border p-4 text-sm shadow", style)}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs uppercase tracking-wide">
                        <span>{result.test_name}</span>
                        <span>{result.status}</span>
                        <span>{(result.execution_time_ms / 1000).toFixed(2)}s</span>
                      </div>
                      {result.error_message ? (
                        <p className="mt-2 text-xs text-rose-100/90">{result.error_message}</p>
                      ) : null}
                      {result.stack_trace ? (
                        <pre className="mt-2 max-h-40 overflow-auto rounded-xl bg-black/40 p-3 text-xs text-slate-200">
                          <code>{result.stack_trace}</code>
                        </pre>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
        </Card>
      ) : null}
    </div>
  );
}
