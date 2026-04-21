"""Mock address verifier for offline development and tests."""
from __future__ import annotations

import re

from app.models.schemas import AddressVerifyResult
from app.tools.address_base import AddressVerifier


class MockAddressVerifier(AddressVerifier):
    name = "mock"

    _ZIP_RE = re.compile(r"(\d{5})(?:[ -](\d{4}))?")
    _STATE_RE = re.compile(r"\b([A-Z]{2})\b")

    async def verify(self, address: str) -> AddressVerifyResult:
        addr = address.strip()
        zm = self._ZIP_RE.search(addr)
        sm = self._STATE_RE.search(addr.upper())
        zip5 = zm.group(1) if zm else None
        zip4 = zm.group(2) if zm and zm.group(2) else "1234"
        state = sm.group(1) if sm else None

        parts = [p.strip() for p in addr.split(",")]
        street = parts[0].upper() if parts else addr.upper()
        city = parts[1].upper() if len(parts) > 1 else None

        verified = bool(zip5 and state and street)
        standardized = None
        if verified:
            standardized = f"{street}, {city or 'UNKNOWN'}, {state} {zip5}-{zip4}"

        return AddressVerifyResult(
            input_address=address,
            standardized=standardized,
            street=street,
            city=city,
            state=state,
            zip5=zip5,
            zip4=zip4,
            dpv_code="Y" if verified else "N",
            return_codes=["MOCK_OK"] if verified else ["MOCK_NO_ZIP"],
            confidence=0.95 if verified else 0.25,
            verified=verified,
        )
