"""Redis Stack vector indexer using RediSearch HNSW.

Index schema:
  HASH keys of the form amie:vec:{chunk_id} with fields:
    text (TEXT), doc_id (TAG), title (TEXT), url (TEXT), vector (VECTOR)

The index is created on boot if it does not exist, then populated from
JSON files in the knowledge base directory.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from redis.asyncio import Redis
from redis.commands.search.field import TagField, TextField, VectorField
try:  # redis-py >= 5.1 uses snake_case, older releases use camelCase
    from redis.commands.search.index_definition import IndexDefinition, IndexType
except ImportError:  # pragma: no cover - legacy fallback
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError
from sentence_transformers import SentenceTransformer

from app.core.logging import get_logger
from app.models.schemas import Citation
from app.rag.chunking import Chunk, chunk_text

log = get_logger(__name__)

_VEC_PREFIX = "amie:vec:"


class RedisVectorIndex:
    def __init__(self, client: Redis, index_name: str, embedding_model: str, dim: int) -> None:
        self._client = client
        self._index = index_name
        self._model_name = embedding_model
        self._dim = dim
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            log.info("loading_embedding_model", model=self._model_name)
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def _embed(self, texts: list[str]) -> np.ndarray:
        vecs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32)

    async def ensure_index(self) -> None:
        try:
            await self._client.ft(self._index).info()
            return
        except ResponseError:
            pass

        schema = (
            TextField("text"),
            TagField("doc_id"),
            TextField("title"),
            TextField("url"),
            VectorField(
                "vector",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self._dim,
                    "DISTANCE_METRIC": "COSINE",
                    "M": 16,
                    "EF_CONSTRUCTION": 200,
                },
            ),
        )
        definition = IndexDefinition(prefix=[_VEC_PREFIX], index_type=IndexType.HASH)
        await self._client.ft(self._index).create_index(fields=schema, definition=definition)
        log.info("vector_index_created", name=self._index, dim=self._dim)

    async def index_chunks(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        vectors = self._embed([c.text for c in chunks])
        pipe = self._client.pipeline(transaction=False)
        for c, vec in zip(chunks, vectors, strict=False):
            key = f"{_VEC_PREFIX}{c.chunk_id}"
            pipe.hset(
                key,
                mapping={
                    "text": c.text,
                    "doc_id": c.doc_id,
                    "title": c.title,
                    "url": c.url or "",
                    "vector": vec.tobytes(),
                },
            )
        await pipe.execute()
        log.info("chunks_indexed", count=len(chunks))
        return len(chunks)

    async def search(self, query: str, top_k: int = 5) -> list[Citation]:
        vec = self._embed([query])[0].tobytes()
        q = (
            Query(f"*=>[KNN {top_k} @vector $BLOB AS score]")
            .sort_by("score")
            .return_fields("text", "doc_id", "title", "url", "score")
            .paging(0, top_k)
            .dialect(2)
        )
        result = await self._client.ft(self._index).search(q, query_params={"BLOB": vec})

        citations: list[Citation] = []
        for doc in result.docs:
            chunk_id = doc.id.removeprefix(_VEC_PREFIX)
            # RediSearch returns COSINE distance (lower is closer). Convert to similarity.
            distance = float(getattr(doc, "score", 0.0))
            similarity = max(0.0, 1.0 - distance)
            text = (doc.text if isinstance(doc.text, str) else doc.text.decode("utf-8", errors="ignore")) if hasattr(doc, "text") else ""
            citations.append(
                Citation(
                    chunk_id=chunk_id,
                    doc_id=getattr(doc, "doc_id", "") or "",
                    title=getattr(doc, "title", "") or chunk_id,
                    snippet=text[:400],
                    score=similarity,
                    url=getattr(doc, "url", None) or None,
                )
            )
        return citations


async def build_from_knowledge_base(index: RedisVectorIndex, kb_dir: str) -> int:
    """Index every JSON and Markdown file under ``kb_dir``.

    JSON files are expected to hold a dict or list of dicts with ``id``,
    ``title``, ``url`` (optional), and ``text`` fields. Markdown files use
    YAML-lite frontmatter for the same metadata; the body of the file is
    the text to index. This mixed-source design lets editors add new
    documents by dropping a ``.md`` file into the directory.
    """
    from app.rag.content_loader import read_markdown

    kb = Path(kb_dir)
    if not kb.exists():
        raise FileNotFoundError(f"kb dir not found: {kb_dir}")
    all_chunks: list[Chunk] = []

    for file in sorted(kb.glob("**/*.json")):
        with open(file, encoding="utf-8") as f:
            docs = json.load(f)
        if isinstance(docs, dict):
            docs = [docs]
        for d in docs:
            doc_id = d.get("id") or file.stem
            title = d.get("title", doc_id)
            url = d.get("url")
            text = d.get("text", "")
            if not text:
                continue
            all_chunks.extend(chunk_text(text, doc_id=doc_id, title=title, url=url))

    for md_path in sorted(kb.glob("**/*.md")):
        doc = read_markdown(md_path)
        if not doc.body:
            continue
        all_chunks.extend(
            chunk_text(doc.body, doc_id=doc.id, title=doc.title, url=doc.url)
        )

    await index.ensure_index()
    return await index.index_chunks(all_chunks)
