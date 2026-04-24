"""Stage 4 — Multimodal knowledge graph index.

Turns :class:`AnalyzedBlock` output into a Redis-backed graph of
``GraphEntity`` + ``GraphRelation`` records. The schema is intentionally
plain Redis data structures (JSON-encoded hashes + sorted sets) rather
than RedisGraph, so the graph works against fakeredis in tests and
against any Redis Stack install in production.

Key layout::

    amie:mmkg:ent:{entity_id}            -> JSON entity blob
    amie:mmkg:doc:{doc_id}:entities      -> set of entity_ids
    amie:mmkg:rel:{src}:{type}           -> zset of dst entity ids, score = weight
    amie:mmkg:inv:{dst}:{type}           -> zset of src entity ids, score = weight
    amie:mmkg:sec:{doc_id}               -> JSON section tree
"""
from __future__ import annotations

import json
from collections.abc import Iterable

from redis.asyncio import Redis

from app.core.logging import get_logger
from app.mmkg.router import SectionNode
from app.mmkg.schemas import AnalyzedBlock, GraphEntity, GraphRelation, Modality
from app.mmkg.weights import weight_for

log = get_logger(__name__)


_ENT_PREFIX = "amie:mmkg:ent:"
_DOC_ENTS = "amie:mmkg:doc:{doc_id}:entities"
_REL_OUT = "amie:mmkg:rel:{src}:{type}"
_REL_IN = "amie:mmkg:inv:{dst}:{type}"
_SEC_KEY = "amie:mmkg:sec:{doc_id}"


