"""Canonical serialization and input-hash determinism (ADR 0001;
docs/engine/semantics.md: "identical canonical inputs must produce
byte-identical canonical results").
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from finguard_core.canonical import canonical_decimal, canonical_json, input_hash
from tests.support.builders import (
    make_commitment,
    make_event,
    make_fx_rate,
    make_input,
    make_minimal_input,
)


def test_canonical_decimal_ignores_trailing_zeros():
    assert canonical_decimal(Decimal("1.50")) == canonical_decimal(Decimal("1.5"))
    assert canonical_decimal(Decimal("100")) == "100"
    assert canonical_decimal(Decimal("100.00")) == "100"
    assert canonical_decimal(Decimal("0.00")) == "0"
    assert canonical_decimal(Decimal("-0")) == "0"


def test_canonical_decimal_never_uses_exponential_notation():
    text = canonical_decimal(Decimal("1E+10"))
    assert "E" not in text and "e" not in text


def test_identical_input_hashes_identically_across_separate_calls():
    a = make_minimal_input()
    b = make_minimal_input()
    assert input_hash(a) == input_hash(b)
    assert canonical_json(a) == canonical_json(b)


def test_input_hash_is_independent_of_unordered_collection_order():
    e1 = make_event("e1", a_date := __import__("datetime").date(2026, 1, 2), Decimal("100"))
    e2 = make_event("e2", a_date, Decimal("200"))
    c1 = make_commitment("c1")
    c2 = make_commitment("c2")
    r1 = make_fx_rate("USD", "INR", a_date, Decimal("80"))
    r2 = make_fx_rate("EUR", "INR", a_date, Decimal("90"))

    forward = make_input(events=(e1, e2), commitments=(c1, c2), fx_rates=(r1, r2))
    reversed_order = make_input(events=(e2, e1), commitments=(c2, c1), fx_rates=(r2, r1))

    assert input_hash(forward) == input_hash(reversed_order)
    assert canonical_json(forward) == canonical_json(reversed_order)


def test_input_hash_distinguishes_different_inputs():
    a = make_minimal_input()
    b = replace(a, purchase=replace(a.purchase, amount=Decimal("2000")))
    assert input_hash(a) != input_hash(b)


def test_input_hash_treats_equal_decimal_values_as_identical_regardless_of_representation():
    a = make_minimal_input()
    b = replace(a, profile=replace(a.profile, current_available_balance=Decimal("10000.00")))
    assert a.profile.current_available_balance == b.profile.current_available_balance
    assert input_hash(a) == input_hash(b)


def test_canonical_json_has_no_insignificant_whitespace():
    text = canonical_json(make_minimal_input())
    assert "\n" not in text
    assert ", " not in text
    assert ": " not in text


def test_hash_is_sha256_hex_digest_length():
    assert len(input_hash(make_minimal_input())) == 64
    int(input_hash(make_minimal_input()), 16)  # raises if not hex
