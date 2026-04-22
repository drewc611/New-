"""USPS Web Tools Address Validation verifier.

Uses ``defusedxml`` for parsing to block XML external entity and billion
laughs attacks. All user-controlled fields are XML-escaped before being
inserted into the request body to prevent XML injection.
"""
from __future__ import annotations

from xml.sax.saxutils import escape as xml_escape, quoteattr

import httpx
from defusedxml.ElementTree import fromstring as defused_fromstring

from app.core.logging import get_logger
from app.models.schemas import AddressVerifyResult
from app.tools.address_base import AddressVerifier
from app.tools.address_parser import parse_address

log = get_logger(__name__)


def _x(value: str | None) -> str:
    """Escape a value for inclusion in XML character data."""
    if value is None:
        return ""
    return xml_escape(value, {'"': "&quot;", "'": "&apos;"})


class UspsAddressVerifier(AddressVerifier):
    name = "usps_api"

    def __init__(
        self,
        base_url: str,
        user_id: str,
        password: str,
        timeout_seconds: float = 15.0,
    ) -> None:
        if not user_id:
            raise ValueError("USPS_API_USER_ID is required for usps_api verifier")
        self._base_url = base_url.rstrip("/")
        self._user_id = user_id
        self._password = password
        self._timeout = timeout_seconds

    def _build_xml(
        self,
        firm: str,
        street: str,
        secondary: str,
        city: str,
        state: str,
        zip5: str,
        zip4: str,
        urbanization: str,
    ) -> str:
        userid_attr = quoteattr(self._user_id)
        return (
            f"<AddressValidateRequest USERID={userid_attr}>"
            f"<Revision>1</Revision>"
            f'<Address ID="0">'
            f"<FirmName>{_x(firm)}</FirmName>"
            f"<Address1>{_x(secondary)}</Address1>"
            f"<Address2>{_x(street)}</Address2>"
            f"<City>{_x(city)}</City>"
            f"<State>{_x(state)}</State>"
            f"<Urbanization>{_x(urbanization)}</Urbanization>"
            f"<Zip5>{_x(zip5)}</Zip5>"
            f"<Zip4>{_x(zip4)}</Zip4>"
            f"</Address>"
            f"</AddressValidateRequest>"
        )

    async def verify(self, address: str) -> AddressVerifyResult:
        parsed = parse_address(address)

        xml = self._build_xml(
            firm=parsed.firm or "",
            street=parsed.primary_line or "",
            secondary=parsed.secondary_line or "",
            city=parsed.city or "",
            state=parsed.state or "",
            zip5=parsed.zip5 or "",
            zip4=parsed.zip4 or "",
            urbanization=parsed.urbanization or "",
        )
        url = f"{self._base_url}/ShippingAPI.dll"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(url, params={"API": "Verify", "XML": xml})
            r.raise_for_status()
            root = defused_fromstring(r.text)

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
            return AddressVerifyResult(
                input_address=address, verified=False, confidence=0.0
            )

        def _text(tag: str) -> str | None:
            node = a.find(tag)
            return node.text if node is not None and node.text else None

        out_secondary = _text("Address1")
        out_street = _text("Address2")
        out_city = _text("City")
        out_state = _text("State")
        out_zip5 = _text("Zip5")
        out_zip4 = _text("Zip4")
        out_urb = _text("Urbanization")
        dpv = _text("DPVConfirmation") or "U"
        returntext = _text("ReturnText") or ""

        standardized = None
        if out_street and out_city and out_state and out_zip5:
            z4 = f"-{out_zip4}" if out_zip4 else ""
            first_line = (
                f"{out_street} {out_secondary}".strip() if out_secondary else out_street
            )
            urb = f"{out_urb}\n" if out_urb else ""
            standardized = f"{urb}{first_line}\n{out_city}, {out_state} {out_zip5}{z4}"

        confidence = {"Y": 0.98, "S": 0.7, "D": 0.55}.get(dpv, 0.2)
        return AddressVerifyResult(
            input_address=address,
            standardized=standardized,
            street=out_street,
            secondary=out_secondary,
            city=out_city,
            state=out_state,
            zip5=out_zip5,
            zip4=out_zip4,
            urbanization=out_urb,
            dpv_code=dpv,
            return_codes=[returntext] if returntext else [],
            confidence=confidence,
            verified=dpv in ("Y", "S"),
        )
