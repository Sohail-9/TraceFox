"use client";

import { useAnalysisStore } from "@/store/analysis-store";

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
    <div className="flex flex-wrap gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-xs text-slate-300">
      <FilterGroup
        label="Severity"
        value={severity}
        options={severityOptions}
        onChange={selectSeverity}
      />
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
      <span className="text-[10px] uppercase tracking-[0.35em] text-slate-500">
        {label}
      </span>
      <button
        type="button"
        onClick={() => onChange(null)}
        className={`rounded-full border px-2 py-1 ${
          value === null
            ? "border-brand-400/70 text-brand-100"
            : "border-slate-700 text-slate-400"
        }`}
      >
        All
      </button>
      {options.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={`rounded-full border px-2 py-1 capitalize ${
            value === option
              ? "border-brand-400/70 text-brand-100"
              : "border-slate-700 text-slate-400"
          }`}
        >
          {option.replace("_", " ")}
        </button>
      ))}
    </div>
  );
}
