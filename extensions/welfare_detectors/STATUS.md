# Welfare Detector Panel: Status

**Stage:** Reference implementation
**Extension URI:** https://ravikiran438.github.io/phala-protocol/extensions/welfare-detectors/v1
**First drafted:** 2026-04-25
**Depends on:** Phala Core v0.1+
**Maintainer:** Ravi Kiran Kadaboina (@ravikiran438)
**License:** Apache 2.0

## Scope

This extension adds a specialized welfare detector panel and four
safety invariants (WD-1, WD-2, WD-3, WD-4) to the Phala Protocol. It
supplements Phala Core's single-scalar `BeliefUpdate` channel with a
typed panel of detectors plus deterministic arbitration, motivated by
the observation that real welfare is multi-dimensional and
single-scalar signals collapse information the agent needs.

## Primitives this extension adds

- `WelfareDetector`: typed detector declaration with priority
- `DetectorPanel`: consumer-side declaration of accepted detectors
- `TypedBeliefUpdate`: BU carrying `detector_type` + `provenance_hash`
- `WelfarePrediction`: predicted welfare delta over a horizon
- `WelfareRealization`: observed delta paired to a prediction

## Invariants this extension adds

- **WD-1 Typed Detector Composition**: every TBU has a known type
- **WD-2 Arbitration Determinism**: priority-ordered, deterministic ties
- **WD-3 Predictive Welfare Horizon**: split into safety + obligation (see below)
- **WD-4 Detector Provenance Disclosure**: provenance hash on every TBU

### WD-3 safety / obligation split

WD-3 carries two distinct properties:

1. **Consistency (safety)**: any `WelfareRealization` paired to a
   prediction lies within the horizon window. This is enforced both
   by Pydantic validators and by the TLA+ model.
2. **Obligation (operational)**: every emitted prediction must
   eventually receive either a realization or a `MissingRealization`
   event. This is a liveness property and would require explicit TLA+
   fairness conditions to verify formally. The current model encodes
   only the safety side; the obligation is enforced at runtime via
   `emit_missing_realization()` and the deployment's scheduling.

This split was chosen because formal liveness verification is
disproportionate cost for an unpublished extension; the runtime
helper is sufficient.

## Interop points with Phala Core

- `BeliefUpdate` remains; `TypedBeliefUpdate` extends it via inheritance
- BU-1 (privacy) is preserved: provenance hash MUST NOT leak
  `signal_components`
- BU-2, BU-3, BU-4 (uniqueness, advisory, TTL) apply unchanged
- Agents that consume only Phala Core continue to ignore the extra
  fields

## What exists today

- TLA+ specification of WD-1/WD-2/WD-3/WD-4 under `WelfareDetectors.tla`
- TLC configuration for a small model (2 agents × 3 detector types).
  **TLC has not been run against this configuration yet**; the spec
  is offered for review and as a static artifact. A model-check pass
  with output captured here is open work.
- Pydantic types for the six primitives (WelfareDetector,
  DetectorPanel, TypedBeliefUpdate, WelfarePrediction,
  WelfareRealization, MissingRealization)
- Runtime validators for the four invariants
- Test suite covering the invariants

## What is open

- **Context-conditional priorities.** Static integer priorities on
  the panel work for the simple cases but real welfare conflicts are
  context-dependent (dignity dominates near end-of-life; cognitive
  load dominates during routine task scaffolding). A context-aware
  priority extension is open work; the current spec deliberately
  fixes priorities for determinism and observability.
- TLC model-check run with captured output
- Detector-type registries per domain (elderly care, BCI, autistic
  augmentation) — application-layer concerns, not part of this spec
- Empirical study on false-positive reduction vs single-channel BU
- Integration with PACE `augmentation_profile` extension for
  capacity-conditioned detector activation

## Not in scope

- The signal-detection algorithms inside each detector (those are
  agent-local and may use any technique)
- Specific detector taxonomies for any single principal population
- Operationalization of the welfare deltas into agent reward shaping

## Feedback

Open an issue or PR on the parent repository. Reference the extension
in the title: `[welfare-detectors] <your topic>`.
