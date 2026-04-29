------------------------- MODULE WelfareDetectors -------------------------
\* Copyright 2026 Ravi Kiran Kadaboina. Licensed under the Apache License, 2.0.
\*
\* TLA+ specification of the welfare-detector panel extension to Phala.
\* This module adds four safety invariants on top of Phala Core's BU-1..BU-4:
\*
\*   WD-1 Typed Detector Composition  : every TBU carries a known type
\*   WD-2 Arbitration Determinism     : priority + deterministic tie-break
\*   WD-3 Predictive Welfare Horizon  : realizations stay within horizon
\*                                       (obligation-to-emit is operational)
\*   WD-4 Detector Provenance Disclosure: provenance hash on every TBU

EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    Agents,        \* Set of agent identifiers
    DetectorTypes, \* Set of detector type identifiers (e.g., "cognitive_load")
    WeightKeys,    \* Set of weight identifiers a TBU may target
    HashSpace,     \* Abstract set of provenance hashes (totally ordered)
    MaxHorizon     \* Maximum horizon ticks for predictions

ASSUME MaxHorizon \in Nat
ASSUME Cardinality(HashSpace) >= 2

\* Provenance hashes are SHA-256 fingerprints in production. We model
\* them as a totally ordered finite set; the model assumes uniqueness
\* of any phash actually used in a TBU, so the <= tie-break in
\* WinsArbitration is effectively a total order on the relevant subset.

VARIABLES
    panel,         \* Function: agent -> [type -> priority]; missing = unknown
    pendingTBUs,   \* Set of TypedBeliefUpdate records awaiting arbitration
    appliedTBUs,   \* Set of TBUs that won arbitration and were applied
    predictions,   \* Set of WelfarePrediction records (id, agent, due_at)
    realizations,  \* Set of WelfareRealization records (prediction_id, at)
    clockTick      \* Abstract monotonic tick

wdVars == <<panel, pendingTBUs, appliedTBUs, predictions, realizations, clockTick>>

\* ─────────────────────────────────────────────────────────────────────
\* Type invariant
\* ─────────────────────────────────────────────────────────────────────

TBURecord ==
    [id: Nat,
     target: Agents,
     weight: WeightKeys,
     valid_from: Nat,
     dtype: DetectorTypes,
     phash: HashSpace]

PredRecord == [id: Nat, agent: Agents, due_at: Nat]
RealRecord == [pred_id: Nat, at: Nat]

TypeOK ==
    /\ panel \in [Agents -> [DetectorTypes -> Nat \cup {-1}]]
    /\ pendingTBUs \subseteq TBURecord
    /\ appliedTBUs \subseteq TBURecord
    /\ predictions \subseteq PredRecord
    /\ realizations \subseteq RealRecord
    /\ clockTick \in Nat

\* ─────────────────────────────────────────────────────────────────────
\* Initial state
\* ─────────────────────────────────────────────────────────────────────

Init ==
    /\ panel = [a \in Agents |-> [d \in DetectorTypes |-> -1]]
    /\ pendingTBUs = {}
    /\ appliedTBUs = {}
    /\ predictions = {}
    /\ realizations = {}
    /\ clockTick = 0

\* ─────────────────────────────────────────────────────────────────────
\* Actions
\* ─────────────────────────────────────────────────────────────────────

\* Register a detector type with priority on an agent's panel.
RegisterDetector(a, d, p) ==
    /\ a \in Agents /\ d \in DetectorTypes /\ p \in Nat
    /\ panel' = [panel EXCEPT ![a] = [@ EXCEPT ![d] = p]]
    /\ UNCHANGED <<pendingTBUs, appliedTBUs, predictions,
                   realizations, clockTick>>

\* Receive a typed belief update; rejected if detector type is unknown.
ReceiveTBU(tbu) ==
    /\ tbu \in TBURecord
    /\ panel[tbu.target][tbu.dtype] >= 0  \* WD-1: must be registered
    /\ pendingTBUs' = pendingTBUs \cup {tbu}
    /\ UNCHANGED <<panel, appliedTBUs, predictions, realizations, clockTick>>

