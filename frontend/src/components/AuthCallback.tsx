import { useEffect } from "react";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export function AuthCallback() {
  const { handleCallback, error } = useAuth();

  useEffect(() => {
    void handleCallback();
  }, [handleCallback]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-ink-50 px-4">
      <div
        className="w-full max-w-md rounded-lg border border-ink-300 bg-white p-8 text-center shadow-sm"
        role="status"
        aria-live="polite"
      >
        {error ? (
          <>
            <h1 className="text-xl font-semibold text-usps-red">
              Sign-in failed
            </h1>
            <p className="mt-2 text-sm text-ink-700">{error}</p>
            <a
              href="/"
              className="mt-4 inline-block text-sm text-usps-blue underline"
            >
              Return to sign in
            </a>
          </>
        ) : (
          <>
            <Loader2
              aria-hidden="true"
              className="mx-auto h-6 w-6 animate-spin text-usps-blue"
            />
            <h1 className="mt-3 text-base font-medium text-ink-900">
              Completing sign-in
            </h1>
            <p className="mt-1 text-sm text-ink-500">
              One moment while we verify your Okta session.
            </p>
          </>
        )}
      </div>
    </main>
  );
}
