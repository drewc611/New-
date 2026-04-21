"""Direct tool endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.schemas import AddressVerifyResult
from app.tools.address_base import get_verifier

router = APIRouter(prefix="/api/tools", tags=["tools"])


class AddressVerifyRequest(BaseModel):
    address: str


@router.post("/address/verify", response_model=AddressVerifyResult)
async def address_verify(
    req: AddressVerifyRequest,
    _user: dict = Depends(get_current_user),
) -> AddressVerifyResult:
    return await get_verifier().verify(req.address)
