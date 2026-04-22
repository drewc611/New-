import { Lock } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export function LoginScreen() {
  const { login, config, error } = useAuth();
  const provider = config?.provider === "okta" ? "Okta" : "your organization";

  return (
    <main className="flex min-h-screen items-center justify-center bg-ink-50 px-4">
      <div className="w-full max-w-md rounded-lg border border-ink-300 bg-white p-8 shadow-sm">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-usps-blue text-white">
          <Lock aria-hidden="true" className="h-6 w-6" />
        </div>
        <h1 className="text-xl font-semibold text-ink-900">
          Sign in to AMIE
        </h1>
        <p className="mt-2 text-sm text-ink-700">
          AMIE requires single sign-on through {provider}. You will be
          redirected to authenticate, then returned here.
        </p>
        {error && (
          <div
            role="alert"
            className="mt-4 rounded-md border border-usps-red bg-red-50 px-3 py-2 text-sm text-usps-red"
          >
            {error}
          </div>
        )}
        <button
          type="button"
          onClick={() => void login()}
          className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-md bg-usps-blue px-4 py-2 text-sm font-medium text-white transition hover:bg-usps-blue/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-usps-blue/50 focus-visible:ring-offset-1"
        >
          Continue with {provider}
        </button>
        <p className="mt-4 text-center text-xs text-ink-500">
          By signing in you agree to USPS Handbook AS-805 acceptable use
          requirements.
        </p>
      </div>
    </main>
  );
}
