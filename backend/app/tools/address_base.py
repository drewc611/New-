"""Address verification tool base and factory."""
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings
from app.models.schemas import AddressVerifyResult


class AddressVerifier(ABC):
    name: str = "base"

    @abstractmethod
    async def verify(self, address: str) -> AddressVerifyResult: ...


@lru_cache
def get_verifier() -> AddressVerifier:
    from app.tools.address_mock import MockAddressVerifier
    from app.tools.address_usps import UspsAddressVerifier

    s = get_settings()
    if s.address_verifier == "mock":
        return MockAddressVerifier()
    if s.address_verifier == "usps_api":
        return UspsAddressVerifier(
            base_url=s.usps_api_base_url,
            user_id=s.usps_api_user_id,
            password=s.usps_api_password,
        )
    raise ValueError(f"unknown verifier: {s.address_verifier}")
