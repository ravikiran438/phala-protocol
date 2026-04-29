# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Runtime validators for the welfare-detector invariants (WD-1 through WD-4)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from .types import (
    DetectorPanel,
    MissingRealization,
    TypedBeliefUpdate,
    WelfarePrediction,
    WelfareRealization,
)


class WelfareDetectorError(ValueError):
    """Raised when a welfare-detector safety invariant is violated."""


# ─────────────────────────────────────────────────────────────────────
# WD-1 Typed Detector Composition
# ─────────────────────────────────────────────────────────────────────


def check_typed_detector_composition(
    panel: DetectorPanel, update: TypedBeliefUpdate
) -> None:
    """WD-1. Reject any TBU whose detector_type is not on the consumer's panel."""
    if update.target_agent_id != panel.consumer_agent_id:
        raise WelfareDetectorError(
            f"TBU targets '{update.target_agent_id}' but panel is for "
            f"'{panel.consumer_agent_id}'"
        )
    if not panel.knows(update.detector_type):
        raise WelfareDetectorError(
            f"detector_type '{update.detector_type}' not in panel for "
            f"'{panel.consumer_agent_id}'; reject per WD-1"
        )


# ─────────────────────────────────────────────────────────────────────
# WD-2 Arbitration Determinism
# ─────────────────────────────────────────────────────────────────────


def _conflict_key(u: TypedBeliefUpdate) -> tuple[str, str, str]:
    return (u.target_agent_id, u.weight_key, u.valid_from)


def arbitrate_conflicting_updates(
    panel: DetectorPanel, updates: Iterable[TypedBeliefUpdate]
) -> TypedBeliefUpdate:
    """WD-2. Among TBUs sharing (target_agent_id, weight_key, valid_from),
    return the unique winner: highest priority, ties broken by lower
    provenance_hash (lexicographic).
    """
    items = list(updates)
    if not items:
        raise WelfareDetectorError("cannot arbitrate empty update set")

    keys = {_conflict_key(u) for u in items}
    if len(keys) != 1:
        raise WelfareDetectorError(
            "arbitrate_conflicting_updates expects updates that share "
            f"(target_agent_id, weight_key, valid_from); got {keys}"
        )

    def sort_key(u: TypedBeliefUpdate) -> tuple[int, str]:
        priority = panel.priority_of(u.detector_type)
        if priority is None:
            raise WelfareDetectorError(
                f"detector_type '{u.detector_type}' not in panel "
                f"during arbitration (WD-1 must hold first)"
            )
        # Higher priority wins; for stable sort we negate, so smallest
        # tuple first means winner.
        return (-priority, u.provenance_hash)

    items.sort(key=sort_key)
    return items[0]


def check_arbitration_determinism(
    panel: DetectorPanel,
    updates: Iterable[TypedBeliefUpdate],
    applied: TypedBeliefUpdate,
) -> None:
    """WD-2 (audit). Verify ``applied`` is the deterministic winner of ``updates``."""
    winner = arbitrate_conflicting_updates(panel, updates)
    if winner.id != applied.id:
        raise WelfareDetectorError(
            f"applied TBU id={applied.id} is not the deterministic winner; "
            f"expected id={winner.id} (WD-2)"
        )


# ─────────────────────────────────────────────────────────────────────
# WD-3 Predictive Welfare Horizon
# ─────────────────────────────────────────────────────────────────────


def check_predictive_horizon(
    prediction: WelfarePrediction,
    realization: WelfareRealization | None,
    horizon_grace_seconds: int = 0,
) -> None:
    """WD-3. A prediction past due_at MUST have a matching realization.

    ``horizon_grace_seconds`` lets a deployment allow modest delay
    before flagging a missing realization; default is 0 (strict).
    """
    if realization is None:
        raise WelfareDetectorError(
            f"prediction {prediction.id} has no matching realization (WD-3)"
        )
    if realization.prediction_id != prediction.id:
        raise WelfareDetectorError(
            f"realization.prediction_id={realization.prediction_id} does not "
            f"match prediction.id={prediction.id} (WD-3)"
        )
    if abs(realization.predicted_delta - prediction.predicted_delta) > 1e-6:
        raise WelfareDetectorError(
            f"realization.predicted_delta={realization.predicted_delta} does "
            f"not match prediction.predicted_delta={prediction.predicted_delta} "
            f"(WD-3)"
        )
    grace = prediction.due_at + timedelta(seconds=horizon_grace_seconds)
    if realization.realized_at > grace:
        raise WelfareDetectorError(
            f"realization arrived at {realization.realized_at.isoformat()}, "
            f"after due_at + grace = {grace.isoformat()} (WD-3)"
        )


# ─────────────────────────────────────────────────────────────────────
# WD-4 Detector Provenance Disclosure
# ─────────────────────────────────────────────────────────────────────

# Substrings that MUST NOT appear in a provenance_hash. The hash must
# be a fingerprint, not a leakage vector for signal_components content.
FORBIDDEN_PROVENANCE_SUBSTRINGS: frozenset[str] = frozenset(
    {
        "signal_components",
        "raw_signals",
        "behavioural_signals",
        "behavioral_signals",
    }
)


def emit_missing_realization(
    prediction: WelfarePrediction,
    detected_at: datetime,
    horizon_grace_seconds: int = 0,
) -> MissingRealization | None:
    """WD-3 helper. If the prediction's due_at + grace has passed and no
    WelfareRealization is paired, return a MissingRealization event. The
    caller is expected to track which predictions still lack realizations
    and call this for the stragglers.
    """
    grace = prediction.due_at + timedelta(seconds=horizon_grace_seconds)
    if detected_at <= grace:
        return None
    return MissingRealization(
        prediction_id=prediction.id,
        agent_id=prediction.agent_id,
        detector_type=prediction.detector_type,
        predicted_delta=prediction.predicted_delta,
        due_at=prediction.due_at,
        detected_at=detected_at,
    )


def check_detector_provenance(update: TypedBeliefUpdate) -> None:
    """WD-4. Every TBU MUST carry a provenance_hash that is non-empty
    and does not encode forbidden privacy fields. The actual hash format
    is implementation-defined (typically SHA-256 hex); this validator
    enforces non-leakage and presence.
    """
    if not update.provenance_hash or len(update.provenance_hash) < 8:
        raise WelfareDetectorError(
            f"TBU id={update.id} missing or too-short provenance_hash (WD-4)"
        )
    lowered = update.provenance_hash.lower()
    for needle in FORBIDDEN_PROVENANCE_SUBSTRINGS:
        if needle in lowered:
            raise WelfareDetectorError(
                f"provenance_hash leaks forbidden field '{needle}' "
                f"(WD-4 + BU-Privacy)"
            )
