# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""WelfareTrace, the on-device longitudinal welfare signal (paper §3.6)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CompletionTrend(str, Enum):
    """Slope of the completion rate over the declared welfare window."""

    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"


class WelfareTrace(BaseModel):
    """On-device longitudinal welfare signal for a principal.

    WelfareTrace addresses a question that per-task SatisfactionRecord
    cannot answer: is this agent system making the principal's life
    better or worse over time? It measures cognitive load, autonomy, and
    completion trend, and modulates the effective learning rate of the
    entire network accordingly. See paper §3.6 and invariants WT-1 (never
    transmitted) and WT-2 (welfare_adjustment clipped to [0.1, 2.0]).
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    principal_id: str = Field(..., description="Opaque internal principal reference")
    window_days: int = Field(
        ..., gt=0, description="Observation window for the computation"
    )
    computed_at: str = Field(..., description="ISO 8601 timestamp of computation")
    task_completion_trend: CompletionTrend = Field(
        ..., description="Slope of completion rate over window_days"
    )
    agent_initiation_frequency_7d: int = Field(
        ...,
        ge=0,
        description=(
            "Count of agent-initiated interactions (notifications, "
            "recommendations, prompts) in the past 7 days."
        ),
    )
    overdue_rate_30d: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of tasks that became overdue in the past 30 days",
    )
    autonomy_index: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Fraction of completions classified as principal_autonomous "
            "under the three-way taxonomy (agent_driven, agent_prompted, "
            "principal_autonomous). A rising autonomy_index indicates "
            "the principal is acting more independently."
        ),
    )
    cognitive_load_proxy: float = Field(
        ...,
        ge=0.0,
        description=(
            "Median time-to-respond in milliseconds over the past 30 days. "
            "A rising ratio against a baseline signals fatigue or "
            "disengagement."
        ),
    )
    context_density_7d: int = Field(
        ...,
        ge=0,
        description=(
            "Count of distinct task contexts active in the past 7 days. "
            "Distinguishes legitimate busyness from cognitive fatigue in "
            "the welfare_adjustment computation."
        ),
    )
