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
    <div className="border-t border-ink-300 bg-white p-4">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKey}
          placeholder="Ask about Publication 28, verify an address, or explore AMS workflows"
          rows={2}
          className="flex-1 resize-none rounded-md border border-ink-300 bg-ink-50 px-3 py-2 text-sm text-ink-900 placeholder:text-ink-500 focus:border-usps-blue focus:outline-none focus:ring-2 focus:ring-usps-blue/30"
        />
        <button
          onClick={submit}
          disabled={streaming || !value.trim()}
          className="flex h-10 w-10 items-center justify-center rounded-md bg-usps-blue text-white transition hover:bg-usps-blue/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </div>
      <div className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-ink-500">
        AMIE may make mistakes. Verify critical addressing decisions against Publication 28.
      </div>
    </div>
  );
}
