"use client";

import clsx from "clsx";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import useSWR from "swr";

import { Card } from "@/components/Card";
import { Skeleton } from "@/components/Skeleton";
import { useToast } from "@/components/ToastProvider";
import { fetchJson, getApiBaseUrl, postJson, swrFetcher } from "@/lib/api";
import {
  bootstrapGitHubRepository,
  fetchGitHubRepositories,
  fetchTrackedRepositories,
  trackGitHubRepository,
} from "@/lib/github";
import {
  SessionState,
  SessionUser,
  clearSession,
  loadSession,
  rememberOAuthState,
  storeSession,
} from "@/lib/session";
import type {
  GenerateTestsResponse,
  RCAResponse,
  OperationsSnapshot,
  ReviewSummary,
  TestExecutionSummary,
  TestResultsResponse,
  WebhookResponse,
  GitHubRepositorySummary,
  GitHubTrackedRepository,
  GitHubCloneJob,
} from "@/types/backend";

const SEVERITY_STYLES: Record<string, string> = {
  critical: "border-rose-400/50 bg-rose-500/10 text-rose-100",
  major: "border-amber-400/50 bg-amber-500/10 text-amber-100",
  minor: "border-emerald-400/50 bg-emerald-500/10 text-emerald-100",
};

const EXECUTION_STATUS_STYLES: Record<string, string> = {
  passed: "border-emerald-400/40 bg-emerald-500/10 text-emerald-100",
  failed: "border-rose-400/40 bg-rose-500/10 text-rose-100",
  flaky: "border-amber-400/40 bg-amber-500/10 text-amber-100",
  skipped: "border-slate-500/40 bg-slate-500/10 text-slate-200",
  running: "border-brand-400/40 bg-brand-500/10 text-brand-100",
};

const PIPELINE_STATUS_STYLES = {
  done: "border-emerald-400/40 bg-emerald-500/10 text-emerald-100",
  active: "border-brand-400/50 bg-brand-500/10 text-brand-50",
  pending: "border-slate-700/60 bg-slate-900/60 text-slate-300",
} as const;

const STAT_TONE_STYLES = {
  rose: "border-rose-400/30 bg-rose-500/10",
  amber: "border-amber-400/30 bg-amber-500/10",
  emerald: "border-emerald-400/30 bg-emerald-500/10",
  brand: "border-brand-400/30 bg-brand-500/10",
  slate: "border-slate-600/60 bg-slate-900/60",
} as const;

const ACTIVITY_TONE_STYLES = {
  success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-100",
  error: "border-rose-500/40 bg-rose-500/10 text-rose-100",
  info: "border-brand-400/40 bg-brand-500/10 text-brand-100",
  neutral: "border-slate-700/60 bg-slate-900/60 text-slate-300",
} as const;

const EXECUTION_BREAKDOWN_STYLES: Record<string, string> = {
  Passed: "bg-emerald-400",
  Failed: "bg-rose-400",
  Flaky: "bg-amber-400",
  Skipped: "bg-slate-500",
};


type PipelineStatus = "done" | "active" | "pending";

interface PipelineStep {
  id: string;
  label: string;
  description: string;
  status: PipelineStatus;
}

type StatTone = keyof typeof STAT_TONE_STYLES;

interface SummaryStat {
  id: string;
  label: string;
  value: string;
  description: string;
  tone: StatTone;
}

type InsightTab = "findings" | "tests" | "rca";

type ActivityTone = keyof typeof ACTIVITY_TONE_STYLES;

interface ActivityItem {
  id: string;
  title: string;
  detail: string;
  tone: ActivityTone;
  timestamp?: string;
}

interface GitHubLoginResponse {
  authorization_url: string;
  state: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  user: SessionUser;
  github_token?: string | null;
}