\* Arbitrate: among TBUs targeting the same (agent, weight, valid_from),
\* the highest-priority detector's TBU wins. Ties broken by phash.
SamePoint(t1, t2) ==
    /\ t1.target = t2.target
    /\ t1.weight = t2.weight
    /\ t1.valid_from = t2.valid_from

ConflictSet(tbu) ==
    {t \in pendingTBUs : SamePoint(t, tbu)}

WinsArbitration(tbu) ==
    /\ tbu \in pendingTBUs
    /\ \A o \in ConflictSet(tbu):
        \/ panel[tbu.target][tbu.dtype] > panel[o.target][o.dtype]
        \/ /\ panel[tbu.target][tbu.dtype] = panel[o.target][o.dtype]
           /\ tbu.phash <= o.phash

ApplyTBU(tbu) ==
    /\ WinsArbitration(tbu)
    /\ appliedTBUs' = appliedTBUs \cup {tbu}
    /\ pendingTBUs' = pendingTBUs \ ConflictSet(tbu)
    /\ UNCHANGED <<panel, predictions, realizations, clockTick>>

EmitPrediction(pid, a, due) ==
    /\ pid \in Nat /\ a \in Agents /\ due \in Nat
    /\ due > clockTick
    /\ due - clockTick <= MaxHorizon
    /\ predictions' = predictions \cup {[id |-> pid, agent |-> a, due_at |-> due]}
    /\ UNCHANGED <<panel, pendingTBUs, appliedTBUs, realizations, clockTick>>

\* Realization may be emitted any time within MaxHorizon ticks of due_at,
\* including after due. The earlier guard p.due_at >= clockTick made
\* PredictiveHorizon unsatisfiable once a prediction passed due, since
\* no realization could be emitted after that point.
EmitRealization(pid) ==
    /\ \E p \in predictions: p.id = pid /\ p.due_at + MaxHorizon >= clockTick
    /\ realizations' = realizations \cup {[pred_id |-> pid, at |-> clockTick]}
    /\ UNCHANGED <<panel, pendingTBUs, appliedTBUs, predictions, clockTick>>

Tick ==
    /\ clockTick' = clockTick + 1
    /\ UNCHANGED <<panel, pendingTBUs, appliedTBUs, predictions, realizations>>

Next ==
    \/ \E a \in Agents, d \in DetectorTypes, p \in 0..3:
            RegisterDetector(a, d, p)
    \/ \E tbu \in TBURecord: ReceiveTBU(tbu)
    \/ \E tbu \in pendingTBUs: ApplyTBU(tbu)
    \/ \E pid \in 0..3, a \in Agents, due \in 1..MaxHorizon:
            EmitPrediction(pid, a, due)
    \/ \E pid \in 0..3: EmitRealization(pid)
    \/ Tick

Spec == Init /\ [][Next]_wdVars

\* ─────────────────────────────────────────────────────────────────────
\* Safety properties
\* ─────────────────────────────────────────────────────────────────────

\* WD-1 Typed Detector Composition: every applied TBU has a registered type
TypedDetectorComposition ==
    \A tbu \in appliedTBUs: panel[tbu.target][tbu.dtype] >= 0

\* WD-2 Arbitration Determinism: at most one TBU applied per
\* (agent, weight, valid_from); two same-point applied TBUs imply equality.
ArbitrationDeterminism ==
    \A t1, t2 \in appliedTBUs:
        SamePoint(t1, t2) => t1 = t2

\* WD-3 Predictive Welfare Horizon (consistency form):
\* Any realization paired to a prediction MUST lie within the prediction's
\* horizon window [issued_at, due_at + MaxHorizon]. The EmitRealization
\* guard (p.due_at + MaxHorizon >= clockTick) ensures this automatically.
\*
\* Note: the *obligation* to emit a realization (or a MissingRealization
\* event) is operational, enforced by the Python `emit_missing_realization`
\* helper at runtime rather than as a safety property in this TLA+ model.
\* See STATUS.md for the safety/liveness split.
PredictiveHorizon ==
    \A r \in realizations:
        \A p \in predictions:
            r.pred_id = p.id => r.at <= p.due_at + MaxHorizon

\* WD-4 Detector Provenance Disclosure: every applied TBU has a phash field.
DetectorProvenance ==
    \A tbu \in appliedTBUs: tbu.phash \in HashSpace

=============================================================================
