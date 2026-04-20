# Phala MCP Server — Sample Payloads

Ready-to-paste JSON for every tool exposed by `phala-mcp`. Drop any
block at an MCP client with an invocation like:

> Call `validate_belief_privacy` with this input: `<paste>`

Each tool has one happy-path payload (returns `"ok": true`) and a
note on how to trip the failure path.

---

## validate_outcome_event

**What it checks:** structural invariants on an OutcomeEvent (§3.1).

```json
{
  "event": {
    "id": "00000000-0000-4000-8000-000000000001",
    "task_id": "task-abc",
    "agents_involved": ["agent-a", "agent-b"],
    "resolved_at": "2026-04-16T10:00:00Z",
    "resolution_type": "completed",
    "latency_ms": 12000,
    "principal_id": "p-001",
    "session_hash": "sha256:deadbeef"
  }
}
```

**Failure variant:** set `"agents_involved": []` — OE requires at
least one agent.

---

## validate_satisfaction_record

**What it checks:** structural invariants on a SatisfactionRecord
(§3.2), including `valence` in [-1, 1].

```json
{
  "record": {
    "id": "sr-1",
    "outcome_event_id": "oe-1",
    "valence": 0.6,
    "source": "implicit",
    "signal_components": {"completion_latency_ratio": 0.8},
    "recorded_at": "2026-04-16T10:00:10Z",
    "confidence": 0.9,
    "psm_version": "v1"
  }
}
```

**Failure variant:** set `"valence": 2.0` (out of range).

---

## validate_belief_update

**What it checks:** structural invariants on a BeliefUpdate (§3.3),
including `weight_delta` in [-1, 1]. Note: BU-Privacy (no
signal-evidence fields) is enforced separately by
`validate_belief_privacy`.

```json
{
  "update": {
    "id": "bu-1",
    "satisfaction_record_id": "sr-1",
    "target_agent_id": "agent-b",
    "weight_key": "routing.agent_b.preference",
    "weight_delta": 0.04,
    "context_hash": "sha256:feedface",
    "valid_from": "2026-04-16T10:00:10Z",
    "ttl_seconds": 3600
  }
}
```

**Failure variant:** set `"weight_delta": 2.0` (out of range).

---

## validate_principal_satisfaction_model

**What it checks:** structural invariants on a PSM (§3.4), including
at least one context profile with all required fields.

```json
{
  "model": {
    "principal_id": "p-001",
    "version": "v1",
    "declared_at": "2026-04-16T08:00:00Z",
    "context_profiles": {
      "travel": {
        "context_key": "travel",
        "signal_weights": {"completion_latency_ratio": 1.0},
        "deadline_tolerance_seconds": 1800,
        "overdue_penalty_multiplier": 1.5,
        "explicit_rating_floor": 0,
        "welfare_lookback_days": 14
      }
    }
  }
}
```

**Failure variant:** drop `"deadline_tolerance_seconds"` from the
context profile to see the Pydantic "field required" error.

---

## validate_welfare_trace

**What it checks:** structural invariants on a WelfareTrace (§3.5),
including `task_completion_trend` ∈ {improving, stable, degrading}.

```json
{
  "trace": {
    "principal_id": "p-001",
    "window_days": 30,
    "computed_at": "2026-04-16T00:00:00Z",
    "task_completion_trend": "stable",
    "agent_initiation_frequency_7d": 3,
    "overdue_rate_30d": 0.05,
    "autonomy_index": 0.8,
    "cognitive_load_proxy": 0.2,
    "context_density_7d": 5
  }
}
```

**Failure variant:** set `"task_completion_trend": "steady"` (not a
valid enum value).

---

## validate_belief_privacy

**What it checks:** invariant BU-1 (§3.3) — serialized BeliefUpdate
must not carry any signal-evidence fields that could leak private
behavioral signals.

```json
{
  "payload": {
    "id": "bu-1",
    "weight_key": "routing.x",
    "weight_delta": 0.1
  }
}
```

Returns `{"ok": true}`.

**Failure variant:** add a forbidden field to trip BU-1. Forbidden
keys include `signal_components`, `signal_component`, `raw_signals`,
`behavioural_signals`, `behavioral_signals`:

```json
{
  "payload": {
    "id": "bu-1",
    "weight_delta": 0.1,
    "signal_components": {"completion_latency_ratio": 0.8}
  }
}
```
