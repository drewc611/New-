import { MessageSquarePlus, Trash2, MessageCircle, LogOut } from "lucide-react";
import { useEffect } from "react";
import { useChat } from "@/hooks/useChat";
import { useAuth } from "@/hooks/useAuth";
import clsx from "clsx";

export function Sidebar() {
  const {
    conversations,
    conversationId,
    refreshConversations,
    loadConversation,
    deleteConversation,
    startNew,
  } = useChat();

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  return (
    <aside className="flex h-full w-72 flex-col border-r border-ink-300 bg-white">
      <div className="flex items-center gap-2 border-b border-ink-300 p-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-usps-blue text-white font-bold">
          A
        </div>
        <div>
          <div className="text-sm font-semibold text-ink-900">AMIE</div>
          <div className="text-xs text-ink-500">
            Address Management Intelligent Engine
          </div>
        </div>
      </div>

      <button
        onClick={startNew}
        className="m-3 flex items-center gap-2 rounded-md border border-ink-300 px-3 py-2 text-sm font-medium text-ink-700 transition hover:bg-ink-50"
      >
        <MessageSquarePlus className="h-4 w-4" />
        New conversation
      </button>

      <div className="flex-1 overflow-y-auto px-2 pb-4">
        <div className="px-2 pb-1 pt-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
          Recent
        </div>
        {conversations.length === 0 && (
          <div className="px-2 py-4 text-sm text-ink-500">No conversations yet</div>
        )}
        <ul className="space-y-1">
          {conversations.map((c) => (
            <li key={c.id}>
              <div
                className={clsx(
                  "group flex items-center gap-2 rounded-md px-2 py-2 text-sm transition",
                  conversationId === c.id
                    ? "bg-ink-100 text-ink-900"
                    : "text-ink-700 hover:bg-ink-50"
                )}
              >
                <button
                  onClick={() => loadConversation(c.id)}
                  className="flex flex-1 items-center gap-2 truncate text-left"
                >
                  <MessageCircle className="h-4 w-4 shrink-0 text-ink-500" />
                  <span className="truncate">{c.title}</span>
                </button>
                <button
                  onClick={() => deleteConversation(c.id)}
                  className="opacity-0 transition group-hover:opacity-100"
                  aria-label="Delete conversation"
                >
                  <Trash2 className="h-4 w-4 text-ink-500 hover:text-usps-red" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <UserChip />
    </aside>
  );
}

function UserChip() {
  const { user, config, logout } = useAuth();
  if (!user) {
    return (
      <div className="border-t border-ink-300 p-3 text-xs text-ink-500">
        <div>USPS Address Management Future State</div>
        <div className="opacity-70">v0.1.0 local dev</div>
      </div>
    );
  }
  const initials = (user.name || user.email || user.sub)
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w.charAt(0).toUpperCase())
    .join("");
  return (
    <div className="border-t border-ink-300 p-3">
      <div className="flex items-center gap-2">
        <div
          aria-hidden="true"
          className="flex h-8 w-8 items-center justify-center rounded-full bg-usps-blue text-xs font-semibold text-white"
        >
          {initials || "U"}
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium text-ink-900">
            {user.name || user.email || "Signed in"}
          </div>
          <div className="truncate text-xs text-ink-700">{user.email}</div>
        </div>
        {config?.enabled && (
          <button
            type="button"
            onClick={logout}
            aria-label="Sign out"
            className="rounded-md p-1 text-ink-500 transition hover:bg-ink-50 hover:text-usps-red focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-usps-blue/50"
          >
            <LogOut aria-hidden="true" className="h-4 w-4" />
          </button>
        )}
      </div>
      {user.groups.length > 0 && (
        <div
          className="mt-2 truncate text-[11px] text-ink-500"
          title={user.groups.join(", ")}
        >
          Groups: {user.groups.join(", ")}
        </div>
      )}
    </div>
  );
}
