# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Invariant validators for the Phala primitives.

The paper §3.7 names five formal safety properties:

- OE-Uniqueness
- BU-Privacy
- Chain-Monotonicity
- Update-Boundedness
- PSM-Sovereignty

and §3 states twelve per-primitive invariants (OE-1, OE-2, SR-1, SR-2,
BU-1 through BU-4, PSM-1, PSM-2, WT-1, WT-2).

This package will host the runtime validators that check these
invariants on concrete records. The first validator to land enforces
BU-Privacy; others follow as the simulations are wired up.
"""

from phala.validators.belief import BeliefPrivacyError, validate_belief_privacy

__all__ = ["BeliefPrivacyError", "validate_belief_privacy"]
