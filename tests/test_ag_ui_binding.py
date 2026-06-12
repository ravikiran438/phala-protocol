# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""Tests for the Phala AG-UI binding (Governance over AG-UI)."""

from __future__ import annotations

import pytest

from phala.ag_ui import (
    GOVERNANCE_KEY,
    meta_event_to_satisfaction,
    model_state_snapshot,
    resolve_satisfaction,
    satisfaction_interrupt,
)
from phala.types.phala_service_ref import PHALA_EXTENSION_URI
from phala.types.principal_satisfaction_model import PrincipalSatisfactionModel
from phala.types.satisfaction_record import SatisfactionRecord, SatisfactionSource

OE = "outcome-1"


def _psm() -> PrincipalSatisfactionModel:
    return PrincipalSatisfactionModel(
        principal_id="p-1", version="1", declared_at="2026-04-01T09:00:00Z",
        context_profiles={})


def _interrupt():
    ev = satisfaction_interrupt(outcome_event_id=OE)
    return ev["outcome"]["interrupts"][0]


# --- PSM state snapshot ------------------------------------------------------

def test_model_snapshot_keyed_by_phala_uri():
    ev = model_state_snapshot(_psm())
    assert ev["type"] == "STATE_SNAPSHOT"
    assert PHALA_EXTENSION_URI in ev["snapshot"]
    assert ev["snapshot"][PHALA_EXTENSION_URI]["principal_id"] == "p-1"


# --- prompted interrupt + resolve --------------------------------------------

def test_interrupt_shape_and_identity():
    it = _interrupt()
    assert it["reason"] == "input_required"
    gov = it["metadata"][GOVERNANCE_KEY]
    assert gov["uri"] == PHALA_EXTENSION_URI          # B-1
    assert gov["type"] == "SatisfactionRecord"
    assert gov["outcome_event_id"] == OE


def test_resolve_positive_valence():
    it = _interrupt()
    rec = resolve_satisfaction(
        interrupt=it,
        resume={"interruptId": it["id"], "status": "resolved", "payload": {"valence": 0.8}},
        record_id="sr-1", recorded_at="2026-04-01T10:05:00Z")
    assert isinstance(rec, SatisfactionRecord)
    assert rec.valence == 0.8
    assert rec.source is SatisfactionSource.EXPLICIT
    assert rec.confidence == 1.0
    assert rec.signal_components == {"explicit_valence": 0.8}
    assert rec.outcome_event_id == OE


def test_resolve_refused_is_no_evidence():
    it = _interrupt()
    rec = resolve_satisfaction(
        interrupt=it,
        resume={"interruptId": it["id"], "status": "resolved", "payload": {"refused": True}},
        record_id="sr-1", recorded_at="2026-04-01T10:05:00Z")
    # SR-1: confidence 0 when no evidence; signal_components empty.
    assert rec.valence == 0.0
    assert rec.confidence == 0.0
    assert rec.signal_components == {}


def test_resolve_cancelled_is_no_evidence():
    it = _interrupt()
    rec = resolve_satisfaction(
        interrupt=it, resume={"interruptId": it["id"], "status": "cancelled"},
        record_id="sr-1", recorded_at="2026-04-01T10:05:00Z")
    assert rec.confidence == 0.0
    assert rec.signal_components == {}


def test_resolve_resolved_requires_valence():
    it = _interrupt()
    with pytest.raises(ValueError):
        resolve_satisfaction(
            interrupt=it,
            resume={"interruptId": it["id"], "status": "resolved", "payload": {}},
            record_id="sr-1", recorded_at="2026-04-01T10:05:00Z")


def test_resolve_rejects_foreign_interrupt():
    foreign = {"id": "x", "reason": "input_required",
               "metadata": {GOVERNANCE_KEY: {"uri": "https://example.com/other", "type": "SatisfactionRecord"}}}
    with pytest.raises(ValueError):
        resolve_satisfaction(
            interrupt=foreign,
            resume={"interruptId": "x", "status": "resolved", "payload": {"valence": 1.0}},
            record_id="sr-1", recorded_at="2026-04-01T10:05:00Z")


# --- volunteered MetaEvent ---------------------------------------------------

def test_meta_thumbs_up():
    rec = meta_event_to_satisfaction(
        meta_event={"metaType": "thumbs_up"}, outcome_event_id=OE,
        record_id="sr-2", recorded_at="2026-04-01T10:06:00Z")
    assert rec.valence == 1.0
    assert rec.source is SatisfactionSource.EXPLICIT
    assert rec.confidence == 1.0


def test_meta_thumbs_down():
    rec = meta_event_to_satisfaction(
        meta_event={"metaType": "thumbs_down"}, outcome_event_id=OE,
        record_id="sr-2", recorded_at="2026-04-01T10:06:00Z")
    assert rec.valence == -1.0


def test_meta_rating_maps_to_unit_interval():
    # 5-point scale: 5 -> +1, 3 -> 0, 1 -> -1.
    top = meta_event_to_satisfaction(
        meta_event={"metaType": "rating", "payload": 5}, outcome_event_id=OE,
        record_id="sr-a", recorded_at="t")
    mid = meta_event_to_satisfaction(
        meta_event={"metaType": "rating", "payload": 3}, outcome_event_id=OE,
        record_id="sr-b", recorded_at="t")
    bot = meta_event_to_satisfaction(
        meta_event={"metaType": "rating", "payload": 1}, outcome_event_id=OE,
        record_id="sr-c", recorded_at="t")
    assert top.valence == 1.0
    assert mid.valence == 0.0
    assert bot.valence == -1.0


def test_meta_rating_out_of_range():
    with pytest.raises(ValueError):
        meta_event_to_satisfaction(
            meta_event={"metaType": "rating", "payload": 9}, outcome_event_id=OE,
            record_id="sr-x", recorded_at="t")


def test_meta_unrecognized_type():
    with pytest.raises(ValueError):
        meta_event_to_satisfaction(
            meta_event={"metaType": "shrug"}, outcome_event_id=OE,
            record_id="sr-x", recorded_at="t")
