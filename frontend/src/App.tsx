import { useEffect } from "react";
import { Loader2 } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { ChatView } from "@/components/ChatView";
import { LoginScreen } from "@/components/LoginScreen";
import { AuthCallback } from "@/components/AuthCallback";
import { useAuth } from "@/hooks/useAuth";

export default function App() {
  const { loading, initialize, isAuthenticated } = useAuth();
  const path = window.location.pathname;

  useEffect(() => {
    void initialize();
  }, [initialize]);

  if (path.startsWith("/auth/callback")) {
    return <AuthCallback />;
  }

  if (loading) {
    return (
      <main
        className="flex min-h-screen items-center justify-center bg-ink-50"
        role="status"
        aria-live="polite"
      >
        <Loader2
          aria-hidden="true"
          className="h-6 w-6 animate-spin text-usps-blue"
        />
        <span className="sr-only">Loading</span>
      </main>
    );
  }

  if (!isAuthenticated()) {
    return <LoginScreen />;
  }

  return (
    <div className="flex h-screen overflow-hidden bg-ink-50">
      <Sidebar />
      <ChatView />
    </div>
  );
}
