"""Suggestion engine for noisy or incorrect addresses.

Given a raw user input, produce up to N candidate standardized addresses
along with a confidence score and human-readable reasons. Called after
the primary verifier runs and returns a low-confidence result, so the
chat view can offer "did you mean" options.

Strategy:

1. Run noise cancellation. Each removed category becomes a reason.
2. Re-parse the cleaned string.
3. Tokenize the primary line; for each unknown suffix, directional, or
   secondary designator, try a fuzzy correction.
4. State abbreviations are corrected against :data:`STATES`.
5. Cities, when a KB is available, are corrected to the closest known
   city for the detected state.
6. Each accepted correction bumps the candidate confidence by its
   match score weighted by a category factor.
7. The engine emits at most ``max_suggestions`` candidates, sorted by
   confidence, and never returns a candidate identical to the input.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.models.schemas import AddressSuggestion
from app.tools.address_fuzzy import (
    FuzzyMatch,
    fuzzy_city,
    fuzzy_designator,
    fuzzy_directional,
    fuzzy_state,
    fuzzy_suffix,
)
from app.tools.address_noise import cancel_noise
from app.tools.address_parser import parse_address

# Weighting for how much each category boosts the candidate confidence.
_CATEGORY_WEIGHT: dict[str, float] = {
    "suffix": 0.20,
    "directional": 0.10,
    "designator": 0.15,
    "state": 0.30,
    "city": 0.15,
    "noise": 0.10,
}


@dataclass
class _Candidate:
    line: str
    confidence: float
    reasons: list[str]
    replacements: list[dict[str, str]]
    address_type: str


def _apply_token_correction(
    tokens: list[str],
    idx: int,
    correction: FuzzyMatch,
    replacements: list[dict[str, str]],
    reasons: list[str],
) -> None:
    tokens[idx] = correction.suggestion
    replacements.append(
        {
            "from": correction.original.upper(),
            "to": correction.suggestion,
            "category": correction.category,
            "score": f"{correction.score:.2f}",
        }
    )
    reasons.append(
        f"corrected {correction.category} '{correction.original}' -> '{correction.suggestion}'"
    )


def _correct_street_tokens(
    line: str,
    reasons: list[str],
    replacements: list[dict[str, str]],
) -> tuple[str, float]:
    tokens = line.split()
    boost = 0.0
    if not tokens:
        return line, boost

    # Suffix is typically the last non-secondary token; try that slot first
    last_idx = len(tokens) - 1
    suffix_match = fuzzy_suffix(tokens[last_idx])
    if suffix_match and suffix_match.score > 0.82:
        _apply_token_correction(tokens, last_idx, suffix_match, replacements, reasons)
        boost += _CATEGORY_WEIGHT["suffix"] * suffix_match.score

    # Scan the middle tokens for directional / designator typos
    for i in range(1, len(tokens) - 1):
        # Skip if already a clean token
        dir_match = fuzzy_directional(tokens[i])
        if dir_match and dir_match.score > 0.82:
            _apply_token_correction(tokens, i, dir_match, replacements, reasons)
            boost += _CATEGORY_WEIGHT["directional"] * dir_match.score
            continue
        des_match = fuzzy_designator(tokens[i])
        if des_match and des_match.score > 0.82:
            _apply_token_correction(tokens, i, des_match, replacements, reasons)
            boost += _CATEGORY_WEIGHT["designator"] * des_match.score
    return " ".join(tokens), boost


def _correct_state_and_city(
    parsed_state: str | None,
    parsed_city: str | None,
    known_cities: Iterable[str] | None,
    reasons: list[str],
    replacements: list[dict[str, str]],
) -> tuple[str | None, str | None, float]:
    boost = 0.0
    state = parsed_state
    city = parsed_city

    if state is None and parsed_state is not None:
        # nothing to do
        pass
    elif state and len(state) == 2:
        m = fuzzy_state(state)
        if m and m.score > 0.8:
            replacements.append(
                {"from": state, "to": m.suggestion, "category": "state", "score": f"{m.score:.2f}"}
            )
            reasons.append(f"corrected state '{state}' -> '{m.suggestion}'")
            state = m.suggestion
            boost += _CATEGORY_WEIGHT["state"] * m.score

    if city and known_cities:
        m = fuzzy_city(city, known_cities)
        if m and m.score > 0.85:
            replacements.append(
                {"from": city, "to": m.suggestion, "category": "city", "score": f"{m.score:.2f}"}
            )
            reasons.append(f"corrected city '{city}' -> '{m.suggestion}'")
            city = m.suggestion
            boost += _CATEGORY_WEIGHT["city"] * m.score

    return state, city, boost


def suggest_corrections(
    raw: str,
    base_confidence: float = 0.3,
    max_suggestions: int = 3,
    known_cities: Iterable[str] | None = None,
) -> tuple[list[AddressSuggestion], list[str]]:
    """Produce suggestions for an address that failed to verify cleanly.

    Returns a tuple of ``(suggestions, noise_removed)``. ``noise_removed``
    lists the noise categories that were stripped from the input prior
    to suggestion generation.
    """
    cleaned, noise = cancel_noise(raw)
    candidates: list[_Candidate] = []

    # Candidate 1: the cleaned input as-is
    parsed = parse_address(cleaned)
    reasons: list[str] = []
    replacements: list[dict[str, str]] = []
    if noise:
        reasons.append(f"removed noise: {', '.join(noise)}")

    primary = parsed.primary_line or cleaned
    corrected_primary, primary_boost = _correct_street_tokens(
        primary, reasons, replacements
    )

    state, city, ls_boost = _correct_state_and_city(
        parsed.state, parsed.city, known_cities, reasons, replacements
    )

    # Re-parse using the corrected pieces joined back together. This is
    # needed so the final ``standardized`` output uses the canonical form.
    stitched_parts: list[str] = []
    if parsed.firm:
        stitched_parts.append(parsed.firm)
    if parsed.urbanization:
        stitched_parts.append(f"URB {parsed.urbanization}")
    stitched_parts.append(corrected_primary)
    if parsed.secondary_line and parsed.secondary_line not in corrected_primary:
        stitched_parts[-1] = f"{stitched_parts[-1]} {parsed.secondary_line}"
    last = None
    if city and state and parsed.zip5:
        z4 = f"-{parsed.zip4}" if parsed.zip4 else ""
        last = f"{city}, {state} {parsed.zip5}{z4}"
    elif city and state:
        last = f"{city}, {state}"
    if last:
        stitched_parts.append(last)

    rebuilt = ", ".join(stitched_parts)
    reparsed = parse_address(rebuilt)

    confidence = min(
        0.99,
        base_confidence
        + primary_boost
        + ls_boost
        + (_CATEGORY_WEIGHT["noise"] * 0.5 if noise else 0.0),
    )

    if reparsed.standardized():
        candidates.append(
            _Candidate(
                line=reparsed.standardized() or rebuilt,
                confidence=confidence,
                reasons=reasons,
                replacements=replacements,
                address_type=reparsed.address_type,
            )
        )

    # De-duplicate and rank. Compare against the standardized parse of the
    # raw input so we don't suppress valid "did you mean" variants when the
    # only difference is noise removal or whitespace.
    raw_parsed = parse_address(raw)
    raw_std = (raw_parsed.standardized() or raw).strip().upper()

    seen: set[str] = set()
    out: list[AddressSuggestion] = []
    for c in sorted(candidates, key=lambda x: x.confidence, reverse=True):
        key = " ".join(c.line.upper().split())
        if key in seen:
            continue
        if key == " ".join(raw_std.split()) and not c.reasons:
            continue
        seen.add(key)
        out.append(
            AddressSuggestion(
                standardized=c.line,
                confidence=round(c.confidence, 3),
                reasons=c.reasons,
                replaced_tokens=c.replacements,
                address_type=c.address_type,
            )
        )
        if len(out) >= max_suggestions:
            break
    return out, noise
