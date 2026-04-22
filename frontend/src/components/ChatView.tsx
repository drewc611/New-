import { useEffect, useRef } from "react";
import {
  Database,
  AlertCircle,
  BarChart3,
  MapPin,
  Upload,
  ListChecks,
  AlertTriangle,
  Send as SendIcon,
  FileText as DocIcon,
  Pencil,
  Download,
  Volume2,
  VolumeX,
  Copy,
  X,
} from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { useTTS, ttsSupported } from "@/hooks/useTTS";
import { MessageBubble } from "@/components/MessageBubble";
import { CitationList } from "@/components/CitationList";
import { ToolCallList } from "@/components/ToolCallList";
import { Composer } from "@/components/Composer";

interface QuickAction {
  label: string;
  prompt: string;
  icon: typeof Database;
}

const QUICK_ACTIONS: QuickAction[] = [
  { label: "Data Summary", prompt: "Give me a summary of my data", icon: BarChart3 },
  { label: "Verify Address", prompt: "Verify an address for me", icon: MapPin },
  { label: "How do I upload files?", prompt: "How do I upload files?", icon: Upload },
  { label: "Required fields", prompt: "What are the required fields?", icon: ListChecks },
  { label: "Validation Issues", prompt: "Show me my validation issues", icon: AlertTriangle },
  { label: "Submission process", prompt: "Explain the submission process", icon: SendIcon },
  { label: "Service Docs", prompt: "Show me the service documentation", icon: DocIcon },
];

const RECORD_COUNT = 21242;
const ISSUE_COUNT = 1;
const LOCATION = "MATTHEWS, NC";

export function ChatView() {
  const { messages, streaming, streamText, citations, toolCalls, error, startNew } = useChat();
  const { enabled: ttsEnabled, toggleEnabled: toggleTTS, stop: stopTTS } = useTTS();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, streamText]);

  const empty = messages.length === 0 && !streaming;
  const ttsOk = ttsSupported();

  const exportTranscript = () => {
    if (messages.length === 0) return;
    const text = messages
      .map((m) => `${m.role === "user" ? "You" : "AES Help Assistant"}: ${m.content}`)
      .join("\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aes-chat-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyTranscript = async () => {
    if (messages.length === 0) return;
    const text = messages
      .map((m) => `${m.role === "user" ? "You" : "AES Help Assistant"}: ${m.content}`)
      .join("\n\n");
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* ignore */
    }
  };

  const closeChat = () => {
    stopTTS();
    startNew();
  };

  return (
    <main className="flex h-full flex-1 flex-col bg-white">
      {/* Header bar */}
      <header className="bg-usps-blue px-4 py-2.5 text-white shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10">
              <EagleIcon />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="truncate text-sm font-semibold tracking-wide">
                  AES Help Assistant
                </h1>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-100 ring-1 ring-inset ring-emerald-400/40">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" />
                  Online
                </span>
              </div>
              <p className="truncate text-[11px] text-white/70">
                United States Postal Service
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <HeaderIconBtn title="New chat" onClick={startNew}>
              <Pencil className="h-4 w-4" />
            </HeaderIconBtn>
            <HeaderIconBtn
              title="Download transcript"
              onClick={exportTranscript}
              disabled={messages.length === 0}
            >
              <Download className="h-4 w-4" />
            </HeaderIconBtn>
            <HeaderIconBtn
              title={ttsEnabled ? "Mute voice responses" : "Unmute voice responses"}
              onClick={toggleTTS}
              disabled={!ttsOk}
              active={ttsEnabled && ttsOk}
            >
              {ttsEnabled && ttsOk ? (
                <Volume2 className="h-4 w-4" />
              ) : (
                <VolumeX className="h-4 w-4" />
              )}
            </HeaderIconBtn>
            <HeaderIconBtn
              title="Copy transcript"
              onClick={copyTranscript}
              disabled={messages.length === 0}
            >
              <Copy className="h-4 w-4" />
            </HeaderIconBtn>
            <HeaderIconBtn title="Close / clear" onClick={closeChat}>
              <X className="h-4 w-4" />
            </HeaderIconBtn>
          </div>
        </div>
      </header>

      {/* Stat bar */}
      <div className="flex items-center gap-4 border-b border-ink-300 bg-ink-50 px-4 py-1.5 text-[11px] text-ink-700">
        <span className="inline-flex items-center gap-1.5">
          <Database className="h-3 w-3 text-usps-blue" />
          <strong className="font-semibold text-ink-900">
            {RECORD_COUNT.toLocaleString()}
          </strong>{" "}
          records
        </span>
        <span className="inline-flex items-center gap-1.5">
          <AlertCircle className="h-3 w-3 text-usps-red" />
          <strong className="font-semibold text-ink-900">{ISSUE_COUNT}</strong>{" "}
          issue{ISSUE_COUNT === 1 ? "" : "s"}
        </span>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {empty && <EmptyState />}

        {messages.map((msg) => {
          const msgCites = citations[msg.id] || [];
          const msgTools = toolCalls[msg.id] || [];
          return (
            <div key={msg.id}>
              <MessageBubble message={msg} />
              {msg.role === "assistant" && msgTools.length > 0 && (
                <ToolCallList toolCalls={msgTools} />
              )}
              {msg.role === "assistant" && msgCites.length > 0 && (
                <CitationList citations={msgCites} />
              )}
            </div>
          );
        })}

        {streaming && streamText && (
          <MessageBubble
            streaming
            message={{ id: "streaming", role: "assistant", content: streamText }}
          />
        )}

        {error && (
          <div className="mx-6 my-3 rounded-md border border-usps-red bg-red-50 px-4 py-2 text-sm text-usps-red">
            {error}
          </div>
        )}
      </div>

      <Composer />
    </main>
  );
}

