#!/usr/bin/env bash
# Rebuild the Redis vector index from the knowledge base.
# Run inside the backend container:
#   kubectl exec -it deploy/amie-backend -- bash scripts/build-index.sh
#   docker compose exec backend bash scripts/build-index.sh

set -euo pipefail

python - <<'PY'
import asyncio

from app.core.config import get_settings
from app.core.redis_client import get_redis
from app.rag.indexer import RedisVectorIndex, build_from_knowledge_base


async def main() -> None:
    s = get_settings()
    r = get_redis()
    # Drop the existing index and keys
    try:
        await r.ft(s.redis_vector_index).dropindex(delete_documents=True)
    except Exception:
        pass
    idx = RedisVectorIndex(r, s.redis_vector_index, s.embedding_model, s.embedding_dim)
    count = await build_from_knowledge_base(idx, s.kb_path)
    print(f"Indexed {count} chunks into {s.redis_vector_index}")


asyncio.run(main())
PY
