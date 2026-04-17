# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""BU-Privacy validator (paper §3.3, invariant BU-1).

Given a serialised BeliefUpdate (or the equivalent dict), verify that
no forbidden field derived from SatisfactionRecord.signal_components
appears on it. The type system already prevents this at the
construction site; this validator exists for checking records received
over the wire, where the type guard no longer applies.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

# Fields that BU-Privacy forbids on any BeliefUpdate, regardless of value.
FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    "signal_components",
    "signal_component",
    "raw_signals",
    "behavioural_signals",
    "behavioral_signals",
})


class BeliefPrivacyError(ValueError):
    """Raised when a BeliefUpdate carries a field that BU-Privacy forbids."""


def validate_belief_privacy(
    payload: Mapping[str, Any],
    *,
    forbidden: Iterable[str] = FORBIDDEN_FIELDS,
) -> None:
    """Verify that ``payload`` does not carry any forbidden privacy field.

    Raises :class:`BeliefPrivacyError` identifying the offending keys.
    Accepts any Mapping so that callers can pass a ``BeliefUpdate``
    rendered via ``model_dump()`` or a raw dict from the wire.
    """
    forbidden_set = set(forbidden)
    offending = sorted(k for k in payload.keys() if k in forbidden_set)
    if offending:
        raise BeliefPrivacyError(
            "BeliefUpdate violates BU-Privacy: carries forbidden "
            f"fields {offending!r}. Per paper §3.3 invariant BU-1, only "
            "weight_delta may be derived from signal evidence."
        )
