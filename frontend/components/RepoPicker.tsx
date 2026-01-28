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
    } catch { }
    if (onSelect) onSelect(v);
  };

  return (
    <div className="flex items-center gap-3">
      <div className="h-4 w-px bg-white/10" />
      <div className="flex items-center gap-2">
        <label className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Repo</label>
        <select
          value={selected ?? ""}
          onChange={(e) => handle(e.target.value)}
          className="rounded-xl border border-white/5 bg-black/20 px-3 py-1.5 text-xs text-slate-200 outline-none focus:ring-1 focus:ring-indigo-500/50 appearance-none cursor-pointer hover:bg-black/40 transition-colors pr-8"
          style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2364748b'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='激19l-7 7-7-7' /%3E%3C/svg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 0.5rem center', backgroundSize: '1rem' }}
        >
          <option value="" disabled className="bg-slate-900">{loading ? "Loading..." : "Select repository"}</option>
          {repos?.repositories.map((r) => (
            <option key={r.full_name} value={r.full_name} className="bg-slate-900 text-slate-200">
              {r.full_name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

export default RepoPicker;
