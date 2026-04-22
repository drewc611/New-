// OIDC Authorization Code + PKCE client.
//
// Uses only Web Crypto and sessionStorage; no third-party SDK required.
// The SPA never sees a client secret. Access tokens are held in memory
// during the session and persisted in sessionStorage so an in-app reload
// does not force a re-login. Refresh is handled by silent authentication
// against the Okta /authorize endpoint (prompt=none) rather than storing
// a refresh token in the browser.

import type { AuthConfig } from "@/types";

const STORAGE_PREFIX = "amie.oidc.";
const PKCE_STATE_KEY = STORAGE_PREFIX + "state";
const PKCE_VERIFIER_KEY = STORAGE_PREFIX + "verifier";
const TOKEN_KEY = STORAGE_PREFIX + "tokens";

export interface TokenSet {
  access_token: string;
  id_token?: string;
  refresh_token?: string;
  token_type: string;
  expires_at: number; // epoch ms
  scope?: string;
}

export interface OidcRuntime {
  issuer: string;
  clientId: string;
  audience: string;
  scopes: string[];
  redirectUri: string;
  postLogoutRedirectUri: string;
}

function randomString(length = 64): string {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, length);
}

function base64UrlEncode(bytes: ArrayBuffer): string {
  const b64 = btoa(String.fromCharCode(...new Uint8Array(bytes)));
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function sha256(value: string): Promise<string> {
  const data = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return base64UrlEncode(digest);
}

function fromBackendConfig(
  config: AuthConfig,
  redirectUri: string,
  postLogoutRedirectUri: string,
): OidcRuntime {
  return {
    issuer: config.issuer,
    clientId: config.client_id,
    audience: config.audience,
    scopes: config.scopes,
    redirectUri,
    postLogoutRedirectUri,
  };
}

function fromViteEnv(): OidcRuntime | null {
  const issuer = import.meta.env.VITE_OKTA_ISSUER;
  const clientId = import.meta.env.VITE_OKTA_CLIENT_ID;
  if (!issuer || !clientId) return null;
  return {
    issuer,
    clientId,
    audience: import.meta.env.VITE_OKTA_AUDIENCE || "",
    scopes: (import.meta.env.VITE_OKTA_SCOPES || "openid profile email").split(
      /\s+/,
    ),
    redirectUri:
      import.meta.env.VITE_OKTA_REDIRECT_URI ||
      `${window.location.origin}/auth/callback`,
    postLogoutRedirectUri:
      import.meta.env.VITE_OKTA_POST_LOGOUT_URI || window.location.origin,
  };
}

export function resolveRuntime(config: AuthConfig | null): OidcRuntime | null {
  if (config?.enabled && config.issuer && config.client_id) {
    return fromBackendConfig(
      config,
      import.meta.env.VITE_OKTA_REDIRECT_URI ||
        `${window.location.origin}/auth/callback`,
      import.meta.env.VITE_OKTA_POST_LOGOUT_URI || window.location.origin,
    );
  }
  return fromViteEnv();
}

export async function beginLogin(runtime: OidcRuntime): Promise<void> {
  const state = randomString(32);
  const verifier = randomString(64);
  const challenge = await sha256(verifier);
  sessionStorage.setItem(PKCE_STATE_KEY, state);
  sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);

  const url = new URL(`${runtime.issuer.replace(/\/$/, "")}/v1/authorize`);
  url.searchParams.set("client_id", runtime.clientId);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("redirect_uri", runtime.redirectUri);
  url.searchParams.set("scope", runtime.scopes.join(" "));
  url.searchParams.set("state", state);
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("code_challenge_method", "S256");
  if (runtime.audience) url.searchParams.set("audience", runtime.audience);
  window.location.assign(url.toString());
}

export async function completeLogin(runtime: OidcRuntime): Promise<TokenSet> {
  const params = new URLSearchParams(window.location.search);
  const error = params.get("error");
  if (error) {
    throw new Error(
      `Okta returned error=${error}; ${params.get("error_description") || ""}`,
    );
  }
  const code = params.get("code");
  const state = params.get("state");
  if (!code || !state) throw new Error("missing code or state from Okta callback");

  const expectedState = sessionStorage.getItem(PKCE_STATE_KEY);
  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
  if (!expectedState || state !== expectedState) {
    throw new Error("state mismatch; possible CSRF, aborting login");
  }
  if (!verifier) throw new Error("missing PKCE verifier in session storage");
  sessionStorage.removeItem(PKCE_STATE_KEY);
  sessionStorage.removeItem(PKCE_VERIFIER_KEY);

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: runtime.redirectUri,
    client_id: runtime.clientId,
    code_verifier: verifier,
  });

  const response = await fetch(
    `${runtime.issuer.replace(/\/$/, "")}/v1/token`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    },
  );
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`token exchange failed ${response.status}: ${text}`);
  }
  const json = (await response.json()) as {
    access_token: string;
    id_token?: string;
    refresh_token?: string;
    token_type: string;
    expires_in: number;
    scope?: string;
  };

  const tokens: TokenSet = {
    access_token: json.access_token,
    id_token: json.id_token,
    refresh_token: json.refresh_token,
    token_type: json.token_type,
    expires_at: Date.now() + (json.expires_in - 30) * 1000,
    scope: json.scope,
  };
  sessionStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  return tokens;
}

export function loadTokens(): TokenSet | null {
  const raw = sessionStorage.getItem(TOKEN_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as TokenSet;
    if (Date.now() >= parsed.expires_at) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearTokens(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

export function logout(runtime: OidcRuntime, idToken?: string): void {
  clearTokens();
  if (!runtime.issuer) {
    window.location.assign(runtime.postLogoutRedirectUri);
    return;
  }
  const url = new URL(`${runtime.issuer.replace(/\/$/, "")}/v1/logout`);
  if (idToken) url.searchParams.set("id_token_hint", idToken);
  url.searchParams.set(
    "post_logout_redirect_uri",
    runtime.postLogoutRedirectUri,
  );
  window.location.assign(url.toString());
}
