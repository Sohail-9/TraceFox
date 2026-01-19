"use client";

type NotificationProps = {
  notifications: Record<string, {
    channel: string;
    body: string;
    severity: string;
  }> | null;
};

const severityColor: Record<string, string> = {
  high: "border-rose-500/60 bg-rose-500/10 text-rose-100",
  info: "border-brand-400/40 bg-brand-500/10 text-brand-100",
  warning: "border-amber-400/60 bg-amber-500/10 text-amber-100",
};

export function NotificationList({ notifications }: NotificationProps) {
  if (!notifications || !Object.keys(notifications).length) {
    return <p className="text-sm text-muted">No notifications have been generated yet.</p>;
  }

  return (
    <div className="space-y-3">
      {Object.entries(notifications).map(([key, message]) => {
        const severityClass = severityColor[message.severity?.toLowerCase?.() ?? ""] ??
          "border-ui bg-glass text-ui";
        return (
          <div
            key={key}
            className={`rounded-xl border px-4 py-3 text-sm shadow ${severityClass} bg-glass`}
          >
            <div className="flex items-center justify-between gap-4">
              <span className="text-xs uppercase tracking-wide text-muted">{message.channel}</span>
              <span className="text-[10px] uppercase tracking-wider text-muted">
                {message.severity ?? "info"}
              </span>
            </div>
            <pre className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-ui">
              {message.body}
            </pre>
          </div>
        );
      })}
    </div>
  );
}

