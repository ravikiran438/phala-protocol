# Phala Welfare-Detectors Extension — Wire Specification

> Generated from `v1/manifest.json`. Re-render after the manifest changes; do not hand-edit.

- **Extension URI:** `https://ravikiran438.github.io/phala-protocol/extensions/welfare-detectors/v1`
- **Protocol version:** 1.0.0
- **Manifest envelope version:** 1.0.0
- **Publisher:** Ravi Kiran Kadaboina

Pluggable panel of welfare-quality detectors emitting typed BeliefUpdates with conflict arbitration.

## AgentCard payload

This extension declares itself by URI presence and does not constrain the AgentCard payload. Validators accept any object in the entry's `params`.

## Invariants

- WD-1: every detector declares its predictive horizon and produces TypedBeliefUpdates only.
- WD-2: arbitration of conflicting updates MUST be deterministic for the same inputs.

---

_Drift between this `SPEC.md` and the protocol's pydantic models indicates the manifest needs regenerating. CI may compare a freshly-rendered version against the committed one._
