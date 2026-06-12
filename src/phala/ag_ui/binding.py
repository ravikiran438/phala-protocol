# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""AG-UI binding for Phala (principal-declared welfare feedback).

AG-UI (the Agent-User Interaction protocol) is the agent <-> human-app
transport, alongside A2A (agent <-> agent) and MCP (agent <-> tools). A Phala
satisfaction signal *originates from the human*, so AG-UI is its natural
transport. This module captures that signal over AG-UI under the cross-cutting
"Governance over AG-UI" convention, via two paths:

  * **Prompted** -- an end-of-task **interrupt** ("did this serve you?"),
    ``reason: "input_required"``; the principal's resume payload (a valence in
    [-1, 1]) becomes a typed ``SatisfactionRecord``.
  * **Volunteered** -- a ``MetaEvent`` (``thumbs_up`` / rating / tag) the human
    offers unprompted, mapped to a ``SatisfactionRecord``.

The ``PrincipalSatisfactionModel`` is published as a ``STATE_SNAPSHOT`` keyed by
``PHALA_EXTENSION_URI`` so the frontend asks the context-appropriate question.

Scope: this binding only *captures* the human's input as a typed
``SatisfactionRecord``. It deliberately does **not** manufacture a
``BeliefUpdate`` -- that valence-signed delta is computed and propagated by the
Phala learning loop over the agent network, unchanged by which transport carried
the human's input. AG-UI is the transport for the input; Phala is the semantics.

