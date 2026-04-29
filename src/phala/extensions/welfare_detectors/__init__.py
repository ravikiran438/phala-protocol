# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Welfare-detector panel extension to Phala.

Public surface of the extension. Importing from here keeps downstream
code isolated from internal module layout.
"""

from .types import (
    DetectorPanel,
    MissingRealization,
    TypedBeliefUpdate,
    WelfareDetector,
    WelfarePrediction,
    WelfareRealization,
)
from .validators import (
    WelfareDetectorError,
    arbitrate_conflicting_updates,
    check_arbitration_determinism,
    check_detector_provenance,
    check_predictive_horizon,
    check_typed_detector_composition,
    emit_missing_realization,
)

__all__ = [
    "DetectorPanel",
    "MissingRealization",
    "TypedBeliefUpdate",
    "WelfareDetector",
    "WelfareDetectorError",
    "WelfarePrediction",
    "WelfareRealization",
    "arbitrate_conflicting_updates",
    "check_arbitration_determinism",
    "check_detector_provenance",
    "check_predictive_horizon",
    "check_typed_detector_composition",
    "emit_missing_realization",
]
