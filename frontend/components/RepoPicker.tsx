"use client";

import { useEffect, useState } from "react";
import { fetchTrackedRepositories } from "@/lib/github";
import type { GitHubTrackedResources } from "@/types/backend";

export function RepoPicker({ onSelect }: { onSelect?: (fullName: string) => void }) {
  const [repos, setRepos] = useState<GitHubTrackedResources | null>(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(() => {
    try {
      return localStorage.getItem("tracefox:selectedRepo");
    } catch {
      return null;
    }
  });

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    fetchTrackedRepositories()
      .then((r) => {
        if (mounted) setRepos(r);
      })
      .catch(() => {
        if (mounted) setRepos(null);
      })
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, []);

  const handle = (v: string) => {
    setSelected(v);
    try {
      localStorage.setItem("tracefox:selectedRepo", v);
    } catch {}
    if (onSelect) onSelect(v);
  };

  return (
    <div className="flex items-center gap-2">
      <label className="text-xs text-muted">Repo</label>
      <select
        value={selected ?? ""}
        onChange={(e) => handle(e.target.value)}
        className="rounded-md border border-ui bg-panel px-2 py-1 text-sm text-ui"
      >
        <option value="">{loading ? "Loading..." : "Select repository"}</option>
        {repos?.repositories.map((r) => (
          <option key={r.id} value={r.full_name} className="text-ui">
            {r.full_name}
          </option>
        ))}
      </select>
    </div>
  );
}

export default RepoPicker;
