"""Offline address verifier backed by the Publication 28 parser.

Produces USPS-standardized output for every major address form:

* Street addresses with primary/secondary components and directionals
* PO Box, Rural Route (RR), Highway Contract (HC), General Delivery
* Military APO/FPO/DPO addresses
* Puerto Rico urbanization (URB) lines

Intended for local development and CI. It does not talk to the USPS API
and does not validate that a given ZIP actually exists, so the DPV code
is assigned heuristically based on parse completeness. Use the ``usps_api``
verifier for live validation against USPS Web Tools.
"""
from __future__ import annotations

from app.models.schemas import AddressVerifyResult
from app.tools.address_base import AddressVerifier
from app.tools.address_noise import cancel_noise
from app.tools.address_parser import parse_address
from app.tools.address_suggester import suggest_corrections


def _confidence_for(warnings: list[str], kind: str) -> tuple[float, str]:
    """Map parse warnings to a DPV-style code and confidence score."""
    if not warnings and kind != "unknown":
        return 0.95, "Y"
    if warnings == ["secondary_missing_number"] and kind == "street":
        return 0.7, "D"
    blocking = {"no_primary_line", "missing_street_name", "only_secondary_line"}
    if any(w in blocking for w in warnings) or kind == "unknown":
        return 0.2, "N"
    # Soft failures (missing_zip, missing_state, missing_city): primary parse
    # succeeded, but the last line is incomplete. Treat as secondary-match-S.
    return 0.55, "S"


def _build_return_codes(parsed) -> list[str]:
    codes: list[str] = [f"PARSED_{parsed.address_type.upper()}"]
    codes.extend(f"WARN_{w.upper()}" for w in parsed.warnings)
    if parsed.urbanization:
        codes.append("URBANIZATION_DETECTED")
    if parsed.address_type == "military":
        codes.append("MILITARY_ADDRESS")
    return codes


class MockAddressVerifier(AddressVerifier):
    name = "mock"

    async def verify(self, address: str) -> AddressVerifyResult:
        cleaned, noise = cancel_noise(address)
        parsed = parse_address(cleaned or address)
        confidence, dpv = _confidence_for(parsed.warnings, parsed.address_type)

        suggestions: list = []
        needs_suggestions = (
            confidence < 0.9
            or bool(parsed.warnings)
            or bool(noise)
            or (parsed.address_type == "street" and parsed.street_suffix is None)
        )
        if needs_suggestions:
            suggestions, _ = suggest_corrections(
                address,
                base_confidence=max(0.3, confidence - 0.1),
            )

        return AddressVerifyResult(
            input_address=address,
            standardized=parsed.standardized(),
            firm=parsed.firm,
            primary_number=parsed.primary_number,
            predirectional=parsed.predirectional,
            street_name=parsed.street_name,
            street_suffix=parsed.street_suffix,
            postdirectional=parsed.postdirectional,
            street=parsed.primary_line,
            secondary=parsed.secondary_line,
            secondary_designator=parsed.secondary_designator,
            secondary_number=parsed.secondary_number,
            city=parsed.city,
            state=parsed.state,
            zip5=parsed.zip5,
            zip4=parsed.zip4,
            urbanization=parsed.urbanization,
            address_type=parsed.address_type,  # type: ignore[arg-type]
            dpv_code=dpv,
            return_codes=_build_return_codes(parsed),
            warnings=parsed.warnings,
            noise_removed=noise,
            suggestions=suggestions,
            confidence=confidence,
            verified=dpv in ("Y", "S"),
        )
