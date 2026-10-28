"""The wire contract: strictness, parity with the core contracts, and a
lossless round trip to the core input.
"""

from __future__ import annotations

import dataclasses
import json

import pytest
from pydantic import ValidationError

from finguard_api import schemas
from finguard_api.schemas import AnalysisRequest
from finguard_core.canonical import input_hash
from finguard_core.contracts import (
    CommitmentInput,
    EngineConfig,
    EvidenceFact,
    FinancialEventInput,
    FinancialProfile,
    FxRateEntry,
    PaymentOption,
    PaymentOptionSchedule,
    PurchaseRequest,
    UserPreferences,
)
from tests.support.api import to_body, to_wire
from tests.support.builders import make_minimal_input
from tests.support.scenarios import rich_scenario


def names(cls):
    return {f.name for f in dataclasses.fields(cls)}


@pytest.mark.parametrize(
    ("model", "core"),
    [
        (schemas.EventIn, FinancialEventInput),
        (schemas.CommitmentIn, CommitmentInput),
        (schemas.EvidenceFactIn, EvidenceFact),
        (schemas.ScheduleStepIn, PaymentOptionSchedule),
        (schemas.PaymentOptionIn, PaymentOption),
        (schemas.PurchaseIn, PurchaseRequest),
        (schemas.ProfileIn, FinancialProfile),
        (schemas.PreferencesIn, UserPreferences),
        (schemas.FxRateIn, FxRateEntry),
        (schemas.EngineConfigIn, EngineConfig),
    ],
)
def test_every_core_input_field_is_exposed_by_the_wire_model(model, core):
    assert set(model.model_fields) == names(core)


def test_top_level_parity():
    from finguard_core.contracts import AnalysisInput

    renamed = {"currency_registry": "currencies"}
    expected = {renamed.get(n, n) for n in names(AnalysisInput)}
    assert set(AnalysisRequest.model_fields) == expected


@pytest.mark.parametrize("make", [make_minimal_input, rich_scenario])
def test_round_trip_to_core_is_lossless(make):
    original = make()
    request = AnalysisRequest.model_validate_json(to_body(original))
    assert input_hash(request.to_core()) == input_hash(original)


def test_omitted_optional_sections_take_core_defaults():
    wire = to_wire(make_minimal_input())
    for key in ("config", "currencies", "events", "commitments", "evidence_facts", "payment_options", "fx_rates"):
        wire.pop(key)
    core = AnalysisRequest.model_validate_json(json.dumps(wire)).to_core()
    assert core.config == EngineConfig()
    assert set(core.currency_registry) == {"INR", "USD", "EUR", "ZAR", "IDR"}


def test_partial_config_overrides_only_the_given_fields():
    wire = to_wire(make_minimal_input())
    wire["config"] = {"horizon_days": 45}
    config = AnalysisRequest.model_validate_json(json.dumps(wire)).to_core().config
    assert config.horizon_days == 45 and config.max_window_days == EngineConfig().max_window_days


def _with(**changes):
    wire = to_wire(make_minimal_input())
    for path, value in changes.items():
        target = wire
        keys = path.split("__")
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
    return json.dumps(wire)


def test_unknown_fields_are_rejected_everywhere():
    for bad in (_with(surprise=1), _with(profile__surprise=1), _with(purchase__surprise=1)):
        with pytest.raises(ValidationError):
            AnalysisRequest.model_validate_json(bad)


@pytest.mark.parametrize("bad", [10.5, 1e3, True, "abc", "NaN", "Infinity", None, [], {}])
def test_money_rejects_floats_booleans_and_non_numbers(bad):
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate_json(_with(purchase__amount=bad))


@pytest.mark.parametrize("good", ["1000", "1000.50", " 7 ", 1000])
def test_money_accepts_strings_and_integers(good):
    AnalysisRequest.model_validate_json(_with(purchase__amount=good))


def test_strict_types_are_not_coerced():
    for bad in (_with(as_of="not-a-date"), _with(as_of=20260101), _with(purchase__allows_partial_payment="yes")):
        with pytest.raises(ValidationError):
            AnalysisRequest.model_validate_json(bad)
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate_json(_with(preferences__accepted_methods=["teleport"]))
