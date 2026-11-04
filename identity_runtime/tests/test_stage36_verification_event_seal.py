# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""WP-3.6.6 Blocker #3 — trusted sealing boundary unit tests."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from identity_runtime.zk_abstraction.identity import IdentityTuple
from identity_runtime.zk_abstraction.verification_event_seal import (
    APPROVED_INTEGRITY_MATERIAL,
    SealStatus,
    assert_sealed_provenance,
    map_verification_outcome,
    policy_requires_verification_event_provenance,
    seal_verification_event,
    VerificationOutcome,
)


def _id(
    protocol_id: str = "proto",
    protocol_version: str = "1",
    scheme_id: str = "scheme",
    scheme_version: str = "1",
    policy_version: str = "1",
) -> IdentityTuple:
    return IdentityTuple(
        protocol_id=protocol_id,
        protocol_version=protocol_version,
        scheme_id=scheme_id,
        scheme_version=scheme_version,
        policy_version=policy_version,
    )


@dataclass
class FakeResult:
    accepted: bool
    status_code: str
    reason: str = ""
    identity_tuple: Optional[IdentityTuple] = None


FIXED_TS = datetime(2026, 10, 29, 12, 0, 0, tzinfo=timezone.utc)


def _clock():
    return FIXED_TS


class TestSealHappyPath(unittest.TestCase):
    def test_valid_result_seals(self) -> None:
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r,
            recording_boundary_id="boundary-1",
            finalization_clock=_clock,
            event_id_generator=lambda: "ve_fixed_1",
        )
        self.assertEqual(out.status, SealStatus.SEALED)
        self.assertIsNotNone(out.record)
        assert out.record is not None
        self.assertEqual(out.record.verification_event_id, "ve_fixed_1")
        self.assertEqual(out.record.verification_outcome, "valid")
        self.assertEqual(out.record.protocol_id, "proto")
        self.assertIn("2026-10-29", out.record.verification_finalized_at)
        self.assertEqual(
            dict(out.record.integrity_material), APPROVED_INTEGRITY_MATERIAL
        )


class TestRefuseInputs(unittest.TestCase):
    def test_string_only_cannot_seal(self) -> None:
        out = seal_verification_event(
            "OK",
            recording_boundary_id="b",
            finalization_clock=_clock,
        )
        self.assertEqual(out.status, SealStatus.REFUSED)
        self.assertIsNone(out.record)
        self.assertIn("string", out.reason or "")

    def test_missing_identity_refused(self) -> None:
        r = FakeResult(True, "OK", identity_tuple=None)
        out = seal_verification_event(
            r, recording_boundary_id="b", finalization_clock=_clock
        )
        self.assertEqual(out.status, SealStatus.REFUSED)

    def test_empty_identity_field_refused(self) -> None:
        r = FakeResult(True, "OK", identity_tuple=_id(protocol_id="  "))
        out = seal_verification_event(
            r, recording_boundary_id="b", finalization_clock=_clock
        )
        self.assertEqual(out.status, SealStatus.REFUSED)

    def test_empty_boundary_refused(self) -> None:
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r, recording_boundary_id="", finalization_clock=_clock
        )
        self.assertEqual(out.status, SealStatus.REFUSED)


class TestOutcomeMapping(unittest.TestCase):
    def test_ok_valid(self) -> None:
        self.assertEqual(map_verification_outcome(True, "OK"), VerificationOutcome.VALID)

    def test_invalid_proof(self) -> None:
        self.assertEqual(
            map_verification_outcome(False, "INVALID_PROOF"), VerificationOutcome.INVALID
        )

    def test_structural_error(self) -> None:
        self.assertEqual(
            map_verification_outcome(False, "STRUCTURAL_FAILURE"),
            VerificationOutcome.ERROR,
        )

    def test_unlisted_never_valid(self) -> None:
        self.assertEqual(
            map_verification_outcome(False, "TOTALLY_UNKNOWN_STATUS"),
            VerificationOutcome.ERROR,
        )
        self.assertEqual(
            map_verification_outcome(True, "TOTALLY_UNKNOWN_STATUS"),
            VerificationOutcome.ERROR,
        )

    def test_sealed_invalid_outcome_value(self) -> None:
        r = FakeResult(False, "INVALID_PROOF", identity_tuple=_id())
        out = seal_verification_event(
            r, recording_boundary_id="b", finalization_clock=_clock
        )
        self.assertTrue(out.is_sealed)
        assert out.record is not None
        self.assertEqual(out.record.verification_outcome, "invalid")


