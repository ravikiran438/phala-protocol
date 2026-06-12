# Phala — repository status

Internal snapshot. The canonical references are this repo's README and the
published paper (Zenodo DOI 10.5281/zenodo.19625611).

## Last touched

May 1, 2026 — formalized `PhalaServiceRef` as the AgentCard descriptor with
`belief_update_endpoint` as a separate optional path, added
`validate_phala_service_ref` MCP tool, generated the v1 manifest.

## What works (verified)

- 86 tests passing (incl. the AG-UI binding suite).
- **AG-UI binding** at `phala.ag_ui` (`src/phala/ag_ui/binding.py`): captures the
  principal's satisfaction signal over the agent↔human transport — prompted
  (`input_required` interrupt → typed `SatisfactionRecord`) or volunteered
  (`MetaEvent` → `SatisfactionRecord`), with the `PrincipalSatisfactionModel`
  published as a `STATE_SNAPSHOT`. Capture-only (no `BeliefUpdate` fabrication);
  refusals/abandons are no-evidence per SR-1. 12 tests in
  `tests/test_ag_ui_binding.py`. Follows the cross-cutting *Governance over
  AG-UI* spec (<https://ravikiran438.github.io/agent-protocol-stack/ag-ui/>).
- TLA+ model `specification/Phala.tla` is a skeleton (no Init/Next/Spec
  defined yet) — TLC isn't run; the skeleton documents intended constants only.
- MCP server at `phala.mcp_server` exposes 12 validator tools including
  `validate_phala_service_ref`.
- ExtensionManifest published at `v1/manifest.json`, auto-generated from
  `phala.types.PhalaServiceRef`.
- One sub-extension (welfare-detectors) has its own URI constant + manifest at
  `extensions/welfare-detectors/v1/manifest.json`.

## What's pending

- TLA+ skeleton needs an Init / Next / Spec relation before TLC can verify any
  invariants. Currently invariants are documented in code + tests only.

## Verify

1. `python -m pytest -q` — expect 86/86.
2. Read `src/phala/types/phala_service_ref.py` for the wire shape; the manifest
   is generated from this class.

## Files to look at first

- `src/phala/types/phala_service_ref.py` — AgentCard descriptor (carries
  `belief_update_endpoint`).
- `src/phala/types/{outcome_event,satisfaction_record,belief_update,welfare_trace,principal_satisfaction_model}.py`
  — five core primitives.
- `src/phala/mcp_server/tools.py` — MCP validator surface.
- `v1/manifest.json` — published wire spec.

## Known gaps / future work

- TLA+ specification is a placeholder. Filling in Init/Next/Spec for Phala is a
  sizeable task on its own.
- `welfare-detectors` extension has primitives but minimal end-to-end testing.
- BeliefUpdate "bundled-with-satisfaction vs separate-endpoint" tradeoff is
  documented in the paper; both delivery paths remain conformant.
