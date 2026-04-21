import { fetchEventSource } from "@microsoft/fetch-event-source";
import type {
  AddressVerifyResult,
  ChatRequest,
  ChatResponse,
  Conversation,
  ConversationSummary,
  StreamEvent,
} from "@/types";

const BASE = import.meta.env.VITE_API_BASE_URL || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    const body = await resp.text().catch(() => "");
    throw new Error(`API ${resp.status}: ${body || resp.statusText}`);
  }
  return (await resp.json()) as T;
}

export const api = {
  health: () =>
    request<{ status: string; version: string; redis_ok: boolean }>("/api/health"),

  chat: (req: ChatRequest) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  listConversations: () => request<ConversationSummary[]>("/api/conversations"),
  getConversation: (id: string) => request<Conversation>(`/api/conversations/${id}`),
  deleteConversation: (id: string) =>
    request<{ deleted: string }>(`/api/conversations/${id}`, { method: "DELETE" }),

  verifyAddress: (address: string) =>
    request<AddressVerifyResult>("/api/tools/address/verify", {
      method: "POST",
      body: JSON.stringify({ address }),
    }),

  stream: async (
    req: ChatRequest,
    onEvent: (event: StreamEvent) => void,
    signal?: AbortSignal
  ): Promise<void> => {
    await fetchEventSource(`${BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
      signal,
      openWhenHidden: true,
      onmessage(ev) {
        if (!ev.data) return;
        try {
          const parsed = JSON.parse(ev.data) as StreamEvent;
          onEvent(parsed);
        } catch {
          // ignore malformed
        }
      },
      onerror(err) {
        onEvent({ type: "error", error: String(err) });
        throw err;
      },
    });
  },
};
