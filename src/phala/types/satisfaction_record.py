# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""SatisfactionRecord, the principal-authoritative quality signal (paper §3.2)."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class SatisfactionSource(str, Enum):
    """How the satisfaction signal was obtained."""

    IMPLICIT = "implicit"
    EXPLICIT = "explicit"


# SignalComponents is a free-form mapping from signal name to scalar value
# (e.g. {"completion_latency_ratio": 0.82, "engagement_quality": 0.9}).
# The exact vocabulary is implementation-defined; what matters is that
# the same keys appear in PrincipalSatisfactionModel.ContextProfile.signal_weights.
SignalComponents = Dict[str, float]


class SatisfactionRecord(BaseModel):
    """Encodes the quality of the outcome referenced by an OutcomeEvent.

    A SatisfactionRecord is the signal that distinguishes a task that
    completed from one that served the principal. It is produced either
    immediately from implicit behavioral signals or after an explicit
    principal interaction. See paper §3.2 and invariants SR-1 (confidence
    zero when no evidence) and SR-2 (PSM-first valence computation).
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    id: str = Field(..., description="UUID v4")
    outcome_event_id: str = Field(
        ..., description="Reference to the OutcomeEvent this quality signal applies to"
    )
    valence: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description="Aggregate quality signal in [-1.0, 1.0]",
    )
    timing_quality: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Sub-signal for time-sensitive tasks in [0.0, 1.0]",
    )
    recommendation_quality: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Sub-signal for recommendation tasks in [0.0, 1.0]",
    )
    source: SatisfactionSource
    signal_components: SignalComponents = Field(
        default_factory=dict,
        description=(
            "Key-value map of raw signals from which valence is derived. "
            "Per BU-1 this map MUST NOT appear on any BeliefUpdate."
        ),
    )
    recorded_at: str = Field(..., description="ISO 8601 timestamp")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Reliability of the valence estimate. Per SR-1, MUST be 0.0 when "
            "signal_components is empty."
        ),
    )
    psm_version: Optional[str] = Field(
        default=None,
        description=(
            "Version of the PrincipalSatisfactionModel used to compute "
            "valence. Null means the reference formula was used."
        ),
    )
