import { getAccessToken } from "./session";

const DEFAULT_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_BASE_URL;
}

export async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const base = getApiBaseUrl();
  const url = `${base}${path}`;
  const headers = new Headers({
    "Content-Type": "application/json",
  });
  if (options?.headers) {
    new Headers(options.headers).forEach((value, key) => {
      headers.set(key, value);
    });
  }
  const token = getAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(url, {
    ...options,
    headers,
    next: { revalidate: 5 },
  });
  if (!res.ok) {
    let errorMessage = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data?.detail) {
        errorMessage = `${errorMessage} - ${data.detail}`;
      }
    } catch {
      try {
        const text = await res.text();
        if (text) {
          errorMessage = `${errorMessage} - ${text}`;
        }
      } catch {
        // ignore
      }
    }
    throw new Error(`Failed to fetch ${path}: ${errorMessage}`);
  }
  return res.json() as Promise<T>;
}

export const swrFetcher = <T,>(path: string) => fetchJson<T>(path);

export async function postJson<T>(path: string, body: unknown, options?: RequestInit): Promise<T> {
  return fetchJson<T>(path, {
    ...options,
    method: options?.method ?? "POST",
    body: JSON.stringify(body),
  });
}
