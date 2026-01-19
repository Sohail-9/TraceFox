export function Skeleton({ className }: { className?: string }): JSX.Element {
  return <div className={`animate-pulse rounded-2xl bg-glass ${className ?? "h-6 w-full"}`} />;
}
