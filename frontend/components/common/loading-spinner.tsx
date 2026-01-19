"use client";

import clsx from "clsx";

type LoadingSpinnerProps = {
  label?: string;
  className?: string;
};

export function LoadingSpinner({ label, className }: LoadingSpinnerProps): JSX.Element {
  return (
    <div className={clsx("flex items-center gap-2 text-muted", className)}>
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-ui/60 border-t-transparent" />
      <span className="text-xs uppercase tracking-[0.3em]">{label ?? "Loading"}</span>
    </div>
  );
}
