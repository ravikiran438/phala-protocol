# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for the Phala MCP server tool handlers.

Handlers are called directly with JSON payloads to verify the contract
exposed to an MCP client. The stdio transport is covered separately in
test_server_stdio.py.
"""

from __future__ import annotations

import json

import pytest

from phala.mcp_server.tools import (
    HANDLERS,
    TOOL_SCHEMAS,
    ToolInvocationError,
    handle_arbitrate_conflicting_updates,
    handle_validate_belief_privacy,
    handle_validate_belief_update,
    handle_validate_detector_provenance,
    handle_validate_outcome_event,
    handle_validate_predictive_horizon,
    handle_validate_principal_satisfaction_model,
    handle_validate_satisfaction_record,
    handle_validate_typed_belief_update,
    handle_validate_typed_detector_composition,
    handle_validate_welfare_trace,
    list_tool_names,
)


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────


def test_schemas_and_handlers_are_consistent():
    assert set(TOOL_SCHEMAS.keys()) == set(HANDLERS.keys())
    assert set(list_tool_names()) == set(HANDLERS.keys())


def test_schemas_have_required_shape():
    for name, schema in TOOL_SCHEMAS.items():
        assert "description" in schema, f"{name} missing description"
        assert "inputSchema" in schema, f"{name} missing inputSchema"
        assert schema["inputSchema"]["type"] == "object"


# ─────────────────────────────────────────────────────────────────────────────
# validate_outcome_event
# ─────────────────────────────────────────────────────────────────────────────


def _outcome_event_payload() -> dict:
    return {
        "id": "00000000-0000-4000-8000-000000000001",
        "task_id": "task-abc",
        "agents_involved": ["agent-a", "agent-b"],
        "resolved_at": "2026-04-16T10:00:00Z",
        "resolution_type": "completed",
        "latency_ms": 12000,
        "principal_id": "p-001",
        "session_hash": "sha256:deadbeef",
    }


def test_validate_outcome_event_happy_path():
    result = json.loads(
        handle_validate_outcome_event({"event": _outcome_event_payload()})
    )
    assert result["ok"] is True


def test_validate_outcome_event_rejects_empty_agents():
    payload = _outcome_event_payload()
    payload["agents_involved"] = []
    with pytest.raises(ToolInvocationError, match="invalid event"):
        handle_validate_outcome_event({"event": payload})


def test_validate_outcome_event_rejects_non_object():
    with pytest.raises(ToolInvocationError, match="expected object"):
        handle_validate_outcome_event({"event": "not-a-dict"})


# ─────────────────────────────────────────────────────────────────────────────
# validate_satisfaction_record
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_satisfaction_record_happy_path():
    payload = {
        "id": "sr-1",
        "outcome_event_id": "oe-1",
        "valence": 0.6,
        "source": "implicit",
        "signal_components": {"completion_latency_ratio": 0.8},
        "recorded_at": "2026-04-16T10:00:10Z",
        "confidence": 0.9,
        "psm_version": "v1",
    }
    result = json.loads(
        handle_validate_satisfaction_record({"record": payload})
    )
    assert result["ok"] is True


def test_validate_satisfaction_record_rejects_out_of_range_valence():
    payload = {
        "id": "sr-1",
        "outcome_event_id": "oe-1",
        "valence": 2.0,  # out of [-1, 1]
        "source": "implicit",
        "signal_components": {},
        "recorded_at": "2026-04-16T10:00:10Z",
        "confidence": 0.0,
    }
    with pytest.raises(ToolInvocationError, match="invalid record"):
        handle_validate_satisfaction_record({"record": payload})


# ─────────────────────────────────────────────────────────────────────────────
# validate_belief_update
# ─────────────────────────────────────────────────────────────────────────────


def _belief_update_payload() -> dict:
    return {
        "id": "bu-1",
        "satisfaction_record_id": "sr-1",
        "target_agent_id": "agent-b",
        "weight_key": "routing.agent_b.preference",
        "weight_delta": 0.04,
        "context_hash": "sha256:feedface",
        "valid_from": "2026-04-16T10:00:10Z",
        "ttl_seconds": 3600,
    }


def test_validate_belief_update_happy_path():
    result = json.loads(
        handle_validate_belief_update({"update": _belief_update_payload()})
    )
    assert result["ok"] is True


def test_validate_belief_update_rejects_out_of_bound_delta():
    payload = _belief_update_payload()
    payload["weight_delta"] = 2.0
    with pytest.raises(ToolInvocationError, match="invalid update"):
        handle_validate_belief_update({"update": payload})


def test_validate_belief_update_rejects_signal_components_leak():
    """BeliefUpdate doesn't declare extra='forbid', so a payload with
    signal_components would silently round-trip as 'valid' through pure
    Pydantic validation. The tool must run BU-Privacy first to surface
    the leak rather than dropping it.
    """
    payload = _belief_update_payload()
    payload["signal_components"] = {"raw_scroll_distance": 1234}
    result = json.loads(handle_validate_belief_update({"update": payload}))
    assert result["ok"] is False
    assert (
        "signal_components" in result["error"]
        or "BU-Privacy" in result["error"]
    )


# ─────────────────────────────────────────────────────────────────────────────
# validate_principal_satisfaction_model
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_psm_happy_path():
    payload = {
        "principal_id": "p-001",
        "version": "v1",
        "declared_at": "2026-04-16T08:00:00Z",
        "context_profiles": {
            "travel": {
                "context_key": "travel",
                "signal_weights": {"completion_latency_ratio": 1.0},
                "deadline_tolerance_seconds": 1800,
                "overdue_penalty_multiplier": 1.5,
                "explicit_rating_floor": 0,
                "welfare_lookback_days": 14,
            }
        },
    }
    result = json.loads(
        handle_validate_principal_satisfaction_model({"model": payload})
    )
    assert result["ok"] is True


# ─────────────────────────────────────────────────────────────────────────────
# validate_welfare_trace
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_welfare_trace_happy_path():
    payload = {
        "principal_id": "p-001",
        "window_days": 30,
        "computed_at": "2026-04-16T00:00:00Z",
        "task_completion_trend": "stable",
        "agent_initiation_frequency_7d": 3,
        "overdue_rate_30d": 0.05,
        "autonomy_index": 0.8,
        "cognitive_load_proxy": 0.2,
        "context_density_7d": 5,
    }
    result = json.loads(
        handle_validate_welfare_trace({"trace": payload})
    )
    assert result["ok"] is True


# ─────────────────────────────────────────────────────────────────────────────
# validate_belief_privacy
# ─────────────────────────────────────────────────────────────────────────────


def test_validate_belief_privacy_accepts_clean_payload():
    result = json.loads(
        handle_validate_belief_privacy(
            {
                "payload": {
                    "id": "bu-1",
                    "weight_key": "routing.x",
                    "weight_delta": 0.1,
                }
            }
        )
    )
    assert result["ok"] is True


def test_validate_belief_privacy_rejects_signal_components_leak():
    result = json.loads(
        handle_validate_belief_privacy(
            {
                "payload": {
                    "id": "bu-1",
                    "weight_delta": 0.1,
                    "signal_components": {"completion_latency_ratio": 0.8},
                }
            }
        )
    )
    assert result["ok"] is False
    assert "BU-Privacy" in result["error"] or "signal_components" in result["error"]


def test_validate_belief_privacy_rejects_raw_signals_alias():
    result = json.loads(
        handle_validate_belief_privacy(
            {"payload": {"raw_signals": ["click", "scroll"]}}
        )
    )
    assert result["ok"] is False


def test_validate_belief_privacy_rejects_non_object():
    with pytest.raises(ToolInvocationError, match="expected object"):
        handle_validate_belief_privacy({"payload": "string-not-object"})


# ─────────────────────────────────────────────────────────────────────────────
# welfare_detectors extension handlers
# ─────────────────────────────────────────────────────────────────────────────


def _panel_payload() -> dict:
    return {
        "consumer_agent_id": "agent-target",
        "detectors": [
            {"detector_type": "cognitive_load", "priority": 10},
            {"detector_type": "autonomy", "priority": 20},
            {"detector_type": "dignity", "priority": 30},
        ],
    }


def _tbu_payload(detector_type: str = "cognitive_load",
                  provenance_hash: str = "abcdef0123456789") -> dict:
    return {
        "id": "00000000-0000-4000-8000-000000000010",
        "satisfaction_record_id": "00000000-0000-4000-8000-000000000099",
        "target_agent_id": "agent-target",
        "weight_key": "routing.preference",
        "weight_delta": 0.1,
        "context_hash": "0" * 64,
        "valid_from": "2026-04-25T12:00:00+00:00",
        "ttl_seconds": 3600,
        "detector_type": detector_type,
        "provenance_hash": provenance_hash,
    }


def test_validate_typed_belief_update_happy_path():
    result = json.loads(
        handle_validate_typed_belief_update({"update": _tbu_payload()})
    )
    assert result["ok"] is True


def test_validate_typed_belief_update_rejects_signal_components_leak():
    payload = _tbu_payload()
    payload["signal_components"] = {"raw_scroll_distance": 1234}
    result = json.loads(handle_validate_typed_belief_update({"update": payload}))
    assert result["ok"] is False
    assert "signal_components" in result["error"]


def test_validate_typed_detector_composition_passes():
    result = json.loads(
        handle_validate_typed_detector_composition(
            {"panel": _panel_payload(), "update": _tbu_payload()}
        )
    )
    assert result["ok"] is True
    assert result["detector_type"] == "cognitive_load"


def test_validate_typed_detector_composition_rejects_unknown_type():
    result = json.loads(
        handle_validate_typed_detector_composition(
            {"panel": _panel_payload(), "update": _tbu_payload("sensory_load")}
        )
    )
    assert result["ok"] is False
    assert "not in panel" in result["error"]


def test_arbitrate_conflicting_updates_higher_priority_wins():
    result = json.loads(
        handle_arbitrate_conflicting_updates(
            {
                "panel": _panel_payload(),
                "updates": [
                    _tbu_payload("cognitive_load", "aaaaaaaa11111111"),
                    _tbu_payload("dignity", "bbbbbbbb22222222"),
                ],
            }
        )
    )
    assert result["ok"] is True
    assert result["detector_type"] == "dignity"


def test_arbitrate_conflicting_updates_rejects_non_conflicting_set():
    u1 = _tbu_payload("cognitive_load", "aaaaaaaa11111111")
    u2 = _tbu_payload("dignity", "bbbbbbbb22222222")
    u2["weight_key"] = "different.key"  # break conflict-key sharing
    result = json.loads(
        handle_arbitrate_conflicting_updates(
            {"panel": _panel_payload(), "updates": [u1, u2]}
        )
    )
    assert result["ok"] is False


def test_arbitrate_surfaces_offending_update_index_on_wd1_failure():
    """Pre-validation should report which update failed WD-1 by index."""
    u_ok = _tbu_payload("cognitive_load", "aaaaaaaa11111111")
    u_bad = _tbu_payload("not_on_panel", "bbbbbbbb22222222")
    result = json.loads(
        handle_arbitrate_conflicting_updates(
            {"panel": _panel_payload(), "updates": [u_ok, u_bad]}
        )
    )
    assert result["ok"] is False
    assert "updates[1]" in result["error"]
    assert "WD-1" in result["error"]


def test_validate_predictive_horizon_passes_within_window():
    prediction = {
        "id": "p-1",
        "agent_id": "agent-A",
        "detector_type": "cognitive_load",
        "predicted_delta": 0.3,
        "issued_at": "2026-04-25T12:00:00+00:00",
        "due_at": "2026-04-25T13:00:00+00:00",
    }
    realization = {
        "prediction_id": "p-1",
        "predicted_delta": 0.3,
        "realized_delta": 0.2,
        "realized_at": "2026-04-25T12:55:00+00:00",
    }
    result = json.loads(
        handle_validate_predictive_horizon(
            {"prediction": prediction, "realization": realization}
        )
    )
    assert result["ok"] is True


def test_validate_predictive_horizon_rejects_missing_realization():
    prediction = {
        "id": "p-1",
        "agent_id": "agent-A",
        "detector_type": "cognitive_load",
        "predicted_delta": 0.3,
        "issued_at": "2026-04-25T12:00:00+00:00",
        "due_at": "2026-04-25T13:00:00+00:00",
    }
    result = json.loads(
        handle_validate_predictive_horizon(
            {"prediction": prediction, "realization": None}
        )
    )
    assert result["ok"] is False
    assert "no matching realization" in result["error"]


def test_validate_detector_provenance_passes():
    result = json.loads(
        handle_validate_detector_provenance({"update": _tbu_payload()})
    )
    assert result["ok"] is True


def test_validate_detector_provenance_rejects_leaking_hash():
    result = json.loads(
        handle_validate_detector_provenance(
            {"update": _tbu_payload(provenance_hash="signal_components_xyz")}
        )
    )
    assert result["ok"] is False
    assert "leaks" in result["error"]
