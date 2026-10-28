"""Byte-identical canonical results (ADR 0001): the same canonical input
must yield the same canonical result bytes across calls, across input
ordering of unordered collections, and across separate processes with
different hash seeds.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from finguard_core import analyze
from finguard_core.canonical import canonical_json, result_hash
from tests.support.builders import AS_OF, make_event, make_input, make_minimal_input

BACKEND = Path(__file__).resolve().parents[2]

_SCRIPT = """
import sys
sys.path.insert(0, {backend!r})
from finguard_core import analyze
from finguard_core.canonical import result_hash
from tests.unit.test_result_determinism import _scenario
print(result_hash(analyze(_scenario())))
"""


def _scenario():
    events = tuple(
        make_event(
            f"e{i}",
            AS_OF + timedelta(days=i * 3),
            Decimal(100 + i * 7),
            category="groceries" if i % 2 else "other",
        )
        for i in range(1, 12)
    )
    return make_input(events=events)


def test_repeated_analysis_is_byte_identical():
    first = canonical_json(analyze(_scenario()))
    second = canonical_json(analyze(_scenario()))
    assert first == second
    assert result_hash(analyze(_scenario())) == result_hash(analyze(_scenario()))


def test_result_bytes_independent_of_event_order():
    inp = _scenario()
    reordered = replace(inp, events=tuple(reversed(inp.events)))
    assert canonical_json(analyze(inp)) == canonical_json(analyze(reordered))


def test_result_bytes_identical_across_processes_and_hash_seeds():
    digests = set()
    for seed in ("0", "1", "424242"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        out = subprocess.run(
            [sys.executable, "-c", _SCRIPT.format(backend=str(BACKEND))],
            capture_output=True, text=True, env=env, check=True,
        )
        digests.add(out.stdout.strip())
    assert len(digests) == 1
    assert digests == {result_hash(analyze(_scenario()))}


def test_result_contains_no_timestamps_or_random_identifiers():
    text = canonical_json(analyze(make_minimal_input()))
    # input_hash is the only digest-like value, and it is derived, not random.
    assert "uuid" not in text.lower()
    assert str(AS_OF.year) in text  # dates are caller-supplied, ISO formatted


def test_blocked_certification_is_flagged_and_explained():
    from tests.support.builders import make_input_with_unconvertible_debit

    result = analyze(make_input_with_unconvertible_debit())
    assert result.certified is False
    assert result.reasons[0].code == "UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION"
    assert result.chosen is None
    assert analyze(make_minimal_input()).certified is True
