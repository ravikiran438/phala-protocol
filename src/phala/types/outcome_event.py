# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""OutcomeEvent, the objective facts of a task's resolution (paper §3.1)."""

from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class ResolutionType(str, Enum):
    """Terminal state of a task at the moment the OutcomeEvent is produced."""

    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ESCALATED = "escalated"
    OVERDUE = "overdue"
    DEFERRED = "deferred"


class OutcomeEvent(BaseModel):
    """Records the objective facts of a task reaching a terminal state.

    Produced by the agent closest to the principal immediately after a
    task resolves. An OutcomeEvent carries no subjective quality signal;
    that role belongs to SatisfactionRecord. See paper §3.1 for the
    complete specification and invariants OE-1 (uniqueness) and OE-2
    (ordering).
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    id: str = Field(..., description="UUID v4 for this event")
    task_id: str = Field(
        ..., description="A2A task identifier or MCP tool call identifier"
    )
    agents_involved: List[str] = Field(
        ...,
        min_length=1,
        description=(
            "Ordered list of agent identifiers, shallowest first. "
            "Drives the participation-weighted update rule (OE-2)."
        ),
    )
    resolved_at: str = Field(..., description="ISO 8601 timestamp of resolution")
    resolution_type: ResolutionType
    latency_ms: int = Field(
        ..., ge=0, description="Elapsed time from submission to terminal state"
    )
    principal_id: str = Field(
        ...,
        description=(
            "Opaque internal reference to the principal. MUST NOT be PII."
        ),
    )
    session_hash: str = Field(
        ...,
        description=(
            "SHA-256 of the session context. Enables correlation without "
            "exfiltrating session content."
        ),
    )
