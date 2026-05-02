# Phala — repository status

Snapshot for future-me; lives next to the canonical README.

## Last touched

May 1, 2026 — formalized `PhalaServiceRef` as the AgentCard descriptor
with `belief_update_endpoint` as a required separate path, added
`validate_phala_service_ref` MCP tool, generated v1 manifest.

## What works (verified)

- 74 tests passing locally via the shared venv at `../../.venv`.
- TLA+ model `specification/Phala.tla` is a skeleton (no Init/Next/Spec
  defined yet) — TLC isn't run; the skeleton documents intended
  constants only.
- MCP server at `phala.mcp_server` exposes 12 validator tools
  including the new `validate_phala_service_ref`.
- ExtensionManifest published at `v1/manifest.json` auto-generated
  from `phala.types.PhalaServiceRef`.
- One sub-extension (welfare-detectors) has its own URI constant +
  manifest at `extensions/welfare-detectors/v1/manifest.json`.

## What's pending

- Repo not yet pushed. Phase 2 commit + push owed.
- Phala preprint v3 drafted at `/Users/rkadaboina/Sites/research/Phala/preprint/phala-outcome-protocol-v3.md`
  documenting the new `belief_update_endpoint` field. Not yet
  published; current Zenodo is v2 (DOI .19625612).
- TLA+ skeleton needs an Init / Next / Spec relation before TLC can
  verify any invariants. Currently invariants are documented in code +
  tests only.

## Re-page-in checklist

1. `cd <here> && ../../.venv/bin/python -m pytest -q` — expect 74/74.
2. Read `src/phala/types/phala_service_ref.py` to remember the wire
   shape; the manifest is generated from this class.
3. `MASTER_STATUS.md` in the testbed for cross-repo state.

## Files I'd look at first

- `src/phala/types/phala_service_ref.py` — AgentCard descriptor (the
  v3 preprint adds `belief_update_endpoint` here).
- `src/phala/types/{outcome_event,satisfaction_record,belief_update,welfare_trace,principal_satisfaction_model}.py`
  — five core primitives.
- `src/phala/mcp_server/tools.py` — MCP validator surface.
- `v1/manifest.json` — published wire spec.
- `preprint/phala-outcome-protocol-v3.md` (in the sibling Phala
  preprint directory, not this repo) — pending publication.

## Known gaps / future work

- TLA+ specification is a placeholder. Filling in Init/Next/Spec for
  Phala is a sizeable task on its own.
- `welfare-detectors` extension has primitives but minimal
  end-to-end testing.
- BeliefUpdate "bundled-with-satisfaction vs separate-endpoint"
  tradeoff is documented in v3 preprint; both paths remain
  conformant to v3.
