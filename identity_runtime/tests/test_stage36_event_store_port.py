# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""WP-3.6.6 Blocker #4 Phase A — Event Store port and type contract tests."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from types import MappingProxyType

from identity_runtime.zk_abstraction.event_store import (
    EventStore,
    EventStorePersistOutcome,
    EventStorePersistRequest,
    EventStorePersistResult,
    EventStoreResolveOutcome,
    EventStoreResolveResult,
    TrustedEvidenceView,
)
from identity_runtime.zk_abstraction.identity import IdentityTuple
from identity_runtime.zk_abstraction.verification_event_seal import (
    APPROVED_INTEGRITY_MATERIAL,
    RECORD_SCHEMA_VERSION,
    SealResult,
    SealStatus,
    VerificationEventRecord,
    seal_verification_event,
)


def _clock() -> datetime:
    return datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone.utc)


def _identity() -> IdentityTuple:
    return IdentityTuple(
        protocol_id="proto",
        protocol_version="1",
        scheme_id="scheme",
        scheme_version="1",
        policy_version="1",
    )


class _FakeResult:
    def __init__(self, accepted: bool, status_code: str, identity_tuple: IdentityTuple):
        self.accepted = accepted
        self.status_code = status_code
        self.identity_tuple = identity_tuple


def _genuine_sealed() -> SealResult:
    r = _FakeResult(True, "OK", _identity())
    out = seal_verification_event(
        r, recording_boundary_id="boundary-1", finalization_clock=_clock
    )
    assert out.is_trusted_sealed and out.record is not None
    return out


def _raw_view(**overrides):
    """Direct construction without factory capability (untrusted / unusable)."""
    base = dict(
        verification_event_id="ve_direct",
        verification_finalized_at="2020-01-01T00:00:00Z",
        verification_outcome="valid",
        protocol_id="proto",
        protocol_version="1",
        scheme_id="scheme",
        scheme_version="1",
        policy_version="1",
        record_schema_version=RECORD_SCHEMA_VERSION,
        recording_boundary_id="direct",
        integrity_material=dict(APPROVED_INTEGRITY_MATERIAL),
    )
    base.update(overrides)
    return TrustedEvidenceView(**base)


class TestPersistResultEnum(unittest.TestCase):
    def test_exact_membership(self) -> None:
        names = {m.name for m in EventStorePersistResult}
        self.assertEqual(names, {"CONFIRMED", "FAILED", "UNCERTAIN"})

    def test_values(self) -> None:
        self.assertEqual(EventStorePersistResult.CONFIRMED.value, "CONFIRMED")
        self.assertEqual(EventStorePersistResult.FAILED.value, "FAILED")
        self.assertEqual(EventStorePersistResult.UNCERTAIN.value, "UNCERTAIN")


class TestResolveResultEnum(unittest.TestCase):
    def test_exact_membership(self) -> None:
        names = {m.name for m in EventStoreResolveResult}
        self.assertEqual(
            names,
            {
                "FOUND_VALID",
                "NOT_FOUND",
                "FOUND_INVALID",
                "UNAVAILABLE",
                "LOOKUP_UNCERTAIN",
            },
        )

    def test_not_merged_with_persist(self) -> None:
        persist = {m.value for m in EventStorePersistResult}
        resolve = {m.value for m in EventStoreResolveResult}
        self.assertTrue(persist.isdisjoint(resolve))

    def test_mismatched_not_a_resolution_outcome(self) -> None:
        self.assertNotIn("MISMATCHED", {m.name for m in EventStoreResolveResult})
        self.assertNotIn("mismatched", {m.value for m in EventStoreResolveResult})


