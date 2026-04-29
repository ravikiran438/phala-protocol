# Copyright 2026 Ravi Kiran Kadaboina
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tool registrations for the Phala MCP server.

Each tool wraps a Phala primitive validator. Structural validators
round-trip a JSON payload through the relevant Pydantic model. Tools
that accept a serialized BeliefUpdate or TypedBeliefUpdate also run
the BU-Privacy invariant on the raw payload before Pydantic, so
signal-evidence fields cannot be silently dropped.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from phala.types import (
    BeliefUpdate,
    OutcomeEvent,
    PrincipalSatisfactionModel,
    SatisfactionRecord,
    WelfareTrace,
)
from phala.validators import BeliefPrivacyError, validate_belief_privacy

# welfare_detectors extension (WD-1, WD-2, WD-3, WD-4).
# See extensions/welfare_detectors/.
from phala.extensions.welfare_detectors import (
    DetectorPanel,
    TypedBeliefUpdate,
    WelfareDetectorError,
    WelfarePrediction,
    WelfareRealization,
    arbitrate_conflicting_updates,
    check_detector_provenance,
    check_predictive_horizon,
    check_typed_detector_composition,
)


# ─────────────────────────────────────────────────────────────────────────────
# Generic MCP glue — portable across sibling protocol repos.
# Keep these four symbols (ToolInvocationError, _parse, _ok, _fail) in sync
# by convention when copying to acap, pratyahara-nerve, or sauvidya-pace.
# ─────────────────────────────────────────────────────────────────────────────


class ToolInvocationError(Exception):
    """Raised when a tool's handler rejects its input or runtime fails."""


def _parse(cls, payload: Any, label: str):
    try:
        return cls.model_validate(payload)
    except ValidationError as exc:
        raise ToolInvocationError(f"invalid {label}: {exc}") from exc


def _ok(payload: dict[str, Any]) -> str:
    return json.dumps({"ok": True, **payload}, default=str, indent=2)


def _fail(message: str) -> str:
    return json.dumps({"ok": False, "error": message}, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# Tool handlers (repo-specific; everything below this line is Phala-only).
# ─────────────────────────────────────────────────────────────────────────────


TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    "validate_outcome_event": {
        "description": (
            "Validate the structural integrity of an OutcomeEvent. "
            "Enforces the type-level invariants from paper §3.1."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"event": {"type": "object"}},
            "required": ["event"],
        },
    },
    "validate_satisfaction_record": {
        "description": (
            "Validate the structural integrity of a SatisfactionRecord. "
            "Enforces §3.2 type invariants; note that principal-sovereign "
            "weights belong in SignalComponents only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"record": {"type": "object"}},
            "required": ["record"],
        },
    },
    "validate_belief_update": {
        "description": (
            "Validate a BeliefUpdate end-to-end. Runs the BU-Privacy "
            "invariant first on the raw payload (so forbidden "
            "signal-evidence fields cannot be silently dropped by "
            "Pydantic), then validates structural integrity. Returns "
            "ok=false for either kind of failure."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"update": {"type": "object"}},
            "required": ["update"],
        },
    },
    "validate_principal_satisfaction_model": {
        "description": (
            "Validate the structural integrity of a "
            "PrincipalSatisfactionModel. Enforces the PSM-Sovereignty "
            "type shape from §3.4."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"model": {"type": "object"}},
            "required": ["model"],
        },
    },
    "validate_welfare_trace": {
        "description": (
            "Validate the structural integrity of a WelfareTrace. "
            "Enforces §3.5 type invariants."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"trace": {"type": "object"}},
            "required": ["trace"],
        },
    },
    "validate_belief_privacy": {
        "description": (
            "Check that a serialized BeliefUpdate does not carry any "
            "forbidden signal-evidence fields. Enforces invariant BU-1 "
            "(paper §3.3). Accepts any JSON object; reports which "
            "forbidden keys appear."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"payload": {"type": "object"}},
            "required": ["payload"],
        },
    },
    # ── welfare_detectors extension (TBU structural + WD-1..WD-4) ─────────
    "validate_typed_belief_update": {
        "description": (
            "Validate the structural integrity of a TypedBeliefUpdate "
            "from the welfare_detectors extension. Verifies BU base "
            "fields plus detector_type and provenance_hash. Note: "
            "WD-1 (panel composition) and WD-4 (provenance non-leakage) "
            "are checked separately by their dedicated tools."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"update": {"type": "object"}},
            "required": ["update"],
        },
    },
    "validate_typed_detector_composition": {
        "description": (
            "welfare_detectors WD-1: verify that an incoming "
            "TypedBeliefUpdate carries a detector_type that appears in "
            "the consumer's DetectorPanel. Untyped or unknown-type "
            "updates are rejected."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "panel": {"type": "object"},
                "update": {"type": "object"},
            },
            "required": ["panel", "update"],
        },
    },
    "arbitrate_conflicting_updates": {
        "description": (
            "welfare_detectors WD-2: among a set of TypedBeliefUpdates "
            "that share (target_agent_id, weight_key, valid_from), "
            "return the unique winner — highest priority on the panel, "
            "ties broken by lower provenance_hash (lexicographic). "
            "Resolution is deterministic across observers."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "panel": {"type": "object"},
                "updates": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
            "required": ["panel", "updates"],
        },
    },
    "validate_predictive_horizon": {
        "description": (
            "welfare_detectors WD-3 (consistency): verify that a "
            "WelfareRealization paired to a WelfarePrediction lies "
            "within the prediction's horizon window and that the "
            "mirrored predicted_delta agrees with the prediction."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prediction": {"type": "object"},
                "realization": {
                    "type": ["object", "null"],
                    "description": (
                        "WelfareRealization object, or null to test the "
                        "missing-realization rejection path."
                    ),
                },
                "horizon_grace_seconds": {
                    "type": "integer",
                    "description": "Optional grace period in seconds; default 0.",
                },
            },
            "required": ["prediction"],
        },
    },
    "validate_detector_provenance": {
        "description": (
            "welfare_detectors WD-4: verify that a TypedBeliefUpdate "
            "carries a non-empty provenance_hash that does not encode "
            "forbidden privacy fields (signal_components, raw_signals, "
            "etc). Compatible with BU-Privacy."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"update": {"type": "object"}},
            "required": ["update"],
        },
    },
}