Dependency-free: builds plain JSON-serializable AG-UI event dicts. Identity
travels in ``metadata.governance.uri`` (B-1); generic clients fall back to
``message`` + ``responseSchema`` (B-2, non-breaking).
"""

from __future__ import annotations

from typing import Any, Optional

from phala.types.principal_satisfaction_model import PrincipalSatisfactionModel
from phala.types.phala_service_ref import PHALA_EXTENSION_URI
from phala.types.satisfaction_record import SatisfactionRecord, SatisfactionSource

# Key under an interrupt's ``metadata`` / a MetaEvent that carries identity.
GOVERNANCE_KEY = "governance"

# Resume payload for a prompted satisfaction interrupt. A refusal is encoded as
# ``refused: true`` in the payload (B-3), distinct from AG-UI ``cancelled``.
SATISFACTION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "valence": {
            "type": "number",
            "minimum": -1.0,
            "maximum": 1.0,
            "description": "Aggregate quality of the outcome, -1 (bad) to 1 (good).",
        },
        "refused": {
            "type": "boolean",
            "description": "True if the principal declined to rate the outcome.",
        },
    },
    "additionalProperties": False,
}


def model_state_snapshot(psm: PrincipalSatisfactionModel) -> dict[str, Any]:
    """AG-UI ``STATE_SNAPSHOT`` publishing the PrincipalSatisfactionModel.

    Lets the frontend ask the context-appropriate satisfaction question
    (e.g. weight timing for time-sensitive tasks) before prompting.
    """
    return {
        "type": "STATE_SNAPSHOT",
        "snapshot": {PHALA_EXTENSION_URI: psm.model_dump()},
    }


def satisfaction_interrupt(
    *,
    outcome_event_id: str,
    question: str = "Did this outcome serve you?",
) -> dict[str, Any]:
    """Build an ``input_required`` interrupt soliciting a satisfaction rating.

    The resume becomes a typed ``SatisfactionRecord`` via
    ``resolve_satisfaction``. The interrupt is bound to the ``OutcomeEvent`` the
    rating applies to via ``metadata.governance``.
    """
    interrupt = {
        "id": f"phala-sat-{outcome_event_id}",
        "reason": "input_required",
        "message": question,
        "responseSchema": SATISFACTION_RESPONSE_SCHEMA,
        "metadata": {
            GOVERNANCE_KEY: {
                "uri": PHALA_EXTENSION_URI,
                "type": "SatisfactionRecord",
                "outcome_event_id": outcome_event_id,
            }
        },
    }
    return {
        "type": "RUN_FINISHED",
        "outcome": {"type": "interrupt", "interrupts": [interrupt]},
    }


def resolve_satisfaction(
    *,
    interrupt: dict[str, Any],
    resume: dict[str, Any],
    record_id: str,
    recorded_at: str,
    psm_version: Optional[str] = None,
) -> SatisfactionRecord:
    """Turn an AG-UI resume into a typed, validated ``SatisfactionRecord``.

    An explicit valence is high-evidence: the principal's number is recorded
    under ``signal_components`` with ``confidence = 1.0``. A refusal
    (``refused: true``) or a ``cancelled`` resume is **no evidence**: valence 0,
    empty ``signal_components``, ``confidence = 0.0`` (invariant SR-1). Source is
    always ``EXPLICIT`` -- this is a stated principal response, not an inferred
    behavioral signal. Raises ``ValueError`` if the interrupt is not a Phala
    satisfaction prompt (B-1) or, for a resolved non-refusal, if no valence is
    supplied (B-4).
    """
    gov = (interrupt.get("metadata") or {}).get(GOVERNANCE_KEY) or {}
    if gov.get("uri") != PHALA_EXTENSION_URI or gov.get("type") != "SatisfactionRecord":
        raise ValueError("interrupt is not a Phala satisfaction prompt")

    status = resume.get("status")
    payload = resume.get("payload") or {}

    no_evidence = status == "cancelled" or bool(payload.get("refused"))
    if no_evidence:
        valence, components, confidence = 0.0, {}, 0.0
    elif status == "resolved":
        if "valence" not in payload:
            raise ValueError("resolved satisfaction resume carries no valence (B-4)")
        valence = float(payload["valence"])
        components = {"explicit_valence": valence}
        confidence = 1.0
    else:
        raise ValueError(f"unknown resume status {status!r}")

    return SatisfactionRecord(
        id=record_id,
        outcome_event_id=gov["outcome_event_id"],
        valence=valence,
        source=SatisfactionSource.EXPLICIT,
        signal_components=components,
        recorded_at=recorded_at,
        confidence=confidence,
        psm_version=psm_version,
    )


def meta_event_to_satisfaction(
    *,
    meta_event: dict[str, Any],
    outcome_event_id: str,
    record_id: str,
    recorded_at: str,
    rating_scale: int = 5,
    psm_version: Optional[str] = None,
) -> SatisfactionRecord:
    """Map a volunteered AG-UI ``MetaEvent`` to a ``SatisfactionRecord``.

    Recognized ``metaType`` values: ``thumbs_up`` (+1), ``thumbs_down`` (-1),
    and ``rating`` (payload an integer in ``[1, rating_scale]`` linearly mapped
    to ``[-1, 1]``). Volunteered feedback is still an explicit principal action,
    so ``source = EXPLICIT`` with ``confidence = 1.0``. Raises ``ValueError`` on
    an unrecognized ``metaType`` or an out-of-range rating.
    """
    meta_type = meta_event.get("metaType")
    payload = meta_event.get("payload")

    if meta_type == "thumbs_up":
        valence = 1.0
    elif meta_type == "thumbs_down":
        valence = -1.0
    elif meta_type == "rating":
        if rating_scale < 2:
            raise ValueError("rating_scale must be >= 2")
        rating = int(payload)
        if not 1 <= rating <= rating_scale:
            raise ValueError(f"rating {rating} out of range [1, {rating_scale}]")
        # Linearly map [1, scale] -> [-1, 1].
        valence = 2.0 * (rating - 1) / (rating_scale - 1) - 1.0
    else:
        raise ValueError(f"unrecognized MetaEvent metaType {meta_type!r}")

    return SatisfactionRecord(
        id=record_id,
        outcome_event_id=outcome_event_id,
        valence=valence,
        source=SatisfactionSource.EXPLICIT,
        signal_components={"meta_event": valence},
        recorded_at=recorded_at,
        confidence=1.0,
        psm_version=psm_version,
    )
