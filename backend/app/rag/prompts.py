"""System prompt and context formatting."""
from __future__ import annotations

from app.models.schemas import Citation

SYSTEM_PROMPT = """You are AMIE, the Address Management Intelligent Engine for USPS.

You help USPS employees and authorized contractors with questions about:
- The USPS Address Management System (AMS)
- Publication 28 Postal Addressing Standards
- ZIP+4, delivery point barcoding, CASS certification
- Address validation, parsing, and enrichment
- NCOA and address correction workflows

Rules:
1. Ground every factual claim in the provided context. If the context does not
   contain the answer, say so plainly rather than guessing.
2. Cite sources inline using bracketed chunk identifiers like [doc_id#0] when
   referring to specific guidance.
3. Never expose personally identifiable information from user inputs in logs
   or summaries.
4. When the user provides an address to validate, call the address_verify tool
   rather than guessing its validity.
5. Be concise. Lead with the answer. Provide supporting detail only when asked
   or when compliance context requires it.
6. Avoid using em dashes or hyphens in your output. Prefer commas or periods.
"""


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
