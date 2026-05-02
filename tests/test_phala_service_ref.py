# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for PhalaServiceRef.

Locks the wire shape that third-party validators rely on to decide
whether an agent claims Phala compatibility.
"""

from __future__ import annotations

import pytest

from phala.types import (
    PHALA_EXTENSION_URI,
    AdjustmentBounds,
    PhalaServiceRef,
)


def _ref(**overrides) -> PhalaServiceRef:
    base = dict(
        version="1.0.0",
        outcome_endpoint="https://agent.example.com/phala/outcomes",
        satisfaction_endpoint="https://agent.example.com/phala/satisfactions",
        belief_update_endpoint="https://agent.example.com/phala/belief_updates",
        weight_keys=["routing.peer_a.preference", "routing.peer_b.preference"],
        learning_rate=0.05,
        weight_bounds=AdjustmentBounds(min=-1.0, max=1.0),
    )
    base.update(overrides)
    return PhalaServiceRef(**base)


def test_extension_uri_is_stable():
    assert PHALA_EXTENSION_URI == (
        "https://ravikiran438.github.io/phala-protocol/v1"
    )


def test_ref_round_trip():
    ref = _ref()
    blob = ref.model_dump_json()
    parsed = PhalaServiceRef.model_validate_json(blob)
    assert parsed.belief_update_endpoint.endswith("/phala/belief_updates")
    assert parsed.weight_bounds.min == -1.0


def test_belief_update_endpoint_is_required():
    with pytest.raises(ValueError):
        PhalaServiceRef(
            version="1.0.0",
            outcome_endpoint="https://x/o",
            satisfaction_endpoint="https://x/s",
            # belief_update_endpoint omitted
            weight_keys=["k"],
            learning_rate=0.1,
            weight_bounds=AdjustmentBounds(min=0.0, max=1.0),
        )


def test_learning_rate_must_be_in_zero_one():
    with pytest.raises(ValueError):
        _ref(learning_rate=0.0)
    with pytest.raises(ValueError):
        _ref(learning_rate=1.5)
