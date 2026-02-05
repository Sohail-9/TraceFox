"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Card } from "@/components/Card";
import { useToast } from "@/components/ToastProvider";
import { postJson } from "@/lib/api";
import {
  SessionUser,
  consumeOAuthState,
  storeSession,
} from "@/lib/session";

interface TokenResponse {
  access_token: string;
  token_type: string;
  user: SessionUser;
  github_token?: string | null;
}

export const dynamic = 'force-dynamic'; // Prevent static rendering

export default function GitHubCallbackPage(): JSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100">
          <Card
            title="GitHub Sign-in"
            accent="brand"
            className="max-w-md border border-slate-800 bg-slate-900/70 p-8"
          >
            <p className="text-sm text-slate-300">
              Loading GitHub sign-in...
            </p>
          </Card>
        </div>
      }
    >
      <GitHubCallbackContent router={router} searchParams={searchParams} />
    </Suspense>
  );
}

interface GitHubCallbackProps {
  router: ReturnType<typeof useRouter>;
  searchParams: ReturnType<typeof useSearchParams>;
}

function GitHubCallbackContent({
  router,
  searchParams,
}: GitHubCallbackProps): JSX.Element {
  const { addToast } = useToast();
  const [status, setStatus] = useState("Validating GitHub authorisation…");
  const [error, setError] = useState<string | null>(null);
  const code = searchParams.get("code");
  const state = searchParams.get("state");

  useEffect(() => {
    if (!code || !state) {
      setStatus("Unable to continue.");
      setError("Missing GitHub authorisation parameters.");
      return;
    }

    const expectedState = consumeOAuthState();
    if (expectedState && expectedState !== state) {
      setStatus("State validation failed.");
      setError("The OAuth state token did not match. Please try signing in again.");
      return;
    }

    let cancelled = false;

    async function exchangeCode() {
      try {
        const response = await postJson<TokenResponse>("/auth/github/callback", {
          code,
          state,
        });
        if (cancelled) return;
        storeSession(response.access_token, response.user);
        addToast({
          tone: "success",
          title: "GitHub connected",
          description: `Welcome back, ${response.user.login}!`,
        });
        router.replace("/dashboard");
      } catch (exchangeError) {
        if (cancelled) return;
        const message =
          exchangeError instanceof Error
            ? exchangeError.message
            : "Unable to complete GitHub authentication.";
        setError(message);
        setStatus("Authentication failed.");
      }
    }

    exchangeCode();

    return () => {
      cancelled = true;
    };
  }, [addToast, router, code, state]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100">
      <Card
        title="GitHub Sign-in"
        accent="brand"
        className="max-w-md border border-slate-800 bg-slate-900/70 p-8"
      >
        <div className="space-y-4">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.4em] text-slate-400">
              TraceFox Mission Control
            </p>
            <h1 className="text-2xl font-semibold text-white">
              Completing GitHub Sign-in
            </h1>
          </div>
          <p className="text-sm text-slate-300">{status}</p>
          {error ? (
            <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </div>
          ) : null}
          <button
            type="button"
            onClick={() => router.replace("/dashboard")}
            className="w-full rounded-xl border border-brand-400/40 bg-brand-500/20 px-4 py-2 text-sm font-semibold text-brand-100 transition hover:bg-brand-500/30"
          >
            Return to dashboard
          </button>
        </div>
      </Card>
    </main>
  );
}
