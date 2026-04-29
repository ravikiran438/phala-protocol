# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Pydantic types for the welfare-detector panel extension to Phala.

Reference: extensions/welfare_detectors/README.md and WelfareDetectors.tla.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from phala.types.belief_update import BeliefUpdate


class WelfareDetector(BaseModel):
    """A typed welfare detector declared by an agent's panel.

    A detector represents one channel of the principal's welfare signal,
    e.g. cognitive load, autonomy preservation, dignity, social
    connection, pace, or sensory load. Each is distinct; each may
    target a different weight in the consumer agent's local model.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    detector_type: str = Field(
        ...,
        min_length=1,
        description=(
            "Identifier of the detector type, e.g. 'cognitive_load' or "
            "'dignity'. Free-form within a deployment; the panel "
            "registers which types it accepts."
        ),
    )
    priority: int = Field(
        ...,
        ge=0,
        description=(
            "Arbitration priority. Higher wins when two TypedBeliefUpdates "
            "target the same (target_agent_id, weight_key, valid_from)."
        ),
    )
    description: Optional[str] = Field(
        default=None, description="Human-readable purpose of the detector"
    )


class DetectorPanel(BaseModel):
    """Consumer-side declaration of which detector types an agent accepts.

    A receiving agent's panel is authoritative: incoming TypedBeliefUpdates
    whose detector_type is not registered here MUST be rejected (I-1).
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    consumer_agent_id: str = Field(..., min_length=1)
    detectors: list[WelfareDetector] = Field(min_length=1)
    panel_version: str = Field(default="1")

    @model_validator(mode="after")
    def _types_unique(self) -> "DetectorPanel":
        seen: set[str] = set()
        for d in self.detectors:
            if d.detector_type in seen:
                raise ValueError(
                    f"detector_type '{d.detector_type}' declared twice in panel"
                )
            seen.add(d.detector_type)
        return self

    def priority_of(self, detector_type: str) -> Optional[int]:
        """Return the registered priority for a type, or None if unknown."""
        for d in self.detectors:
            if d.detector_type == detector_type:
                return d.priority
        return None

    def knows(self, detector_type: str) -> bool:
        return self.priority_of(detector_type) is not None


class TypedBeliefUpdate(BeliefUpdate):
    """A BeliefUpdate carrying detector_type and provenance_hash.

    Inherits all Phala Core BU fields plus the BU-1 privacy guarantee:
    provenance_hash MUST be a fingerprint of the detector instance, not
    a leak of signal_components content.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    detector_type: str = Field(
        ..., min_length=1, description="MUST appear in consumer's DetectorPanel (WD-1)"
    )
    provenance_hash: str = Field(
        ...,
        min_length=8,
        description=(
            "Detector-instance fingerprint for audit. MUST NOT encode "
            "signal_components content (WD-4 + BU-Privacy)."
        ),
    )


class WelfarePrediction(BaseModel):
    """An agent's predicted welfare delta over a declared horizon.

    Pairs with a WelfareRealization on or before due_at + MaxHorizon.
    Missing realizations indicate the agent stopped tracking and are
    themselves a welfare-relevant signal (WD-3).
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    id: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    detector_type: str = Field(..., min_length=1)
    predicted_delta: float = Field(..., ge=-1.0, le=1.0)
    issued_at: datetime
    due_at: datetime

    @model_validator(mode="after")
    def _due_after_issue(self) -> "WelfarePrediction":
        if self.due_at <= self.issued_at:
            raise ValueError("due_at must be after issued_at")
        return self


class WelfareRealization(BaseModel):
    """Observed welfare delta paired to a prior WelfarePrediction.

    The realization mirrors `predicted_delta` from the paired
    `WelfarePrediction` so it stays self-contained for audit. To
    guarantee the mirrored value matches the original prediction at
    construction time, prefer ``WelfareRealization.from_prediction()``
    over the raw constructor — the factory is the structural way to
    avoid mismatch.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, extra="forbid")

    prediction_id: str = Field(..., min_length=1)
    predicted_delta: float = Field(
        ..., ge=-1.0, le=1.0,
        description="Mirrored from the paired WelfarePrediction for self-contained audit",
    )
    realized_delta: float = Field(..., ge=-1.0, le=1.0)
    realized_at: datetime

    @classmethod
    def from_prediction(
        cls,
        prediction: "WelfarePrediction",
        *,
        realized_delta: float,
        realized_at: datetime,
    ) -> "WelfareRealization":
        """Preferred constructor: copies prediction_id and predicted_delta
        from the prediction so consistency is structural, not validated.
        """
        return cls(
            prediction_id=prediction.id,
            predicted_delta=prediction.predicted_delta,
            realized_delta=realized_delta,
            realized_at=realized_at,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def error(self) -> float:
        """Prediction-error signal: predicted_delta - realized_delta."""
        return self.predicted_delta - self.realized_delta


class MissingRealization(BaseModel):
    """Auto-emitted when a WelfarePrediction's horizon elapses without a
    matching WelfareRealization. Itself a welfare-relevant signal: the
    agent stopped tracking what it predicted.

    Downstream agents subscribe to this type rather than scanning
    prediction tables for stragglers.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    prediction_id: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    detector_type: str = Field(..., min_length=1)
    predicted_delta: float = Field(..., ge=-1.0, le=1.0)
    due_at: datetime
    detected_at: datetime
