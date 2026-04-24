"""Stage 3 — Multimodal analysis engine.

Modality-aware processing units. Each analyzer takes one
:class:`ParsedBlock` and returns an :class:`AnalyzedBlock` enriched with:

* a short prose ``summary`` — used for embedding and as the entity label
  downstream,
* a list of ``facts`` — atomic observations that become graph attributes.

All analyzers use :func:`app.llm.factory.get_llm_provider` when they need
generative help, so the pipeline honours the project's provider-agnostic
design. Under ``LLM_PROVIDER=mock`` every analyzer still produces useful
deterministic output drawn from the block's raw content — no test will
depend on a real model.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from app.core.logging import get_logger
from app.llm.base import LLMMessage, LLMProvider
from app.llm.factory import get_llm_provider
from app.mmkg.schemas import AnalyzedBlock, Modality, ParsedBlock

log = get_logger(__name__)


_SUMMARY_SYSTEM = (
    "You are a precise technical summariser. Respond with one sentence, "
    "no preamble."
)


class ModalityAnalyzer(ABC):
    name: str = "base"
    modality: Modality = Modality.OTHER

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    @property
    def llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = get_llm_provider()
        return self._llm

    async def _short_summary(self, prompt: str, fallback: str) -> str:
        try:
            resp = await self.llm.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system=_SUMMARY_SYSTEM,
                max_tokens=128,
                temperature=0.1,
            )
            text = resp.text.strip()
            return text or fallback
        except Exception as e:
            log.warning("analyzer_llm_failed", analyzer=self.name, error=str(e))
            return fallback

    @abstractmethod
    async def analyze(self, block: ParsedBlock) -> AnalyzedBlock: ...


class TextAnalyzer(ModalityAnalyzer):
    """Plain text and headings. Cheap — no LLM round-trip — because
    headings and paragraphs are already their own summary."""

    name = "text"
    modality = Modality.TEXT

    async def analyze(self, block: ParsedBlock) -> AnalyzedBlock:
        summary = block.raw_content.split("\n\n", 1)[0][:240]
        facts: list[dict[str, Any]] = []
        for eq in block.meta.get("inline_equations", []) or []:
            facts.append({"type": "inline_equation", "latex": eq})
        return AnalyzedBlock(block=block, summary=summary, facts=facts, analyzer=self.name)


class HeadingAnalyzer(ModalityAnalyzer):
    name = "heading"
    modality = Modality.HEADING

    async def analyze(self, block: ParsedBlock) -> AnalyzedBlock:
        return AnalyzedBlock(
            block=block,
            summary=block.raw_content,
            facts=[{"type": "heading_level", "value": block.meta.get("level", 1)}],
            analyzer=self.name,
        )


class VisualContentAnalyzer(ModalityAnalyzer):
    """Images. Generates a context-aware caption and records the image's
    spatial role via its ``section_path`` and ``meta.src``."""

    name = "visual"
    modality = Modality.IMAGE

    async def analyze(self, block: ParsedBlock) -> AnalyzedBlock:
        alt = block.meta.get("alt") or block.raw_content or ""
        src = block.meta.get("src", "")
        section_ctx = " / ".join(block.section_path) or "document root"
        prompt = (
            f"Image reference in section '{section_ctx}'. Alt text: {alt!r}. "
            f"Source: {src!r}. Write one sentence describing the likely content."
        )
        summary = await self._short_summary(prompt, fallback=alt or f"Image: {src}")
        facts = [
            {"type": "image_src", "value": src},
            {"type": "alt_text", "value": alt},
            {"type": "section", "value": section_ctx},
        ]
        return AnalyzedBlock(block=block, summary=summary, facts=facts, analyzer=self.name)


class StructuredDataInterpreter(ModalityAnalyzer):
    """Tables. Extracts header/row structure and a short narrative summary."""

    name = "table"
    modality = Modality.TABLE

    async def analyze(self, block: ParsedBlock) -> AnalyzedBlock:
        rows = _parse_pipe_table(block.raw_content)
        header = rows[0] if rows else []
        body_rows = rows[1:] if len(rows) > 1 else []
        facts: list[dict[str, Any]] = [
            {"type": "row_count", "value": len(body_rows)},
            {"type": "column_count", "value": len(header)},
            {"type": "columns", "value": header},
        ]
        # Simple statistical summary: for each numeric-looking column,
        # record min/max so downstream retrieval can answer "what's the
        # biggest X?" without another LLM call.
        for col_idx, col_name in enumerate(header):
            values = [
                _to_number(r[col_idx]) for r in body_rows if col_idx < len(r)
            ]
            numeric = [v for v in values if v is not None]
            if numeric and len(numeric) >= 2:
                facts.append(
                    {
                        "type": "column_stats",
                        "column": col_name,
                        "min": min(numeric),
                        "max": max(numeric),
                    }
                )

        section_ctx = " / ".join(block.section_path) or "document root"
        preview = "\n".join(block.raw_content.splitlines()[:6])
        prompt = (
            f"Section '{section_ctx}'. Table preview:\n{preview}\n"
            "Write one sentence describing what the table shows."
        )
        fallback = (
            f"Table with {len(body_rows)} rows and columns {header}."
            if header
            else "Table"
        )
        summary = await self._short_summary(prompt, fallback=fallback)
        return AnalyzedBlock(block=block, summary=summary, facts=facts, analyzer=self.name)


class MathematicalExpressionParser(ModalityAnalyzer):
    """Equations. Normalises to LaTeX and extracts the variable vocabulary
    so stage 4 can link equations to textual entities that mention the
    same symbols."""

    name = "equation"
    modality = Modality.EQUATION

    _VAR_RE = re.compile(r"(?:\\[a-zA-Z]+)|[a-zA-Z][a-zA-Z0-9_]*")

    async def analyze(self, block: ParsedBlock) -> AnalyzedBlock:
        latex = block.raw_content.strip()
        tokens = self._VAR_RE.findall(latex)
        # Filter out LaTeX command tokens and keep symbolic variables.
        variables = sorted({t for t in tokens if not t.startswith("\\") and len(t) <= 3})
        facts = [
            {"type": "latex", "value": latex},
            {"type": "variables", "value": variables},
        ]
        summary = (
            f"Equation involving {', '.join(variables)}." if variables else "Equation."
        )
        return AnalyzedBlock(block=block, summary=summary, facts=facts, analyzer=self.name)


class CodeAnalyzer(ModalityAnalyzer):
    name = "code"
    modality = Modality.CODE

    async def analyze(self, block: ParsedBlock) -> AnalyzedBlock:
        lang = block.meta.get("lang", "text")
        first = block.raw_content.splitlines()[0] if block.raw_content else ""
        summary = f"Code snippet ({lang}): {first[:120]}"
        facts = [
            {"type": "language", "value": lang},
            {"type": "line_count", "value": len(block.raw_content.splitlines())},
        ]
        return AnalyzedBlock(block=block, summary=summary, facts=facts, analyzer=self.name)


class ListAnalyzer(ModalityAnalyzer):
    name = "list"
    modality = Modality.LIST

    async def analyze(self, block: ParsedBlock) -> AnalyzedBlock:
        items = [
            re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", line)
            for line in block.raw_content.splitlines()
            if line.strip()
        ]
        summary = (
            f"List of {len(items)} items; first: {items[0][:80]}" if items else "List"
        )
        return AnalyzedBlock(
            block=block,
            summary=summary,
            facts=[{"type": "items", "value": items}],
            analyzer=self.name,
        )


class NoopAnalyzer(ModalityAnalyzer):
    name = "noop"
    modality = Modality.OTHER

    async def analyze(self, block: ParsedBlock) -> AnalyzedBlock:
        return AnalyzedBlock(
            block=block, summary=block.raw_content[:200], analyzer=self.name
        )


class AnalyzerRegistry:
    """Extensible modality handler.

    Third-party code can call :meth:`register` to plug in a new modality
    processor at runtime, matching the "plugin architecture" requirement
    of stage 3's Extensible Modality Handler.
    """

    def __init__(self) -> None:
        self._analyzers: dict[Modality, ModalityAnalyzer] = {}
        self._fallback: ModalityAnalyzer = NoopAnalyzer()

    def register(self, analyzer: ModalityAnalyzer) -> None:
        self._analyzers[analyzer.modality] = analyzer

    def for_modality(self, modality: Modality) -> ModalityAnalyzer:
        return self._analyzers.get(modality, self._fallback)

    def registered_modalities(self) -> list[Modality]:
        return list(self._analyzers.keys())


def get_default_registry(llm: LLMProvider | None = None) -> AnalyzerRegistry:
    """Build a registry populated with the shipped analyzers.

    ``llm`` is injected into each analyzer so callers (and tests) can
    swap in a deterministic provider without monkeypatching."""
    reg = AnalyzerRegistry()
    for cls in (
        TextAnalyzer,
        HeadingAnalyzer,
        VisualContentAnalyzer,
        StructuredDataInterpreter,
        MathematicalExpressionParser,
        CodeAnalyzer,
        ListAnalyzer,
    ):
        reg.register(cls(llm=llm))
    return reg


def _parse_pipe_table(raw: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in raw.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # Markdown tables use a divider row like |---|---|; drop those.
        if cells and all(re.fullmatch(r":?-+:?", c or "") for c in cells):
            continue
        rows.append(cells)
    return rows


def _to_number(s: str) -> float | None:
    try:
        return float(s.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None
