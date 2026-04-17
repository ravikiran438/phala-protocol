------------------------------ MODULE Phala ------------------------------
\* Copyright 2026 Ravi Kiran Kadaboina. Licensed under the Apache License, 2.0.
\*
\* TLA+ specification of the Phala protocol's five core safety properties
\* as stated in the paper §3.7:
\*
\*   OE-Uniqueness      Every terminal task produces exactly one OutcomeEvent.
\*   BU-Privacy         No BeliefUpdate field is derived from signal_components.
\*   Chain-Monotonicity SatisfactionRecord entries are append-only.
\*   Update-Boundedness All weights remain within [w_min, w_max].
\*   PSM-Sovereignty    When a PSM exists for a context, valence MUST use its
\*                      signal_weights; no agent formula may override.
\*
\* Status: specification-in-progress. The module declares the invariants and
\* sketches the state space. A full state machine with Next actions and
\* TLC-checkable properties will land in a subsequent revision. See README
\* for the roadmap.

EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    Agents,          \* Set of agent identifiers
    Tasks,           \* Set of task identifiers
    Contexts,        \* Set of context keys
    MaxDepth,        \* Maximum invocation-chain depth considered
    MaxVersions,     \* Maximum PSM versions per principal
    WMin,            \* Weight lower bound (per AdjustmentBounds)
    WMax             \* Weight upper bound (per AdjustmentBounds)

ASSUME WMin < WMax
ASSUME MaxDepth \in Nat /\ MaxDepth > 0
ASSUME MaxVersions \in Nat /\ MaxVersions > 0

VARIABLES
    outcome_events,        \* Set of OutcomeEvent records produced so far
    satisfaction_records,  \* Sequence of SatisfactionRecord records (append-only)
    belief_updates,        \* Set of BeliefUpdate records emitted
    psm_versions,          \* Function: principal -> Sequence of PSM versions
    weights                \* Function: (agent, weight_key) -> current weight

vars == <<outcome_events, satisfaction_records, belief_updates,
          psm_versions, weights>>

\* --------------------------------------------------------------------------
\* Safety properties (to be made operational in a future revision)
\* --------------------------------------------------------------------------

\* OE-Uniqueness: no two OutcomeEvents share the same task_id.
OEUniqueness ==
    \A oe1, oe2 \in outcome_events :
        (oe1.task_id = oe2.task_id) => (oe1.id = oe2.id)

\* BU-Privacy: no BeliefUpdate carries a signal_components field.
\* In a model where BeliefUpdate is a record, this reduces to a schema check:
\* the record's DOMAIN must not contain "signal_components".
BUPrivacy ==
    \A bu \in belief_updates :
        "signal_components" \notin DOMAIN bu

\* Chain-Monotonicity: SatisfactionRecord entries are append-only.
\* In TLA+ terms, the sequence never loses or reorders elements; any transition
\* must extend it strictly.
ChainMonotonicityOK(sr_before, sr_after) ==
    /\ Len(sr_after) >= Len(sr_before)
    /\ \A i \in 1..Len(sr_before) : sr_after[i] = sr_before[i]

\* Update-Boundedness: every weight stays within [WMin, WMax].
UpdateBoundedness ==
    \A pair \in DOMAIN weights :
        weights[pair] >= WMin /\ weights[pair] <= WMax

\* PSM-Sovereignty: any SatisfactionRecord whose psm_version is set must
\* declare a valence computed using that PSM's signal_weights, not an agent
\* formula. We express the sanity side: if psm_version is non-null, it must
\* reference a valid version of the principal's PSM chain.
PSMSovereignty ==
    \A i \in 1..Len(satisfaction_records) :
        LET sr == satisfaction_records[i] IN
            (sr.psm_version # NULL) =>
                \E p \in DOMAIN psm_versions :
                    \E j \in 1..Len(psm_versions[p]) :
                        psm_versions[p][j] = sr.psm_version

\* Conjunction of all five safety properties.
Invariants ==
    /\ OEUniqueness
    /\ BUPrivacy
    /\ UpdateBoundedness
    /\ PSMSovereignty

\* --------------------------------------------------------------------------
\* State machine (skeleton, to be filled in)
\* --------------------------------------------------------------------------
\*
\* Init == ...
\* EmitOutcomeEvent(task) == ...
\* RecordSatisfaction(outcome) == ...
\* EmitBeliefUpdate(satisfaction) == ...
\* ApplyBeliefUpdate(update) == ...
\* DeclarePSMVersion(principal) == ...
\* Next == \E a \in {actions above} : a
\* Spec == Init /\ [][Next]_vars
\*
\* These actions will be filled in with full pre/post-conditions and the
\* ChainMonotonicityOK check invoked at every transition that touches
\* satisfaction_records. The current file establishes the invariants and
\* their scope; the operational model follows in the next revision.
\* --------------------------------------------------------------------------

=========================================================================
