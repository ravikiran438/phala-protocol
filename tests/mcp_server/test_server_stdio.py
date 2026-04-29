# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""End-to-end stdio smoke test for the Phala MCP server.

Spawns the server as a subprocess, issues the MCP handshake via the
official client SDK, lists tools, and calls one. Confirms the
registration, transport, and call plumbing work together.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _spawn_env() -> dict[str, str]:
    """Inherit current env and prepend repo's src/ to PYTHONPATH so the
    spawned subprocess can import the package even without an editable
    install. Without this, `python -m phala.mcp_server` fails when the
    package was added to sys.path via pyproject's pythonpath setting,
    because subprocesses do not inherit that.
    """
    repo_root = Path(__file__).resolve().parents[2]
    src = str(repo_root / "src")
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{src}{os.pathsep}{existing}" if existing else src
    return env


@pytest.mark.asyncio
async def test_server_lists_tools_over_stdio():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "phala.mcp_server"],
        env=_spawn_env(),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

    names = {t.name for t in tools.tools}
    expected = {
        "validate_outcome_event",
        "validate_satisfaction_record",
        "validate_belief_update",
        "validate_principal_satisfaction_model",
        "validate_welfare_trace",
        "validate_belief_privacy",
        # welfare_detectors extension
        "validate_typed_belief_update",
        "validate_typed_detector_composition",
        "arbitrate_conflicting_updates",
        "validate_predictive_horizon",
        "validate_detector_provenance",
    }
    assert names == expected


@pytest.mark.asyncio
async def test_server_call_validate_belief_privacy_over_stdio():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "phala.mcp_server"],
        env=_spawn_env(),
    )

    leaked_payload = {
        "id": "bu-1",
        "weight_delta": 0.1,
        "signal_components": {"completion_latency_ratio": 0.8},
    }

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "validate_belief_privacy", {"payload": leaked_payload}
            )

    assert result.content, "tool returned no content"
    body = json.loads(result.content[0].text)
    assert body["ok"] is False
    assert "signal_components" in body["error"] or "BU-Privacy" in body["error"]
