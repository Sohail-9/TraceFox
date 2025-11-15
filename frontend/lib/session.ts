export interface SessionUser {
  user_id: string;
  login: string;
  name?: string | null;
  email?: string | null;
  avatar_url?: string | null;
  github_access_token?: string | null;
}

export interface SessionState {
  token: string;
  user: SessionUser;
}

const TOKEN_KEY = "tracefox.auth.token";
const USER_KEY = "tracefox.auth.user";
const STATE_KEY = "tracefox.auth.oauthState";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function loadSession(): SessionState | null {
  if (!isBrowser()) return null;
  const token = window.localStorage.getItem(TOKEN_KEY);
  const userRaw = window.localStorage.getItem(USER_KEY);
  if (!token || !userRaw) return null;
  try {
    const parsed = JSON.parse(userRaw) as SessionUser;
    return { token, user: parsed };
  } catch (error) {
    console.warn("Failed to parse stored TraceFox session", error);
    return null;
  }
}

export function storeSession(token: string, user: SessionUser): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
  window.sessionStorage.removeItem(STATE_KEY);
}

export function getAccessToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function rememberOAuthState(state: string): void {
  if (!isBrowser()) return;
  window.sessionStorage.setItem(STATE_KEY, state);
}

export function generateOAuthState(): string {
  const state = crypto.randomUUID();
  rememberOAuthState(state);
  return state;
}

export function consumeOAuthState(): string | null {
  if (!isBrowser()) return null;
  const state = window.sessionStorage.getItem(STATE_KEY);
  if (state) {
    window.sessionStorage.removeItem(STATE_KEY);
  }
  return state;
}

export function loadUser(): SessionUser | null {
  if (!isBrowser()) return null;
  const userRaw = window.localStorage.getItem(USER_KEY);
  if (!userRaw) return null;
  try {
    return JSON.parse(userRaw) as SessionUser;
  } catch (error) {
    console.warn("Failed to parse stored TraceFox user", error);
    return null;
  }
}
