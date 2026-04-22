import { create } from "zustand";
import { api } from "@/lib/api";
import type { AuthConfig, MeResponse } from "@/types";
import {
  beginLogin,
  clearTokens,
  completeLogin,
  loadTokens,
  logout as oidcLogout,
  resolveRuntime,
} from "@/lib/oidc";

interface AuthState {
  config: AuthConfig | null;
  user: MeResponse | null;
  loading: boolean;
  error: string | null;

  initialize: () => Promise<void>;
  login: () => Promise<void>;
  handleCallback: () => Promise<void>;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuth = create<AuthState>((set, get) => ({
  config: null,
  user: null,
  loading: true,
  error: null,

  initialize: async () => {
    set({ loading: true, error: null });
    try {
      const config = await api.authConfig();
      set({ config });

      // If auth is disabled, create a synthetic "dev" user so the rest
      // of the UI can treat authentication as a uniform concept.
      if (!config.enabled) {
        set({
          user: {
            sub: "dev-user",
            email: "dev@usps.gov",
            name: "Developer",
            tenant: "default",
            groups: [],
          },
          loading: false,
        });
        return;
      }

      const tokens = loadTokens();
      if (!tokens) {
        set({ user: null, loading: false });
        return;
      }
      try {
        const user = await api.me();
        set({ user, loading: false });
      } catch (err) {
        // Token is present but rejected by the backend. Force re-login.
        clearTokens();
        set({ user: null, loading: false });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ error: msg, loading: false });
    }
  },

  login: async () => {
    const runtime = resolveRuntime(get().config);
    if (!runtime) {
      set({ error: "Okta is not configured on this deployment" });
      return;
    }
    await beginLogin(runtime);
  },

  handleCallback: async () => {
    set({ loading: true, error: null });
    try {
      const runtime = resolveRuntime(get().config ?? (await api.authConfig()));
      if (!runtime) throw new Error("auth config unavailable");
      await completeLogin(runtime);
      const user = await api.me();
      // Clean the URL so the code/state do not linger in history.
      window.history.replaceState({}, document.title, "/");
      set({ user, loading: false });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ error: msg, loading: false });
    }
  },

  logout: () => {
    const runtime = resolveRuntime(get().config);
    if (runtime) {
      oidcLogout(runtime);
    } else {
      clearTokens();
      window.location.assign("/");
    }
    set({ user: null });
  },

  isAuthenticated: () => {
    const { config, user } = get();
    if (!config) return false;
    if (!config.enabled) return true;
    return !!user;
  },
}));
