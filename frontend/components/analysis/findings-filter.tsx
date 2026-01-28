"use client";

import { useAnalysisStore } from "@/store/analysis-store";
import clsx from "clsx";

const severityOptions = ["high", "medium", "low"];
const categoryOptions = [
  "security",
  "performance",
  "style",
  "logic",
  "breaking_change",
  "cross_layer",
];

export function FindingsFilter(): JSX.Element {
  const severity = useAnalysisStore((state) => state.severity);
  const category = useAnalysisStore((state) => state.category);
  const selectSeverity = useAnalysisStore((state) => state.selectSeverity);
  const selectCategory = useAnalysisStore((state) => state.selectCategory);

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/5 bg-slate-900/40 p-5 shadow-inner">
      <FilterGroup
        label="Severity"
        value={severity}
        options={severityOptions}
        onChange={selectSeverity}
      />
      <div className="h-px w-full bg-white/5" />
      <FilterGroup
        label="Category"
        value={category}
        options={categoryOptions}
        onChange={selectCategory}
      />
    </div>
  );
}

function FilterGroup({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string | null;
  options: string[];
  onChange: (value: string | null) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="min-w-[70px] text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
        {label}
      </span>
      <div className="flex flex-wrap gap-1.5">
        <button
          type="button"
          onClick={() => onChange(null)}
          className={clsx(
            "rounded-lg px-3 py-1.5 text-[11px] font-medium transition-all duration-200",
            value === null
              ? "bg-indigo-500/10 text-indigo-400 ring-1 ring-inset ring-indigo-500/30"
              : "text-slate-500 hover:bg-white/5 hover:text-slate-300"
          )}
        >
          All
        </button>
        {options.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => onChange(option)}
            className={clsx(
              "rounded-lg px-3 py-1.5 text-[11px] font-medium capitalize transition-all duration-200",
              value === option
                ? "bg-indigo-500/10 text-indigo-100 ring-1 ring-inset ring-indigo-500/40"
                : "text-slate-500 hover:bg-white/5 hover:text-slate-300"
            )}
          >
            {option.replace("_", " ")}
          </button>
        ))}
      </div>
    </div>
  );
}
