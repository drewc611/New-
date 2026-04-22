import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Volume2, Square } from "lucide-react";
import type { Message } from "@/types";
import { useTTS, ttsSupported } from "@/hooks/useTTS";
import clsx from "clsx";

interface Props {
  message: Message;
  streaming?: boolean;
}

export function MessageBubble({ message, streaming }: Props) {
  const isUser = message.role === "user";
  const { enabled, speakingId, speak, stop } = useTTS();
  const autoSpokenRef = useRef<string | null>(null);
  const ttsOk = ttsSupported();

  useEffect(() => {
    if (isUser || streaming || !ttsOk || !enabled) return;
    if (!message.content) return;
    if (autoSpokenRef.current === message.id) return;
    autoSpokenRef.current = message.id;
    speak(message.id, message.content);
  }, [isUser, streaming, enabled, ttsOk, message.id, message.content, speak]);

  const isSpeaking = speakingId === message.id;

  return (
    <div className={clsx("flex gap-3 px-4 py-4", isUser ? "" : "bg-ink-50")}>
      <div
        className={clsx(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-ink-700 text-white" : "bg-usps-blue text-white"
        )}
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : (
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
            <path d="M3 12l7-2 2-5 2 5 7 2-5 3 2 6-6-4-6 4 2-6-5-3z" />
          </svg>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center justify-between gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-ink-500">
            {isUser ? "You" : "AES Assistant"}
          </span>
          {!isUser && !streaming && ttsOk && message.content && (
            <button
              type="button"
              onClick={() =>
                isSpeaking ? stop() : speak(message.id, message.content)
              }
              title={isSpeaking ? "Stop speaking" : "Read aloud"}
              aria-label={isSpeaking ? "Stop speaking" : "Read aloud"}
              className={clsx(
                "flex h-6 w-6 items-center justify-center rounded text-ink-500 transition hover:bg-ink-100 hover:text-usps-blue",
                isSpeaking && "text-usps-blue"
              )}
            >
              {isSpeaking ? (
                <Square className="h-3.5 w-3.5" fill="currentColor" />
              ) : (
                <Volume2 className="h-3.5 w-3.5" />
              )}
            </button>
          )}
        </div>
        <div
          className={clsx(
            "prose-chat max-w-none text-sm text-ink-900",
            streaming && "typing-cursor"
          )}
        >
          {isUser ? (
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content || " "}
            </ReactMarkdown>
          )}
        </div>
      </div>
    </div>
  );
}
