"""Load user-supplied overrides for address standards from markdown.

The canonical tables live in :mod:`app.tools.address_standards`. This
module parses any markdown files under ``content/standards/`` that
contain a ``| variant | standard |`` table and merges the rows into the
in-memory dicts at module-import time.

This lets non-engineers add a spelling variant (for example a county
clerk's preferred abbreviation) without a code change.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.content_loader import load_markdown_dir
from app.tools.address_standards import (
    DIRECTIONALS,
    SECONDARY_DESIGNATORS,
    SECONDARY_DESIGNATORS_WITH_NUMBER,
    SECONDARY_DESIGNATORS_WITHOUT_NUMBER,
    STREET_SUFFIXES,
)

log = get_logger(__name__)

_TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")


def _parse_table(body: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in body.splitlines():
        m = _TABLE_ROW_RE.match(line.strip())
        if not m:
            continue
        left, right = m.group(1).strip(), m.group(2).strip()
        if not left or not right:
            continue
        # Skip header separators "| --- | --- |"
        if set(left) <= {"-", ":"} or set(right) <= {"-", ":"}:
            continue
        if left.lower() in {"variant", "from", "alias"}:
            continue
        rows.append((left.upper(), right.upper()))
    return rows


def apply_overrides() -> dict[str, int]:
    """Merge every override file into the standards dicts.

    Returns a count of rows applied per category for logging.
    """
    settings = get_settings()
    std_dir = Path(settings.content_dir) / "standards"
    # Fall back to the in-repo content directory for local dev
    if not std_dir.exists():
        alt = Path(__file__).resolve().parents[2] / "content" / "standards"
        if alt.exists():
            std_dir = alt

    counts: dict[str, int] = {
        "suffix": 0,
        "directional": 0,
        "secondary": 0,
    }
    for doc in load_markdown_dir(std_dir):
        meta_id = doc.meta.get("id", "").lower()
        rows = _parse_table(doc.body)
        if not rows:
            continue
        if "suffix" in meta_id:
            for variant, std in rows:
                STREET_SUFFIXES.setdefault(variant, std)
            counts["suffix"] += len(rows)
        elif "directional" in meta_id:
            for variant, std in rows:
                DIRECTIONALS.setdefault(variant, std)
            counts["directional"] += len(rows)
        elif "secondary" in meta_id:
            for variant, std in rows:
                SECONDARY_DESIGNATORS.setdefault(variant, std)
                SECONDARY_DESIGNATORS_WITH_NUMBER.setdefault(variant, std)
        else:
            log.debug("unknown_override_file", path=str(doc.path))
    if any(counts.values()):
        log.info("address_overrides_loaded", **counts)
    return counts
