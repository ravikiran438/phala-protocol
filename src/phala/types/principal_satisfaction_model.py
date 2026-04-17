# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""PrincipalSatisfactionModel, the primitive that closes the welfare inversion (paper §3.4)."""

from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, ConfigDict, Field


class ContextProfile(BaseModel):
    """Per-context preferences declared by the principal.

    Each ContextProfile carries the principal's signal weights, deadline
    tolerance, overdue penalty multiplier, explicit-rating floor, and
    WelfareTrace lookback window for a specific interaction context (e.g.
    ``"travel"``, ``"time_sensitive_duties"``, ``"financial"``).
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    context_key: str = Field(..., description="Context identifier")
    signal_weights: Dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Weight map over the keys appearing in SatisfactionRecord."
            "signal_components for this context. Weights sum to 1.0."
        ),
    )
    deadline_tolerance_seconds: int = Field(
        ...,
        ge=0,
        description="Acceptable latency buffer before a task is considered late",
    )
    overdue_penalty_multiplier: float = Field(
        ...,
        gt=0.0,
        description=(
            "Scales the negative valence signal for overdue tasks. "
            "Principal-declared, may be greater or less than 1.0."
        ),
    )
    explicit_rating_floor: int = Field(
        ...,
        description=(
            "Minimum explicit rating the principal would accept as "
            "neutral. Accommodates principals who systematically rate low."
        ),
    )
    welfare_lookback_days: int = Field(
        ...,
        gt=0,
        description="Window for WelfareTrace computation (see §3.6)",
    )


class PrincipalSatisfactionModel(BaseModel):
    """Per-principal, per-context declaration of what *good* means.

    The PSM is authored and controlled exclusively by the principal. No
    remote agent may write or modify a PSM; agents receiving a
    SatisfactionRecord whose psm_version is set MUST treat the valence as
    principal-authoritative (PSM-1). PSM versions are immutable and
    append-only (PSM-2): a new declaration creates a new version rather
    than overwriting a previous one, preserving the audit trail of the
    principal's evolving preferences.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    principal_id: str = Field(..., description="Opaque internal principal reference")
    version: str = Field(..., description="Monotonic version string for this PSM")
    declared_at: str = Field(..., description="ISO 8601 timestamp of declaration")
    context_profiles: Dict[str, ContextProfile] = Field(
        default_factory=dict,
        description="Map from context_key to ContextProfile",
    )
