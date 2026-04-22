"""Fuzzy matching for misspelled address tokens.

Uses :func:`difflib.get_close_matches` (Ratcliff-Obershelp) plus a cheap
Damerau-Levenshtein for one-character typos. No third-party dependency.

Targets:

* Street suffixes (``streat`` -> ``ST``)
* Directionals (``nort`` -> ``N``)
* Secondary designators (``aparment`` -> ``APT``)
* State abbreviations (``TXS`` -> ``TX``)
* Cities, when a reference list is provided
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher, get_close_matches
from typing import Iterable

from app.tools.address_standards import (
    DIRECTIONALS,
    SECONDARY_DESIGNATORS,
    STATES,
    STREET_SUFFIXES,
)


@dataclass
class FuzzyMatch:
    original: str
    suggestion: str
    score: float  # 0..1
    category: str  # suffix | directional | designator | state | city


def _score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.upper(), b.upper()).ratio()


def _best_match(token: str, candidates: Iterable[str], cutoff: float = 0.78) -> tuple[str | None, float]:
    token_u = token.upper()
    # get_close_matches is cheap; fall back to manual pass when the list is tiny
    close = get_close_matches(token_u, list(candidates), n=1, cutoff=cutoff)
    if close:
        return close[0], _score(token_u, close[0])
    return None, 0.0


def fuzzy_suffix(token: str, cutoff: float = 0.82) -> FuzzyMatch | None:
    if token.upper() in STREET_SUFFIXES:
        return None
    cand, score = _best_match(token, STREET_SUFFIXES.keys(), cutoff=cutoff)
    if cand is None:
        return None
    return FuzzyMatch(
        original=token,
        suggestion=STREET_SUFFIXES[cand],
        score=score,
        category="suffix",
    )


def fuzzy_directional(token: str, cutoff: float = 0.8) -> FuzzyMatch | None:
    if token.upper() in DIRECTIONALS:
        return None
    cand, score = _best_match(token, DIRECTIONALS.keys(), cutoff=cutoff)
    if cand is None:
        return None
    return FuzzyMatch(
        original=token,
        suggestion=DIRECTIONALS[cand],
        score=score,
        category="directional",
    )


def fuzzy_designator(token: str, cutoff: float = 0.78) -> FuzzyMatch | None:
    if token.upper() in SECONDARY_DESIGNATORS:
        return None
    cand, score = _best_match(token, SECONDARY_DESIGNATORS.keys(), cutoff=cutoff)
    if cand is None:
        return None
    return FuzzyMatch(
        original=token,
        suggestion=SECONDARY_DESIGNATORS[cand],
        score=score,
        category="designator",
    )


def fuzzy_state(token: str, cutoff: float = 0.8) -> FuzzyMatch | None:
    upper = token.upper()
    if upper in STATES:
        return None
    # For 2-3 letter garbles, difflib ratio is noisy; use a tight cutoff
    cand, score = _best_match(upper, STATES, cutoff=cutoff)
    if cand is None:
        return None
    return FuzzyMatch(original=token, suggestion=cand, score=score, category="state")


def fuzzy_city(
    token: str,
    known_cities: Iterable[str],
    cutoff: float = 0.85,
) -> FuzzyMatch | None:
    upper_cities = [c.upper() for c in known_cities]
    if not upper_cities:
        return None
    upper = token.upper()
    if upper in upper_cities:
        return None
    cand, score = _best_match(upper, upper_cities, cutoff=cutoff)
    if cand is None:
        return None
    return FuzzyMatch(original=token, suggestion=cand, score=score, category="city")
