"""End-to-end mmkg pipeline tests under fakeredis + LLM_PROVIDER=mock."""
from __future__ import annotations

import pytest

from app.mmkg.graph import MultiModalKnowledgeGraph
from app.mmkg.pipeline import MMKGPipeline
from app.mmkg.retrieval import ModalityAwareRetriever
from app.mmkg.router import ContentRouter, build_section_tree
from app.mmkg.schemas import Modality
from app.mmkg.parsers import parse_document


DOC = """# DPV Codes

The Delivery Point Validation code indicates deliverability status.

## Code Y

Y means the address is deliverable.

| code | meaning      |
|------|--------------|
| Y    | deliverable  |
| N    | undeliverable|

![dpv chart](dpv.png)

## Code N

N is non-deliverable. See equation:

$$ score = deliverability \\times 100 $$
"""


def test_section_tree_preserves_hierarchy():
    blocks = parse_document(content=DOC, doc_id="dpv")
    root = build_section_tree(blocks)
    # Root -> DPV Codes -> Code Y, Code N
    titles = [c.title for c in root.children]
    assert "DPV Codes" in titles
    dpv = next(c for c in root.children if c.title == "DPV Codes")
    sub_titles = [c.title for c in dpv.children]
    assert "Code Y" in sub_titles
    assert "Code N" in sub_titles


def test_router_analyzes_every_block():
    blocks = parse_document(content=DOC, doc_id="dpv")
    router = ContentRouter(max_concurrency=4)

    import asyncio

    analyzed = asyncio.run(router.route(blocks))
    assert len(analyzed) == len(blocks)
    # Each analyzed block has a non-empty summary.
    assert all(a.summary for a in analyzed)


@pytest.mark.asyncio
async def test_pipeline_ingest_persists_entities():
    from app.core.redis_client import get_redis

    pipeline = MMKGPipeline(graph=MultiModalKnowledgeGraph(get_redis()))
    entities = await pipeline.ingest(doc_id="dpv", content=DOC)
    assert entities
    modalities = {e.modality for e in entities}
    # Expect at least heading, text, table, image, equation types.
    assert Modality.HEADING in modalities
    assert Modality.TABLE in modalities
    assert Modality.IMAGE in modalities
    assert Modality.EQUATION in modalities


@pytest.mark.asyncio
async def test_retrieval_finds_relevant_entity_and_coheres():
    from app.core.redis_client import get_redis

    graph = MultiModalKnowledgeGraph(get_redis())
    pipeline = MMKGPipeline(graph=graph)
    await pipeline.ingest(doc_id="dpv", content=DOC)

    retriever = ModalityAwareRetriever(graph)
    hits = await retriever.retrieve("deliverable", doc_ids=["dpv"], top_k=3)

    assert hits, "retriever returned no hits for a query present in the doc"
    top = hits[0]
    # At least one hit should include the word 'deliverable' in its label
    # or summary, confirming modality-biased lexical scoring landed.
    assert any(
        "deliver" in (h.entity.label + h.entity.summary).lower() for h in hits
    )
    # Coherence boost attaches sibling hits to the anchor.
    assert top.source in {"vector", "fusion"}


@pytest.mark.asyncio
async def test_belongs_to_chain_materialized():
    from app.core.redis_client import get_redis

    graph = MultiModalKnowledgeGraph(get_redis())
    pipeline = MMKGPipeline(graph=graph)
    entities = await pipeline.ingest(doc_id="dpv", content=DOC)

    # Pick any non-heading entity under 'Code Y' and follow belongs_to up.
    code_y_child = next(
        e
        for e in entities
        if e.section_path and e.section_path[-1] == "Code Y" and e.modality != Modality.HEADING
    )
    parents = await graph.neighbors(code_y_child.entity_id, "belongs_to", limit=5)
    assert parents, "expected at least one belongs_to edge"
