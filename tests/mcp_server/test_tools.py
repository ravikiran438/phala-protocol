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
    handle_validate_belief_privacy,
    handle_validate_belief_update,
    handle_validate_outcome_event,
    handle_validate_principal_satisfaction_model,
    handle_validate_satisfaction_record,
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
