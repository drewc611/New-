"""Document chunking. Splits source docs into semantic chunks."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    url: str | None = None


def chunk_text(
    text: str,
    doc_id: str,
    title: str,
    url: str | None = None,
    max_chars: int = 1200,
    overlap: int = 150,
) -> list[Chunk]:
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[Chunk] = []
    buf = ""
    idx = 0
    for p in paragraphs:
        if len(buf) + len(p) + 2 <= max_chars:
            buf = f"{buf}\n\n{p}".strip() if buf else p
            continue
        if buf:
            chunks.append(Chunk(f"{doc_id}#{idx}", doc_id, title, buf, url))
            idx += 1
            tail = buf[-overlap:] if overlap else ""
            buf = f"{tail}\n\n{p}".strip() if tail else p
        else:
            for i in range(0, len(p), max_chars - overlap):
                sub = p[i : i + max_chars]
                chunks.append(Chunk(f"{doc_id}#{idx}", doc_id, title, sub, url))
                idx += 1
            buf = ""
    if buf:
        chunks.append(Chunk(f"{doc_id}#{idx}", doc_id, title, buf, url))
    return chunks
