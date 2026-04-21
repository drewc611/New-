import { FileText, ExternalLink } from "lucide-react";
import type { Citation } from "@/types";

export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <div className="border-l-2 border-usps-gold bg-white px-6 py-4">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ink-500">
        <FileText className="h-3.5 w-3.5" />
        Sources
      </div>
      <ul className="space-y-2">
        {citations.map((c) => (
          <li key={c.chunk_id} className="rounded-md border border-ink-300 bg-ink-50 p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-semibold text-ink-900">{c.title}</div>
                <div className="mt-0.5 font-mono text-[11px] text-ink-500">
                  {c.chunk_id} · score {c.score.toFixed(3)}
                </div>
              </div>
              {c.url && (
                <a
                  href={c.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-ink-500 hover:text-usps-blue"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              )}
            </div>
            <p className="mt-2 line-clamp-3 text-xs text-ink-700">{c.snippet}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