function formatTimestamp(value?: string) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export default function DashboardPage(): JSX.Element {
  const { addToast } = useToast();
  const [session, setSession] = useState<SessionState | null>(null);
  useEffect(() => {
    if (session) {
      storeSession(session.token, session.user);
    }
  }, [session]);
  const [hydrated, setHydrated] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [provider, setProvider] = useState("github");
  const [webhookBody, setWebhookBody] = useState(() =>
    JSON.stringify({
      event_type: "pull_request",
      action: "opened",
      repository: {
        id: "",
        name: "",
        url: "",
        default_branch: "main"
      },
      pull_request: {
        number: "",
        title: "",
        author: "",
        source_branch: "",
        target_branch: "main",
        diff_url: ""
      },
      files: []
    }, null, 2)
  );
  const [webhookStatus, setWebhookStatus] = useState<string | null>(null);
  const [webhookError, setWebhookError] = useState<string | null>(null);
  const [activePrId, setActivePrId] = useState<string | null>(null);
  const [prInput, setPrInput] = useState("");
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<
    "webhook" | "load" | "generate" | "execute" | null
  >(null);
  const [insightTab, setInsightTab] = useState<InsightTab>("findings");
  const [stepsCompleted, setStepsCompleted] = useState({
    webhook: false,
    review: false,
    tests: false,
    execution: false,
  });
  const [githubRepos, setGithubRepos] = useState<GitHubRepositorySummary[]>([]);
  const [githubReposLoading, setGithubReposLoading] = useState(false);
  const [trackedRepos, setTrackedRepos] = useState<GitHubTrackedRepository[]>([]);
  const [bootstrapTarget, setBootstrapTarget] = useState<string | null>(null);
  const [cloneJobs, setCloneJobs] = useState<GitHubCloneJob[]>([]);
  const [trackedLoading, setTrackedLoading] = useState(false);
  const [githubSearch, setGithubSearch] = useState("");
  const [githubError, setGithubError] = useState<string | null>(null);
  const isAuthenticated = hydrated && Boolean(session);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const syncSession = () => {
      setSession(loadSession());
    };
    syncSession();
    setHydrated(true);
    window.addEventListener("storage", syncSession);
    return () => {
      window.removeEventListener("storage", syncSession);
    };
  }, []);

  const reviewKey = activePrId && isAuthenticated
    ? `/reviews/pr/${encodeURIComponent(
        activePrId
      )}?include_tests=true&include_rca=true`
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
    executionId && isAuthenticated ? `/tests/results/${executionId}` : null,
    swrFetcher,
    {
      refreshInterval: executionId && isAuthenticated ? 4000 : 0,
      revalidateOnFocus: false,
    }
  );

  const { data: rca } = useSWR<RCAResponse>(
    executionId && isAuthenticated ? `/rca/${executionId}` : null,
    swrFetcher,
    {
      refreshInterval: executionId && isAuthenticated ? 6000 : 0,
      revalidateOnFocus: false,
    }
  );

  const operationsKey = isAuthenticated ? "/operations/console" : null;
  const { data: operations, mutate: mutateOperations } = useSWR<OperationsSnapshot>(
    operationsKey,
    swrFetcher,
    {
      refreshInterval: 8000,
      revalidateOnFocus: false,
    }
  );

  const userInitials = useMemo(() => {
    const login = session?.user?.login ?? "";
    if (!login) return "TF";
    const stripped = login.replace(/[^a-zA-Z0-9]/g, "");
    const initials = stripped.slice(0, 2) || login.slice(0, 2);
    return initials.toUpperCase();
  }, [session?.user?.login]);

  useEffect(() => {
    if (activePrId) {
      setPrInput(activePrId);
    }
  }, [activePrId]);

  useEffect(() => {
    if (review) {
      setStepsCompleted((prev) =>
        prev.review ? prev : { ...prev, review: true }
      );
    }
  }, [review]);

  useEffect(() => {
    if (review?.tests?.length) {
      setStepsCompleted((prev) =>
        prev.tests ? prev : { ...prev, tests: true }
      );
    }
  }, [review?.tests?.length]);

  useEffect(() => {
    if (executionResults) {
      setStepsCompleted((prev) =>
        prev.execution ? prev : { ...prev, execution: true }
      );
    }
  }, [executionResults]);

  useEffect(() => {
    if (!hydrated) {
      return;
    }
    const login = session?.user?.login;
    if (!login) {
      return;
    }
    setWebhookBody((current) => {
      try {
        const parsed = JSON.parse(current);
        const currentAuthor = parsed?.pull_request?.author;
        if (!currentAuthor) {
          const updated = {
            ...parsed,
            pull_request: {
              ...parsed.pull_request,
              author: login,
            },
          };
          return JSON.stringify(updated, null, 2);
        }
        return current;
      } catch {
        return current;
      }
    });
  }, [hydrated, session?.user?.login]);

  const handleLogin = useCallback(async () => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const response = await fetchJson<GitHubLoginResponse>("/auth/github/login");
      if (response.authorization_url.startsWith("dev://")) {
        setAuthError(
          "GitHub OAuth dev_mode is enabled on the backend. Provide real OAuth credentials and disable dev_mode to use GitHub sign-in."
        );
        addToast({
          tone: "info",
          title: "Dev mode detected",
          description:
            "Update TRACEFOX_AUTH__GITHUB__* values and set TRACEFOX_AUTH__GITHUB__DEV_MODE=false to enable real GitHub authentication.",
        });
        return;
      }
      rememberOAuthState(response.state);
      window.location.href = response.authorization_url;
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unable to start the GitHub sign-in flow.";
      setAuthError(message);
      addToast({
        tone: "error",
        title: "Sign-in failed",
        description: message,
      });
    } finally {
      setAuthLoading(false);
    }
  }, [addToast]);

  const handleLogout = useCallback(async () => {
    clearSession();
    setSession(null);
    setActivePrId(null);
    setExecutionId(null);
    setStepsCompleted({
      webhook: false,
      review: false,
      tests: false,
      execution: false,
    });
    setWebhookStatus(null);
    setWebhookError(null);
    setActionMessage(null);
    setActionError(null);
    setWebhookBody(JSON.stringify({
      event_type: "pull_request",
      action: "opened",
      repository: {
        id: "",
        name: "",
        url: "",
        default_branch: "main",
      },
      pull_request: {
        number: "",
        title: "",
        author: "",
        source_branch: "",
        target_branch: "main",
        diff_url: "",
      },
      files: [],
    }, null, 2));
    await mutateReview(undefined, false);
    await mutateOperations(undefined, false);
    setGithubRepos([]);
    setTrackedRepos([]);
    setCloneJobs([]);
    setGithubSearch("");
    addToast({
      tone: "info",
      title: "Signed out",
      description: "You have been signed out of TraceFox.",
    });
  }, [addToast, mutateOperations, mutateReview]);

  const refreshTrackedRepositories = useCallback(async () => {
    setTrackedLoading(true);
    try {
      const response = await fetchTrackedRepositories();
      setTrackedRepos(response.repositories ?? []);
      setCloneJobs(response.clone_jobs ?? []);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load tracked repositories.";
      setGithubError(message);
      addToast({
        tone: "error",
        title: "Repository load failed",
        description: message,
      });
    } finally {
      setTrackedLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    if (isAuthenticated) {
      void refreshTrackedRepositories();
    } else {
      setGithubRepos([]);
      setTrackedRepos([]);
      setCloneJobs([]);
      setGithubError(null);
    }
  }, [isAuthenticated, refreshTrackedRepositories]);

  const loadGithubRepositories = useCallback(async () => {
    setGithubReposLoading(true);
    setGithubError(null);
    try {
      const response = await fetchGitHubRepositories();
      setGithubRepos(response.repositories ?? []);
      await refreshTrackedRepositories();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load GitHub repositories.";
      setGithubError(message);
      addToast({
        tone: "error",
        title: "GitHub fetch failed",
        description: message,
      });
    } finally {
      setGithubReposLoading(false);
    }
  }, [addToast, refreshTrackedRepositories]);

  const handleTrackRepository = useCallback(
    async (fullName: string) => {
      try {
        setGithubError(null);
        await trackGitHubRepository(fullName);
        addToast({
          tone: "success",
          title: "Repository queued",
          description: `${fullName} scheduled for cloning and indexing.`,
        });
        await refreshTrackedRepositories();
      } catch (error) {
        const message = error instanceof Error ? error.message : "Unable to track repository.";
        setGithubError(message);
        addToast({
          tone: "error",
          title: "Tracking failed",
          description: message,
        });
      }
    },
    [addToast, refreshTrackedRepositories]
  );

  const handleBootstrapRepository = useCallback(
    async (fullName: string) => {
      setBootstrapTarget(fullName);
      try {
        await bootstrapGitHubRepository(fullName);
        addToast({
          tone: "success",
          title: "Analysis started",
          description: `${fullName} queued for TraceFox analysis.`,
        });
        await refreshTrackedRepositories();
        await mutateOperations();
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Unable to start TraceFox analysis.";
        addToast({
          tone: "error",
          title: "Analysis failed",
          description: message,
        });
      } finally {
        setBootstrapTarget(null);
      }
    },
    [addToast, mutateOperations, refreshTrackedRepositories]
  );

  const trackedByFullName = useMemo(() => {
    const map = new Map<string, GitHubTrackedRepository>();
    trackedRepos.forEach((repo) => {
      map.set(repo.full_name, repo);
    });
    return map;
  }, [trackedRepos]);

  const filteredGithubRepos = useMemo(() => {
    const term = githubSearch.trim().toLowerCase();
    const base = term
      ? githubRepos.filter((repo) => repo.full_name.toLowerCase().includes(term) || repo.description?.toLowerCase().includes(term))
      : githubRepos;
    return base.slice(0, 25);
  }, [githubRepos, githubSearch]);

  const cloneStatusBadge = useCallback((status: string) => {
    const tone = {
      queued: "border-amber-400/50 bg-amber-500/10 text-amber-100",
      running: "border-brand-400/50 bg-brand-500/10 text-brand-100",
      cloned: "border-emerald-400/50 bg-emerald-500/10 text-emerald-100",
      completed: "border-emerald-400/50 bg-emerald-500/10 text-emerald-100",
      failed: "border-rose-400/50 bg-rose-500/10 text-rose-100",
    } as const;
    return tone[status as keyof typeof tone] ?? "border-slate-600/60 bg-slate-900/60 text-slate-200";
  }, []);

  useEffect(() => {
    if (reviewError) {
      const message =
        reviewError instanceof Error
          ? reviewError.message
          : "Unable to load review.";
      addToast({
        tone: "error",
        title: "Review fetch failed",
        description: message,
      });
    }
  }, [addToast, reviewError]);

  useEffect(() => {
    if (operations?.active_pr_id) {
      setActivePrId((current) =>
        current === operations.active_pr_id ? current : operations.active_pr_id
      );
    }
  }, [operations?.active_pr_id]);

  useEffect(() => {
    if (operations?.checklist) {
      setStepsCompleted(operations.checklist);
    }
  }, [operations?.checklist]);

  useEffect(() => {
    const latestExecution = operations?.executions?.latest;
    if (latestExecution?.execution_id && !executionId) {
      setExecutionId(latestExecution.execution_id);
    }
  }, [executionId, operations?.executions?.latest]);

  const activePrMetadata = useMemo<OperationsSnapshot["pr_registry"][number] | null>(() => {
    const id = operations?.active_pr_id;
    if (!id) return null;
    return operations?.pr_registry?.find((entry) => entry.pr_id === id) ?? null;
  }, [operations?.active_pr_id, operations?.pr_registry]);

  const latestPayload = operations?.latest_payload ?? null;

const latestPayloadTimestamp = useMemo(() => {
  const received = activePrMetadata?.received_at;
  return typeof received === "string" ? formatTimestamp(received) : "";
}, [activePrMetadata?.received_at]);

const focusedPrId = activePrId ?? operations?.active_pr_id ?? null;
const summaryPerPr = operations?.summary?.per_pr ?? {};
const activeSummary = focusedPrId ? summaryPerPr[focusedPrId] : undefined;

const activePrDisplay = useMemo(() => {
  if (activePrMetadata) {
    const repo = activePrMetadata.repository_name ?? activePrMetadata.repository_id ?? "";
    const prNumber = activePrMetadata.pull_request_number;
    const main = prNumber ? `${repo} #${prNumber}` : repo || activePrId || "—";
      const subtitle = activePrMetadata.pull_request_title ?? undefined;
      return { main, subtitle };
    }
    return { main: activePrId ?? "—", subtitle: undefined };
  }, [activePrId, activePrMetadata]);

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
    const webhookDone =
      stepsCompleted.webhook || Boolean(focusedPrId) || Boolean(webhookStatus);
    const reviewDone = stepsCompleted.review || Boolean(review) || Boolean(activeSummary);
    const testsDone =
      stepsCompleted.tests || tests.length > 0 || (focusedPrId ? (operations?.tests?.per_pr?.[focusedPrId] ?? 0) > 0 : false);
    const executionDone =
      stepsCompleted.execution || Boolean(executionResults) || (focusedPrId ? (operations?.executions?.per_pr_counts?.[focusedPrId] ?? 0) > 0 : false);
    const rcaDone =
      rcaItems.length > 0 || (focusedPrId ? (operations?.rca?.per_pr_counts?.[focusedPrId] ?? 0) > 0 : false);

    const stepStatus = (complete: boolean, previousComplete: boolean): PipelineStatus => {
      if (complete) return "done";
      return previousComplete ? "active" : "pending";
    };

    return [
      {
        id: "webhook",
        label: "Webhook Received",
        description: "Ingest PR metadata and queue indexing jobs",
        status: webhookDone ? "done" : "active",
      },
      {
        id: "review",
        label: "AI Review",
        description: "Generate review summary and actionable findings",
        status: stepStatus(reviewDone, webhookDone),
      },
      {
        id: "tests",
        label: "Test Generation",
        description: "Produce deterministic tests mapped to findings",
        status: stepStatus(testsDone, reviewDone),
      },
      {
        id: "execution",
        label: "Test Execution",
        description: "Run prioritized suites and capture telemetry",
        status: stepStatus(executionDone, testsDone),
      },
      {
        id: "rca",
        label: "Root Cause Analysis",
        description: "Synthesize failures into remediation guidance",
        status: stepStatus(rcaDone, executionDone),
      },
    ];
  }, [activeSummary, executionResults, focusedPrId, operations?.executions?.per_pr_counts, operations?.rca?.per_pr_counts, operations?.tests?.per_pr, rcaItems.length, review, stepsCompleted, tests.length, webhookStatus]);

  const passRate = useMemo(() => {
    if (executionResults && executionResults.total_tests > 0) {
      return Math.round(
        (executionResults.passed / executionResults.total_tests) * 100
      );
    }
    const latestExecutionForActive = focusedPrId
      ? operations?.executions?.latest_per_pr?.[focusedPrId]
      : undefined;
    if (latestExecutionForActive && latestExecutionForActive.total_tests > 0) {
      return Math.round(
        (latestExecutionForActive.passed / latestExecutionForActive.total_tests) * 100
      );
    }
    return null;
  }, [executionResults, focusedPrId, operations?.executions?.latest_per_pr]);

  const summaryStats = useMemo<SummaryStat[]>(() => {
    const passTone: StatTone =
      passRate === null
        ? "slate"
        : passRate >= 90
        ? "emerald"
        : passRate >= 70
        ? "amber"
        : "rose";

    const critical = review?.critical_count ?? activeSummary?.critical ?? 0;
    const major = review?.major_count ?? activeSummary?.major ?? 0;
    const minor = review?.minor_count ?? activeSummary?.minor ?? 0;
    const generatedTests = tests.length || (focusedPrId ? operations?.tests?.per_pr?.[focusedPrId] ?? 0 : 0);
    const latestExecution = executionResults ?? (focusedPrId ? operations?.executions?.latest_per_pr?.[focusedPrId] ?? null : null);

    return [
      {
        id: "critical",
        label: "Critical",
        value: String(critical),
        description: "Blocking issues that must be resolved before merge",
        tone: "rose",
      },
      {
        id: "major",
        label: "Major",
        value: String(major),
        description: "High-impact findings affecting reliability or security",
        tone: "amber",
      },
      {
        id: "tests",
        label: "Generated Tests",
        value: String(generatedTests),
        description: "Ready-to-run suites mapped to review findings",
        tone: "brand",
      },
      {
        id: "pass-rate",
        label: "Pass Rate",
        value: passRate !== null ? `${passRate}%` : "—",
        description: latestExecution
          ? `Latest run of ${latestExecution.total_tests ?? 0} tests`
          : "Awaiting the next execution",
        tone: passTone,
      },
    ];
  }, [activeSummary, executionResults, focusedPrId, operations?.executions?.latest_per_pr, operations?.tests?.per_pr, passRate, review, tests.length]);

  const quickStats = useMemo(
    () => {
      const provider = activePrMetadata?.provider;
      const testsGenerated = tests.length || (focusedPrId ? operations?.tests?.per_pr?.[focusedPrId] ?? 0 : 0);
      const rcaCount = rcaItems.length || (focusedPrId ? operations?.rca?.per_pr_counts?.[focusedPrId] ?? 0 : 0);
      const activeDescription = activePrMetadata?.pull_request_title
        ?? (provider ? `Source provider: ${provider}` : "Current repository under review");
      return [
        {
          label: "Active PR",
          value: activePrDisplay.main,
          description: activeDescription,
        },
        {
          label: "Tests Generated",
          value: String(testsGenerated),
          description: "TraceFox-managed cases ready to execute",
        },
        {
          label: "RCA Insights",
          value: String(rcaCount),
          description: "Actionable remediation reports available",
        },
        {
          label: "Pass Rate",
          value: passRate !== null ? `${passRate}%` : "—",
          description: "Latest execution success ratio",
        },
      ];
    },
    [activePrDisplay.main, activePrMetadata, focusedPrId, operations?.rca?.per_pr_counts, operations?.tests?.per_pr, passRate, rcaItems.length, tests.length]
  );

  const latestExecutionForActive = focusedPrId
    ? operations?.executions?.latest_per_pr?.[focusedPrId]
    : undefined;

  const executionStatusValue = executionResults
    ? executionResults.status
    : executionId
    ? "Awaiting results"
    : latestExecutionForActive
    ? latestExecutionForActive.status ?? "Completed"
    : "Idle";

  const rcaCountForActive = rcaItems.length || (focusedPrId ? operations?.rca?.per_pr_counts?.[focusedPrId] ?? 0 : 0);

  const checklistItems = useMemo(
    () => [
      {
        key: "webhook",
        label: "Send a webhook",
        detail: "Kick off indexing and an initial AI review",
        done: stepsCompleted.webhook,
      },
      {
        key: "review",
        label: "Review AI findings",
        detail: "Inspect generated findings for your PR",
        done: stepsCompleted.review,
      },
      {
        key: "tests",
        label: "Generate tests",
        detail: "Synthesize deterministic cases mapped to findings",
        done: stepsCompleted.tests,
      },
      {
        key: "execution",
        label: "Run a test execution",
        detail: "Capture telemetry and unlock RCA insights",
        done: stepsCompleted.execution,
      },
    ],
    [stepsCompleted]
  );

  const checklistProgress = useMemo(() => {
    const total = checklistItems.length;
    const completed = checklistItems.filter((item) => item.done).length;
    return {
      total,
      completed,
      percent: total === 0 ? 0 : Math.round((completed / total) * 100),
    };
  }, [checklistItems]);

  const insightNav = useMemo(
    () => [
      { id: "findings" as const, label: "Findings", count: findings.length },
      { id: "tests" as const, label: "Tests", count: tests.length },
      { id: "rca" as const, label: "RCA", count: rcaItems.length },
    ],
    [findings.length, rcaItems.length, tests.length]
  );

  const activityItems = useMemo<ActivityItem[]>(() => {
    const serverItems = (operations?.activity ?? []).map((item) => {
      const tone = Object.prototype.hasOwnProperty.call(
        ACTIVITY_TONE_STYLES,
        item.tone
      )
        ? (item.tone as ActivityTone)
        : ("neutral" as ActivityTone);
      return {
        id: item.id,
        title: item.title,
        detail: item.detail,
        tone,
        timestamp: item.timestamp,
      };
    });

    const clientItems: ActivityItem[] = [];
    if (webhookStatus) {
      clientItems.push({
        id: "webhook-success",
        title: "Webhook accepted",
        detail: webhookStatus,
        tone: "success",
      });
    }
    if (webhookError) {
      clientItems.push({
        id: "webhook-error",
        title: "Webhook failed",
        detail: webhookError,
        tone: "error",
      });
    }
    if (actionMessage) {
      clientItems.push({
        id: "action-success",
        title: "Workflow updated",
        detail: actionMessage,
        tone: "success",
      });
    }
    if (actionError) {
      clientItems.push({
        id: "action-error",
        title: "Action required",
        detail: actionError,
        tone: "error",
      });
    }
    if (reviewLoading) {
      clientItems.push({
        id: "review-loading",
        title: "Review loading",
        detail: "Fetching AI insights for the selected pull request…",
        tone: "info",
      });
    }
    if (review) {
      clientItems.push({
        id: `review-${review.review_id}`,
        title: "Review ready",
        detail: `${review.total_findings} findings surfaced for PR ${review.pr_id}`,
        tone: "success",
      });
    }
    if (executionResults) {
      const failed = executionResults.failed > 0;
      clientItems.push({
        id: `execution-${executionResults.execution_id}`,
        title: "Execution update",
        detail: `${executionResults.status} · Passed ${executionResults.passed}/${executionResults.total_tests}`,
        tone: failed ? "info" : "success",
      });
    }
    if (rcaItems.length) {
      clientItems.push({
        id: `rca-${rcaItems[0].id}`,
        title: "RCA insights ready",
        detail: `${rcaItems.length} remediation recommendations generated`,
        tone: "info",
      });
    }
    return [...clientItems, ...serverItems];
  }, [
    actionError,
    actionMessage,
    executionResults,
    operations?.activity,
    review,
    reviewLoading,
    rcaItems,
    webhookError,
    webhookStatus,
  ]);

  const nextPipelineAction = pipelineSteps.find(
    (step) => step.status === "active"
  );

  const resetMessages = useCallback(() => {
    setActionMessage(null);
    setActionError(null);
  }, []);

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
      await mutateOperations();
      setStepsCompleted((prev) => ({ ...prev, webhook: true }));
      addToast({
        tone: "success",
        title: "Webhook accepted",
        description:
          response.message ?? "TraceFox queued indexing and AI review.",
      });
      const newPrId =
        payload?.repository?.id && payload?.pull_request?.number
          ? `${payload.repository.id}:${payload.pull_request.number}`
          : null;
      if (newPrId) {
        setActivePrId(newPrId);
        setExecutionId(null);
      }
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unable to submit webhook payload.";
      setWebhookError(message);
      addToast({
        tone: "error",
        title: "Webhook failed",
        description: message,
      });
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
      setActionError(
        "Enter a PR identifier in the form <repository-id>:<pr-number>."
      );
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
      const total =
        response.total_generated ?? response.test_cases?.length ?? 0;
      setActionMessage(`Queued ${total} tests for generation.`);
      setStepsCompleted((prev) => ({ ...prev, tests: true }));
      addToast({
        tone: "success",
        title: "Test generation queued",
        description: `TraceFox prepared ${total} tests.`,
      });
      await mutateReview();
      await mutateOperations();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unable to queue test generation.";
      setActionError(message);
      addToast({
        tone: "error",
        title: "Test generation failed",
        description: message,
      });
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
      setStepsCompleted((prev) => ({ ...prev, execution: true }));
      addToast({
        tone: "success",
        title: "Execution started",
        description: `Running ${summary.total_tests} tests in parallel.`,
      });
      await mutateReview();
      await mutateOperations();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unable to execute tests.";
      setActionError(message);
      addToast({
        tone: "error",
        title: "Execution failed",
        description: message,
      });
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

  if (!hydrated) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100">
        <Card title="TraceFox" accent="brand" className="max-w-md border border-slate-800 bg-slate-900/70 p-8">
          <div className="space-y-4">
            <p className="text-sm text-slate-300">Preparing your workspace…</p>
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-3/4" />
          </div>
        </Card>
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100">
        <Card
          title="Connect GitHub"
          accent="brand"
          className="max-w-md border border-slate-800 bg-slate-900/70 p-8"
        >
          <div className="space-y-6">
            <div className="space-y-2">
              <p className="text-xs uppercase tracking-[0.4em] text-slate-400">
                TraceFox Mission Control
              </p>
              <h1 className="text-3xl font-semibold text-white">
                Sign in with GitHub
              </h1>
              <p className="text-sm text-slate-300">
                Connect your GitHub account to authorise TraceFox for automated
                reviews, deterministic testing, and remediation workflows.
              </p>
            </div>
            {authError ? (
              <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
                {authError}
              </div>
            ) : null}
            <button
              type="button"
              onClick={handleLogin}
              disabled={authLoading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-white/95 px-4 py-3 text-sm font-semibold text-slate-900 shadow-lg shadow-brand-500/20 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-70"
            >
              {authLoading ? "Redirecting to GitHub…" : "Continue with GitHub"}
            </button>
            <p className="text-xs text-slate-500">
              TraceFox only uses your GitHub identity to orchestrate code reviews
              and testing automation. You can revoke access at any time from your
              GitHub account settings.
            </p>
          </div>
        </Card>
      </main>
    );
  }

  const currentSession = session as SessionState;

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-slate-100">
      <div className="mx-auto flex max-w-7xl flex-col gap-10 pb-16">
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
              Drive resilient delivery by coordinating AI reviews, deterministic
              tests, and automated remediation. Everything you need to evaluate a
              pull request lives in one adaptive workspace.
            </p>
          </div>
          <div className="flex w-full flex-col gap-4 md:max-w-xs">
            <div className="rounded-2xl border border-brand-400/40 bg-brand-500/10 px-4 py-4 text-sm text-brand-50 shadow-inner shadow-brand-500/20">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-brand-200">Signed in as</p>
                  <p className="mt-1 text-lg font-semibold text-white">
                    {currentSession.user.login}
                  </p>
                  {currentSession.user.email ? (
                    <p className="text-xs text-brand-100/80">{currentSession.user.email}</p>
                  ) : null}
                </div>
                <div className="flex h-12 w-12 items-center justify-center rounded-full border border-brand-400/40 bg-brand-500/20 text-sm font-semibold text-white">
                  {userInitials}
                </div>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="mt-4 w-full rounded-xl border border-brand-400/40 bg-brand-500/20 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-brand-50 transition hover:bg-brand-500/30"
              >
                Sign out
              </button>
            </div>
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
            <div className="rounded-2xl border border-brand-500/40 bg-brand-500/10 px-4 py-3 text-xs uppercase tracking-wide text-brand-100">
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between gap-2">
                  <span>Active PR</span>
                  <span>{activePrDisplay.main}</span>
                </div>
                {activePrDisplay.subtitle ? (
                  <p className="text-[11px] normal-case text-brand-50/80">
                    {activePrDisplay.subtitle}
                  </p>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <Card
          title="Onboarding Checklist"
          accent="slate"
          icon={<span>🧭</span>}
          action={
            <span className="text-slate-300">
              {checklistProgress.completed}/{checklistProgress.total} Complete
            </span>
          }
        >
          <div className="space-y-3">
            <div>
              <div className="flex items-center justify-between text-[11px] uppercase tracking-wide text-slate-400">
                <span>Progress</span>
                <span>{checklistProgress.percent}%</span>
              </div>
              <div className="mt-2 h-2 w-full rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-brand-500 transition-all"
                  style={{ width: `${checklistProgress.percent}%` }}
                />
              </div>
            </div>
            <ul className="space-y-3">
              {checklistItems.map((item) => (
                <li
                  key={item.key}
                  className={clsx(
                    "rounded-2xl border px-4 py-3 text-sm shadow-inner shadow-black/20",
                    item.done
                      ? "border-emerald-400/40 bg-emerald-500/10 text-emerald-100"
                      : "border-slate-700/60 bg-slate-900/60 text-slate-200"
                  )}
                >
                  <div className="flex items-center justify-between text-xs uppercase tracking-wide">
                    <span className="text-white">{item.label}</span>
                    <span>{item.done ? "Done" : "Pending"}</span>
                  </div>
                  <p className="mt-2 text-xs text-slate-200/80">{item.detail}</p>
                </li>
              ))}
            </ul>
          </div>
        </Card>

        <Card title="Operational Pulse" accent="emerald" icon={<span>📈</span>}>
          <div className="grid gap-4 sm:grid-cols-2">
            {quickStats.map((stat) => (
              <div
                key={stat.label}
                className="rounded-2xl border border-emerald-400/30 bg-emerald-500/5 px-4 py-3 text-sm text-slate-100"
              >
                <p className="text-xs uppercase tracking-wide text-emerald-200">
                  {stat.label}
                </p>
                <p className="mt-2 text-2xl font-semibold text-white">
                  {stat.value}
                </p>
                <p className="mt-1 text-xs text-emerald-200/80">
                  {stat.description}
                </p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card
        title="Repository Sync"
        accent="brand"
        icon={<span>📂</span>}
        className="border-brand-500/50"
        action={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void refreshTrackedRepositories()}
              disabled={trackedLoading}
              className="rounded-xl border border-emerald-400/60 bg-emerald-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-emerald-100 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {trackedLoading ? "Refreshing…" : "Refresh Tracked"}
            </button>
            <button
              type="button"
              onClick={() => void loadGithubRepositories()}
              disabled={githubReposLoading}
              className="rounded-xl border border-brand-400/60 bg-brand-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-brand-100 transition hover:bg-brand-500/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {githubReposLoading ? "Loading…" : "Load Repositories"}
            </button>
          </div>
        }
      >
        {githubError ? (
          <div className="rounded-xl border border-rose-400/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-100">
            {githubError}
          </div>
        ) : null}
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-brand-100/80">
                Available Repositories
              </h3>
              <span className="text-[11px] text-slate-400">
                {githubRepos.length ? `${githubRepos.length} fetched` : "Not loaded"}
              </span>
            </div>
            <div className="relative">
              <input
                value={githubSearch}
                onChange={(event) => setGithubSearch(event.target.value)}
                placeholder="Search repositories…"
                className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-brand-400 focus:outline-none"
              />
            </div>
            {githubReposLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : filteredGithubRepos.length === 0 ? (
              <p className="text-sm text-slate-300/80">
                {githubRepos.length
                  ? "No repositories match your search."
                  : "Use the Load button to fetch your GitHub repositories."}
              </p>
            ) : (
              <ul className="space-y-2 text-sm">
                {filteredGithubRepos.map((repo) => {
                  const tracked = trackedByFullName.get(repo.full_name);
                  return (
                    <li
                      key={repo.id}
                      className="rounded-xl border border-slate-700/60 bg-slate-900/70 p-3 shadow-inner shadow-black/10"
                    >
                      <div className="flex flex-col gap-2">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-semibold text-white">{repo.full_name}</p>
                            {repo.description ? (
                              <p className="text-xs text-slate-300/80">{repo.description}</p>
                            ) : null}
                            <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-wide text-slate-400">
                              <span>{repo.default_branch}</span>
                              <span>{repo.private ? "Private" : "Public"}</span>
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-2">
                            <a
                              href={repo.html_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-xs text-brand-200 hover:text-brand-50"
                            >
                              View on GitHub ↗
                            </a>
                            <button
                              type="button"
                              onClick={() => void handleTrackRepository(repo.full_name)}
                              disabled={Boolean(tracked)}
                              className={clsx(
                                "rounded-lg border px-3 py-1 text-xs font-semibold transition",
                                tracked
                                  ? "cursor-not-allowed border-slate-700 bg-slate-900/60 text-slate-500"
                                  : "border-brand-400/60 bg-brand-500/10 text-brand-100 hover:bg-brand-500/20"
                              )}
                            >
                              {tracked ? "Tracking" : "Track"}
                            </button>
                          </div>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-brand-100/80">
                Tracked Repositories
              </h3>
              <span className="text-[11px] text-slate-400">
                {trackedRepos.length ? `${trackedRepos.length} tracked` : "None"}
              </span>
            </div>
            {trackedLoading && !trackedRepos.length ? (
              <div className="space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : trackedRepos.length === 0 ? (
              <p className="text-sm text-slate-300/80">
                Track a repository to kick off cloning and indexing. Clone jobs will appear here with live status.
              </p>
            ) : (
              <ul className="space-y-2 text-sm">
                {trackedRepos.map((repo) => (
                  <li
                    key={repo.repo_id}
                    className="rounded-xl border border-slate-700/60 bg-slate-900/70 p-3 shadow-inner shadow-black/10"
                  >
                    <div className="flex flex-col gap-2">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-white">{repo.full_name}</p>
                          {repo.clone_path ? (
                            <p className="text-[11px] text-slate-400/80">Cloned to {repo.clone_path}</p>
                          ) : null}
                        </div>
                        <span
                          className={clsx(
                            "rounded-full px-3 py-1 text-[11px] uppercase tracking-wide",
                            cloneStatusBadge(repo.sync_status)
                          )}
                        >
                          {repo.sync_status}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="text-[11px] text-slate-400/80">
                          Default branch: <span className="text-slate-200">{repo.default_branch}</span>
                        </p>
                        <button
                          type="button"
                          onClick={() => void handleBootstrapRepository(repo.full_name)}
                          disabled={
                            bootstrapTarget === repo.full_name || trackedLoading || repo.sync_status === "queued"
                          }
                          className={clsx(
                            "inline-flex items-center gap-1 rounded-lg border px-3 py-1 text-xs font-semibold transition",
                            bootstrapTarget === repo.full_name
                              ? "border-brand-400/60 bg-brand-500/20 text-brand-50"
                              : "border-brand-400/60 bg-brand-500/10 text-brand-100 hover:bg-brand-500/20",
                            (bootstrapTarget === repo.full_name || trackedLoading || repo.sync_status === "queued") &&
                              "cursor-not-allowed opacity-60"
                          )}
                        >
                          {bootstrapTarget === repo.full_name ? "Starting…" : "Run Analysis"}
                        </button>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            {cloneJobs.length ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Recent Clone Jobs</p>
                  <span className="text-[11px] text-slate-500">Showing latest {Math.min(cloneJobs.length, 5)}</span>
                </div>
                <ul className="space-y-2 text-xs text-slate-200">
                  {cloneJobs.slice(0, 5).map((job) => (
                    <li
                      key={job.job_id}
                      className="rounded-xl border border-slate-700/60 bg-slate-900/70 px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex flex-col">
                          <span className="font-semibold text-white">{job.full_name}</span>
                          <span className="text-[11px] text-slate-400/80">{job.job_id}</span>
                        </div>
                        <span
                          className={clsx(
                            "rounded-full px-3 py-1 text-[11px] uppercase tracking-wide",
                            cloneStatusBadge(job.status)
                          )}
                        >
                          {job.status}
                        </span>
                      </div>
                      {job.message ? (
                        <p className="mt-2 text-[11px] text-rose-200/80">{job.message}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card title="Pipeline Overview" accent="brand" icon={<span>🛰️</span>}>
          <ol className="space-y-4">
            {pipelineSteps.map((step) => (
              <li
                key={step.id}
                className={clsx(
                  "flex flex-col gap-1 rounded-2xl border px-4 py-3 text-sm shadow",
                  PIPELINE_STATUS_STYLES[step.status]
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
                  STAT_TONE_STYLES[stat.tone]
                )}
              >
                <dt className="text-xs uppercase tracking-wide text-slate-300">
                  {stat.label}
                </dt>
                <dd className="mt-1 text-2xl font-semibold text-white">
                  {stat.value}
                </dd>
                <p className="mt-1 text-xs text-slate-300/90">
                  {stat.description}
                </p>
              </div>
            ))}
          </dl>
        </Card>
      </div>

        {/* Removed Operations Console section */}

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
            reviewLoading && !review ? (
              <div className="space-y-4">
                <Skeleton className="h-4 w-1/2" />
                <div className="space-y-3">
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-20 w-full" />
                </div>
              </div>
            ) : (
              <FindingList findings={findings} review={review} />
            )
          ) : null}

          {insightTab === "tests" ? (
            loadingAction === "generate" && !tests.length ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-24 w-full" />
              </div>
            ) : (
              <TestList tests={tests} />
            )
          ) : null}

          {insightTab === "rca" ? (
            executionLoading && !rcaItems.length ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-1/4" />
                <Skeleton className="h-28 w-full" />
              </div>
            ) : (
              <RcaList rcaItems={rcaItems} />
            )
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
                    ACTIVITY_TONE_STYLES[item.tone]
                  )}
              >
                <p className="text-xs uppercase tracking-wide text-slate-200/80">
                  {item.title}
                </p>
                {item.timestamp ? (
                  <p className="text-[10px] uppercase tracking-wide text-slate-400/80">
                    {formatTimestamp(item.timestamp)}
                  </p>
                ) : null}
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
            <ExecutionSummary
              executionResults={executionResults}
              executionBreakdown={executionBreakdown}
              executionTotal={executionTotal}
            />
          ) : null}
        </Card>
      ) : null}
      </div>
    </main>
  );
}

function StatusBadge({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}): JSX.Element {
  return (
    <div
      className={clsx(
        "rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-xs uppercase tracking-wide text-slate-300",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span>{label}</span>
        <span className="text-white">{value}</span>
      </div>
    </div>
  );
}

function FindingList({
  findings,
  review,
}: {
  findings: ReviewSummary["findings"];
  review: ReviewSummary | undefined;
}): JSX.Element {
  return (
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
            const severityClass =
              SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.minor;
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
                <p className="mt-3 text-sm text-slate-200">
                  {finding.description}
                </p>
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
        <p className="text-sm text-slate-400">
          No findings recorded yet.
        </p>
      )}
    </div>
  );
}

function TestList({
  tests,
}: {
  tests: ReviewSummary["tests"] | undefined;
}): JSX.Element {
  if (!tests?.length) {
    return (
      <p className="text-sm text-slate-400">
        No generated tests yet. Queue test generation to seed execution.
      </p>
    );
  }
  return (
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
  );
}

function RcaList({ rcaItems }: { rcaItems: RCAResponse[] }): JSX.Element {
  if (!rcaItems.length) {
    return (
      <p className="text-sm text-slate-400">
        RCA insights will appear as soon as a test execution produces failures.
      </p>
    );
  }
  return (
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
  );
}

function ExecutionSummary({
  executionResults,
  executionBreakdown,
  executionTotal,
}: {
  executionResults: TestResultsResponse;
  executionBreakdown: Array<{ label: string; value: number }>;
  executionTotal: number;
}): JSX.Element {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <div className="grid gap-3 text-sm text-slate-200 md:grid-cols-2">
          <span>Status: {executionResults.status}</span>
          <span>Total: {executionResults.total_tests}</span>
          <span>Passed: {executionResults.passed}</span>
          <span>Failed: {executionResults.failed}</span>
          <span>Flaky: {executionResults.flaky}</span>
          <span>
            Duration: {(executionResults.execution_time_ms / 1000).toFixed(1)}s
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div className="flex h-full">
            {executionBreakdown.map((part) => {
              const toneClass = EXECUTION_BREAKDOWN_STYLES[part.label] ?? "bg-slate-700";
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
          const style =
            EXECUTION_STATUS_STYLES[result.status] ?? EXECUTION_STATUS_STYLES.running;
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
                <p className="mt-2 text-xs text-rose-100/90">
                  {result.error_message}
                </p>
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
  );
}
