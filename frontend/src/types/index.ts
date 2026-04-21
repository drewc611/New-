export type Role = "user" | "assistant" | "system" | "tool";

export interface Message {
  id: string;
  role: Role;
  content: string;
  created_at?: string;
}

export interface Citation {
  chunk_id: string;
  doc_id: string;
  title: string;
  snippet: string;
  score: number;
  url?: string | null;
}

export interface ToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
  output?: Record<string, unknown> | null;
  latency_ms?: number | null;
  error?: string | null;
}

export interface AddressVerifyResult {
  input_address: string;
  standardized?: string | null;
  street?: string | null;
  city?: string | null;
  state?: string | null;
  zip5?: string | null;
  zip4?: string | null;
  dpv_code?: string | null;
  return_codes: string[];
  confidence: number;
  verified: boolean;
}

export interface ChatRequest {
  conversation_id?: string | null;
  message: string;
  intent_hint?: "rag" | "address_verify" | "auto";
  stream?: boolean;
}

export interface ChatResponse {
  conversation_id: string;
  message: Message;
  citations: Citation[];
  tool_calls: ToolCall[];
  address_result?: AddressVerifyResult | null;
  usage: Record<string, number>;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
  tenant: string;
  user_id: string;
}

export interface StreamEvent {
  type: "start" | "tool_call" | "citations" | "token" | "done" | "error";
  conversation_id?: string;
  message_id?: string;
  tool_call?: ToolCall;
  citations?: Citation[];
  text?: string;
  error?: string;
}
