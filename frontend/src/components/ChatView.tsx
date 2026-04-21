import { useEffect, useRef } from "react";
import { useChat } from "@/hooks/useChat";
import { MessageBubble } from "@/components/MessageBubble";
import { CitationList } from "@/components/CitationList";
import { ToolCallList } from "@/components/ToolCallList";
import { Composer } from "@/components/Composer";

export function ChatView() {
  const { messages, streaming, streamText, citations, toolCalls, error } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, streamText]);

  const empty = messages.length === 0 && !streaming;

  return (
    <main className="flex h-full flex-1 flex-col">
      <header className="border-b border-ink-300 bg-white px-6 py-3">
        <h1 className="text-sm font-semibold text-ink-900">AMIE Assistant</h1>
        <p className="text-xs text-ink-500">USPS Address Management Intelligent Engine</p>
      </header>

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

function EmptyState() {
  const samples = [
    "Explain CASS certification in plain terms",
    "What does a DPV code of S mean for an address?",
    "Verify 1600 Pennsylvania Ave, Washington, DC 20500",
    "What are the secondary address unit designators per Publication 28?",
  ];
  const { send } = useChat();
  return (
    <div className="flex h-full flex-col items-center justify-center px-8 py-16 text-center">
      <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-usps-blue text-2xl font-bold text-white">
        A
      </div>
      <h2 className="text-xl font-semibold text-ink-900">How can AMIE help you today?</h2>
      <p className="mt-2 max-w-lg text-sm text-ink-500">
        Ask a question about USPS addressing standards, or paste an address to validate.
        AMIE grounds every answer in Publication 28 and AMS documentation.
      </p>
      <div className="mt-8 grid w-full max-w-2xl grid-cols-1 gap-2 sm:grid-cols-2">
        {samples.map((s) => (
          <button
            key={s}
            onClick={() => send(s)}
            className="rounded-md border border-ink-300 bg-white px-4 py-3 text-left text-sm text-ink-700 transition hover:border-usps-blue hover:bg-ink-50"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
