"""USPS Web Tools Address Validation verifier."""
from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from app.core.logging import get_logger
from app.models.schemas import AddressVerifyResult
from app.tools.address_base import AddressVerifier

log = get_logger(__name__)


class UspsAddressVerifier(AddressVerifier):
    name = "usps_api"

    def __init__(self, base_url: str, user_id: str, password: str) -> None:
        if not user_id:
            raise ValueError("USPS_API_USER_ID is required for usps_api verifier")
        self._base_url = base_url.rstrip("/")
        self._user_id = user_id
        self._password = password

    def _build_xml(self, street: str, city: str, state: str, zip5: str, zip4: str) -> str:
        return (
            f'<AddressValidateRequest USERID="{self._user_id}">'
            f"<Revision>1</Revision>"
            f"<Address ID=\"0\">"
            f"<Address1></Address1>"
            f"<Address2>{street}</Address2>"
            f"<City>{city}</City>"
            f"<State>{state}</State>"
            f"<Zip5>{zip5}</Zip5>"
            f"<Zip4>{zip4}</Zip4>"
            f"</Address>"
            f"</AddressValidateRequest>"
        )

    def _parse_input(self, address: str) -> tuple[str, str, str, str, str]:
        parts = [p.strip() for p in address.split(",")]
        street = parts[0] if parts else ""
        city = parts[1] if len(parts) > 1 else ""
        state = ""
        zip5 = ""
        zip4 = ""
        if len(parts) > 2:
            tail = parts[2].split()
            if tail:
                state = tail[0]
            if len(tail) > 1:
                zip_part = tail[1]
                if "-" in zip_part:
                    z5, z4 = zip_part.split("-", 1)
                    zip5, zip4 = z5, z4
                else:
                    zip5 = zip_part
        return street, city, state, zip5, zip4

    async def verify(self, address: str) -> AddressVerifyResult:
        street, city, state, zip5, zip4 = self._parse_input(address)
        xml = self._build_xml(street, city, state, zip5, zip4)
        url = f"{self._base_url}/ShippingAPI.dll"

        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, params={"API": "Verify", "XML": xml})
            r.raise_for_status()
            root = ET.fromstring(r.text)

        err = root.find(".//Error/Description")
        if err is not None:
            return AddressVerifyResult(
                input_address=address,
                verified=False,
                return_codes=[err.text or "ERROR"],
                confidence=0.0,
            )

        a = root.find(".//Address")
        if a is None:
            return AddressVerifyResult(input_address=address, verified=False, confidence=0.0)

        def _text(tag: str) -> str | None:
            node = a.find(tag)
            return node.text if node is not None and node.text else None

        out_street = _text("Address2")
        out_city = _text("City")
        out_state = _text("State")
        out_zip5 = _text("Zip5")
        out_zip4 = _text("Zip4")
        dpv = _text("DPVConfirmation") or "U"
        returntext = _text("ReturnText") or ""

        standardized = None
        if out_street and out_city and out_state and out_zip5:
            z4 = f"-{out_zip4}" if out_zip4 else ""
            standardized = f"{out_street}, {out_city}, {out_state} {out_zip5}{z4}"

        return AddressVerifyResult(
            input_address=address,
            standardized=standardized,
            street=out_street,
            city=out_city,
            state=out_state,
            zip5=out_zip5,
            zip4=out_zip4,
            dpv_code=dpv,
            return_codes=[returntext] if returntext else [],
            confidence=0.98 if dpv == "Y" else 0.6 if dpv == "S" else 0.2,
            verified=dpv in ("Y", "S"),
        )