def _validate_primitive(cls, argument_key: str, arguments: dict[str, Any]) -> str:
    payload = arguments.get(argument_key)
    if not isinstance(payload, dict):
        raise ToolInvocationError(
            f"expected object under key {argument_key!r}"
        )
    _parse(cls, payload, argument_key)
    return _ok({argument_key: "valid"})


def handle_validate_outcome_event(arguments: dict[str, Any]) -> str:
    return _validate_primitive(OutcomeEvent, "event", arguments)


def handle_validate_satisfaction_record(arguments: dict[str, Any]) -> str:
    return _validate_primitive(SatisfactionRecord, "record", arguments)


def handle_validate_belief_update(arguments: dict[str, Any]) -> str:
    # BeliefUpdate is not declared with extra='forbid', so a payload
    # carrying signal_components or other forbidden fields would
    # silently round-trip as "valid" while Pydantic drops the extras.
    # Run BU-Privacy on the raw payload first so the failure surfaces.
    payload = arguments.get("update")
    if not isinstance(payload, dict):
        raise ToolInvocationError("expected object under key 'update'")
    try:
        validate_belief_privacy(payload)
    except BeliefPrivacyError as exc:
        return _fail(str(exc))
    return _validate_primitive(BeliefUpdate, "update", arguments)


def handle_validate_principal_satisfaction_model(
    arguments: dict[str, Any],
) -> str:
    return _validate_primitive(
        PrincipalSatisfactionModel, "model", arguments
    )


def handle_validate_welfare_trace(arguments: dict[str, Any]) -> str:
    return _validate_primitive(WelfareTrace, "trace", arguments)


def handle_validate_belief_privacy(arguments: dict[str, Any]) -> str:
    payload = arguments.get("payload")
    if not isinstance(payload, dict):
        raise ToolInvocationError("expected object under key 'payload'")
    try:
        validate_belief_privacy(payload)
    except BeliefPrivacyError as exc:
        return _fail(str(exc))
    return _ok({"payload": "privacy-compliant"})


# ── welfare_detectors extension handlers (TBU structural + WD-1..WD-4) ───