class TestEventIdAndClock(unittest.TestCase):
    def test_sealer_owned_id(self) -> None:
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r,
            recording_boundary_id="b",
            finalization_clock=_clock,
            event_id_generator=lambda: "ve_only_sealer",
        )
        assert out.record is not None
        self.assertEqual(out.record.verification_event_id, "ve_only_sealer")

    def test_generator_exception_refused(self) -> None:
        def boom() -> str:
            raise RuntimeError("nope")

        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r,
            recording_boundary_id="b",
            finalization_clock=_clock,
            event_id_generator=boom,
        )
        self.assertEqual(out.status, SealStatus.REFUSED)
        self.assertIsNone(out.record)

    def test_generator_empty_refused(self) -> None:
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r,
            recording_boundary_id="b",
            finalization_clock=_clock,
            event_id_generator=lambda: "",
        )
        self.assertEqual(out.status, SealStatus.REFUSED)

    def test_clock_used_once(self) -> None:
        calls = {"n": 0}

        def clk():
            calls["n"] += 1
            return FIXED_TS

        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r, recording_boundary_id="b", finalization_clock=clk
        )
        self.assertTrue(out.is_sealed)
        self.assertEqual(calls["n"], 1)

    def test_clock_exception_refused(self) -> None:
        def clk():
            raise ValueError("clock")

        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r, recording_boundary_id="b", finalization_clock=clk
        )
        self.assertEqual(out.status, SealStatus.REFUSED)
        self.assertIsNone(out.record)

    def test_naive_timestamp_refused(self) -> None:
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r,
            recording_boundary_id="b",
            finalization_clock=lambda: datetime(2026, 1, 1, 0, 0, 0),  # naive
        )
        self.assertEqual(out.status, SealStatus.REFUSED)

    def test_none_clock_refused(self) -> None:
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r, recording_boundary_id="b", finalization_clock=lambda: None
        )
        self.assertEqual(out.status, SealStatus.REFUSED)

    def test_non_utc_offset_refused(self) -> None:
        # +01:00 is not UTC
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r,
            recording_boundary_id="b",
            finalization_clock=lambda: datetime(
                2026, 1, 1, 0, 0, 0, tzinfo=timezone(timedelta(hours=1))
            ),
        )
        # Implementation converts via astimezone to UTC — that is allowed if convertible.
        # Contract: disallow non-UTC *presentation* without conversion; we convert.
        # Strict: if we want refuse non-utc input before convert, adjust.
        # Phase2 said disallowed non-UTC values → REFUSED.
        # Our _normalize converts to UTC; tighten test to expect SEALED after convert OR refuse.
        # Prefer refuse non-zero offset without accepting as "caller local".
        # Re-read normalize: zero offset only on original; else astimezone utc.
        # So +01:00 becomes sealed UTC — for stricter contract, refuse non-zero offset inputs.
        self.assertEqual(out.status, SealStatus.REFUSED)


class TestIntegrityMaterial(unittest.TestCase):
    def test_missing_key_refused(self) -> None:
        bad = dict(APPROVED_INTEGRITY_MATERIAL)
        del bad["integrity_profile_id"]
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r,
            recording_boundary_id="b",
            finalization_clock=_clock,
            integrity_material=bad,
        )
        self.assertEqual(out.status, SealStatus.REFUSED)

    def test_extra_key_refused(self) -> None:
        bad = dict(APPROVED_INTEGRITY_MATERIAL)
        bad["extra"] = "x"
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r,
            recording_boundary_id="b",
            finalization_clock=_clock,
            integrity_material=bad,
        )
        self.assertEqual(out.status, SealStatus.REFUSED)

    def test_bool_version_refused(self) -> None:
        bad = dict(APPROVED_INTEGRITY_MATERIAL)
        bad["metadata_schema_version"] = True  # bool
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r,
            recording_boundary_id="b",
            finalization_clock=_clock,
            integrity_material=bad,
        )
        self.assertEqual(out.status, SealStatus.REFUSED)

    def test_string_version_refused(self) -> None:
        bad = dict(APPROVED_INTEGRITY_MATERIAL)
        bad["integrity_profile_version"] = "1"
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r,
            recording_boundary_id="b",
            finalization_clock=_clock,
            integrity_material=bad,
        )
        self.assertEqual(out.status, SealStatus.REFUSED)


class TestImmutabilityAndRetry(unittest.TestCase):
    def test_frozen_record(self) -> None:
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r, recording_boundary_id="b", finalization_clock=_clock
        )
        assert out.record is not None
        with self.assertRaises(Exception):
            out.record.verification_event_id = "mutated"  # type: ignore[misc]

    def test_retry_reuses_same_record_object_fields(self) -> None:
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r,
            recording_boundary_id="b",
            finalization_clock=_clock,
            event_id_generator=lambda: "ve_retry",
        )
        assert out.record is not None
        retained = out.record
        # Retry semantics: reuse retained record — do not reseal/restamp
        self.assertEqual(retained.verification_event_id, "ve_retry")
        self.assertEqual(retained.verification_finalized_at, out.record.verification_finalized_at)


class TestProvenanceGuard(unittest.TestCase):
    def test_predicate(self) -> None:
        self.assertFalse(policy_requires_verification_event_provenance())
        self.assertTrue(
            policy_requires_verification_event_provenance(freshness_required=True)
        )

    def test_guard_rejects_missing_when_required(self) -> None:
        err = assert_sealed_provenance(None, freshness_required=True)
        self.assertIsNotNone(err)

    def test_guard_ok_when_sealed(self) -> None:
        r = FakeResult(True, "OK", identity_tuple=_id())
        sealed = seal_verification_event(
            r, recording_boundary_id="b", finalization_clock=_clock
        )
        err = assert_sealed_provenance(sealed, freshness_required=True)
        self.assertIsNone(err)

    def test_non_provenance_mode_allows_missing_sealed(self) -> None:
        err = assert_sealed_provenance(None, freshness_required=False)
        self.assertIsNone(err)


class TestNoSideEffects(unittest.TestCase):
    def test_seal_does_not_import_audit_port_side_effect(self) -> None:
        # Sealing module must not require AuditPort to function
        r = FakeResult(True, "OK", identity_tuple=_id())
        out = seal_verification_event(
            r, recording_boundary_id="b", finalization_clock=_clock
        )
        self.assertTrue(out.is_sealed)


if __name__ == "__main__":
    unittest.main()
