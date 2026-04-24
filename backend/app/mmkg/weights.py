"""Relationship weights for stage-4 scoring.

Tuning these numbers is an operator concern, not an engineering one, so
they live as a plain dict here instead of being hard-coded in
:mod:`app.mmkg.graph`. Higher weights mean the relationship is more
relevant to answer-quality during retrieval.
"""
from __future__ import annotations


RELATION_WEIGHTS: dict[str, float] = {
    # Hierarchical chain from child block to containing section.
    "belongs_to": 0.4,
    # Explicit citation or pointer between entities.
    "references": 0.7,
    # Caption / alt-text describes an image entity.
    "describes": 0.8,
    # Equation derived from another equation or text.
    "derives_from": 0.6,
    # Two entities surfaced from the same section.
    "co_occurs_with": 0.3,
    # Computation or data flow dependency.
    "depends_on": 0.5,
}


def weight_for(rel_type: str) -> float:
    return RELATION_WEIGHTS.get(rel_type, 0.3)
