import { create } from "zustand";
import { api } from "@/lib/api";
import type {
  AddressVerifyResult,
  Citation,
  ConversationSummary,
  Message,
  ToolCall,
} from "@/types";

interface ChatState {
  conversationId: string | null;
  messages: Message[];
  citations: Record<string, Citation[]>;
  toolCalls: Record<string, ToolCall[]>;
  addressResults: Record<string, AddressVerifyResult>;
  streaming: boolean;
  streamText: string;
  error: string | null;
  conversations: ConversationSummary[];

  send: (text: string) => Promise<void>;
  startNew: () => void;
  loadConversation: (id: string) => Promise<void>;
  refreshConversations: () => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
}

export const useChat = create<ChatState>((set, get) => ({
  conversationId: null,
  messages: [],
  citations: {},
  toolCalls: {},
  addressResults: {},
  streaming: false,
  streamText: "",
  error: null,
  conversations: [],

  startNew: () =>
    set({
      conversationId: null,
      messages: [],
      citations: {},
      toolCalls: {},
      addressResults: {},
      streamText: "",
      error: null,
    }),

  send: async (text: string) => {
    const { conversationId, messages } = get();
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    set({
      messages: [...messages, userMsg],
      streaming: true,
      streamText: "",
      error: null,
    });

    let accumulatedText = "";
    const pendingCitations: Citation[] = [];
    const pendingTools: ToolCall[] = [];
    let assistantId = crypto.randomUUID();
    let finalConvId = conversationId;

    try {
      await api.stream(
        { conversation_id: conversationId, message: text, stream: true },
        (event) => {
          if (event.type === "start" && event.conversation_id) {
            finalConvId = event.conversation_id;
            set({ conversationId: event.conversation_id });
          } else if (event.type === "citations" && event.citations) {
            pendingCitations.push(...event.citations);
          } else if (event.type === "tool_call" && event.tool_call) {
            pendingTools.push(event.tool_call);
          } else if (event.type === "token" && event.text) {
            accumulatedText += event.text;
            set({ streamText: accumulatedText });
          } else if (event.type === "done") {
            if (event.message_id) assistantId = event.message_id;
          } else if (event.type === "error") {
            set({ error: event.error || "stream error" });
          }
        }
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ error: msg });
    }

    const assistantMsg: Message = {
      id: assistantId,
      role: "assistant",
      content: accumulatedText,
      created_at: new Date().toISOString(),
    };

    set((s) => ({
      messages: [...s.messages, assistantMsg],
      citations: { ...s.citations, [assistantMsg.id]: pendingCitations },
      toolCalls: { ...s.toolCalls, [assistantMsg.id]: pendingTools },
      streamText: "",
      streaming: false,
      conversationId: finalConvId,
    }));

    await get().refreshConversations();
  },

  loadConversation: async (id: string) => {
    const conv = await api.getConversation(id);
    set({
      conversationId: conv.id,
      messages: conv.messages,
      citations: {},
      toolCalls: {},
      addressResults: {},
      streamText: "",
      error: null,
    });
  },

  refreshConversations: async () => {
    try {
      const list = await api.listConversations();
      set({ conversations: list });
    } catch {
      // ignore
    }
  },

  deleteConversation: async (id: string) => {
    await api.deleteConversation(id);
    if (get().conversationId === id) get().startNew();
    await get().refreshConversations();
  },
}));
