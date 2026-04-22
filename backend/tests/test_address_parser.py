"""Coverage for the Publication 28 address parser and mock verifier."""
from __future__ import annotations

import pytest

from app.tools.address_mock import MockAddressVerifier
from app.tools.address_parser import parse_address


@pytest.mark.asyncio
async def test_simple_street_address_standardizes():
    result = await MockAddressVerifier().verify(
        "1600 Pennsylvania Avenue NW, Washington, DC 20500"
    )
    assert result.verified
    assert result.address_type == "street"
    assert result.primary_number == "1600"
    assert result.street_name == "PENNSYLVANIA"
    assert result.street_suffix == "AVE"
    assert result.postdirectional == "NW"
    assert result.city == "WASHINGTON"
    assert result.state == "DC"
    assert result.zip5 == "20500"
    assert "AVE" in (result.standardized or "")


@pytest.mark.asyncio
async def test_secondary_unit_apt_parsed():
    r = await MockAddressVerifier().verify("123 N Main St Apt 4B, Dallas, TX 75201")
    assert r.predirectional == "N"
    assert r.street_name == "MAIN"
    assert r.street_suffix == "ST"
    assert r.secondary_designator == "APT"
    assert r.secondary_number == "4B"
    assert r.verified


@pytest.mark.asyncio
async def test_secondary_unit_suite_number_sign():
    r = await MockAddressVerifier().verify("500 Market Street #2200, San Francisco, CA 94105")
    assert r.secondary_designator == "UNIT"
    assert r.secondary_number == "2200"


@pytest.mark.asyncio
async def test_basement_designator_without_number():
    r = await MockAddressVerifier().verify("221 Baker St Bsmt, Chicago, IL 60614")
    assert r.secondary_designator == "BSMT"
    assert r.secondary_number is None


@pytest.mark.asyncio
async def test_po_box_recognized():
    r = await MockAddressVerifier().verify("PO Box 12345, Anchorage, AK 99501-0001")
    assert r.address_type == "po_box"
    assert r.primary_number == "12345"
    assert r.zip5 == "99501"
    assert r.zip4 == "0001"
    assert "PO BOX 12345" in (r.standardized or "")


@pytest.mark.asyncio
async def test_rural_route_with_box():
    r = await MockAddressVerifier().verify("RR 2 Box 152, Ames, IA 50014")
    assert r.address_type == "rural_route"
    assert r.primary_number == "2"
    assert r.secondary_number == "152"
    assert "RR 2 BOX 152" in (r.standardized or "")


@pytest.mark.asyncio
async def test_highway_contract():
    r = await MockAddressVerifier().verify("HC 68 Box 23A, Eagle, AK 99738")
    assert r.address_type == "highway_contract"
    assert r.primary_number == "68"
    assert r.secondary_number == "23A"


@pytest.mark.asyncio
async def test_military_apo():
    r = await MockAddressVerifier().verify(
        "PSC 1234 Box 5678, APO AE 09369"
    )
    assert r.state == "AE"
    assert r.address_type in {"military", "po_box", "unknown"}
    assert r.zip5 == "09369"


@pytest.mark.asyncio
async def test_urbanization_puerto_rico():
    r = await MockAddressVerifier().verify(
        "URB Las Gladiolas, 150 Calle A, San Juan, PR 00926"
    )
    assert r.urbanization == "LAS GLADIOLAS"
    assert r.state == "PR"
    assert r.zip5 == "00926"
    assert r.primary_number == "150"
    assert r.standardized and "URB LAS GLADIOLAS" in r.standardized


@pytest.mark.asyncio
async def test_multiline_address_with_firm():
    address = (
        "Acme Widgets Inc\n"
        "100 Industrial Pkwy\n"
        "Suite 400\n"
        "Buffalo, NY 14201"
    )
    r = await MockAddressVerifier().verify(address)
    assert r.firm == "ACME WIDGETS INC"
    assert r.street_suffix == "PKWY"
    assert r.secondary_designator == "STE"
    assert r.secondary_number == "400"


@pytest.mark.asyncio
async def test_directional_preserved_as_name_when_alone():
    """A directional that is the only word after the number is the street
    name, not a predirectional."""
    r = await MockAddressVerifier().verify("100 N St, Washington, DC 20001")
    assert r.predirectional is None
    # With only one remaining token after the number, it becomes the name
    assert r.street_name == "N"


@pytest.mark.asyncio
async def test_missing_zip_is_soft_warning():
    r = await MockAddressVerifier().verify("123 Main St, Austin, TX")
    assert r.state == "TX"
    assert r.zip5 is None
    assert "missing_zip" in r.warnings
    assert r.dpv_code == "S"


@pytest.mark.asyncio
async def test_garbage_input_fails_gracefully():
    r = await MockAddressVerifier().verify("not an address")
    assert not r.verified
    assert r.dpv_code == "N"


@pytest.mark.asyncio
async def test_suffix_variant_maps_to_canonical():
    r = await MockAddressVerifier().verify("42 Peachtree Boulevard, Atlanta, GA 30303")
    assert r.street_suffix == "BLVD"


@pytest.mark.asyncio
async def test_general_delivery():
    r = await MockAddressVerifier().verify("General Delivery, Juneau, AK 99801")
    assert r.address_type == "general_delivery"
    assert (r.standardized or "").startswith("GENERAL DELIVERY")


def test_parse_hyphenated_grid_number():
    p = parse_address("12-34 Queens Blvd, Queens, NY 11101")
    assert p.primary_number == "12-34"
    assert p.street_suffix == "BLVD"


def test_parse_predirectional_vs_postdirectional():
    p = parse_address("400 S Main St N, Salt Lake City, UT 84101")
    assert p.predirectional == "S"
    assert p.street_name == "MAIN"
    assert p.street_suffix == "ST"
    assert p.postdirectional == "N"
