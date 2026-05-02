# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""PhalaServiceRef: the Phala service descriptor on an A2A AgentCard.

This is the typed payload of the entry whose ``uri`` equals
``PHALA_EXTENSION_URI`` inside ``AgentCard.capabilities.extensions[]``.
Modeled after ACAP's ``UsagePolicyRef``: a small, declarative reference
that tells callers where the Phala data plane lives and what version
this agent implements.

Tells callers (and third-party validators) where to deliver each of the
three Phala wire artefacts (OutcomeEvent, SatisfactionRecord,
BeliefUpdate) and the agent's per-weight clipping bounds + base
learning rate.

Until this module existed, ``belief_update_endpoint`` was undefined: the
paper said "agents accept BeliefUpdates" but the AgentCard advertised no
discoverable URL. Added here as a REQUIRED field so a third-party
validator can confirm an agent that declares Phala support is willing to
receive the BeliefUpdates the protocol depends on.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from phala.types.belief_update import AdjustmentBounds


# Stable identifier published on AgentCard.capabilities.extensions[].uri.
PHALA_EXTENSION_URI = "https://ravikiran438.github.io/phala-protocol/v1"


class PhalaServiceRef(BaseModel):
    """Phala-specific fields contributed to an A2A AgentCard.

    Validators detect Phala support by the presence of an entry in
    ``capabilities.extensions[]`` whose ``uri`` equals ``PHALA_EXTENSION_URI``.
    The body of that entry SHOULD deserialize to this model.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    version: str = Field(
        ...,
        description="Phala protocol semver this agent implements (e.g. '1.0.0').",
    )

    outcome_endpoint: str = Field(
        ...,
        description=(
            "HTTPS URL where OutcomeEvents originating from this agent are "
            "POSTed. Read-back endpoint per OE-1 (every terminal task MUST "
            "produce exactly one OutcomeEvent)."
        ),
    )
    satisfaction_endpoint: str = Field(
        ...,
        description=(
            "HTTPS URL where SatisfactionRecords are POSTed for outcomes "
            "produced by this agent."
        ),
    )
    belief_update_endpoint: str = Field(
        ...,
        description=(
            "HTTPS URL where BeliefUpdates targeting this agent are POSTed. "
            "REQUIRED so peers can deliver the propagated weight deltas the "
            "Phala learning loop depends on. Per BU-3 the agent MAY ignore "
            "individual updates, but the endpoint MUST exist and accept POST."
        ),
    )

    weight_keys: list[str] = Field(
        ...,
        description=(
            "Stable namespace of weight keys this agent will accept on a "
            "BeliefUpdate. Updates targeting unknown keys MAY be discarded."
        ),
    )

    learning_rate: float = Field(
        ...,
        gt=0.0,
        le=1.0,
        description=(
            "Base learning rate applied to BeliefUpdates this agent emits. "
            "Effective rate is modulated by the agent's WelfareTrace per WT-2."
        ),
    )
    weight_bounds: AdjustmentBounds = Field(
        ...,
        description=(
            "Per-weight clipping range for ``weight_delta``. All emitted "
            "BeliefUpdates MUST land within these bounds."
        ),
    )
