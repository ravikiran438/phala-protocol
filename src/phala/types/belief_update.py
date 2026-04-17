# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""BeliefUpdate, the scalar weight adjustment propagated through the network (paper §3.3)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AdjustmentBounds(BaseModel):
    """Declared minimum and maximum for a weight, for Update-Boundedness."""

    model_config = ConfigDict(frozen=True)

    min: float = Field(..., description="Minimum allowed weight value")
    max: float = Field(..., description="Maximum allowed weight value")

    @model_validator(mode="after")
    def _min_le_max(self) -> "AdjustmentBounds":
        if self.min > self.max:
            raise ValueError("AdjustmentBounds.min must be <= max")
        return self


class BeliefUpdate(BaseModel):
    """Local weight adjustment a participating agent should apply.

    This is the mechanism by which outcome quality propagates back through
    the agent network. See paper §3.3 and invariants BU-1 (privacy: no
    signal_components fields), BU-2 (one per agent per SatisfactionRecord),
    BU-3 (advisory: agents MAY ignore), BU-4 (TTL expiry).
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    id: str = Field(..., description="UUID v4")
    satisfaction_record_id: str = Field(
        ..., description="Reference to the SatisfactionRecord that produced this update"
    )
    target_agent_id: str = Field(
        ..., description="The agent whose local model should apply this update"
    )
    weight_key: str = Field(
        ...,
        description=(
            "Identifies the specific weight within the target agent's model, "
            "e.g. 'routing.agent_b.preference'."
        ),
    )
    weight_delta: float = Field(
        ...,
        ge=-1.0,
        le=1.0,
        description=(
            "Signed scalar adjustment in [-1.0, 1.0]. Per BU-1 this is the "
            "only quality-derived field transmitted."
        ),
    )
    context_hash: str = Field(
        ...,
        description=(
            "SHA-256 of the task context, allowing agents to apply updates "
            "only to the relevant context partition."
        ),
    )
    valid_from: str = Field(
        ..., description="ISO 8601 timestamp; the earliest applicable time"
    )
    ttl_seconds: int = Field(
        ...,
        gt=0,
        description=(
            "Expiry window from valid_from. Per BU-4, updates arriving after "
            "expiry MUST be discarded."
        ),
    )
