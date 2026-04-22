"""MongoDB vector indexer.

Supports two retrieval backends:

1. **In-process cosine similarity** (default). Loads all document
   vectors from the ``vectors`` collection once per query, computes
   cosine similarity with numpy, returns the top K. Fast and
   predictable for knowledge bases up to roughly 50k chunks; requires
   no special MongoDB feature.
2. **Atlas Vector Search** (when ``mongo_use_atlas_vector_search`` is
   True). Runs an aggregation pipeline with ``$vectorSearch``. Requires
   an Atlas cluster with a configured vector search index; the index
   name is taken from ``mongo_atlas_vector_index_name``.

Schema (collection ``vectors``):

```
{
  "_id": "<chunk_id>",
  "doc_id": "pub28-sec-21",
  "title": "...",
  "url": "...",
  "text": "...",
  "vector": [0.1, 0.2, ...]
}
```
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from sentence_transformers import SentenceTransformer

from app.core.logging import get_logger
from app.models.schemas import Citation
from app.rag.chunking import Chunk, chunk_text

log = get_logger(__name__)


class MongoVectorIndex:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        collection_name: str,
        embedding_model: str,
        dim: int,
        use_atlas_vector_search: bool = False,
        atlas_index_name: str = "vector_index",
    ) -> None:
        self._collection: AsyncIOMotorCollection = db[collection_name]
        self._model_name = embedding_model
        self._dim = dim
        self._model: SentenceTransformer | None = None
        self._use_atlas = use_atlas_vector_search
        self._atlas_index_name = atlas_index_name
        self._index_ensured = False

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            log.info("loading_embedding_model", model=self._model_name)
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def _embed(self, texts: list[str]) -> np.ndarray:
        vecs = self.model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return np.asarray(vecs, dtype=np.float32)

    async def ensure_index(self) -> None:
        if self._index_ensured:
            return
        try:
            await self._collection.create_index([("doc_id", 1)], name="doc_id_idx")
        except Exception as e:
            log.debug("vector_index_create_failed", error=str(e))
        self._index_ensured = True

    async def count(self) -> int:
        try:
            return await self._collection.count_documents({})
        except Exception:
            return 0

    async def index_chunks(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        vectors = self._embed([c.text for c in chunks])
        ops = []
        for c, vec in zip(chunks, vectors, strict=False):
            ops.append(
                {
                    "_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "title": c.title,
                    "url": c.url or "",
                    "text": c.text,
                    "vector": vec.tolist(),
                }
            )
        # Upsert one by one to preserve idempotence under re-index calls.
        for doc in ops:
            await self._collection.replace_one(
                {"_id": doc["_id"]}, doc, upsert=True
            )
        log.info("chunks_indexed", count=len(ops))
        return len(ops)

    async def search(self, query: str, top_k: int = 5) -> list[Citation]:
        query_vec = self._embed([query])[0]
        if self._use_atlas:
            return await self._search_atlas(query_vec.tolist(), top_k)
        return await self._search_in_process(query_vec, top_k)

    async def _search_atlas(
        self, query_vec: list[float], top_k: int
    ) -> list[Citation]:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self._atlas_index_name,
                    "path": "vector",
                    "queryVector": query_vec,
                    "numCandidates": max(top_k * 10, 50),
                    "limit": top_k,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "doc_id": 1,
                    "title": 1,
                    "url": 1,
                    "text": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        citations: list[Citation] = []
        async for doc in self._collection.aggregate(pipeline):
            citations.append(
                Citation(
                    chunk_id=doc["_id"],
                    doc_id=doc.get("doc_id", ""),
                    title=doc.get("title") or doc["_id"],
                    snippet=(doc.get("text") or "")[:400],
                    score=float(doc.get("score", 0.0)),
                    url=doc.get("url") or None,
                )
            )
        return citations

    async def _search_in_process(
        self, query_vec: np.ndarray, top_k: int
    ) -> list[Citation]:
        ids: list[str] = []
        doc_ids: list[str] = []
        titles: list[str] = []
        urls: list[str] = []
        snippets: list[str] = []
        vectors: list[list[float]] = []

        cursor = self._collection.find(
            {}, projection={"doc_id": 1, "title": 1, "url": 1, "text": 1, "vector": 1}
        )
        async for doc in cursor:
            vec = doc.get("vector")
            if not vec:
                continue
            ids.append(doc["_id"])
            doc_ids.append(doc.get("doc_id", ""))
            titles.append(doc.get("title") or doc["_id"])
            urls.append(doc.get("url") or "")
            snippets.append((doc.get("text") or "")[:400])
            vectors.append(vec)

        if not vectors:
            return []

        matrix = np.asarray(vectors, dtype=np.float32)
        # Query and stored vectors are already L2-normalized.
        scores = matrix @ query_vec.astype(np.float32)
        k = min(top_k, len(scores))
        # Partial sort: top-k by descending score.
        top_idx = np.argpartition(-scores, kth=k - 1)[:k]
        top_idx = top_idx[np.argsort(-scores[top_idx])]
        citations: list[Citation] = []
        for i in top_idx:
            citations.append(
                Citation(
                    chunk_id=ids[i],
                    doc_id=doc_ids[i],
                    title=titles[i],
                    snippet=snippets[i],
                    score=float(scores[i]),
                    url=urls[i] or None,
                )
            )
        return citations


async def build_from_knowledge_base(index: MongoVectorIndex, kb_dir: str) -> int:
    """Index every JSON and Markdown file under ``kb_dir``."""
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
