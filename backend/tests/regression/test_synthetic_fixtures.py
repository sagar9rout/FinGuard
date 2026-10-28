"""Committed, public-safe synthetic fixtures (fixtures/README.md's
``synthetic/`` split) loaded and run through ``analyze()`` end to end.
None of the values here are derived from the third-party dataset — see
docs/dataset-provenance.md.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from finguard_core import analyze
from tests.support.builders import make_input, make_profile, make_purchase

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "synthetic_fixtures"


def _load_cases():
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as fh:
            yield path.name, json.load(fh)


@pytest.mark.parametrize("name,case", list(_load_cases()), ids=[n for n, _ in _load_cases()])
def test_synthetic_fixture_produces_the_expected_status(name, case):
    profile = make_profile(
        home_currency=case["home_currency"],
        current_available_balance=Decimal(case["current_available_balance"]),
        minimum_balance_to_keep=Decimal(case["minimum_balance_to_keep"]),
    )
    purchase = make_purchase(
        amount=Decimal(case["purchase_amount"]),
        currency=case["purchase_currency"],
    )
    as_of = date.fromisoformat(case["as_of"])
    result = analyze(make_input(as_of=as_of, profile=profile, purchase=purchase))
    assert result.status.value == case["expected_status"], name
