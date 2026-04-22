"""System prompt and context formatting.

The system prompt is loaded from ``backend/content/prompts/system.md``
when available, so non-engineers can tune wording without touching
Python. If the file is missing, a safe embedded default is used.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.models.schemas import Citation
from app.rag.content_loader import load_prompt

_DEFAULT_SYSTEM_PROMPT = """You are AMIE, the Address Management Intelligent Engine for USPS.

You help USPS employees and authorized contractors with questions about
USPS Address Management, Publication 28 standards, CASS, DPV, and address
verification workflows.

Ground every factual claim in the provided context. If the context does not
contain the answer, say so plainly rather than guessing. Cite sources inline
using bracketed chunk identifiers like [doc_id#0]. Never expose personally
identifiable information from user inputs. When the user provides an address
to validate, call the address_verify tool. When an <address_verification>
block is present with confidence below 0.85, offer the top suggestion and
ask the user to confirm, edit, or reject. Be concise.
"""


def _content_dir() -> Path:
    settings = get_settings()
    explicit = getattr(settings, "content_dir", None)
    if explicit:
        return Path(explicit)
    # Default: <backend_root>/content
    return Path(__file__).resolve().parents[2] / "content"


@lru_cache
def _load_system_prompt() -> str:
    return load_prompt(_content_dir() / "prompts", "system", _DEFAULT_SYSTEM_PROMPT)


# Exposed as both a module-level constant (for backwards compatibility)
# and via :func:`get_system_prompt` for tests that swap implementations.
SYSTEM_PROMPT = _load_system_prompt()


def get_system_prompt() -> str:
    return _load_system_prompt()


def format_context(citations: list[Citation]) -> str:
    if not citations:
        return "No relevant context was retrieved."
    blocks = []
    for c in citations:
        blocks.append(
            f"[{c.chunk_id}] Title: {c.title}\n"
            f"Source: {c.url or c.doc_id}\n"
            f"Content: {c.snippet}"
        )
    return "\n\n".join(blocks)


def build_user_turn_with_context(user_message: str, citations: list[Citation]) -> str:
    context = format_context(citations)
    return (
        "Use the following retrieved context to answer the user. Cite chunks "
        "by their identifier.\n\n"
        f"<context>\n{context}\n</context>\n\n"
        f"<user_message>\n{user_message}\n</user_message>"
    )