class TestTrustedEvidenceView(unittest.TestCase):
    def test_from_trusted_sealed_preserves_event_id(self) -> None:
        sealed = _genuine_sealed()
        view = TrustedEvidenceView.from_trusted_sealed(sealed)
        self.assertEqual(view.verification_event_id, sealed.record.verification_event_id)
        self.assertEqual(view.verification_finalized_at, sealed.record.verification_finalized_at)
        self.assertEqual(view.protocol_id, sealed.record.protocol_id)
        self.assertTrue(view.is_trusted_view)

    def test_top_level_field_reassignment_rejected(self) -> None:
        view = TrustedEvidenceView.from_trusted_sealed(_genuine_sealed())
        with self.assertRaises(FrozenInstanceError):
            view.verification_event_id = "ve_mutated"  # type: ignore[misc]

    def test_nested_mapping_not_mutable(self) -> None:
        view = TrustedEvidenceView.from_trusted_sealed(_genuine_sealed())
        self.assertIsInstance(view.integrity_material, MappingProxyType)
        with self.assertRaises(TypeError):
            view.integrity_material["integrity_profile_id"] = "P99"  # type: ignore[index]
        # mappingproxy has no clear(); mutation APIs raise TypeError or AttributeError
        with self.assertRaises((TypeError, AttributeError)):
            view.integrity_material.clear()  # type: ignore[attr-defined]

    def test_nested_mapping_value_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            _raw_view(integrity_material={"outer": {"inner": 1}})
        self.assertIn("immutable scalars", str(ctx.exception))

    def test_nested_sequence_value_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            _raw_view(integrity_material={"tags": ["a", "b"]})
        self.assertIn("immutable scalars", str(ctx.exception))

    def test_mutable_object_value_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _raw_view(integrity_material={"obj": object()})
        with self.assertRaises(ValueError):
            _raw_view(integrity_material={"flag": True})  # bool excluded

    def test_valid_scalar_integrity_material_representable(self) -> None:
        view = TrustedEvidenceView.from_trusted_sealed(_genuine_sealed())
        self.assertEqual(view.integrity_material["integrity_profile_id"], "P0")
        self.assertEqual(view.integrity_material["integrity_profile_version"], 1)
        self.assertIsInstance(view.integrity_material["metadata_schema"], str)

    def test_rejects_untrusted_seal_result(self) -> None:
        rec = VerificationEventRecord(
            verification_event_id="ve_forged",
            verification_finalized_at="2020-01-01T00:00:00Z",
            verification_outcome="valid",
            protocol_id="proto",
            protocol_version="1",
            scheme_id="scheme",
            scheme_version="1",
            policy_version="1",
            record_schema_version=RECORD_SCHEMA_VERSION,
            recording_boundary_id="attacker",
            integrity_material=dict(APPROVED_INTEGRITY_MATERIAL),
        )
        forged = SealResult(status=SealStatus.SEALED, record=rec)
        self.assertFalse(forged.is_trusted_sealed)
        with self.assertRaises(ValueError) as ctx:
            TrustedEvidenceView.from_trusted_sealed(forged)
        self.assertIn("trusted_evidence_requires_sealer_origin", str(ctx.exception))

    def test_rejects_none(self) -> None:
        with self.assertRaises(ValueError):
            TrustedEvidenceView.from_trusted_sealed(None)  # type: ignore[arg-type]

    def test_empty_verification_event_id_rejected_on_view(self) -> None:
        with self.assertRaises(ValueError):
            TrustedEvidenceView(
                verification_event_id="",
                verification_finalized_at="2026-01-01T00:00:00Z",
                verification_outcome="valid",
                protocol_id="p",
                protocol_version="1",
                scheme_id="s",
                scheme_version="1",
                policy_version="1",
                record_schema_version=RECORD_SCHEMA_VERSION,
                recording_boundary_id="b",
                integrity_material=dict(APPROVED_INTEGRITY_MATERIAL),
            )

    def test_direct_construction_not_trusted_view(self) -> None:
        view = _raw_view()
        self.assertFalse(view.is_trusted_view)
        self.assertIsInstance(view.integrity_material, MappingProxyType)

    def test_capability_not_accepted_as_constructor_argument(self) -> None:
        import identity_runtime.zk_abstraction.event_store as mod

        with self.assertRaises(TypeError):
            TrustedEvidenceView(
                verification_event_id="ve_x",
                verification_finalized_at="2026-01-01T00:00:00Z",
                verification_outcome="valid",
                protocol_id="p",
                protocol_version="1",
                scheme_id="s",
                scheme_version="1",
                policy_version="1",
                record_schema_version=RECORD_SCHEMA_VERSION,
                recording_boundary_id="b",
                integrity_material=dict(APPROVED_INTEGRITY_MATERIAL),
                _capability=mod._VIEW_CAPABILITY,  # type: ignore[call-arg]
            )


