# ADR 001: Principal-Declared Valence Over Service-Declared Valence

**Status:** Accepted
**Date:** 2026-04-16
**Authors:** Ravi Kiran Kadaboina

---

## Context

Every existing mechanism for routing outcome signals in autonomous
agent systems defines *good* from the service provider's perspective.
Reinforcement learning from human feedback (RLHF) collects preference
labels from researchers or crowdworkers. Multi-agent reinforcement
learning (MARL) reward functions are designed by the environment
designer. The IAB Tech Lab User Context Protocol (UCP) exchanges
reinforcement signals (impressions, clicks, conversions) whose
interpretation is governed by the advertiser. A2A's task-success
signal is binary and defined by the protocol, not the human on whose
behalf the task ran.

The principal, the human whose agent initiated the task, has no
protocol-level mechanism to declare their own satisfaction weights.
When a personal agent nudges a user about a grocery pickup, the agent
optimizes for task completion because that is what its reward model
measures. Whether the user felt the nudge was timely, useful, or
stressful is not represented anywhere in the protocol.

We call this the **welfare inversion**: the feedback loop is closed in
the direction of the service provider, not the principal.

Three models were considered for how Phala should compute the valence
of a SatisfactionRecord:

1. **Service-declared valence.** The callee or the protocol defines
   signal weights; the principal's preferences are not carried.
2. **Global user preferences.** The principal declares a single global
   preference profile that applies identically across every context.
3. **Per-context principal declarations (PSM).** The principal declares
   a `PrincipalSatisfactionModel` that carries per-context
   `ContextProfile` entries, each with its own signal_weights,
   deadline_tolerance, overdue_penalty_multiplier, and related fields.
   Every SatisfactionRecord whose context matches a declared profile
   MUST compute valence using the profile's weights.

## Decision

Phala implements model 3: principal-declared, per-context valence
(the `PrincipalSatisfactionModel`, PSM). The PSM is authored and
controlled exclusively by the principal (PSM-1). When a valid PSM
exists for the context of a SatisfactionRecord, no remote agent may
substitute its own formula; valence MUST be computed using the PSM's
signal weights. When no PSM exists for the context, a reference formula
defined in §3.2 of the paper is used as a fallback.

## Rationale

**Against model 1 (service-declared):** Reinstates the welfare
inversion. The principal has no voice in what counts as a good outcome
for their own interactions. This is what every existing system does
and what Phala explicitly rejects.

**Against model 2 (global preferences):** Collapses legitimate
contextual variation. A principal at a surgery app cares deeply about
biometric storage and third-party sharing; the same principal at a
pharmacy has no issue with prescription data being recorded but would
strongly object to that data being shared with an advertising network.
A single global profile cannot express this asymmetry. Sensitivity is
context-dependent; a single "I agree" flag cannot encode it.

**For model 3 (per-context PSM):**

- The PSM sits structurally one layer above the SatisfactionRecord
  computation. Its signal_weights govern every valence calculation for
  the matching context, in every agent in the network, for this
  principal. No agent can substitute its own preference while a PSM
  version applies.
- Immutability with append-only versioning (PSM-2) preserves the audit
  trail of the principal's evolving preferences, which is important
  both for accountability and for welfare analysis over time.
- The ContextProfile's structured fields
  (`overdue_penalty_multiplier`, `explicit_rating_floor`,
  `welfare_lookback_days`) carry principal-specific context that a
  global profile cannot. Some principals rate systematically low and
  need a floor; some care three times as much about deadlines as the
  default; the PSM is the place this context lives.
- A separate regulatory-context extension could plug in a
  complementary floor on top of the principal's declared preferences
  for regulatorily-protected categories; the PSM handles the
  per-principal layer cleanly without needing to encode jurisdictional
  frameworks in its own schema.

## Consequences

- Implementing agents take on a non-trivial burden: they MUST look up
  the principal's active PSM for the interaction context before
  computing valence, and MUST honor the declared signal_weights.
  Agents that substitute their own formula where a PSM exists are
  non-conformant.
- User experience design matters. Principals will not author PSMs by
  editing JSON. Client applications MUST surface the preference
  declaration in a human-usable form (e.g., a slider labelled "How
  much does meeting the deadline matter vs. being reminded less
  often?") and translate that into ContextProfile weights. The PSM
  weight arithmetic is implementation detail that should not be
  exposed to the principal.
- The PSM is a new object on the critical path: agents that cannot
  look up the PSM within their latency budget must fall back to the
  reference formula and set `psm_version = null` on the resulting
  SatisfactionRecord. This is explicitly allowed in §3.2's fallback
  rules.
- Protocol evolution is simplified. New contexts can be added by
  principals without protocol changes; new signal types require only
  that agents and PSMs agree on a key in `signal_components` /
  `signal_weights`. The structural invariant (PSM governs valence) is
  stable.
- The decision embeds a normative stance: Phala is not a neutral
  protocol. It takes a position that the principal's definition of
  welfare is authoritative for interactions conducted on their behalf.
  This stance is stated in the paper's abstract and is not expected
  to change.