class MultiModalKnowledgeGraph:
    """Thin Redis-backed graph store.

    Operations are async-first and batched with a pipeline where possible
    so ingest of a single document is one round-trip per relation type.
    """

    def __init__(self, client: Redis) -> None:
        self._r = client

    # ----- writes -----------------------------------------------------

    async def upsert_entity(self, entity: GraphEntity) -> None:
        payload = entity.model_dump_json().encode("utf-8")
        pipe = self._r.pipeline(transaction=False)
        pipe.set(f"{_ENT_PREFIX}{entity.entity_id}", payload)
        pipe.sadd(_DOC_ENTS.format(doc_id=entity.doc_id), entity.entity_id)
        await pipe.execute()

    async def add_relation(self, rel: GraphRelation) -> None:
        # Stored in both directions so traversal works either way.
        pipe = self._r.pipeline(transaction=False)
        pipe.zadd(
            _REL_OUT.format(src=rel.src, type=rel.type),
            {rel.dst: rel.weight},
        )
        pipe.zadd(
            _REL_IN.format(dst=rel.dst, type=rel.type),
            {rel.src: rel.weight},
        )
        await pipe.execute()

    async def save_section_tree(self, doc_id: str, root: SectionNode) -> None:
        await self._r.set(_SEC_KEY.format(doc_id=doc_id), json.dumps(_node_to_dict(root)))

    # ----- reads ------------------------------------------------------

    async def get_entity(self, entity_id: str) -> GraphEntity | None:
        raw = await self._r.get(f"{_ENT_PREFIX}{entity_id}")
        if not raw:
            return None
        return GraphEntity.model_validate_json(raw)

    async def list_entities(self, doc_id: str) -> list[GraphEntity]:
        ids = await self._r.smembers(_DOC_ENTS.format(doc_id=doc_id))
        return [e for e in await self._mget_entities(_decode(ids)) if e is not None]

    async def neighbors(
        self, entity_id: str, rel_type: str, limit: int = 20
    ) -> list[tuple[str, float]]:
        key = _REL_OUT.format(src=entity_id, type=rel_type)
        pairs = await self._r.zrevrange(key, 0, limit - 1, withscores=True)
        return [(_decode_one(k), float(s)) for k, s in pairs]

    async def inbound(
        self, entity_id: str, rel_type: str, limit: int = 20
    ) -> list[tuple[str, float]]:
        key = _REL_IN.format(dst=entity_id, type=rel_type)
        pairs = await self._r.zrevrange(key, 0, limit - 1, withscores=True)
        return [(_decode_one(k), float(s)) for k, s in pairs]

    async def section_siblings(self, entity: GraphEntity) -> list[str]:
        """Entity ids that share the same section_path. Used by stage 5
        to reweight retrieval hits for relational coherence."""
        peers = await self.list_entities(entity.doc_id)
        path = entity.section_path
        return [
            p.entity_id
            for p in peers
            if p.entity_id != entity.entity_id and p.section_path == path
        ]

    async def _mget_entities(self, ids: Iterable[str]) -> list[GraphEntity | None]:
        id_list = list(ids)
        if not id_list:
            return []
        keys = [f"{_ENT_PREFIX}{i}" for i in id_list]
        raws = await self._r.mget(keys)
        return [
            GraphEntity.model_validate_json(r) if r else None for r in raws
        ]

    # ----- stage-4 ingest --------------------------------------------

    async def ingest(
        self,
        doc_id: str,
        analyzed: list[AnalyzedBlock],
        section_tree: SectionNode,
    ) -> list[GraphEntity]:
        """Convert analyzed blocks into entities, wire up relations."""
        entities: list[GraphEntity] = []
        entity_by_block: dict[str, GraphEntity] = {}
        section_entity: dict[tuple[str, ...], GraphEntity] = {}

        # First pass: one entity per analyzed block, plus one entity per
        # unique section so belongs_to chains have stable anchors.
        for ab in analyzed:
            path_key = tuple(ab.block.section_path)
            # Create / reuse section entity for this path.
            if path_key and path_key not in section_entity:
                section_title = path_key[-1]
                sec = GraphEntity(
                    doc_id=doc_id,
                    modality=Modality.HEADING,
                    label=section_title,
                    summary=f"Section: {' / '.join(path_key)}",
                    section_path=list(path_key[:-1]),
                )
                section_entity[path_key] = sec
                entities.append(sec)

            ent = GraphEntity(
                doc_id=doc_id,
                modality=ab.block.modality,
                label=_entity_label(ab),
                summary=ab.summary,
                section_path=list(ab.block.section_path),
                meta={"facts": ab.facts, "analyzer": ab.analyzer, **ab.block.meta},
                block_id=ab.block.block_id,
            )
            entity_by_block[ab.block.block_id] = ent
            entities.append(ent)

        for ent in entities:
            await self.upsert_entity(ent)

        # Second pass: hierarchical + co-occurrence + modality describes.
        for ab in analyzed:
            ent = entity_by_block[ab.block.block_id]
            path_key = tuple(ab.block.section_path)

            # belongs_to chain: block -> leaf section, leaf -> parent, ...
            if path_key:
                leaf = section_entity[path_key]
                await self.add_relation(
                    GraphRelation(
                        src=ent.entity_id,
                        dst=leaf.entity_id,
                        type="belongs_to",
                        weight=weight_for("belongs_to"),
                    )
                )
                for depth in range(len(path_key) - 1, 0, -1):
                    parent_key = path_key[:depth]
                    if parent_key not in section_entity:
                        parent = GraphEntity(
                            doc_id=doc_id,
                            modality=Modality.HEADING,
                            label=parent_key[-1],
                            summary=f"Section: {' / '.join(parent_key)}",
                            section_path=list(parent_key[:-1]),
                        )
                        section_entity[parent_key] = parent
                        await self.upsert_entity(parent)
                    child = section_entity[path_key[: depth + 1]]
                    parent = section_entity[parent_key]
                    await self.add_relation(
                        GraphRelation(
                            src=child.entity_id,
                            dst=parent.entity_id,
                            type="belongs_to",
                            weight=weight_for("belongs_to"),
                        )
                    )

            # Images "describe" their nearest preceding text, if any —
            # this captures the common caption-and-figure relationship.
            if ab.block.modality == Modality.IMAGE:
                caption_src = _nearest_text_before(ab.block.order, analyzed)
                if caption_src and caption_src.block.block_id in entity_by_block:
                    caption_ent = entity_by_block[caption_src.block.block_id]
                    await self.add_relation(
                        GraphRelation(
                            src=caption_ent.entity_id,
                            dst=ent.entity_id,
                            type="describes",
                            weight=weight_for("describes"),
                        )
                    )

        # Co-occurrence: pairwise between entities in the same section
        # (cheap; bounded by section fan-out).
        for path_key, _ in section_entity.items():
            peers = [
                entity_by_block[ab.block.block_id]
                for ab in analyzed
                if tuple(ab.block.section_path) == path_key
            ]
            for i in range(len(peers)):
                for j in range(i + 1, len(peers)):
                    await self.add_relation(
                        GraphRelation(
                            src=peers[i].entity_id,
                            dst=peers[j].entity_id,
                            type="co_occurs_with",
                            weight=weight_for("co_occurs_with"),
                        )
                    )

        await self.save_section_tree(doc_id, section_tree)
        log.info("mmkg_ingested", doc_id=doc_id, entities=len(entities))
        return entities


def _entity_label(ab: AnalyzedBlock) -> str:
    if ab.block.modality == Modality.HEADING:
        return ab.block.raw_content or ab.summary
    return (ab.summary or ab.block.raw_content)[:120]


def _nearest_text_before(
    order: int, analyzed: list[AnalyzedBlock]
) -> AnalyzedBlock | None:
    candidates = [
        a for a in analyzed if a.block.order < order and a.block.modality == Modality.TEXT
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda a: a.block.order)


def _node_to_dict(node: SectionNode) -> dict:
    return {
        "title": node.title,
        "path": list(node.path),
        "block_ids": node.block_ids,
        "children": [_node_to_dict(c) for c in node.children],
    }


def _decode(xs: Iterable[bytes | str]) -> list[str]:
    return [_decode_one(x) for x in xs]


def _decode_one(x: bytes | str) -> str:
    return x.decode("utf-8") if isinstance(x, (bytes, bytearray)) else str(x)
