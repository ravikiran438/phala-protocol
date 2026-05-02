# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Lock-in tests for Phala's published extension URIs."""

from __future__ import annotations


def test_phala_core_extension_uri():
    from phala.types import PHALA_EXTENSION_URI
    assert PHALA_EXTENSION_URI == (
        "https://github.com/ravikiran438/phala-protocol/v1"
    )


def test_welfare_detectors_extension_uri():
    from phala.extensions.welfare_detectors import EXTENSION_URI
    assert EXTENSION_URI == (
        "https://github.com/ravikiran438/phala-protocol/"
        "extensions/welfare-detectors/v1"
    )
