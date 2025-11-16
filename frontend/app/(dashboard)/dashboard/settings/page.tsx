"use client";

import { Card } from "@/components/Card";

export default function SettingsPage(): JSX.Element {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">TraceFox</p>
        <h1 className="text-3xl font-semibold text-white">Settings</h1>
        <p className="text-sm text-slate-400">
          Configure GitHub/GitLab integrations, notification channels, and feature flags.
        </p>
      </div>
      <Card className="border border-slate-800 bg-slate-950/60 p-5 text-sm text-slate-400">
        Settings UI coming soon. Use environment variables or the backend configuration service to
        control providers, rate limits, and authentication.
      </Card>
    </div>
  );
}
