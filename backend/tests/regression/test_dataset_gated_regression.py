"""Dataset-gated regression suite (docs/engine/semantics.md's
regression-classification strategy; docs/dataset-provenance.md).

This suite is opt-in via the ``FINGUARD_FIXTURES_DIR`` environment
variable and skips cleanly when it is unset — which it always is in
this session, since the dataset's redistribution rights are still
unconfirmed (see docs/dataset-provenance.md) and PR-1's hard
constraints forbid moving the dataset or committing dataset-derived
fixtures. No dataset path is read, written, or guessed anywhere in this
file; it only checks whether the opt-in variable happens to be set.
"""

from __future__ import annotations

import os

import pytest

FIXTURES_DIR = os.environ.get("FINGUARD_FIXTURES_DIR")

pytestmark = pytest.mark.skipif(
    not FIXTURES_DIR,
    reason=(
        "FINGUARD_FIXTURES_DIR is not set — dataset-derived regression "
        "fixtures are opt-in and unavailable until dataset provenance is "
        "resolved (docs/dataset-provenance.md). This is expected, not a "
        "failure."
    ),
)


def test_dataset_gated_regression_placeholder():
    """A real implementation will walk FINGUARD_FIXTURES_DIR and compare
    analyze() output against the dataset's historical examples, per the
    classification/characterization strategy in docs/engine/semantics.md.
    Phase 1 only needs the gate to exist and skip cleanly; the fixture
    loader itself is follow-up work once provenance is resolved.
    """

    pytest.skip("Fixture loader not yet implemented — gate verified above.")
