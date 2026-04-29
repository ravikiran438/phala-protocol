# Welfare Detector Panel Extension

This extension extends the Phala Protocol with a typed panel of
specialized welfare detectors, deterministic arbitration rules, and a
predictive welfare horizon. The motivation is that a single scalar
`BeliefUpdate` channel cannot represent the multi-dimensional welfare
signal real principals produce — cognitive load, autonomy preservation,
dignity, social connection, and pace are each a distinct welfare
dimension, and conflating them into one weight delta loses information
the agent needs to act well.

## What this extension adds

### Primitives

| Primitive | Purpose |
|---|---|
| `WelfareDetector` | A typed detector declaration: `detector_type`, signal source, target weight, priority |
| `DetectorPanel` | The set of detectors an agent consumes plus the arbitration rule |
| `TypedBeliefUpdate` | A `BeliefUpdate` carrying `detector_type` and `provenance_hash` fields |
| `WelfarePrediction` | An agent's predicted welfare delta over a declared horizon |
| `WelfareRealization` | The realized welfare delta observed at the horizon, paired to a prediction |

### Invariants

| Invariant | Statement |
|---|---|
| **WD-1 Typed Detector Composition** | Every `TypedBeliefUpdate` MUST carry a `detector_type` that appears in the consumer's `DetectorPanel`. Untyped or unknown-type updates MUST be rejected. |
| **WD-2 Arbitration Determinism** | When two or more `TypedBeliefUpdate`s target the same `(target_agent_id, weight_key, valid_from)`, resolution MUST follow the panel's declared priority order. Ties MUST be broken by the lower `provenance_hash` (lexicographic) so the outcome is deterministic across observers. |
| **WD-3 Predictive Welfare Horizon** | An agent that emits a `WelfarePrediction` MUST emit a matching `WelfareRealization` within `horizon_seconds` of the predicted time. Missing realizations are themselves a welfare signal (the agent stopped learning from this prediction). |
| **WD-4 Detector Provenance Disclosure** | Every `TypedBeliefUpdate` MUST carry a `provenance_hash` that an observer can use to identify the detector instance. The hash MUST NOT leak `signal_components` content (compatible with BU-Privacy). |

## Files

| File | Purpose |
|---|---|
| [`README.md`](./README.md) | This file |
| [`STATUS.md`](./STATUS.md) | Stage, URI, and scope |
| [`WelfareDetectors.tla`](./WelfareDetectors.tla) | TLA+ specification of the four invariants |
| [`WelfareDetectors.cfg`](./WelfareDetectors.cfg) | Small-model TLC configuration |

Python implementation lives under [`src/phala/extensions/welfare_detectors/`](../../src/phala/extensions/welfare_detectors/),
tests under [`tests/extensions/test_welfare_detectors.py`](../../tests/extensions/test_welfare_detectors.py).

## Usage

```python
from phala.extensions.welfare_detectors import (
    DetectorPanel,
    TypedBeliefUpdate,
    WelfareDetector,
    check_typed_detector_composition,
    arbitrate_conflicting_updates,
)

panel = DetectorPanel(
    consumer_agent_id="caregiver-agent-v1",
    detectors=[
        WelfareDetector(detector_type="cognitive_load", priority=10),
        WelfareDetector(detector_type="autonomy",       priority=20),
        WelfareDetector(detector_type="dignity",        priority=30),
    ],
)

# Incoming update typed against the panel
update = TypedBeliefUpdate(..., detector_type="cognitive_load", provenance_hash="...")
check_typed_detector_composition(panel, update)  # passes

# Two updates conflict on the same weight_key — arbitration resolves
winner = arbitrate_conflicting_updates(panel, [update_dignity, update_autonomy])
# winner is the higher-priority detector's update
```

## Relationship to Phala Core

This extension is additive. Agents that do not declare a `DetectorPanel`
continue to operate under Phala's existing single-channel `BeliefUpdate`
model (BU-1 through BU-4 unchanged). Agents that do declare a panel
gain typed welfare signals plus deterministic arbitration without
breaking any existing Phala guarantees.

## Background: specialized signals beat scalar reward

The thesis behind this extension — that welfare is multi-dimensional
and that conflating multiple dimensions into one scalar loses
information the agent needs — has support from two literatures.

In neuroscience, the hypothalamus is not a single drive center but a
collection of specialized survival circuits, each tuned to a distinct
homeostatic dimension (thirst, hunger, thermoregulation, social-status
threat, satiety). Sternson's review of hypothalamic survival circuits
[1] makes the case that purposive behavior emerges from many parallel,
specialized predictors rather than a single global reward. Reward
itself is not one signal either: Berridge & Kringelbach [2] separate
*wanting* from *liking* as distinct neural systems — wanting mediated
by mesolimbic dopamine, liking by opioid and endocannabinoid hedonic
hotspots within limbic circuitry — showing that even the construct
that ML reduces to a scalar is multi-system in biology. The pattern
in both cases is the same: specialization, not scalarization.

In machine learning, Marblestone, Wayne, and Kording [3] argue that
cost functions are diverse and structured in the brain — varying
across cortical regions and over development — and that brain-inspired
deep learning should adopt similarly structured, location-specific
cost functions. The implication this extension acts on is that
contemporary ML's reliance on a single cross-entropy or RLHF reward
signal is a live constraint when modeling welfare in a multi-agent
system, not a feature of the design.

This extension applies the same insight at the protocol layer: a
typed panel of specialized welfare detectors with deterministic
arbitration is the protocol-layer analog of a hypothalamic-nuclei
panel feeding a basal-ganglia arbiter. The lizard-brain analogy is
loose but the underlying engineering principle is concrete.

## References

[1] Sternson, S.M. (2013). Hypothalamic survival circuits: blueprints
for purposive behaviors. *Neuron*, 77(5), 810–824.
DOI: [10.1016/j.neuron.2013.02.018](https://doi.org/10.1016/j.neuron.2013.02.018)

[2] Berridge, K.C. & Kringelbach, M.L. (2015). Pleasure systems in
the brain. *Neuron*, 86(3), 646–664.
DOI: [10.1016/j.neuron.2015.02.018](https://doi.org/10.1016/j.neuron.2015.02.018)

[3] Marblestone, A.H., Wayne, G., & Kording, K.P. (2016). Toward an
integration of deep learning and neuroscience. *Frontiers in
Computational Neuroscience*, 10, 94.
DOI: [10.3389/fncom.2016.00094](https://doi.org/10.3389/fncom.2016.00094)

## License

Apache 2.0. See [../../LICENSE](../../LICENSE).
