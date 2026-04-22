"""Redis-backed analytics for address verification outcomes.

Records each verification attempt into a bounded Redis stream and
computes rollups for dashboarding. Degrades silently when Redis is not
reachable so the verification path itself stays resilient.

Keys:
  ``amie:addr:events``              stream of JSON-encoded events (capped)
  ``amie:addr:counters:dpv:{code}`` int counter of verifications per DPV
  ``amie:addr:counters:type:{t}``   int counter per address type
  ``amie:addr:counters:warn:{w}``   int counter per warning category
  ``amie:addr:totals``              hash with total, verified, sum_confidence
"""
from __future__ import annotations

from functools import lru_cache

from app.core.logging import get_logger
from app.core.redis_client import get_redis
from app.models.schemas import (
    AddressAnalyticsEvent,
    AddressAnalyticsSummary,
    AddressVerifyResult,
)

log = get_logger(__name__)

_STREAM_KEY = "amie:addr:events"
_COUNTER_DPV = "amie:addr:counters:dpv:"
_COUNTER_TYPE = "amie:addr:counters:type:"
_COUNTER_WARN = "amie:addr:counters:warn:"
_TOTALS = "amie:addr:totals"

_STREAM_MAX_LEN = 50_000
_RECENT_LIMIT = 25


class AddressAnalytics:
    def __init__(self, client=None) -> None:
        self._client = client or get_redis()

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
        try:
            pipe = self._client.pipeline(transaction=False)
            pipe.xadd(
                _STREAM_KEY,
                {"json": event.model_dump_json()},
                maxlen=_STREAM_MAX_LEN,
                approximate=True,
            )
            pipe.hincrby(_TOTALS, "total", 1)
            if result.verified:
                pipe.hincrby(_TOTALS, "verified", 1)
            pipe.hincrbyfloat(_TOTALS, "sum_confidence", float(result.confidence))
            if result.dpv_code:
                pipe.incr(f"{_COUNTER_DPV}{result.dpv_code}")
            pipe.incr(f"{_COUNTER_TYPE}{result.address_type}")
            for w in result.warnings:
                pipe.incr(f"{_COUNTER_WARN}{w}")
            await pipe.execute()
        except Exception as e:
            log.warning("address_analytics_record_failed", error=str(e))

    async def summary(self) -> AddressAnalyticsSummary:
        try:
            totals_raw = await self._client.hgetall(_TOTALS)

            def _decode_key(k):
                return k.decode() if isinstance(k, bytes) else k

            def _decode_val(v):
                return v.decode() if isinstance(v, bytes) else v

            totals = {_decode_key(k): _decode_val(v) for k, v in totals_raw.items()}
            total = int(totals.get("total", 0))
            verified = int(totals.get("verified", 0))
            sum_conf = float(totals.get("sum_confidence", 0.0))

            dpv_keys = []
            async for k in self._client.scan_iter(match=f"{_COUNTER_DPV}*"):
                dpv_keys.append(k)
            type_keys = []
            async for k in self._client.scan_iter(match=f"{_COUNTER_TYPE}*"):
                type_keys.append(k)
            warn_keys = []
            async for k in self._client.scan_iter(match=f"{_COUNTER_WARN}*"):
                warn_keys.append(k)

            async def _to_map(keys, prefix):
                out: dict[str, int] = {}
                for key in keys:
                    val = await self._client.get(key)
                    if val is None:
                        continue
                    name = _decode_key(key)[len(prefix):]
                    try:
                        out[name] = int(val)
                    except (TypeError, ValueError):
                        continue
                return out

            by_dpv = await _to_map(dpv_keys, _COUNTER_DPV)
            by_type = await _to_map(type_keys, _COUNTER_TYPE)
            by_warn = await _to_map(warn_keys, _COUNTER_WARN)

            top_warnings = [
                {"warning": name, "count": count}
                for name, count in sorted(
                    by_warn.items(), key=lambda x: x[1], reverse=True
                )[:10]
            ]

            # Pull the most recent events from the stream
            recent: list[AddressAnalyticsEvent] = []
            try:
                entries = await self._client.xrevrange(
                    _STREAM_KEY, count=_RECENT_LIMIT
                )
                for _entry_id, fields in entries:
                    raw = fields.get(b"json") if isinstance(next(iter(fields), b""), bytes) else fields.get("json")
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    if raw:
                        recent.append(AddressAnalyticsEvent.model_validate_json(raw))
            except Exception as e:
                log.debug("analytics_recent_unavailable", error=str(e))

            return AddressAnalyticsSummary(
                total=total,
                verified=verified,
                verified_rate=(verified / total) if total else 0.0,
                average_confidence=(sum_conf / total) if total else 0.0,
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
    return AddressAnalytics()
