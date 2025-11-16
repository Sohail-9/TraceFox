"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Card } from "@/components/Card";
import { initiateGitHubLogin } from "@/lib/api";
import { loadSession } from "@/lib/session";

export default function LoginPage(): JSX.Element {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const session = loadSession();
    if (session?.token) {
      router.replace("/dashboard");
    }
  }, [router]);

  const handleSignIn = async () => {
    try {
      setLoading(true);
      await initiateGitHubLogin();
    } catch (error) {
      console.error("Failed to initiate GitHub login", error);
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 py-12 text-white">
      <Card className="w-full max-w-md border border-slate-800 bg-slate-900/80 p-8 shadow-2xl shadow-black/40">
        <div className="space-y-6 text-center">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.45em] text-slate-500">
              TraceFox
            </p>
            <h1 className="text-3xl font-semibold">AI-Powered Code Review</h1>
            <p className="text-sm text-slate-400">
              Connect your Git provider to unlock DeepSeek + Llama insights for
              every pull request.
            </p>
          </div>
          <div className="space-y-3">
            <button
              type="button"
              onClick={handleSignIn}
              className="w-full rounded-2xl bg-brand-500 px-4 py-2 text-sm font-semibold uppercase tracking-wide text-white transition hover:bg-brand-400 disabled:opacity-50"
              disabled={loading}
            >
              {loading ? "Redirecting…" : "Sign in with GitHub"}
            </button>
            <button
              type="button"
              className="w-full rounded-2xl border border-slate-700 px-4 py-2 text-sm font-semibold uppercase tracking-wide text-slate-200 transition hover:border-brand-400/60 hover:text-brand-100"
              disabled
            >
              GitLab SSO (coming soon)
            </button>
          </div>
          <p className="text-xs text-slate-500">
            Need an account?{" "}
            <Link
              href="https://github.com/your-org/tracefox"
              className="text-brand-300 underline underline-offset-4 hover:text-brand-200"
            >
              Request access
            </Link>
          </p>
        </div>
      </Card>
    </main>
  );
}
