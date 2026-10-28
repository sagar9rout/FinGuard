"""P0-1: no output may depend on the order of ANY unordered input
collection, and identical canonical inputs cannot yield different result
bytes (ADR 0001; docs/engine/semantics.md Section 1).
"""

from __future__ import annotations

import os
import random
import subprocess
import sys
from dataclasses import fields, replace
from pathlib import Path

import pytest

from finguard_core import analyze, forecast
from finguard_core.canonical import canonical_json, input_hash, result_hash
from finguard_core.contracts import AnalysisInput, UserPreferences
from tests.support.scenarios import rich_scenario, shuffled

BACKEND = Path(__file__).resolve().parents[2]


def test_rich_scenario_exercises_every_unordered_collection():
    inp = rich_scenario()
    for name in ("events", "commitments", "evidence_facts", "payment_options", "fx_rates"):
        assert len(getattr(inp, name)) >= 2, name
    for name in (
        "accepted_methods",
        "stoppable_categories",
        "reducible_categories",
        "protected_categories",
        "variable_spend_categories",
        "category_min_allowed",
    ):
        assert len(getattr(inp.preferences, name)) >= 2, name


def test_every_tuple_field_of_the_input_is_covered_by_the_shuffle():
    """Guards the guard: a new tuple-valued input field must either be
    shuffled here or be explicitly declared order-meaningful.
    """

    order_meaningful = {"fx_pivot_currencies", "schedule", "financial_priorities"}
    top = {
        f.name
        for f in fields(AnalysisInput)
        if f.name in {"events", "commitments", "evidence_facts", "payment_options", "fx_rates"}
    }
    pref = {f.name for f in fields(UserPreferences) if f.type.startswith("tuple")} - order_meaningful
    shuffled_pref = {
        "accepted_methods",
        "stoppable_categories",
        "reducible_categories",
        "protected_categories",
        "variable_spend_categories",
        "category_min_allowed",
    }
    assert top == {"events", "commitments", "evidence_facts", "payment_options", "fx_rates"}
    assert pref == shuffled_pref


@pytest.mark.parametrize("seed", range(30))
def test_reordering_all_collections_never_changes_result_bytes(seed):
    base = rich_scenario()
    permuted = shuffled(base, random.Random(seed))
    assert canonical_json(analyze(base)) == canonical_json(analyze(permuted))
    assert canonical_json(forecast(base)) == canonical_json(forecast(permuted))


@pytest.mark.parametrize("seed", range(10))
def test_input_hash_is_identical_for_every_permutation(seed):
    base = rich_scenario()
    assert input_hash(base) == input_hash(shuffled(base, random.Random(1000 + seed)))


def test_result_input_hash_is_the_canonical_input_hash():
    base = rich_scenario()
    assert analyze(shuffled(base, random.Random(7))).input_hash == input_hash(base)


def test_different_inputs_do_not_collide():
    base = rich_scenario()
    changed = replace(base, purchase=replace(base.purchase, amount=base.purchase.amount + 1))
    assert input_hash(base) != input_hash(changed)
    assert result_hash(analyze(base)) != result_hash(analyze(changed))


def test_rich_result_is_identical_across_processes_and_hash_seeds():
    script = (
        "import sys, random\n"
        f"sys.path.insert(0, {str(BACKEND)!r})\n"
        "from finguard_core import analyze\n"
        "from finguard_core.canonical import result_hash\n"
        "from tests.support.scenarios import rich_scenario, shuffled\n"
        "print(result_hash(analyze(shuffled(rich_scenario(), random.Random(int(sys.argv[1]))))))\n"
    )
    digests = set()
    for seed, process_seed in (("1", "0"), ("2", "1"), ("3", "987654")):
        env = {**os.environ, "PYTHONHASHSEED": process_seed}
        out = subprocess.run([sys.executable, "-c", script, seed], capture_output=True, text=True, env=env, check=True)
        digests.add(out.stdout.strip())
    assert digests == {result_hash(analyze(rich_scenario()))}


def test_assumptions_issues_and_candidates_have_semantic_order():
    result = analyze(rich_scenario())
    assert [e.code for e in result.assumptions] == sorted(e.code for e in result.assumptions)
    assert [e.code for e in result.issues] == sorted(e.code for e in result.issues)
    assert [e.field_name for e in result.missing_information] == sorted(
        e.field_name for e in result.missing_information
    )
    keys = [(c.candidate_type.value, c.option_id or "") for c in result.candidates]
    option_ids = [c.option_id for c in result.candidates if c.option_id]
    assert option_ids == sorted(option_ids)
    assert len(keys) == len(set(keys))