class TestPersistRequestRequiresTrustedView(unittest.TestCase):
    def test_genuine_view_accepted(self) -> None:
        view = TrustedEvidenceView.from_trusted_sealed(_genuine_sealed())
        req = EventStorePersistRequest(evidence=view)
        self.assertEqual(req.verification_event_id, view.verification_event_id)

    def test_direct_view_cannot_bypass_into_persist_request(self) -> None:
        view = _raw_view()
        with self.assertRaises(ValueError) as ctx:
            EventStorePersistRequest(evidence=view)
        self.assertIn("evidence_requires_trusted_view", str(ctx.exception))


class TestRequestAndOutcomes(unittest.TestCase):
    def test_persist_outcome_holds_result(self) -> None:
        out = EventStorePersistOutcome(
            result=EventStorePersistResult.FAILED,
            reason="verification_event_payload_conflict",
        )
        self.assertIs(out.result, EventStorePersistResult.FAILED)
        self.assertEqual(out.reason, "verification_event_payload_conflict")

    def test_persist_outcome_rejects_non_enum_result(self) -> None:
        with self.assertRaises(ValueError):
            EventStorePersistOutcome(result="CONFIRMED")  # type: ignore[arg-type]

    def test_no_event_store_record_wrapper_symbol(self) -> None:
        import identity_runtime.zk_abstraction.event_store as mod

        self.assertFalse(hasattr(mod, "EventStoreRecord"))


