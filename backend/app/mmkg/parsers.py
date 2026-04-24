"""Stage 1 — Document parsing.

Adaptive decomposition of heterogeneous documents into ordered
:class:`ParsedBlock` lists. Each parser is responsible for one input
format; :func:`parse_document` dispatches by file extension or content
hint.

MinerU is intentionally optional. Bringing in the upstream MinerU package
would pull torch + layoutlmv3 into the backend image, which this project
deliberately avoids. If operators install ``magic-pdf`` themselves we
opportunistically use it, otherwise we fall back to a built-in PDF text
extractor via :mod:`pypdf` when available.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.core.logging import get_logger
from app.mmkg.schemas import Modality, ParsedBlock

log = get_logger(__name__)


class DocumentParser(Protocol):
    """Contract that every stage-1 parser satisfies."""

    name: str

    def can_parse(self, path: Path | None, content: str | None) -> bool: ...

    def parse(self, *, doc_id: str, path: Path | None, content: str | None) -> list[ParsedBlock]: ...


@dataclass
class _Section:
    level: int
    title: str


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_FENCE_RE = re.compile(r"^```(\w+)?\s*$")
_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_EQUATION_INLINE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)


class MarkdownParser:
    """Parses markdown into ordered blocks while tracking section hierarchy.

    Recognises: headings, fenced code, pipe-tables, ``$$...$$`` equations,
    image references, and plain paragraphs. List items are grouped as a
    single ``LIST`` block per contiguous run so stage-3 can reason about
    them collectively.
    """

    name = "markdown"

    def can_parse(self, path: Path | None, content: str | None) -> bool:
        if path is not None and path.suffix.lower() in {".md", ".markdown"}:
            return True
        return content is not None

    def parse(
        self, *, doc_id: str, path: Path | None, content: str | None
    ) -> list[ParsedBlock]:
        text = content if content is not None else path.read_text(encoding="utf-8")
        blocks: list[ParsedBlock] = []
        section_stack: list[_Section] = []
        order = 0
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]

            # Fenced code: consume until the closing fence.
            m_fence = _FENCE_RE.match(line)
            if m_fence:
                lang = m_fence.group(1) or ""
                code: list[str] = []
                i += 1
                while i < len(lines) and not _FENCE_RE.match(lines[i]):
                    code.append(lines[i])
                    i += 1
                i += 1  # skip closing fence
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.CODE,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content="\n".join(code),
                        meta={"lang": lang},
                    )
                )
                order += 1
                continue

            # Heading: update section stack, emit heading block.
            m_head = _HEADING_RE.match(line)
            if m_head:
                level = len(m_head.group(1))
                title = m_head.group(2).strip()
                while section_stack and section_stack[-1].level >= level:
                    section_stack.pop()
                section_stack.append(_Section(level=level, title=title))
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.HEADING,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content=title,
                        meta={"level": level},
                    )
                )
                order += 1
                i += 1
                continue

            # Table: consume contiguous pipe-lines.
            if _TABLE_RE.match(line):
                table_lines: list[str] = []
                while i < len(lines) and _TABLE_RE.match(lines[i]):
                    table_lines.append(lines[i])
                    i += 1
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.TABLE,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content="\n".join(table_lines),
                    )
                )
                order += 1
                continue

            # Equation block.
            if line.strip().startswith("$$"):
                eq: list[str] = [line]
                i += 1
                while i < len(lines) and "$$" not in lines[i]:
                    eq.append(lines[i])
                    i += 1
                if i < len(lines):
                    eq.append(lines[i])
                    i += 1
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.EQUATION,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content="\n".join(eq).strip("$ \n"),
                    )
                )
                order += 1
                continue

            # Image reference.
            m_img = _IMAGE_RE.search(line)
            if m_img:
                alt, src = m_img.group(1), m_img.group(2)
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.IMAGE,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content=alt,
                        meta={"src": src, "alt": alt},
                    )
                )
                order += 1
                i += 1
                continue

            # List: group contiguous bullet/numeric items.
            if re.match(r"^\s*(?:[-*+]|\d+\.)\s+", line):
                items: list[str] = []
                while i < len(lines) and re.match(
                    r"^\s*(?:[-*+]|\d+\.)\s+", lines[i]
                ):
                    items.append(lines[i])
                    i += 1
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.LIST,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content="\n".join(items),
                    )
                )
                order += 1
                continue

            # Paragraph: gather until blank line.
            if line.strip():
                para: list[str] = [line]
                i += 1
                while i < len(lines) and lines[i].strip() and not _looks_structural(
                    lines[i]
                ):
                    para.append(lines[i])
                    i += 1
                raw = "\n".join(para)
                # Inline equations inside paragraphs become facts on the text block
                # rather than standalone blocks — a future analyzer can reconsider.
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.TEXT,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content=raw,
                        meta={"inline_equations": _EQUATION_INLINE.findall(raw)},
                    )
                )
                order += 1
                continue

            i += 1

        return blocks


def _looks_structural(line: str) -> bool:
    return (
        _HEADING_RE.match(line) is not None
        or _FENCE_RE.match(line) is not None
        or _TABLE_RE.match(line) is not None
        or line.strip().startswith("$$")
        or bool(re.match(r"^\s*(?:[-*+]|\d+\.)\s+", line))
        or bool(_IMAGE_RE.search(line))
    )


class PlainTextParser:
    """Paragraph-based fallback for .txt and unknown formats."""

    name = "text"

    def can_parse(self, path: Path | None, content: str | None) -> bool:
        if path is not None and path.suffix.lower() in {".txt", ""}:
            return True
        return content is not None

    def parse(
        self, *, doc_id: str, path: Path | None, content: str | None
    ) -> list[ParsedBlock]:
        text = content if content is not None else path.read_text(encoding="utf-8")
        paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        return [
            ParsedBlock(
                doc_id=doc_id,
                modality=Modality.TEXT,
                order=i,
                raw_content=p,
            )
            for i, p in enumerate(paras)
        ]


class HTMLParser:
    """Minimal HTML parser using the stdlib. Emits the same block set as
    the markdown parser. We deliberately avoid bs4 to keep the dependency
    surface small — the project already has enough moving parts."""

    name = "html"

    def can_parse(self, path: Path | None, content: str | None) -> bool:
        if path is not None and path.suffix.lower() in {".html", ".htm"}:
            return True
        if content is not None and content.lstrip().lower().startswith(("<html", "<!doctype")):
            return True
        return False

    def parse(
        self, *, doc_id: str, path: Path | None, content: str | None
    ) -> list[ParsedBlock]:
        from html.parser import HTMLParser as _StdHTML

        text = content if content is not None else path.read_text(encoding="utf-8")
        blocks: list[ParsedBlock] = []
        section_stack: list[_Section] = []
        order = 0

        # The stdlib HTMLParser streams events; we accumulate per-tag text
        # so the block boundaries line up with block-level elements.
        class _Collector(_StdHTML):
            def __init__(self) -> None:
                super().__init__()
                self.events: list[tuple[str, str, dict[str, str]]] = []
                self._stack: list[tuple[str, dict[str, str], list[str]]] = []

            def handle_starttag(self, tag, attrs):  # type: ignore[override]
                self._stack.append((tag, dict(attrs), []))

            def handle_endtag(self, tag):  # type: ignore[override]
                while self._stack and self._stack[-1][0] != tag:
                    popped = self._stack.pop()
                    self.events.append((popped[0], "".join(popped[2]), popped[1]))
                if self._stack:
                    popped = self._stack.pop()
                    self.events.append((popped[0], "".join(popped[2]), popped[1]))

            def handle_data(self, data):  # type: ignore[override]
                if self._stack:
                    self._stack[-1][2].append(data)

            def handle_startendtag(self, tag, attrs):  # type: ignore[override]
                self.events.append((tag, "", dict(attrs)))

        c = _Collector()
        c.feed(text)

        for tag, body, attrs in c.events:
            body = body.strip()
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                level = int(tag[1])
                while section_stack and section_stack[-1].level >= level:
                    section_stack.pop()
                section_stack.append(_Section(level=level, title=body))
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.HEADING,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content=body,
                        meta={"level": level},
                    )
                )
                order += 1
            elif tag == "table":
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.TABLE,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content=body,
                    )
                )
                order += 1
            elif tag == "img":
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.IMAGE,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content=attrs.get("alt", ""),
                        meta={"src": attrs.get("src", ""), "alt": attrs.get("alt", "")},
                    )
                )
                order += 1
            elif tag in {"pre", "code"}:
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.CODE,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content=body,
                    )
                )
                order += 1
            elif tag in {"ul", "ol"}:
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.LIST,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content=body,
                    )
                )
                order += 1
            elif tag == "p" and body:
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.TEXT,
                        order=order,
                        section_path=[s.title for s in section_stack],
                        raw_content=body,
                    )
                )
                order += 1

        return blocks


class PDFParser:
    """Optional PDF parser. Uses MinerU's ``magic-pdf`` if present, otherwise
    falls back to ``pypdf`` page-level text. If neither is installed we emit a
    single placeholder block so the graph still records the document."""

    name = "pdf"

    def can_parse(self, path: Path | None, content: str | None) -> bool:
        return path is not None and path.suffix.lower() == ".pdf"

    def parse(
        self, *, doc_id: str, path: Path | None, content: str | None
    ) -> list[ParsedBlock]:
        assert path is not None
        try:
            # MinerU integration hook — import is intentionally lazy.
            from magic_pdf.pipe.UNIPipe import UNIPipe  # type: ignore[import-not-found]

            pipe = UNIPipe(str(path), {}, [])
            pipe.pipe_classify()
            pipe.pipe_parse()
            items = pipe.pipe_mk_markdown(str(path.parent), drop_mode="none") or []
            return MarkdownParser().parse(
                doc_id=doc_id, path=None, content="\n\n".join(items)
            )
        except Exception as e:
            log.info("mineru_unavailable", error=str(e))

        try:
            from pypdf import PdfReader  # type: ignore[import-not-found]

            reader = PdfReader(str(path))
            blocks: list[ParsedBlock] = []
            for i, page in enumerate(reader.pages):
                text = (page.extract_text() or "").strip()
                if not text:
                    continue
                blocks.append(
                    ParsedBlock(
                        doc_id=doc_id,
                        modality=Modality.TEXT,
                        order=i,
                        raw_content=text,
                        meta={"page": i + 1},
                    )
                )
            return blocks
        except Exception as e:
            log.warning("pdf_fallback_failed", error=str(e))

        return [
            ParsedBlock(
                doc_id=doc_id,
                modality=Modality.OTHER,
                order=0,
                raw_content=f"[PDF {path.name} — no parser available]",
                meta={"src": str(path)},
            )
        ]


_DEFAULT_PARSERS: list[DocumentParser] = [
    PDFParser(),
    HTMLParser(),
    MarkdownParser(),
    PlainTextParser(),
]


def parse_document(
    *,
    path: str | Path | None = None,
    content: str | None = None,
    doc_id: str | None = None,
    parsers: list[DocumentParser] | None = None,
) -> list[ParsedBlock]:
    """Dispatch to the first parser that claims the input.

    Either ``path`` or ``content`` must be provided. ``doc_id`` defaults
    to the file stem (for paths) or a random short id (for raw strings).
    """
    if path is None and content is None:
        raise ValueError("parse_document requires path or content")
    p = Path(path) if path is not None else None
    resolved_id = doc_id or (p.stem if p is not None else uuid4().hex[:12])
    for parser in parsers or _DEFAULT_PARSERS:
        try:
            if parser.can_parse(p, content):
                blocks = parser.parse(doc_id=resolved_id, path=p, content=content)
                log.info(
                    "document_parsed",
                    doc_id=resolved_id,
                    parser=parser.name,
                    blocks=len(blocks),
                )
                return blocks
        except Exception as e:
            log.warning("parser_failed", parser=parser.name, error=str(e))
    # Last-resort fallback so ingest never crashes callers.
    return PlainTextParser().parse(doc_id=resolved_id, path=p, content=content)
