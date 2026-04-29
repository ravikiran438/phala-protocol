# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for the welfare-detector panel extension (WD-1..WD-4)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from phala.extensions.welfare_detectors import (
    DetectorPanel,
    MissingRealization,
    TypedBeliefUpdate,
    WelfareDetector,
    WelfareDetectorError,
    WelfarePrediction,
    WelfareRealization,
    arbitrate_conflicting_updates,
    check_arbitration_determinism,
    check_detector_provenance,
    check_predictive_horizon,
    check_typed_detector_composition,
    emit_missing_realization,
)


def _panel(
    consumer_agent_id: str = "agent-target",
    detectors: list[tuple[str, int]] | None = None,
) -> DetectorPanel:
    detectors = detectors or [
        ("cognitive_load", 10),
        ("autonomy", 20),
        ("dignity", 30),
    ]
    return DetectorPanel(
        consumer_agent_id=consumer_agent_id,
        detectors=[
            WelfareDetector(detector_type=t, priority=p) for t, p in detectors
        ],
    )


def _tbu(
    detector_type: str = "cognitive_load",
    target_agent_id: str = "agent-target",
    weight_key: str = "routing.preference",
    valid_from: str = "2026-04-25T12:00:00+00:00",
    weight_delta: float = 0.1,
    provenance_hash: str = "abcdef0123456789",
    id: str | None = None,
) -> TypedBeliefUpdate:
    return TypedBeliefUpdate(
        id=id or str(uuid4()),
        satisfaction_record_id=str(uuid4()),
        target_agent_id=target_agent_id,
        weight_key=weight_key,
        weight_delta=weight_delta,
        context_hash="0" * 64,
        valid_from=valid_from,
        ttl_seconds=3600,
        detector_type=detector_type,
        provenance_hash=provenance_hash,
    )


# ─────────────────────────────────────────────────────────────────────
# WD-1 Typed Detector Composition
# ─────────────────────────────────────────────────────────────────────


class TestTypedDetectorComposition:
    def test_known_type_passes(self):
        panel = _panel()
        check_typed_detector_composition(panel, _tbu("cognitive_load"))

    def test_unknown_type_rejected(self):
        panel = _panel()
        with pytest.raises(WelfareDetectorError, match="not in panel"):
            check_typed_detector_composition(panel, _tbu("sensory_load"))

    def test_wrong_target_rejected(self):
        panel = _panel(consumer_agent_id="agent-A")
        with pytest.raises(WelfareDetectorError, match="targets"):
            check_typed_detector_composition(
                panel, _tbu(target_agent_id="agent-B")
            )

    def test_panel_rejects_duplicate_types(self):
        with pytest.raises(ValueError, match="declared twice"):
            DetectorPanel(
                consumer_agent_id="a",
                detectors=[
                    WelfareDetector(detector_type="x", priority=1),
                    WelfareDetector(detector_type="x", priority=2),
                ],
            )


# ─────────────────────────────────────────────────────────────────────
# WD-2 Arbitration Determinism
# ─────────────────────────────────────────────────────────────────────


