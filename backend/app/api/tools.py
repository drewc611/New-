"""Direct tool endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.schemas import (
    AddressAnalyticsSummary,
    AddressSuggestion,
    AddressVerifyResult,
)
from app.services.address_analytics import get_analytics
from app.tools.address_base import get_verifier
from app.tools.address_suggester import suggest_corrections

router = APIRouter(prefix="/api/tools", tags=["tools"])


class AddressVerifyRequest(BaseModel):
    address: str


class AddressSuggestRequest(BaseModel):
    address: str
    max_suggestions: int = 3


class AddressSuggestResponse(BaseModel):
    input_address: str
    noise_removed: list[str]
    suggestions: list[AddressSuggestion]


@router.post("/address/verify", response_model=AddressVerifyResult)
async def address_verify(
    req: AddressVerifyRequest,
    user: dict = Depends(get_current_user),
) -> AddressVerifyResult:
    verifier = get_verifier()
    result = await verifier.verify(req.address)
    await get_analytics().record(result, verifier=verifier.name, user_id=user["sub"])
    return result


@router.post("/address/suggest", response_model=AddressSuggestResponse)
async def address_suggest(
    req: AddressSuggestRequest,
    _user: dict = Depends(get_current_user),
) -> AddressSuggestResponse:
    suggestions, noise = suggest_corrections(
        req.address, max_suggestions=max(1, min(10, req.max_suggestions))
    )
    return AddressSuggestResponse(
        input_address=req.address,
        noise_removed=noise,
        suggestions=suggestions,
    )


@router.get("/address/analytics", response_model=AddressAnalyticsSummary)
async def address_analytics(
    _user: dict = Depends(get_current_user),
) -> AddressAnalyticsSummary:
    return await get_analytics().summary()
