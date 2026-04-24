"""Stage 2 — Multi-modal content routing.

Takes raw :class:`ParsedBlock` output from stage 1, categorises each
block by modality, and dispatches to the matching analyzer from stage 3
through concurrent asyncio pipelines. Also builds an explicit section
tree so stage 4 can attach ``belongs_to`` relations without having to
re-parse headings.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.mmkg.analyzers import AnalyzerRegistry, get_default_registry
from app.mmkg.schemas import AnalyzedBlock, Modality, ParsedBlock

log = get_logger(__name__)


@dataclass
class SectionNode:
    """One node of the section tree used for hierarchy preservation."""

    title: str
    path: tuple[str, ...]
    children: list["SectionNode"] = field(default_factory=list)
    block_ids: list[str] = field(default_factory=list)

    def find_or_create(self, path: tuple[str, ...]) -> "SectionNode":
        if path == self.path:
            return self
        # Descend one level.
        prefix = self.path + (path[len(self.path)],) if len(path) > len(self.path) else None
        if prefix is None:
            return self
        for child in self.children:
            if child.path == prefix:
                return child.find_or_create(path)
        new = SectionNode(title=path[len(self.path)], path=prefix)
        self.children.append(new)
        return new.find_or_create(path)


def build_section_tree(blocks: list[ParsedBlock]) -> SectionNode:
    root = SectionNode(title="__root__", path=())
    for blk in blocks:
        node = root.find_or_create(tuple(blk.section_path))
        node.block_ids.append(blk.block_id)
    return root


def categorize(blocks: list[ParsedBlock]) -> dict[Modality, list[ParsedBlock]]:
    """Group blocks by modality. Order within each bucket is preserved."""
    buckets: dict[Modality, list[ParsedBlock]] = {}
    for blk in blocks:
        buckets.setdefault(blk.modality, []).append(blk)
    return buckets


class ContentRouter:
    """Runs analyzers in parallel, one coroutine per block.

    A semaphore caps fan-out so heavy LLM analyzers don't stampede the
    provider. Defaults are tuned for the mock provider used in tests;
    operators can override via the ``max_concurrency`` constructor arg.
    """

    def __init__(
        self,
        registry: AnalyzerRegistry | None = None,
        max_concurrency: int = 8,
    ) -> None:
        self._registry = registry or get_default_registry()
        self._sem = asyncio.Semaphore(max_concurrency)

    async def _run_one(self, block: ParsedBlock) -> AnalyzedBlock:
        analyzer = self._registry.for_modality(block.modality)
        async with self._sem:
            try:
                return await analyzer.analyze(block)
            except Exception as e:
                log.warning(
                    "analyzer_failed",
                    analyzer=analyzer.name,
                    block_id=block.block_id,
                    error=str(e),
                )
                return AnalyzedBlock(block=block, analyzer=analyzer.name)

    async def route(self, blocks: list[ParsedBlock]) -> list[AnalyzedBlock]:
        if not blocks:
            return []
        log.info("routing_blocks", count=len(blocks))
        results = await asyncio.gather(*(self._run_one(b) for b in blocks))
        # Re-sort by the original order so downstream consumers see stable
        # output even though analyzers may finish out of order.
        return sorted(results, key=lambda a: a.block.order)