def _parse_optional(cls, payload: Any, label: str):
    if payload is None:
        return None
    return _parse(cls, payload, label)


def handle_validate_typed_belief_update(arguments: dict[str, Any]) -> str:
    payload = arguments.get("update")
    if not isinstance(payload, dict):
        raise ToolInvocationError("expected object under key 'update'")
    # Same defensive composition as validate_belief_update: run BU-Privacy
    # before Pydantic, since BeliefUpdate (parent class) does not declare
    # extra='forbid' and would silently drop signal_components.
    try:
        validate_belief_privacy(payload)
    except BeliefPrivacyError as exc:
        return _fail(str(exc))
    _parse(TypedBeliefUpdate, payload, "update")
    return _ok({"update": "valid"})


def handle_validate_typed_detector_composition(arguments: dict[str, Any]) -> str:
    panel = _parse(DetectorPanel, arguments.get("panel"), "panel")
    update = _parse(TypedBeliefUpdate, arguments.get("update"), "update")
    try:
        check_typed_detector_composition(panel, update)
    except WelfareDetectorError as exc:
        return _fail(str(exc))
    return _ok({"composition": "valid", "detector_type": update.detector_type})


def handle_arbitrate_conflicting_updates(arguments: dict[str, Any]) -> str:
    panel = _parse(DetectorPanel, arguments.get("panel"), "panel")
    updates_raw = arguments.get("updates")
    if not isinstance(updates_raw, list):
        raise ToolInvocationError("updates must be a list of objects")
    updates = [
        _parse(TypedBeliefUpdate, u, f"updates[{i}]")
        for i, u in enumerate(updates_raw)
    ]
    # Pre-validate WD-1 per update so the caller learns the offending
    # index instead of getting a generic "during arbitration" message.
    for i, u in enumerate(updates):
        try:
            check_typed_detector_composition(panel, u)
        except WelfareDetectorError as exc:
            return _fail(f"updates[{i}] failed WD-1: {exc}")
    try:
        winner = arbitrate_conflicting_updates(panel, updates)
    except WelfareDetectorError as exc:
        return _fail(str(exc))
    return _ok(
        {
            "winner_id": winner.id,
            "detector_type": winner.detector_type,
            "provenance_hash": winner.provenance_hash,
        }
    )


def handle_validate_predictive_horizon(arguments: dict[str, Any]) -> str:
    prediction = _parse(
        WelfarePrediction, arguments.get("prediction"), "prediction"
    )
    realization = _parse_optional(
        WelfareRealization, arguments.get("realization"), "realization"
    )
    grace = arguments.get("horizon_grace_seconds", 0)
    if isinstance(grace, bool) or not isinstance(grace, int):
        raise ToolInvocationError("horizon_grace_seconds must be an integer")
    try:
        check_predictive_horizon(prediction, realization, horizon_grace_seconds=grace)
    except WelfareDetectorError as exc:
        return _fail(str(exc))
    return _ok({"horizon": "consistent"})


def handle_validate_detector_provenance(arguments: dict[str, Any]) -> str:
    update = _parse(TypedBeliefUpdate, arguments.get("update"), "update")
    try:
        check_detector_provenance(update)
    except WelfareDetectorError as exc:
        return _fail(str(exc))
    return _ok({"provenance": "non-leaking"})


HANDLERS: dict[str, Any] = {
    "validate_outcome_event": handle_validate_outcome_event,
    "validate_satisfaction_record": handle_validate_satisfaction_record,
    "validate_belief_update": handle_validate_belief_update,
    "validate_principal_satisfaction_model": handle_validate_principal_satisfaction_model,
    "validate_welfare_trace": handle_validate_welfare_trace,
    "validate_belief_privacy": handle_validate_belief_privacy,
    # welfare_detectors extension
    "validate_typed_belief_update": handle_validate_typed_belief_update,
    "validate_typed_detector_composition": handle_validate_typed_detector_composition,
    "arbitrate_conflicting_updates": handle_arbitrate_conflicting_updates,
    "validate_predictive_horizon": handle_validate_predictive_horizon,
    "validate_detector_provenance": handle_validate_detector_provenance,
}


def list_tool_names() -> list[str]:
    return list(TOOL_SCHEMAS.keys())
