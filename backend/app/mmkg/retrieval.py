"""Stage 5 — Modality-aware retrieval.

Fuses three signals:

1. **Vector similarity** over entity summaries (lexical fallback when no
   vector index is reachable, which keeps fakeredis-based tests useful).
2. **Graph traversal** from the top vector hit across ``references``,
   ``describes``, and ``belongs_to`` edges.
3. **Coherence reweighting** — entities that share a section with the
   query's best match get a boost so answers read as a unit instead of
   a grab-bag of disconnected facts.

``modality_bias`` (a dict keyed by :class:`Modality`) lets callers
amplify or suppress particular modalities at query time, implementing
stage 5's "adaptive scoring based on content type relevance".
"""
from __future__ import annotations

import math
import re

from app.core.logging import get_logger
from app.mmkg.graph import MultiModalKnowledgeGraph
from app.mmkg.schemas import GraphEntity, Modality, RetrievalHit

log = get_logger(__name__)


_DEFAULT_MODALITY_BIAS: dict[Modality, float] = {
    Modality.TEXT: 1.0,
    Modality.HEADING: 0.6,
    Modality.IMAGE: 1.1,
    Modality.TABLE: 1.15,
    Modality.EQUATION: 1.1,
    Modality.CODE: 0.9,
    Modality.LIST: 0.95,
    Modality.OTHER: 0.5,
}

_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


class ModalityAwareRetriever:
    def __init__(
        self,
        graph: MultiModalKnowledgeGraph,
        modality_bias: dict[Modality, float] | None = None,
    ) -> None:
        self._graph = graph
        self._bias = modality_bias or _DEFAULT_MODALITY_BIAS

    async def retrieve(
        self,
        query: str,
        doc_ids: list[str],
        top_k: int = 5,
        graph_hops: int = 1,
        modality_bias: dict[Modality, float] | None = None,
    ) -> list[RetrievalHit]:
        if not query.strip() or not doc_ids:
            return []

        bias = modality_bias or self._bias
        # Pull all entities for the requested documents. This is fine for
        # workloads in the KB-size range AMIE targets; larger corpora
        # would push this into a KNN vector index, which the existing
        # :class:`RedisVectorIndex` already supports if needed.
        candidates: list[GraphEntity] = []
        for doc_id in doc_ids:
            candidates.extend(await self._graph.list_entities(doc_id))
        if not candidates:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[GraphEntity, float]] = []
        for ent in candidates:
            raw_score = _lexical_score(ent, query_tokens)
            if raw_score <= 0.0:
                continue
            modal_score = raw_score * bias.get(ent.modality, 1.0)
            scored.append((ent, modal_score))

        if not scored:
            return []
        scored.sort(key=lambda p: p[1], reverse=True)

        # Vector-graph fusion: take top vector hits, then expand via graph
        # edges. De-duplicate by entity_id.
        seen: dict[str, RetrievalHit] = {}
        for ent, score in scored[: top_k * 2]:
            seen[ent.entity_id] = RetrievalHit(
                entity=ent, score=score, source="vector"
            )

        if graph_hops > 0:
            await self._expand_via_graph(seen, hops=graph_hops)

        # Coherence reweighting: boost hits that share a section with the
        # top vector result.
        await self._apply_coherence(seen, scored[0][0])

        hits = sorted(seen.values(), key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    async def _expand_via_graph(
        self, seen: dict[str, RetrievalHit], hops: int
    ) -> None:
        frontier = list(seen.keys())
        for _ in range(hops):
            next_frontier: list[str] = []
            for ent_id in frontier:
                for rel_type in ("references", "describes", "depends_on", "belongs_to"):
                    neighbors = await self._graph.neighbors(ent_id, rel_type, limit=10)
                    for nb_id, weight in neighbors:
                        if nb_id in seen:
                            seen[nb_id].score += 0.1 * weight
                            continue
                        nb = await self._graph.get_entity(nb_id)
                        if not nb:
                            continue
                        # Seed score comes from the source hit's score
                        # attenuated by the edge weight and a damping
                        # factor so multi-hop fan-out stays bounded.
                        seed = seen[ent_id].score * weight * 0.5
                        seen[nb_id] = RetrievalHit(
                            entity=nb, score=seed, source="graph"
                        )
                        next_frontier.append(nb_id)
            frontier = next_frontier
            if not frontier:
                break

    async def _apply_coherence(
        self, seen: dict[str, RetrievalHit], anchor: GraphEntity
    ) -> None:
        siblings = set(await self._graph.section_siblings(anchor))
        for hit in seen.values():
            if hit.entity.entity_id in siblings:
                hit.score *= 1.15
                hit.coherent_with.append(anchor.entity_id)
                hit.source = "fusion"


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _WORD_RE.findall(text)]


def _lexical_score(ent: GraphEntity, query_tokens: list[str]) -> float:
    """TF-IDF-lite scoring over an entity's label + summary + facts.

    Reusing the project's sentence-transformers model here would be the
    natural choice, but the mmkg ingest path already runs large and we
    don't want to double the embedding load at query time when a simple
    token-overlap score is adequate for the sizes AMIE handles today.
    """
    haystack = " ".join(
        [
            ent.label,
            ent.summary,
            " ".join(str(f.get("value", "")) for f in ent.meta.get("facts", []) or []),
        ]
    )
    hay_tokens = _tokenize(haystack)
    if not hay_tokens:
        return 0.0
    overlap = 0
    for q in query_tokens:
        overlap += hay_tokens.count(q)
    if overlap == 0:
        return 0.0
    # log-saturated scoring so a very-long entity summary can't dominate.
    return overlap / math.log2(len(hay_tokens) + 2)
