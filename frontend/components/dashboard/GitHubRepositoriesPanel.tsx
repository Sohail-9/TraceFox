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
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner />
        </div>
      );
    }
    if (trackedError) {
      return (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4">
          <p className="text-sm text-rose-400">
            Unable to load tracked repositories: {trackedError instanceof Error ? trackedError.message : "Unknown error"}
          </p>
        </div>
      );
    }
    if (!trackedRepos.length) {
      return (
        <div className="rounded-2xl border border-white/5 bg-black/20 p-8 text-center">
          <p className="text-sm font-medium text-slate-400">
            No repositories have been tracked for analysis yet.
          </p>
          <p className="mt-1 text-[11px] text-slate-500">Pick one below to begin.</p>
        </div>
      );
    }
    return (
      <ul className="space-y-3">
        {trackedRepos.map((repo) => (
          <li key={repo.repo_id} className="group rounded-2xl border border-white/5 bg-slate-900/40 p-5 transition-all hover:border-white/10 hover:bg-slate-900/60">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <p className="text-sm font-bold text-slate-200">{repo.full_name}</p>
                <p className="text-xs text-slate-500 max-w-md">{repo.description ?? "No description provided."}</p>
                <div className="flex items-center gap-2 text-[10px] font-medium text-slate-600 uppercase tracking-wider">
                  <span>{repo.default_branch}</span>
                  <span>·</span>
                  <span className="text-indigo-400/80">{repo.sync_status}</span>
                </div>
              </div>
              <button
                type="button"
                className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-6 py-2.5 text-[11px] font-bold uppercase tracking-widest text-indigo-400 transition-all hover:bg-indigo-500/20 hover:text-indigo-300 active:scale-95"
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
        <div className="flex items-center gap-3 text-xs font-medium text-slate-500">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-500 border-t-transparent" />
          Fetching repositories from GitHub...
        </div>
      );
    }
    if (availableError) {
      return (
        <p className="text-sm text-rose-400">
          Unable to fetch GitHub repositories. Confirm your OAuth token has permissions.
        </p>
      );
    }
    if (!availableRepos.length) {
      return (
        <p className="text-sm text-slate-500">GitHub did not return any repositories for your account.</p>
      );
    }
    return (
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="flex-1 space-y-2">
          <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Select Repository</label>
          <div className="relative">
            <select
              className="w-full rounded-xl border border-white/5 bg-black/40 px-4 py-3 text-xs text-slate-200 outline-none focus:ring-1 focus:ring-indigo-500/50 appearance-none cursor-pointer"
              value={selectedRepo}
              onChange={(event) => setSelectedRepo(event.target.value)}
            >
              <option value="" className="bg-slate-900">Choose a repository…</option>
              {availableRepos.map((repo: GitHubRepositorySummary) => (
                <option key={repo.id} value={repo.full_name} className="bg-slate-900">
                  {repo.full_name}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-500">
              ↓
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={handleTrack}
          className="h-[38px] rounded-xl bg-indigo-500 px-6 text-[11px] font-bold uppercase tracking-widest text-white transition-all hover:bg-indigo-400 hover:shadow-[0_0_20px_rgba(99,102,241,0.3)] disabled:opacity-50 active:scale-95"
          disabled={actionLoading}
        >
          {actionLoading ? "Processing…" : "Track & Bootstrap"}
        </button>
      </div>
    );
  };

  return (
    <Card accent="slate" className="p-8">
      <div className="mb-8 flex flex-col gap-2">
        <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-indigo-400/80">GitHub Repositories</p>
        <h2 className="text-2xl font-bold tracking-tight text-slate-100">Connected Sources</h2>
        <p className="text-sm text-slate-500 max-w-2xl">Track repositories to bootstrap pull requests and hydrate the dashboard with actionable findings.</p>
      </div>
      <div className="space-y-8">
        {renderTrackedList()}
        <div className="rounded-2xl border border-white/5 bg-slate-900/20 p-6">{renderRepositorySelector()}</div>
      </div>
    </Card>
  );
}
