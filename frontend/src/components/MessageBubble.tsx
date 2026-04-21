import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Bot } from "lucide-react";
import type { Message } from "@/types";
import clsx from "clsx";

interface Props {
  message: Message;
  streaming?: boolean;
}

export function MessageBubble({ message, streaming }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={clsx("flex gap-4 px-6 py-5", isUser ? "" : "bg-ink-50")}>
      <div
        className={clsx(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-md",
          isUser ? "bg-ink-700 text-white" : "bg-usps-blue text-white"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-500">
          {isUser ? "You" : "AMIE"}
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