class TestArbitrationDeterminism:
    def test_higher_priority_wins(self):
        panel = _panel()
        cog = _tbu("cognitive_load", provenance_hash="aaaaaaaaaaaa")
        dig = _tbu("dignity", provenance_hash="bbbbbbbbbbbb")
        winner = arbitrate_conflicting_updates(panel, [cog, dig])
        assert winner.id == dig.id  # dignity priority=30 > cognitive_load=10

    def test_tie_broken_by_lower_provenance_hash(self):
        panel = _panel(detectors=[("a", 5), ("b", 5)])
        u1 = _tbu("a", provenance_hash="aaaaaaaa11111111")
        u2 = _tbu("b", provenance_hash="bbbbbbbb22222222")
        winner = arbitrate_conflicting_updates(panel, [u1, u2])
        assert winner.id == u1.id  # lower phash wins on ties

    def test_arbitration_requires_shared_conflict_key(self):
        panel = _panel()
        u1 = _tbu("cognitive_load", weight_key="w1")
        u2 = _tbu("dignity", weight_key="w2")
        with pytest.raises(WelfareDetectorError, match="share"):
            arbitrate_conflicting_updates(panel, [u1, u2])

    def test_arbitration_empty_set_rejected(self):
        with pytest.raises(WelfareDetectorError, match="empty"):
            arbitrate_conflicting_updates(_panel(), [])

    def test_audit_check_passes_when_correct_winner_applied(self):
        panel = _panel()
        cog = _tbu("cognitive_load", provenance_hash="aaaaaaaa")
        dig = _tbu("dignity", provenance_hash="bbbbbbbb")
        check_arbitration_determinism(panel, [cog, dig], applied=dig)

    def test_audit_check_fails_when_wrong_winner_applied(self):
        panel = _panel()
        cog = _tbu("cognitive_load", provenance_hash="aaaaaaaa")
        dig = _tbu("dignity", provenance_hash="bbbbbbbb")
        with pytest.raises(WelfareDetectorError, match="not the deterministic"):
            check_arbitration_determinism(panel, [cog, dig], applied=cog)


# ─────────────────────────────────────────────────────────────────────
# WD-3 Predictive Welfare Horizon
# ─────────────────────────────────────────────────────────────────────


class TestPredictiveHorizon:
    def _prediction(self, predicted_delta: float = 0.3) -> WelfarePrediction:
        now = datetime.now(timezone.utc)
        return WelfarePrediction(
            id="p-1",
            agent_id="agent-A",
            detector_type="cognitive_load",
            predicted_delta=predicted_delta,
            issued_at=now,
            due_at=now + timedelta(hours=1),
        )

    def test_realization_within_horizon_passes(self):
        p = self._prediction(predicted_delta=0.3)
        r = WelfareRealization.from_prediction(
            p, realized_delta=0.2, realized_at=p.due_at - timedelta(minutes=1)
        )
        check_predictive_horizon(p, r)
        assert abs(r.error - 0.1) < 1e-9  # computed property

    def test_factory_copies_predicted_delta_from_prediction(self):
        p = self._prediction(predicted_delta=0.42)
        r = WelfareRealization.from_prediction(
            p, realized_delta=0.1, realized_at=p.due_at - timedelta(minutes=1)
        )
        assert r.predicted_delta == 0.42
        assert r.prediction_id == p.id

    def test_missing_realization_rejected(self):
        p = self._prediction()
        with pytest.raises(WelfareDetectorError, match="no matching realization"):
            check_predictive_horizon(p, None)

    def test_late_realization_rejected(self):
        p = self._prediction()
        r = WelfareRealization(
            prediction_id="p-1",
            predicted_delta=0.3,
            realized_delta=0.2,
            realized_at=p.due_at + timedelta(hours=2),
        )
        with pytest.raises(WelfareDetectorError, match="after due_at"):
            check_predictive_horizon(p, r)

    def test_grace_period_allows_modest_lateness(self):
        p = self._prediction()
        r = WelfareRealization(
            prediction_id="p-1",
            predicted_delta=0.3,
            realized_delta=0.2,
            realized_at=p.due_at + timedelta(seconds=30),
        )
        check_predictive_horizon(p, r, horizon_grace_seconds=60)

    def test_mismatched_prediction_id_rejected(self):
        p = self._prediction()
        r = WelfareRealization(
            prediction_id="p-other",
            predicted_delta=0.3,
            realized_delta=0.2,
            realized_at=p.due_at - timedelta(minutes=1),
        )
        with pytest.raises(WelfareDetectorError, match="does not match"):
            check_predictive_horizon(p, r)

    def test_mismatched_predicted_delta_rejected(self):
        p = self._prediction(predicted_delta=0.3)
        r = WelfareRealization(
            prediction_id="p-1",
            predicted_delta=0.5,  # disagrees with prediction's 0.3
            realized_delta=0.2,
            realized_at=p.due_at - timedelta(minutes=1),
        )
        with pytest.raises(WelfareDetectorError, match="predicted_delta"):
            check_predictive_horizon(p, r)

    def test_error_is_computed_not_stored(self):
        r = WelfareRealization(
            prediction_id="p-1",
            predicted_delta=0.4,
            realized_delta=0.1,
            realized_at=datetime.now(timezone.utc),
        )
        assert abs(r.error - 0.3) < 1e-9
        # Cannot pass `error` as input — computed only
        with pytest.raises(ValueError):
            WelfareRealization(
                prediction_id="p-1",
                predicted_delta=0.4,
                realized_delta=0.1,
                realized_at=datetime.now(timezone.utc),
                error=99.0,  # type: ignore[call-arg]
            )


