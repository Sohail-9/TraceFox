"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";

import { Card } from "@/components/Card";
import { useToast } from "@/components/ToastProvider";
import { LoadingSpinner } from "@/components/common/loading-spinner";
import {
  bootstrapGitHubRepository,
  fetchGitHubRepositories,
  fetchTrackedRepositories,
  trackGitHubRepository,
} from "@/lib/github";
import type {
  GitHubRepositorySummary,
  GitHubTrackedRepository,
} from "@/types/backend";

const trackedKey = "/integrations/github/tracked";
const availableKey = "/integrations/github/repos";

export function GitHubRepositoriesPanel(): JSX.Element {
  const { addToast } = useToast();
  const [selectedRepo, setSelectedRepo] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const {
    data: tracked,
    error: trackedError,
    isLoading: trackedLoading,
    mutate: mutateTracked,
  } = useSWR(trackedKey, fetchTrackedRepositories, {
    refreshInterval: 30_000,
    revalidateOnFocus: false,
  });
  const {
    data: available,
    error: availableError,
    isLoading: availableLoading,
  } = useSWR(availableKey, fetchGitHubRepositories, {
    revalidateOnFocus: false,
  });

  const availableRepos = useMemo(() => {
    const repos = available?.repositories ?? [];
    return repos.slice(0, 25);
  }, [available]);

  const trackedRepos = tracked?.repositories ?? [];

  const handleTrack = async () => {
    if (!selectedRepo) {
      addToast({
        tone: "info",
        title: "Select a repository",
        description: "Choose a repo from the dropdown before tracking.",
      });
      return;
    }
    setActionLoading(true);
    try {
      await trackGitHubRepository(selectedRepo);
      addToast({
        tone: "success",
        title: "Repository tracked",
        description: `${selectedRepo} has been registered.`,
      });
      await mutateTracked();
    } catch (error) {
      addToast({
        tone: "error",
        title: "Unable to track repository",
        description:
          error instanceof Error ? error.message : "Unexpected error occurred",
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleBootstrap = async (repo: GitHubTrackedRepository) => {
    setActionLoading(true);
    try {
      await bootstrapGitHubRepository(repo.full_name);
      addToast({
        tone: "success",
        title: "Bootstrap queued",
        description: `Fetching recent PRs for ${repo.full_name}.`,
      });
    } catch (error) {
      addToast({
        tone: "error",
        title: "Unable to bootstrap repository",
        description:
          error instanceof Error ? error.message : "Unexpected error occurred",
      });
    } finally {
      setActionLoading(false);
    }
  };

  const renderTrackedList = () => {
    if (trackedLoading) {
      return (
        <div className="flex items-center justify-center py-4">
          <LoadingSpinner />
        </div>
      );
    }
    if (trackedError) {
      return (
        <p className="text-sm text-rose-300">
          Unable to load tracked repositories:{" "}
          {trackedError instanceof Error ? trackedError.message : "Unknown error"}
        </p>
      );
    }
    if (!trackedRepos.length) {
      return (
        <p className="text-sm text-slate-400">
          No repositories have been tracked for analysis yet. Pick one below to
          bootstrap analysis.
        </p>
      );
    }
    return (
      <ul className="space-y-3">
        {trackedRepos.map((repo) => (
          <li
            key={repo.repo_id}
            className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4"
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-white">
                  {repo.full_name}
                </p>
                <p className="text-xs text-slate-400">
                  {repo.description ?? "No description provided."}
                </p>
                <p className="text-xs text-slate-500">
                  Branch: {repo.default_branch} · Sync status: {repo.sync_status}
                </p>
              </div>
              <button
                type="button"
                className="rounded-xl border border-brand-400/40 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-brand-100 transition hover:bg-brand-500/20"
                onClick={() => handleBootstrap(repo)}
                disabled={actionLoading}
              >
                Bootstrap
              </button>
            </div>
          </li>
        ))}
      </ul>
    );
  };

  const renderRepositorySelector = () => {
    if (availableLoading) {
      return (
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <LoadingSpinner /> Loading repositories...
        </div>
      );
    }
    if (availableError) {
      return (
        <p className="text-sm text-rose-300">
          Unable to fetch GitHub repositories. Confirm your OAuth token has
          permissions.
        </p>
      );
    }
    if (!availableRepos.length) {
      return (
        <p className="text-sm text-slate-400">
          GitHub did not return any repositories for your account.
        </p>
      );
    }
    return (
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label className="text-[10px] uppercase tracking-[0.35em] text-slate-500">
            Select Repository
          </label>
          <select
            className="mt-1 w-full rounded-2xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white"
            value={selectedRepo}
            onChange={(event) => setSelectedRepo(event.target.value)}
          >
            <option value="">Choose a repository…</option>
            {availableRepos.map((repo: GitHubRepositorySummary) => (
              <option key={repo.id} value={repo.full_name}>
                {repo.full_name}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={handleTrack}
          className="rounded-2xl bg-brand-500 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:bg-brand-400 disabled:opacity-50"
          disabled={actionLoading}
        >
          {actionLoading ? "Processing…" : "Track & Bootstrap"}
        </button>
      </div>
    );
  };

  return (
    <Card className="border border-slate-800 bg-slate-950/70 p-5">
      <div className="mb-4 space-y-2">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
          GitHub Repositories
        </p>
        <h2 className="text-xl font-semibold text-white">Connected Sources</h2>
        <p className="text-sm text-slate-400">
          Track repositories to bootstrap pull requests and hydrate the dashboard
          with DeepSeek + Llama findings.
        </p>
      </div>
      <div className="space-y-5">
        {renderTrackedList()}
        <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4">
          {renderRepositorySelector()}
        </div>
      </div>
    </Card>
  );
}