interface HeaderIconBtnProps {
  title: string;
  onClick: () => void;
  disabled?: boolean;
  active?: boolean;
  children: React.ReactNode;
}

function HeaderIconBtn({
  title,
  onClick,
  disabled,
  active,
  children,
}: HeaderIconBtnProps) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={onClick}
      disabled={disabled}
      className={
        "flex h-7 w-7 items-center justify-center rounded-md text-white/90 transition " +
        "hover:bg-white/15 hover:text-white " +
        "disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent " +
        (active ? "bg-white/10 " : "")
      }
    >
      {children}
    </button>
  );
}

function EagleIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-5 w-5 text-white"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M3 12l7-2 2-5 2 5 7 2-5 3 2 6-6-4-6 4 2-6-5-3z" />
    </svg>
  );
}

function EmptyState() {
  const { send } = useChat();

  return (
    <div className="flex flex-col px-4 py-5">
      {/* Bot welcome bubble */}
      <div className="flex gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-usps-blue text-white">
          <EagleIcon />
        </div>
        <div className="flex-1 space-y-3">
          <p className="text-sm font-semibold text-ink-900">
            Welcome to Address Enterprise Service Portal. I'm the AES Help
            Assistant.
          </p>
          <p className="text-sm text-ink-700">
            I can see you have{" "}
            <strong className="text-ink-900">
              {RECORD_COUNT.toLocaleString()}
            </strong>{" "}
            address records loaded for{" "}
            <strong className="text-ink-900">{LOCATION}</strong>. I can help you
            with validation issues, required fields, plat maps, submissions, and
            more.
          </p>
          <p className="text-sm text-ink-700">
            Try asking{" "}
            <em className="text-ink-900">"Give me a summary of my data"</em> or
            use one of the quick actions below.
          </p>
          <p className="text-[11px] text-ink-500">
            {new Date().toLocaleTimeString([], {
              hour: "numeric",
              minute: "2-digit",
            })}
          </p>
        </div>
      </div>

      {/* Quick actions */}
      <div className="mt-6">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-ink-500">
          Quick Actions
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {QUICK_ACTIONS.map(({ label, prompt, icon: Icon }) => (
            <button
              key={label}
              onClick={() => send(prompt)}
              className="flex items-center gap-2 rounded-md border border-ink-300 bg-white px-3 py-2 text-left text-sm text-ink-800 transition hover:border-usps-blue hover:bg-ink-50 hover:text-usps-blue"
            >
              <Icon className="h-4 w-4 shrink-0 text-usps-blue" />
              <span className="truncate">{label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