# ─────────────────────────────────────────────────────────────────────
# WD-3 helper: emit_missing_realization
# ─────────────────────────────────────────────────────────────────────


class TestMissingRealization:
    def test_no_event_before_due(self):
        now = datetime.now(timezone.utc)
        p = WelfarePrediction(
            id="p",
            agent_id="a",
            detector_type="cognitive_load",
            predicted_delta=0.2,
            issued_at=now,
            due_at=now + timedelta(hours=1),
        )
        assert emit_missing_realization(p, detected_at=now) is None

    def test_event_emitted_after_due_plus_grace(self):
        now = datetime.now(timezone.utc)
        p = WelfarePrediction(
            id="p",
            agent_id="a",
            detector_type="cognitive_load",
            predicted_delta=0.2,
            issued_at=now,
            due_at=now + timedelta(minutes=10),
        )
        ev = emit_missing_realization(
            p,
            detected_at=now + timedelta(minutes=15),
            horizon_grace_seconds=60,
        )
        assert isinstance(ev, MissingRealization)
        assert ev.prediction_id == "p"
        assert ev.predicted_delta == 0.2

    def test_grace_window_suppresses_event(self):
        now = datetime.now(timezone.utc)
        p = WelfarePrediction(
            id="p",
            agent_id="a",
            detector_type="cognitive_load",
            predicted_delta=0.2,
            issued_at=now,
            due_at=now + timedelta(minutes=10),
        )
        # Detected 30s after due, but grace is 60s — no event yet.
        ev = emit_missing_realization(
            p,
            detected_at=now + timedelta(minutes=10, seconds=30),
            horizon_grace_seconds=60,
        )
        assert ev is None


# ─────────────────────────────────────────────────────────────────────
# WD-4 Detector Provenance Disclosure
# ─────────────────────────────────────────────────────────────────────


class TestDetectorProvenance:
    def test_valid_provenance_passes(self):
        check_detector_provenance(_tbu(provenance_hash="0123456789abcdef"))

    def test_missing_provenance_rejected(self):
        with pytest.raises(ValueError):
            _tbu(provenance_hash="")

    def test_short_provenance_rejected_by_validator(self):
        with pytest.raises(ValueError):
            _tbu(provenance_hash="abcd")

    def test_provenance_leaking_signal_components_rejected(self):
        with pytest.raises(WelfareDetectorError, match="leaks"):
            check_detector_provenance(
                _tbu(provenance_hash="signal_components_xyz")
            )

    def test_provenance_leaking_raw_signals_rejected(self):
        with pytest.raises(WelfareDetectorError, match="leaks"):
            check_detector_provenance(
                _tbu(provenance_hash="rAw_SiGnAlS_data_here")
            )


# ─────────────────────────────────────────────────────────────────────
# Type-level sanity
# ─────────────────────────────────────────────────────────────────────


class TestTypes:
    def test_typed_belief_update_inherits_phala_bu_constraints(self):
        with pytest.raises(ValueError):
            _tbu(weight_delta=2.0)

    def test_panel_priority_lookup(self):
        panel = _panel()
        assert panel.priority_of("cognitive_load") == 10
        assert panel.priority_of("autonomy") == 20
        assert panel.priority_of("does-not-exist") is None
        assert panel.knows("dignity") is True
        assert panel.knows("does-not-exist") is False

    def test_prediction_due_must_follow_issue(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="due_at must be after"):
            WelfarePrediction(
                id="p",
                agent_id="a",
                detector_type="cognitive_load",
                predicted_delta=0.1,
                issued_at=now,
                due_at=now,
            )
