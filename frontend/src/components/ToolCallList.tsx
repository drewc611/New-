import { Wrench, CheckCircle2, XCircle, Clock } from "lucide-react";
import type { ToolCall } from "@/types";

export function ToolCallList({ toolCalls }: { toolCalls: ToolCall[] }) {
  if (!toolCalls.length) return null;
  return (
    <div className="border-l-2 border-usps-blue bg-white px-6 py-4">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
        <Wrench className="h-3.5 w-3.5" />
        Tool calls
      </div>
      <ul className="space-y-2">
        {toolCalls.map((t) => (
          <li key={t.id} className="rounded-md border border-ink-300 bg-ink-50 p-3">
            <div className="flex items-center gap-2">
              {t.error ? (
                <XCircle className="h-4 w-4 text-usps-red" />
              ) : (
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              )}
              <span className="font-mono text-sm font-semibold text-ink-900">{t.name}</span>
              {t.latency_ms != null && (
                <span className="ml-auto flex items-center gap-1 text-xs text-ink-500">
                  <Clock className="h-3 w-3" />
                  {t.latency_ms} ms
                </span>
              )}
            </div>
            <pre className="mt-2 overflow-x-auto rounded bg-ink-900 p-2 font-mono text-[11px] text-ink-100">
              {JSON.stringify(t.input, null, 2)}
            </pre>
            {t.error && <div className="mt-2 text-xs text-usps-red">{t.error}</div>}
            {t.output && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-ink-500">Output</summary>
                <pre className="mt-2 overflow-x-auto rounded bg-ink-900 p-2 font-mono text-[11px] text-ink-100">
                  {JSON.stringify(t.output, null, 2)}
                </pre>
              </details>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
