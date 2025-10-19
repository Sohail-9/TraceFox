const DEFAULT_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_BASE_URL;
}

export async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const base = getApiBaseUrl();
  const url = `${base}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    next: { revalidate: 5 },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ${path}: ${res.status} ${res.statusText}`);
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
