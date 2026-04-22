"""Publication 28 compliant address parser.

Splits a free-form address string into USPS-standardized components:

* Primary number, predirectional, street name, suffix, postdirectional
* Secondary unit designator and number (APT, STE, FL, BSMT, etc.)
* Firm (company) name when present as a separate line
* City, state, ZIP5, ZIP4
* Urbanization (URB) line for Puerto Rico addresses
* Address type: street, PO Box, rural route, highway contract, military,
  general delivery, unknown

Input can be comma-delimited, newline-delimited, or a mix. The parser is
defensive: each stage catches its own failure and degrades gracefully so
an unparsable blob still yields a useful structured result.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.tools.address_standards import (
    DIRECTIONALS,
    GENERAL_DELIVERY,
    HIGHWAY_CONTRACT_PREFIXES,
    MILITARY_LAST_LINE_CODES,
    MILITARY_STATES,
    PO_BOX_PATTERNS,
    RURAL_ROUTE_PREFIXES,
    SECONDARY_DESIGNATORS,
    SECONDARY_DESIGNATORS_WITH_NUMBER,
    SECONDARY_DESIGNATORS_WITHOUT_NUMBER,
    STATES,
    STREET_SUFFIXES,
    URBANIZATION_PREFIXES,
)


@dataclass
class ParsedAddress:
    raw: str
    firm: str | None = None
    urbanization: str | None = None
    primary_number: str | None = None
    predirectional: str | None = None
    street_name: str | None = None
    street_suffix: str | None = None
    postdirectional: str | None = None
    secondary_designator: str | None = None
    secondary_number: str | None = None
    city: str | None = None
    state: str | None = None
    zip5: str | None = None
    zip4: str | None = None
    address_type: str = "unknown"
    warnings: list[str] = field(default_factory=list)

    @property
    def primary_line(self) -> str | None:
        """Return the standardized delivery address line (primary only)."""
        if self.address_type == "po_box" and self.primary_number:
            return f"PO BOX {self.primary_number}"
        if self.address_type == "rural_route" and self.primary_number:
            box = f" BOX {self.secondary_number}" if self.secondary_number else ""
            return f"RR {self.primary_number}{box}"
        if self.address_type == "highway_contract" and self.primary_number:
            box = f" BOX {self.secondary_number}" if self.secondary_number else ""
            return f"HC {self.primary_number}{box}"
        if self.address_type == "general_delivery":
            return GENERAL_DELIVERY
        parts = [
            self.primary_number,
            self.predirectional,
            self.street_name,
            self.street_suffix,
            self.postdirectional,
        ]
        out = " ".join(p for p in parts if p)
        return out or None

    @property
    def secondary_line(self) -> str | None:
        if not self.secondary_designator:
            return None
        if self.secondary_number:
            return f"{self.secondary_designator} {self.secondary_number}"
        return self.secondary_designator

    @property
    def last_line(self) -> str | None:
        if not (self.city and self.state and self.zip5):
            return None
        z4 = f"-{self.zip4}" if self.zip4 else ""
        return f"{self.city}, {self.state} {self.zip5}{z4}"

    def standardized(self) -> str | None:
        primary = self.primary_line
        last = self.last_line
        if not (primary and last):
            return None
        lines: list[str] = []
        if self.firm:
            lines.append(self.firm)
        if self.urbanization:
            lines.append(f"URB {self.urbanization}")
        first = primary
        if self.secondary_line:
            first = f"{primary} {self.secondary_line}"
        lines.append(first)
        lines.append(last)
        return "\n".join(lines)


_ZIP_RE = re.compile(r"\b(\d{5})(?:[\s-](\d{4}))?\b")
_STATE_RE = re.compile(r"\b([A-Z]{2})\b")
_PO_BOX_RE = re.compile(
    r"^(?:P\.?\s*O\.?\s*BOX|POST\s*OFFICE\s*BOX|BOX)\s*#?\s*([A-Z0-9-]+)",
    re.IGNORECASE,
)
_RR_RE = re.compile(
    r"^(?:RR|R\.\s*R\.|RURAL\s*ROUTE)\s*#?\s*(\d+)(?:\s+BOX\s*#?\s*([A-Z0-9-]+))?",
    re.IGNORECASE,
)
_HC_RE = re.compile(
    r"^(?:HC|HIGHWAY\s*CONTRACT)\s*#?\s*(\d+)(?:\s+BOX\s*#?\s*([A-Z0-9-]+))?",
    re.IGNORECASE,
)
_URB_RE = re.compile(
    r"^\s*(?:URB\.?|URBANIZACION)\s+(.+?)\s*$",
    re.IGNORECASE,
)
_PRIMARY_NUMBER_RE = re.compile(r"^(\d+(?:[-/]\d+)?[A-Z]?|\d+\s*[A-Z]?)\b")


def _normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _tokenize_lines(address: str) -> list[str]:
    """Split on newlines or commas into normalized lines."""
    raw = address.replace("\r", "\n")
    pieces: list[str] = []
    for chunk in raw.split("\n"):
        for sub in chunk.split(","):
            t = _normalize_whitespace(sub)
            if t:
                pieces.append(t)
    return pieces


def _extract_zip(tokens: list[str]) -> tuple[str | None, str | None, list[str]]:
    """Pull a ZIP or ZIP+4 out of the trailing tokens."""
    if not tokens:
        return None, None, tokens
    combined = " ".join(tokens)
    match = None
    for m in _ZIP_RE.finditer(combined):
        match = m
    if not match:
        return None, None, tokens
    zip5, zip4 = match.group(1), match.group(2)
    # Remove the matched text from the tail token(s)
    head = combined[: match.start()].rstrip()
    new_tokens = head.split(" ") if head else []
    new_tokens = [t for t in new_tokens if t]
    return zip5, zip4, new_tokens


def _extract_state(tokens: list[str]) -> tuple[str | None, list[str]]:
    if not tokens:
        return None, tokens
    last = tokens[-1].upper()
    if last in STATES:
        return last, tokens[:-1]
    return None, tokens


def _extract_urbanization(tokens: list[str]) -> tuple[str | None, list[str]]:
    for i, line in enumerate(tokens):
        parts = line.split(None, 1)
        if parts and parts[0].upper().rstrip(".") in {
            p.rstrip(".") for p in URBANIZATION_PREFIXES
        }:
            urb = parts[1] if len(parts) > 1 else ""
            return urb.upper() or None, tokens[:i] + tokens[i + 1 :]
    return None, tokens


def _is_street_line(line: str) -> bool:
    return bool(_PRIMARY_NUMBER_RE.match(line))


def _standardize_suffix(token: str) -> str | None:
    return STREET_SUFFIXES.get(token.upper().rstrip("."))


def _standardize_directional(token: str) -> str | None:
    return DIRECTIONALS.get(token.upper().rstrip("."))


def _is_secondary_token(token: str) -> bool:
    t = token.upper().rstrip(".#")
    return t in SECONDARY_DESIGNATORS or t.startswith("#")


def _split_street_and_secondary(
    tokens: list[str],
) -> tuple[list[str], str | None, str | None]:
    """Return (street_tokens, secondary_designator, secondary_number).

    Walks tokens left-to-right, stops at the first recognized secondary
    designator. If a token is a bare ``#`` it is treated as ``UNIT``.
    """
    for i, tok in enumerate(tokens):
        up = tok.upper().rstrip(".")
        if up.startswith("#") and up != "#":
            number = up.lstrip("#")
            return tokens[:i], "UNIT", number or None
        if up == "#":
            number = tokens[i + 1] if i + 1 < len(tokens) else None
            return tokens[:i], "UNIT", number
        if up in SECONDARY_DESIGNATORS_WITH_NUMBER:
            std = SECONDARY_DESIGNATORS_WITH_NUMBER[up]
            number = tokens[i + 1] if i + 1 < len(tokens) else None
            if number and number.startswith("#"):
                number = number.lstrip("#")
            return tokens[:i], std, number
        if up in SECONDARY_DESIGNATORS_WITHOUT_NUMBER:
            std = SECONDARY_DESIGNATORS_WITHOUT_NUMBER[up]
            return tokens[:i], std, None
    return tokens, None, None


def _parse_street_tokens(
    tokens: list[str],
) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """Parse street tokens into (primary_number, pre_dir, name, suffix, post_dir)."""
    if not tokens:
        return None, None, None, None, None

    # Primary number
    primary: str | None = None
    m = _PRIMARY_NUMBER_RE.match(tokens[0])
    if m:
        primary = m.group(1).replace(" ", "")
        remainder = tokens[0][m.end():].strip()
        tokens = ([remainder] if remainder else []) + tokens[1:]

    # Tentatively peel predirectional, postdirectional, suffix.
    pre_dir: str | None = None
    post_dir: str | None = None
    suffix: str | None = None

    working = list(tokens)

    if len(working) >= 2:
        d = _standardize_directional(working[0])
        if d and not _standardize_directional(working[1]):
            pre_dir = d
            working = working[1:]

    if len(working) > 1:
        d = _standardize_directional(working[-1])
        if d:
            post_dir = d
            working = working[:-1]

    if working:
        s = _standardize_suffix(working[-1])
        if s:
            suffix = s
            working = working[:-1]

    # If peeling left an empty street name but we removed a predirectional,
    # the directional was actually the street name (eg "100 N St" = 100 N ST).
    if not working and pre_dir:
        working = [pre_dir]
        pre_dir = None

    street_name = " ".join(t.upper() for t in working).strip() or None
    return primary, pre_dir, street_name, suffix, post_dir


def _classify_primary_line(line: str) -> str:
    """Classify the primary delivery line."""
    up = line.upper().strip()
    if up == GENERAL_DELIVERY:
        return "general_delivery"
    if _PO_BOX_RE.match(up):
        return "po_box"
    for prefix in RURAL_ROUTE_PREFIXES:
        if up.startswith(prefix + " ") or up == prefix:
            return "rural_route"
    for prefix in HIGHWAY_CONTRACT_PREFIXES:
        if up.startswith(prefix + " ") or up == prefix:
            return "highway_contract"
    if _is_street_line(line):
        return "street"
    return "unknown"


def _parse_po_box(line: str, parsed: ParsedAddress) -> None:
    m = _PO_BOX_RE.match(line)
    if m:
        parsed.primary_number = m.group(1).upper()
        parsed.address_type = "po_box"


def _parse_rural_route(line: str, parsed: ParsedAddress) -> None:
    m = _RR_RE.match(line)
    if m:
        parsed.primary_number = m.group(1)
        if m.group(2):
            parsed.secondary_number = m.group(2).upper()
            parsed.secondary_designator = "BOX"
        parsed.address_type = "rural_route"


def _parse_highway_contract(line: str, parsed: ParsedAddress) -> None:
    m = _HC_RE.match(line)
    if m:
        parsed.primary_number = m.group(1)
        if m.group(2):
            parsed.secondary_number = m.group(2).upper()
            parsed.secondary_designator = "BOX"
        parsed.address_type = "highway_contract"


def _detect_military(parsed: ParsedAddress) -> None:
    if not parsed.city:
        return
    head = parsed.city.split()[0].upper() if parsed.city else ""
    if head in MILITARY_LAST_LINE_CODES and parsed.state in MILITARY_STATES:
        parsed.address_type = "military"


def parse_address(address: str) -> ParsedAddress:
    """Parse a free-form USPS address string."""
    parsed = ParsedAddress(raw=address)
    if not address or not address.strip():
        parsed.warnings.append("empty_input")
        return parsed

    tokens = _tokenize_lines(address)
    if not tokens:
        parsed.warnings.append("no_tokens")
        return parsed

    # ZIP first (operates on the final block of the last line)
    zip5, zip4, trimmed_last = _extract_zip(tokens[-1:])
    if zip5:
        parsed.zip5 = zip5
    if zip4:
        parsed.zip4 = zip4
    if trimmed_last:
        tokens = tokens[:-1] + [" ".join(trimmed_last)]
    elif zip5:
        tokens = tokens[:-1]

    # State (last token of what remains in the last line)
    if tokens:
        last_line_tokens = tokens[-1].split()
        state, rest = _extract_state(last_line_tokens)
        if state:
            parsed.state = state
            last = " ".join(rest)
            if last:
                tokens = tokens[:-1] + [last]
            else:
                tokens = tokens[:-1]

    # City is the final remaining line if no street indicator follows
    if tokens:
        candidate_city = tokens[-1]
        if not _is_street_line(candidate_city) and _classify_primary_line(candidate_city) == "unknown":
            parsed.city = candidate_city.upper()
            tokens = tokens[:-1]

    # Urbanization (Puerto Rico)
    urb, tokens = _extract_urbanization(tokens)
    if urb:
        parsed.urbanization = urb

    # Identify the primary delivery line
    primary_line: str | None = None
    firm_candidates: list[str] = []
    secondary_only: str | None = None

    for line in tokens:
        classification = _classify_primary_line(line)
        if classification == "street" and primary_line is None:
            primary_line = line
            continue
        if classification in {"po_box", "rural_route", "highway_contract", "general_delivery"}:
            primary_line = line
            parsed.address_type = classification
            break
        # A bare secondary line ("APT 4B") sometimes appears on its own.
        first_tok = line.split()[0].upper() if line.split() else ""
        if first_tok in SECONDARY_DESIGNATORS or first_tok.startswith("#"):
            secondary_only = line
            continue
        firm_candidates.append(line)

    if firm_candidates:
        parsed.firm = " ".join(firm_candidates).upper()

    if primary_line is None:
        if secondary_only:
            parsed.warnings.append("only_secondary_line")
        else:
            parsed.warnings.append("no_primary_line")
        return parsed

    if parsed.address_type == "po_box":
        _parse_po_box(primary_line, parsed)
    elif parsed.address_type == "rural_route":
        _parse_rural_route(primary_line, parsed)
    elif parsed.address_type == "highway_contract":
        _parse_highway_contract(primary_line, parsed)
    elif parsed.address_type == "general_delivery":
        parsed.primary_number = None
    else:
        parsed.address_type = "street"
        # Tokenize and split secondary off the primary line
        parts = primary_line.split()
        street_tokens, sec_des, sec_num = _split_street_and_secondary(parts)
        if sec_des is None and secondary_only:
            sec_parts = secondary_only.split()
            _, sec_des, sec_num = _split_street_and_secondary(
                [sec_parts[0]] + sec_parts[1:]
            )
        parsed.secondary_designator = sec_des
        parsed.secondary_number = sec_num.upper() if sec_num else None
        (
            parsed.primary_number,
            parsed.predirectional,
            parsed.street_name,
            parsed.street_suffix,
            parsed.postdirectional,
        ) = _parse_street_tokens(street_tokens)

    _detect_military(parsed)

    if parsed.zip5 is None:
        parsed.warnings.append("missing_zip")
    if parsed.state is None:
        parsed.warnings.append("missing_state")
    if parsed.city is None:
        parsed.warnings.append("missing_city")
    if parsed.address_type == "street" and not parsed.street_name:
        parsed.warnings.append("missing_street_name")
    if (
        parsed.address_type == "street"
        and parsed.secondary_designator
        and parsed.secondary_designator in SECONDARY_DESIGNATORS_WITH_NUMBER.values()
        and not parsed.secondary_number
    ):
        parsed.warnings.append("secondary_missing_number")

    return parsed
