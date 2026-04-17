# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Smoke tests for the five Phala primitives and the BU-Privacy validator."""

import pytest

from phala.types import (
    AdjustmentBounds,
    BeliefUpdate,
    ContextProfile,
    OutcomeEvent,
    PrincipalSatisfactionModel,
    ResolutionType,
    SatisfactionRecord,
    SatisfactionSource,
    WelfareTrace,
)
from phala.types.welfare_trace import CompletionTrend
from phala.validators import BeliefPrivacyError, validate_belief_privacy


def _outcome_event() -> OutcomeEvent:
    return OutcomeEvent(
        id="00000000-0000-4000-8000-000000000001",
        task_id="task-abc",
        agents_involved=["agent-a", "agent-b"],
        resolved_at="2026-04-16T10:00:00Z",
        resolution_type=ResolutionType.COMPLETED,
        latency_ms=12000,
        principal_id="p-001",
        session_hash="sha256:deadbeef",
    )


def test_outcome_event_immutable() -> None:
    oe = _outcome_event()
    with pytest.raises(Exception):
        oe.latency_ms = 999  # type: ignore[misc]


def test_outcome_event_rejects_empty_agents_involved() -> None:
    with pytest.raises(Exception):
        OutcomeEvent(
            id="00000000-0000-4000-8000-000000000002",
            task_id="task-x",
            agents_involved=[],
            resolved_at="2026-04-16T10:00:00Z",
            resolution_type=ResolutionType.COMPLETED,
            latency_ms=100,
            principal_id="p-001",
            session_hash="sha256:cafe",
        )


def test_satisfaction_record_valence_bounds() -> None:
    ok = SatisfactionRecord(
        id="sr-1",
        outcome_event_id="oe-1",
        valence=0.6,
        source=SatisfactionSource.IMPLICIT,
        signal_components={"completion_latency_ratio": 0.8},
        recorded_at="2026-04-16T10:00:10Z",
        confidence=0.9,
        psm_version="v1",
    )
    assert ok.valence == 0.6
    with pytest.raises(Exception):
        SatisfactionRecord(
            id="sr-2",
            outcome_event_id="oe-1",
            valence=1.5,  # out of [-1, 1]
            source=SatisfactionSource.IMPLICIT,
            signal_components={},
            recorded_at="2026-04-16T10:00:10Z",
            confidence=0.0,
        )


def test_belief_update_weight_delta_bounds() -> None:
    bu = BeliefUpdate(
        id="bu-1",
        satisfaction_record_id="sr-1",
        target_agent_id="agent-b",
        weight_key="routing.agent_b.preference",
        weight_delta=0.04,
        context_hash="sha256:feedface",
        valid_from="2026-04-16T10:00:10Z",
        ttl_seconds=3600,
    )
    assert bu.weight_delta == 0.04
    with pytest.raises(Exception):
        BeliefUpdate(
            id="bu-2",
            satisfaction_record_id="sr-1",
            target_agent_id="agent-b",
            weight_key="routing.agent_b.preference",
            weight_delta=2.0,  # out of [-1, 1]
            context_hash="sha256:feedface",
            valid_from="2026-04-16T10:00:10Z",
            ttl_seconds=3600,
        )


def test_adjustment_bounds_ordering() -> None:
    AdjustmentBounds(min=-1.0, max=1.0)
    with pytest.raises(Exception):
        AdjustmentBounds(min=1.0, max=-1.0)


def test_principal_satisfaction_model_context_profiles() -> None:
    psm = PrincipalSatisfactionModel(
        principal_id="p-001",
        version="v1",
        declared_at="2026-04-16T08:00:00Z",
        context_profiles={
            "travel": ContextProfile(
                context_key="travel",
                signal_weights={"completion_latency_ratio": 1.0},
                deadline_tolerance_seconds=3600,
                overdue_penalty_multiplier=2.0,
                explicit_rating_floor=2,
                welfare_lookback_days=30,
            )
        },
    )
    assert "travel" in psm.context_profiles
    assert psm.context_profiles["travel"].overdue_penalty_multiplier == 2.0


def test_welfare_trace_bounds() -> None:
    wt = WelfareTrace(
        principal_id="p-001",
        window_days=30,
        computed_at="2026-04-16T10:00:00Z",
        task_completion_trend=CompletionTrend.STABLE,
        agent_initiation_frequency_7d=14,
        overdue_rate_30d=0.1,
        autonomy_index=0.5,
        cognitive_load_proxy=1800.0,
        context_density_7d=4,
    )
    assert wt.autonomy_index == 0.5
    with pytest.raises(Exception):
        WelfareTrace(
            principal_id="p-001",
            window_days=30,
            computed_at="2026-04-16T10:00:00Z",
            task_completion_trend=CompletionTrend.STABLE,
            agent_initiation_frequency_7d=14,
            overdue_rate_30d=1.5,  # out of [0, 1]
            autonomy_index=0.5,
            cognitive_load_proxy=1800.0,
            context_density_7d=4,
        )


# BU-Privacy validator


def test_validate_belief_privacy_accepts_clean_payload() -> None:
    payload = {
        "id": "bu-1",
        "satisfaction_record_id": "sr-1",
        "target_agent_id": "agent-b",
        "weight_key": "routing.agent_b.preference",
        "weight_delta": 0.04,
        "context_hash": "sha256:feedface",
        "valid_from": "2026-04-16T10:00:10Z",
        "ttl_seconds": 3600,
    }
    validate_belief_privacy(payload)


def test_validate_belief_privacy_rejects_signal_components() -> None:
    payload = {
        "id": "bu-evil",
        "weight_delta": 0.04,
        "signal_components": {"completion_latency_ratio": 0.8},
    }
    with pytest.raises(BeliefPrivacyError) as exc:
        validate_belief_privacy(payload)
    assert "signal_components" in str(exc.value)


def test_validate_belief_privacy_rejects_raw_signals() -> None:
    payload = {"id": "bu-evil", "raw_signals": ["click"]}
    with pytest.raises(BeliefPrivacyError):
        validate_belief_privacy(payload)
