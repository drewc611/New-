import { Send, Loader2 } from "lucide-react";
import { useState, KeyboardEvent } from "react";
import { useChat } from "@/hooks/useChat";

export function Composer() {
  const [value, setValue] = useState("");
  const { send, streaming } = useChat();

  const submit = async () => {
    const trimmed = value.trim();
    if (!trimmed || streaming) return;
    setValue("");
    await send(trimmed);
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-ink-300 bg-white px-3 py-3">
      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKey}
          placeholder="Ask a question or type a command..."
          rows={1}
          className="w-full resize-none rounded-full border border-ink-300 bg-white py-2.5 pl-4 pr-12 text-sm text-ink-900 placeholder:text-ink-500 focus:border-usps-blue focus:outline-none focus:ring-2 focus:ring-usps-blue/20"
        />
        <button
          onClick={submit}
          disabled={streaming || !value.trim()}
          aria-label="Send message"
          className="absolute right-1.5 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-usps-blue text-white transition hover:bg-usps-blue/90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {streaming ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-3.5 w-3.5" />
          )}
        </button>
      </div>
      <div className="mt-2 text-center text-[10px] text-ink-500">
        Powered by USPS Address Enterprise Service
      </div>
    </div>
  );
}
