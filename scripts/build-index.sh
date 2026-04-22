#!/usr/bin/env bash
# Rebuild the MongoDB vector collection from the knowledge base.
# Run inside the backend container:
#   kubectl exec -it deploy/amie-backend -- bash scripts/build-index.sh
#   docker compose exec backend bash scripts/build-index.sh

set -euo pipefail

python - <<'PY'
import asyncio

from app.core.config import get_settings
from app.core.mongo_client import get_mongo_db
from app.rag.indexer import MongoVectorIndex, build_from_knowledge_base


async def main() -> None:
    s = get_settings()
    db = get_mongo_db()
    # Drop existing chunks so we rebuild from a clean state.
    await db[s.mongo_vectors_collection].delete_many({})
    idx = MongoVectorIndex(
        db=db,
        collection_name=s.mongo_vectors_collection,
        embedding_model=s.embedding_model,
        dim=s.embedding_dim,
        use_atlas_vector_search=s.mongo_use_atlas_vector_search,
        atlas_index_name=s.mongo_atlas_vector_index_name,
    )
    count = await build_from_knowledge_base(idx, s.kb_path)
    print(f"Indexed {count} chunks into {s.mongo_database}.{s.mongo_vectors_collection}")


asyncio.run(main())
PY