class TestResolveOutcomeInvariants(unittest.TestCase):
    def test_found_valid_with_trusted_evidence(self) -> None:
        view = TrustedEvidenceView.from_trusted_sealed(_genuine_sealed())
        out = EventStoreResolveOutcome(
            result=EventStoreResolveResult.FOUND_VALID,
            evidence=view,
        )
        self.assertIs(out.result, EventStoreResolveResult.FOUND_VALID)
        self.assertIsInstance(out.evidence, TrustedEvidenceView)

    def test_found_valid_without_evidence_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            EventStoreResolveOutcome(result=EventStoreResolveResult.FOUND_VALID)
        self.assertIn("FOUND_VALID requires", str(ctx.exception))

    def test_found_valid_with_untrusted_evidence_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            EventStoreResolveOutcome(
                result=EventStoreResolveResult.FOUND_VALID,
                evidence=_raw_view(),
            )
        self.assertIn("evidence_requires_trusted_view", str(ctx.exception))

    def test_found_valid_wrong_evidence_type_rejected(self) -> None:
        with self.assertRaises(ValueError):
            EventStoreResolveOutcome(
                result=EventStoreResolveResult.FOUND_VALID,
                evidence="not-a-view",  # type: ignore[arg-type]
            )

    def test_not_found_without_evidence_ok(self) -> None:
        out = EventStoreResolveOutcome(result=EventStoreResolveResult.NOT_FOUND)
        self.assertIsNone(out.evidence)

    def test_not_found_with_evidence_rejected(self) -> None:
        view = TrustedEvidenceView.from_trusted_sealed(_genuine_sealed())
        with self.assertRaises(ValueError) as ctx:
            EventStoreResolveOutcome(
                result=EventStoreResolveResult.NOT_FOUND,
                evidence=view,
            )
        self.assertIn("must not contain evidence", str(ctx.exception))

    def test_unavailable_with_evidence_rejected(self) -> None:
        view = TrustedEvidenceView.from_trusted_sealed(_genuine_sealed())
        with self.assertRaises(ValueError):
            EventStoreResolveOutcome(
                result=EventStoreResolveResult.UNAVAILABLE,
                evidence=view,
            )

    def test_lookup_uncertain_with_evidence_rejected(self) -> None:
        view = TrustedEvidenceView.from_trusted_sealed(_genuine_sealed())
        with self.assertRaises(ValueError):
            EventStoreResolveOutcome(
                result=EventStoreResolveResult.LOOKUP_UNCERTAIN,
                evidence=view,
            )

    def test_found_invalid_without_evidence_ok(self) -> None:
        out = EventStoreResolveOutcome(result=EventStoreResolveResult.FOUND_INVALID)
        self.assertIsNone(out.evidence)

    def test_found_invalid_with_trusted_evidence_ok(self) -> None:
        view = TrustedEvidenceView.from_trusted_sealed(_genuine_sealed())
        out = EventStoreResolveOutcome(
            result=EventStoreResolveResult.FOUND_INVALID,
            evidence=view,
        )
        self.assertIs(out.result, EventStoreResolveResult.FOUND_INVALID)
        self.assertTrue(out.evidence.is_trusted_view)

    def test_found_invalid_with_untrusted_evidence_rejected(self) -> None:
        with self.assertRaises(ValueError):
            EventStoreResolveOutcome(
                result=EventStoreResolveResult.FOUND_INVALID,
                evidence=_raw_view(),
            )

    def test_invalid_result_type_rejected(self) -> None:
        with self.assertRaises(ValueError):
            EventStoreResolveOutcome(result="FOUND_VALID")  # type: ignore[arg-type]

    def test_unavailable_without_evidence_ok(self) -> None:
        out = EventStoreResolveOutcome(result=EventStoreResolveResult.UNAVAILABLE)
        self.assertIsNone(out.evidence)

    def test_lookup_uncertain_without_evidence_ok(self) -> None:
        out = EventStoreResolveOutcome(result=EventStoreResolveResult.LOOKUP_UNCERTAIN)
        self.assertIsNone(out.evidence)


class TestProtocolSurface(unittest.TestCase):
    def test_protocol_declares_persist_and_resolve(self) -> None:
        self.assertTrue(callable(getattr(EventStore, "persist", None)))
        self.assertTrue(callable(getattr(EventStore, "resolve", None)))

    def test_structural_fake_satisfies_protocol(self) -> None:
        class _FakeStore:
            def persist(self, request: EventStorePersistRequest) -> EventStorePersistOutcome:
                return EventStorePersistOutcome(result=EventStorePersistResult.CONFIRMED)

            def resolve(self, verification_event_id: str) -> EventStoreResolveOutcome:
                return EventStoreResolveOutcome(result=EventStoreResolveResult.NOT_FOUND)

        store: EventStore = _FakeStore()
        view = TrustedEvidenceView.from_trusted_sealed(_genuine_sealed())
        p = store.persist(EventStorePersistRequest(evidence=view))
        self.assertIs(p.result, EventStorePersistResult.CONFIRMED)
        r = store.resolve(view.verification_event_id)
        self.assertIs(r.result, EventStoreResolveResult.NOT_FOUND)


class TestOwnershipBoundaries(unittest.TestCase):
    def test_does_not_export_audit_commit_result_alias(self) -> None:
        import identity_runtime.zk_abstraction.event_store as mod

        self.assertFalse(hasattr(mod, "AuditCommitResult"))

    def test_persist_enum_is_not_audit_commit_result(self) -> None:
        from identity_runtime.zk_abstraction.audit_port import AuditCommitResult

        self.assertIsNot(EventStorePersistResult, AuditCommitResult)
        self.assertNotEqual(
            type(EventStorePersistResult.CONFIRMED),
            type(AuditCommitResult.CONFIRMED),
        )


if __name__ == "__main__":
    unittest.main()
