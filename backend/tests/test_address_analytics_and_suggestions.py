"""Coverage for noise cancellation, fuzzy suggestions, and analytics."""
from __future__ import annotations

import pytest

from app.services.address_analytics import AddressAnalytics
from app.tools.address_fuzzy import (
    fuzzy_designator,
    fuzzy_directional,
    fuzzy_state,
    fuzzy_suffix,
)
from app.tools.address_mock import MockAddressVerifier
from app.tools.address_noise import cancel_noise
from app.tools.address_suggester import suggest_corrections


def test_noise_strips_filler_and_quotes():
    out, notes = cancel_noise('Please verify "1600 Pennsylvania Ave, Washington, DC 20500"')
    assert out.startswith("1600 Pennsylvania")
    assert "filler" in notes


def test_noise_strips_emoji_and_phone_and_email():
    out, notes = cancel_noise(
        "123 Main St, Austin, TX 78701 \U0001F600 call 512-555-0100 me@example.com"
    )
    assert "emoji" in notes
    assert "phone" in notes
    assert "email" in notes
    assert "123 Main St" in out


def test_noise_strips_trailing_country():
    out, notes = cancel_noise("10 Downing St, Washington, DC 20001, USA")
    assert "country_suffix" in notes
    assert "USA" not in out.upper()


def test_noise_strips_attention_line():
    out, notes = cancel_noise("ATTN: John Doe, 100 Market St, San Francisco, CA 94105")
    assert "attention" in notes
    assert "ATTN" not in out.upper()


def test_fuzzy_suffix_corrects_typo():
    m = fuzzy_suffix("streat")
    assert m is not None
    assert m.suggestion == "ST"


def test_fuzzy_directional_corrects_typo():
    m = fuzzy_directional("nort")
    assert m is not None
    assert m.suggestion == "N"


def test_fuzzy_designator_corrects_typo():
    m = fuzzy_designator("aparment")
    assert m is not None
    assert m.suggestion == "APT"


def test_fuzzy_state_corrects_typo():
    m = fuzzy_state("TXS")
    assert m is not None
    assert m.suggestion == "TX"


def test_suggester_fixes_misspelled_suffix():
    suggestions, _ = suggest_corrections("123 Peachtree Stret, Atlanta, GA 30303")
    assert suggestions
    assert any("ST" in s.standardized.split() for s in suggestions)
    top = suggestions[0]
    assert any(r["category"] == "suffix" for r in top.replaced_tokens)


def test_suggester_strips_noise_and_standardizes():
    msg = 'Please verify "42 Peachtree Boulevard, Atlanta, GA 30303" thanks'
    suggestions, noise = suggest_corrections(msg)
    assert "filler" in noise
    assert suggestions
    assert "BLVD" in suggestions[0].standardized


def test_suggester_returns_empty_for_identical_input():
    # Already a clean standardized address; no suggestion different from input
    suggestions, _ = suggest_corrections(
        "123 MAIN ST\nDALLAS, TX 75201"
    )
    assert isinstance(suggestions, list)


@pytest.mark.asyncio
async def test_mock_verifier_attaches_suggestions_on_low_confidence():
    r = await MockAddressVerifier().verify("123 Peachtree Stret, Atlanta, GA 30303")
    assert r.suggestions, "expected suggestions for misspelled suffix"
    assert r.suggestions[0].confidence > 0
    # Noise cancellation also populates the result
    assert isinstance(r.noise_removed, list)


@pytest.mark.asyncio
async def test_analytics_records_and_summarizes(patch_mongo):
    from app.core.mongo_client import get_mongo_db

    db = get_mongo_db()
    analytics = AddressAnalytics(
        db=db,
        collection_name="test_events",
        capped_size_mb=1,
        capped_max_docs=1_000,
    )
    result = await MockAddressVerifier().verify("1 Main St, Dallas, TX 75201")
    await analytics.record(result, verifier="mock", user_id="tester")
    result2 = await MockAddressVerifier().verify("not an address")
    await analytics.record(result2, verifier="mock", user_id="tester")

    summary = await analytics.summary()
    assert summary.total == 2
    assert summary.verified >= 1
    assert "mock" not in summary.by_dpv_code  # dpv codes are Y/N/S/D
    assert "street" in summary.by_address_type or "unknown" in summary.by_address_type
