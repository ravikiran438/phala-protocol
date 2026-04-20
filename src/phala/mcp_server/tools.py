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
round-trip a JSON payload through the relevant Pydantic model; the
BU-Privacy tool additionally runs the paper's §3.3 invariant check.
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
            "Validate the structural integrity of a BeliefUpdate. "
            "The BU-Privacy invariant (no signal-evidence fields on the "
            "wire) is enforced separately by validate_belief_privacy."
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


HANDLERS: dict[str, Any] = {
    "validate_outcome_event": handle_validate_outcome_event,
    "validate_satisfaction_record": handle_validate_satisfaction_record,
    "validate_belief_update": handle_validate_belief_update,
    "validate_principal_satisfaction_model": handle_validate_principal_satisfaction_model,
    "validate_welfare_trace": handle_validate_welfare_trace,
    "validate_belief_privacy": handle_validate_belief_privacy,
}


def list_tool_names() -> list[str]:
    return list(TOOL_SCHEMAS.keys())
