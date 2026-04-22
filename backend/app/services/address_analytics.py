"""MongoDB-backed analytics for address verification outcomes.

Writes one document per verification into a capped collection so the
collection self-trims to a bounded size. Rollups are computed via
aggregation on demand so they are always consistent with the event log.

Collection ``address_events`` (capped):

```
{
  "_id": "<uuid>",
  "occurred_at": ISODate,
  "input_address": "...",
  "noise_removed": [...],
  "verifier": "mock",
  "dpv_code": "Y",
  "confidence": 0.95,
  "address_type": "street",
  "warnings": [...],
  "suggestions_offered": 0,
  "top_suggestion_score": 0.0,
  "user_id": "dev-user",
  "verified": true
}
```

The collection is created on first use with capped size from settings.
Capped collections auto-evict the oldest documents; there is no TTL
management to worry about.
"""
from __future__ import annotations

from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.mongo_client import get_mongo_db
from app.models.schemas import (
    AddressAnalyticsEvent,
    AddressAnalyticsSummary,
    AddressVerifyResult,
)

log = get_logger(__name__)

_RECENT_LIMIT = 25


class AddressAnalytics:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        collection_name: str,
        capped_size_mb: int,
        capped_max_docs: int,
    ) -> None:
        self._db = db
        self._collection_name = collection_name
        self._capped_size_bytes = capped_size_mb * 1024 * 1024
        self._capped_max_docs = capped_max_docs
        self._collection: AsyncIOMotorCollection | None = None

    async def _ensure_collection(self) -> AsyncIOMotorCollection:
        if self._collection is not None:
            return self._collection
        names = await self._db.list_collection_names()
        if self._collection_name not in names:
            try:
                await self._db.create_collection(
                    self._collection_name,
                    capped=True,
                    size=self._capped_size_bytes,
                    max=self._capped_max_docs,
                )
            except Exception as e:
                # Mongo <4.2 / mongomock may refuse capped collections; fall
                # back to a regular collection so the feature still works.
                log.debug("capped_create_failed", error=str(e))
        coll = self._db[self._collection_name]
        try:
            await coll.create_index([("occurred_at", -1)], name="occurred_at_desc")
        except Exception:
            pass
        self._collection = coll
        return coll

    async def record(
        self, result: AddressVerifyResult, verifier: str, user_id: str
    ) -> None:
        event = AddressAnalyticsEvent(
            input_address=result.input_address,
            noise_removed=result.noise_removed,
            verifier=verifier,
            dpv_code=result.dpv_code,
            confidence=result.confidence,
            address_type=result.address_type,
            warnings=result.warnings,
            suggestions_offered=len(result.suggestions),
            top_suggestion_score=(
                max((s.confidence for s in result.suggestions), default=0.0)
            ),
            user_id=user_id,
        )
        doc = event.model_dump(mode="python")
        doc["_id"] = doc.pop("id")
        doc["verified"] = result.verified
        try:
            coll = await self._ensure_collection()
            await coll.insert_one(doc)
        except Exception as e:
            log.warning("address_analytics_record_failed", error=str(e))

    async def summary(self) -> AddressAnalyticsSummary:
        try:
            coll = await self._ensure_collection()

            totals_pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": 1},
                        "verified": {
                            "$sum": {"$cond": [{"$eq": ["$verified", True]}, 1, 0]}
                        },
                        "sum_confidence": {"$sum": "$confidence"},
                    }
                }
            ]
            totals = {"total": 0, "verified": 0, "sum_confidence": 0.0}
            async for doc in coll.aggregate(totals_pipeline):
                totals = {
                    "total": int(doc.get("total", 0)),
                    "verified": int(doc.get("verified", 0)),
                    "sum_confidence": float(doc.get("sum_confidence", 0.0)),
                }

            async def _group_count(field: str) -> dict[str, int]:
                out: dict[str, int] = {}
                async for doc in coll.aggregate(
                    [{"$group": {"_id": f"${field}", "count": {"$sum": 1}}}]
                ):
                    key = doc.get("_id")
                    if key is None:
                        continue
                    out[str(key)] = int(doc["count"])
                return out

            by_dpv = await _group_count("dpv_code")
            by_type = await _group_count("address_type")

            # Warnings are an array field; $unwind then group.
            warn_pipeline = [
                {"$unwind": "$warnings"},
                {"$group": {"_id": "$warnings", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10},
            ]
            top_warnings: list[dict] = []
            async for doc in coll.aggregate(warn_pipeline):
                top_warnings.append(
                    {"warning": str(doc["_id"]), "count": int(doc["count"])}
                )

            recent: list[AddressAnalyticsEvent] = []
            async for doc in (
                coll.find().sort("occurred_at", -1).limit(_RECENT_LIMIT)
            ):
                data = dict(doc)
                data["id"] = data.pop("_id")
                data.pop("verified", None)
                try:
                    recent.append(AddressAnalyticsEvent.model_validate(data))
                except Exception:
                    continue

            total = totals["total"]
            return AddressAnalyticsSummary(
                total=total,
                verified=totals["verified"],
                verified_rate=(totals["verified"] / total) if total else 0.0,
                average_confidence=(
                    totals["sum_confidence"] / total if total else 0.0
                ),
                by_dpv_code=by_dpv,
                by_address_type=by_type,
                top_warnings=top_warnings,  # type: ignore[arg-type]
                recent=recent,
            )
        except Exception as e:
            log.warning("address_analytics_summary_failed", error=str(e))
            return AddressAnalyticsSummary(
                total=0,
                verified=0,
                verified_rate=0.0,
                average_confidence=0.0,
                by_dpv_code={},
                by_address_type={},
                top_warnings=[],
                recent=[],
            )


@lru_cache
def get_analytics() -> AddressAnalytics:
    s = get_settings()
    return AddressAnalytics(
        db=get_mongo_db(),
        collection_name=s.mongo_address_events_collection,
        capped_size_mb=s.mongo_address_events_capped_size_mb,
        capped_max_docs=s.mongo_address_events_capped_max_docs,
    )
