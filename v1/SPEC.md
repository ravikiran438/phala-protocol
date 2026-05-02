# Phala Outcome Protocol — Wire Specification

> Generated from `v1/manifest.json`. Re-render after the manifest changes; do not hand-edit.

- **Extension URI:** `https://ravikiran438.github.io/phala-protocol/v1`
- **Protocol version:** 1.0.0
- **Manifest envelope version:** 1.0.0
- **Publisher:** Ravi Kiran Kadaboina
- **Paper / human-readable spec:** https://doi.org/10.5281/zenodo.19625612

Outcome events, satisfaction records, and belief-update propagation for A2A networks.

## AgentCard payload

**Required fields:** `belief_update_endpoint`, `learning_rate`, `outcome_endpoint`, `satisfaction_endpoint`, `version`, `weight_bounds`, `weight_keys`

| Field | Type | Required | Notes |
|---|---|---|---|
| `belief_update_endpoint` | string | yes | HTTPS URL where BeliefUpdates targeting this agent are POSTed. REQUIRED so peers can deliver the propagated weight deltas the Phala learning loop depends on. Per BU-3 the agent MAY ignore individual updates, but the endpoint MUST exist and accept POST. |
| `learning_rate` | number | yes | Base learning rate applied to BeliefUpdates this agent emits. Effective rate is modulated by the agent's WelfareTrace per WT-2. |
| `outcome_endpoint` | string | yes | HTTPS URL where OutcomeEvents originating from this agent are POSTed. Read-back endpoint per OE-1 (every terminal task MUST produce exactly one OutcomeEvent). |
| `satisfaction_endpoint` | string | yes | HTTPS URL where SatisfactionRecords are POSTed for outcomes produced by this agent. |
| `version` | string | yes | Phala protocol semver this agent implements (e.g. '1.0.0'). |
| `weight_bounds` | `$AdjustmentBounds` | yes | Per-weight clipping range for ``weight_delta``. All emitted BeliefUpdates MUST land within these bounds. |
| `weight_keys` | array<string> | yes | Stable namespace of weight keys this agent will accept on a BeliefUpdate. Updates targeting unknown keys MAY be discarded. |

## Invariants

- OE-1: every terminal task MUST produce exactly one OutcomeEvent.
- BU-1: BeliefUpdates MUST NOT carry raw signal_components.
- WT-1: WelfareTraces are on-device only; never transmitted.

---

_Drift between this `SPEC.md` and the protocol's pydantic models indicates the manifest needs regenerating. CI may compare a freshly-rendered version against the committed one._
