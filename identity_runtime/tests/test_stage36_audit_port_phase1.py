# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""WP-3.6.5 Phase 1 — AuditPort contract types and from_path_result tests."""

from __future__ import annotations

import unittest
from dataclasses import replace

from identity_runtime.zk_abstraction.audit_port import (
    AuditCommitResult,
    AuditGatedPathResult,
    AuditReadResult,
    AuditReadStatus,
    EvidenceBindingError,
    OperationEvidence,
    assert_no_forbidden_evidence_keys,
    from_path_result,
    parse_audit_timestamp,
)
from identity_runtime.zk_abstraction.identity import IdentityTuple
from identity_runtime.zk_abstraction.runtime_proof_path import (
    AdmittedClaim,
    EnforcementOutcome,
    FailureClass,
    MatrixDisposition,
    MatrixPolicy,
    PathResult,
    run_runtime_proof_path,
)


def _identity(**kwargs) -> IdentityTuple:
    base = dict(
        protocol_id="sf-zk",
        protocol_version="1.0",
        scheme_id="mock-scheme",
        scheme_version="1",
        policy_version="pol-1",
    )
    base.update(kwargs)
    return IdentityTuple(**base)


def _policy(**kwargs) -> MatrixPolicy:
    base = dict(
        policy_id=None,
        policy_version="pol-1",
        allow_when_valid=True,
    )
    base.update(kwargs)
    return MatrixPolicy(**base)


class TestAuditCommitResult(unittest.TestCase):
    def test_three_states_exact_values(self) -> None:
        self.assertEqual(AuditCommitResult.CONFIRMED.value, "CONFIRMED")
        self.assertEqual(AuditCommitResult.FAILED.value, "FAILED")
        self.assertEqual(AuditCommitResult.UNCERTAIN.value, "UNCERTAIN")
        self.assertEqual(
            {m.value for m in AuditCommitResult},
            {"CONFIRMED", "FAILED", "UNCERTAIN"},
        )


class TestAuditReadResultInvariants(unittest.TestCase):
    def test_found_requires_evidence(self) -> None:
        with self.assertRaises(ValueError):
            AuditReadResult(status=AuditReadStatus.FOUND, evidence=None)

    def test_not_found_clean(self) -> None:
        r = AuditReadResult(status=AuditReadStatus.NOT_FOUND)
        self.assertIsNone(r.evidence)
        self.assertIsNone(r.reason)

    def test_read_error_requires_reason(self) -> None:
        with self.assertRaises(ValueError):
            AuditReadResult(status=AuditReadStatus.READ_ERROR, reason=None)
        with self.assertRaises(ValueError):
            AuditReadResult(status=AuditReadStatus.READ_ERROR, reason="")


class TestFromPathResultAllow(unittest.TestCase):
    def test_allow_path_preserves_bindings_and_enums(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-allow-1",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(policy_id="named-pol"),
            verification_event_id="ve_test_allow_1",
        )
        self.assertTrue(path.authorization_success)
        self.assertIsNotNone(path.aep)
        self.assertIsNotNone(path.decision)

        evidence = from_path_result(path)

        self.assertEqual(evidence.operation_id, "op-allow-1")
        self.assertEqual(evidence.verification_event_id, "ve_test_allow_1")
        self.assertEqual(evidence.verification_event_id, path.aep.verification_event_id)
        self.assertEqual(evidence.decision_id, path.decision.decision_id)
        self.assertIs(evidence.disposition, MatrixDisposition.ALLOW)
        self.assertEqual(evidence.disposition.value, "ALLOW")
        self.assertIs(evidence.enforcement, EnforcementOutcome.PROCEEDED)
        self.assertEqual(evidence.enforcement.value, "proceeded")
        self.assertEqual(evidence.protocol_id, "sf-zk")
        self.assertEqual(evidence.policy_version, "pol-1")
        self.assertEqual(evidence.policy_id, "named-pol")
        self.assertEqual(evidence.verification_result, "valid")
        self.assertEqual(
            evidence.admitted_claims_digest, path.aep.claims_digest()
        )
        self.assertEqual(evidence.admitted_claims_digest, path.decision.admitted_claims_digest)
        self.assertEqual(evidence.emitted_at, path.aep.emitted_at)
        self.assertEqual(evidence.decided_at, path.decision.decided_at)
        self.assertIs(evidence.aep, path.aep)
        self.assertIs(evidence.decision, path.decision)
        self.assertTrue(evidence.path_authorization_success)
        assert_no_forbidden_evidence_keys(evidence)

    def test_absent_policy_id_is_none(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-allow-2",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(policy_id=None),
            verification_event_id="ve_test_allow_2",
        )
        evidence = from_path_result(path)
        self.assertIsNone(evidence.policy_id)
        self.assertEqual(evidence.policy_version, "pol-1")


class TestFromPathResultNonAllow(unittest.TestCase):
    def test_deny_preserves_disposition_and_enforcement(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-deny-1",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(force_deny=True),
            verification_event_id="ve_deny_1",
        )
        self.assertFalse(path.authorization_success)
        evidence = from_path_result(path)
        self.assertIs(evidence.disposition, MatrixDisposition.DENY)
        self.assertEqual(evidence.disposition.value, "DENY")
        self.assertIs(evidence.enforcement, EnforcementOutcome.BLOCKED)
        self.assertEqual(evidence.enforcement.value, "blocked")
        self.assertFalse(evidence.path_authorization_success)

    def test_hard_stop_missing_operation(self) -> None:
        path = run_runtime_proof_path(
            operation_id="",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
        )
        self.assertFalse(path.authorization_success)
        self.assertIs(path.enforcement, EnforcementOutcome.HARD_STOPPED)
        with self.assertRaises(EvidenceBindingError) as ctx:
            from_path_result(path)
        self.assertIn("missing_operation_id", str(ctx.exception))


class TestFromPathResultBindingRejection(unittest.TestCase):
    def test_operation_aep_mismatch(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-bind-1",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_bind_1",
        )
        bad_aep = replace(path.aep, operation_id="other-op")
        bad_path = PathResult(
            operation_id=path.operation_id,
            aep=bad_aep,
            decision=None,
            enforcement=path.enforcement,
            authorization_success=False,
            path_completed_through_aep=False,
            failure_class=FailureClass.MISMATCHED,
            reason="test",
        )
        with self.assertRaises(EvidenceBindingError) as ctx:
            from_path_result(bad_path)
        self.assertIn("operation_aep_mismatch", str(ctx.exception))

    def test_decision_verification_mismatch(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-bind-2",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_bind_2",
        )
        bad_decision = replace(path.decision, verification_event_id="ve_other")
        bad_path = PathResult(
            operation_id=path.operation_id,
            aep=path.aep,
            decision=bad_decision,
            enforcement=path.enforcement,
            authorization_success=False,
            path_completed_through_aep=True,
            failure_class=FailureClass.MISMATCHED,
            reason="test",
        )
        with self.assertRaises(EvidenceBindingError) as ctx:
            from_path_result(bad_path)
        self.assertTrue(
            "verification_event_mismatch" in str(ctx.exception)
            or "decision_aep_binding_violation" in str(ctx.exception)
        )

    def test_does_not_mutate_source(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-immut-1",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_immut_1",
        )
        aep_before = path.aep
        dec_before = path.decision
        _ = from_path_result(path)
        self.assertIs(path.aep, aep_before)
        self.assertIs(path.decision, dec_before)
        self.assertEqual(path.aep.verification_event_id, "ve_immut_1")


class TestNativeEnumSpellings(unittest.TestCase):
    def test_escalate_lowercase(self) -> None:
        self.assertEqual(MatrixDisposition.ESCALATE.value, "escalate")

    def test_enforcement_spellings(self) -> None:
        self.assertEqual(EnforcementOutcome.PROCEEDED.value, "proceeded")
        self.assertEqual(EnforcementOutcome.BLOCKED.value, "blocked")
        self.assertEqual(EnforcementOutcome.ESCALATED.value, "escalated")
        self.assertEqual(EnforcementOutcome.HARD_STOPPED.value, "hard_stopped")


class TestGatedResultTypeOnly(unittest.TestCase):
    def test_type_constructible_without_gate(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-gate-type-1",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_gate_type_1",
        )
        # Phase 1: type exists; gate_path_result is Phase 2 — construct manually.
        gated = AuditGatedPathResult(
            path=path,
            audit_commit_result=AuditCommitResult.CONFIRMED,
            conformant_external_allow=False,  # would require gate logic
            failure_class=None,
            reason="phase1_type_only",
        )
        self.assertIs(gated.path, path)
        self.assertIs(gated.audit_commit_result, AuditCommitResult.CONFIRMED)
        self.assertFalse(gated.conformant_external_allow)


class TestTimestampsNotInvented(unittest.TestCase):
    def test_emitted_and_decided_from_native_only(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-ts-1",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_ts_1",
        )
        evidence = from_path_result(path)
        self.assertEqual(evidence.emitted_at, path.aep.emitted_at)
        self.assertEqual(evidence.decided_at, path.decision.decided_at)
        self.assertFalse(hasattr(evidence, "path_seq") and getattr(evidence, "path_seq"))


class TestForbiddenEvidenceKeys(unittest.TestCase):
    def test_allow_path_nested_names_pass(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-forbid-ok",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_forbid_ok",
            admitted_claims=(
                AdmittedClaim(claim_type="eligibility_predicate_id", value="e1"),
            ),
        )
        evidence = from_path_result(path)
        # Inspects OperationEvidence + nested AEP + decision + claim_type names
        assert_no_forbidden_evidence_keys(evidence)

    def test_forbidden_substring_in_claim_type_rejected(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-forbid-bad",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_forbid_bad",
        )
        evidence = from_path_result(path)
        # Nested claim_type that violates FORBIDDEN_AUDIT_KEYS substring policy
        bad_aep = replace(
            path.aep,
            admitted_claims=(
                AdmittedClaim(claim_type="private_witness_binding", value="x"),
            ),
        )
        bad_evidence = replace(evidence, aep=bad_aep)
        with self.assertRaises(ValueError) as ctx:
            assert_no_forbidden_evidence_keys(bad_evidence)
        self.assertIn("forbidden_evidence_field", str(ctx.exception))
        self.assertIn("private_witness_binding", str(ctx.exception))



class TestEarlyFailureIdentity(unittest.TestCase):
    def test_no_aep_no_decision_identity_is_none_not_empty(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-early-1",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_unavailable=True,
        )
        self.assertIsNone(path.aep)
        self.assertIsNone(path.decision)
        evidence = from_path_result(path)
        self.assertEqual(evidence.operation_id, "op-early-1")
        self.assertIsNone(evidence.protocol_id)
        self.assertIsNone(evidence.protocol_version)
        self.assertIsNone(evidence.scheme_id)
        self.assertIsNone(evidence.scheme_version)
        self.assertIsNone(evidence.policy_version)
        self.assertIsNone(evidence.policy_id)
        self.assertNotEqual(evidence.policy_version, "")
        self.assertIs(evidence.enforcement, EnforcementOutcome.HARD_STOPPED)

    def test_aep_with_empty_policy_version_rejected(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-empty-pol",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_empty_pol",
        )
        bad_aep = replace(path.aep, policy_version="")
        bad_path = PathResult(
            operation_id=path.operation_id,
            aep=bad_aep,
            decision=None,
            enforcement=path.enforcement,
            authorization_success=False,
            path_completed_through_aep=False,
            failure_class=FailureClass.MISSING,
            reason="test_empty_policy_version",
        )
        with self.assertRaises(EvidenceBindingError) as ctx:
            from_path_result(bad_path)
        self.assertIn("missing_identity_field", str(ctx.exception))
        self.assertIn("policy_version", str(ctx.exception))



class TestOperationEvidenceInvariants(unittest.TestCase):
    def test_direct_construct_aep_missing_policy_version_rejected(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-inv-1",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_inv_1",
        )
        with self.assertRaises(ValueError) as ctx:
            OperationEvidence(
                operation_id="op-inv-1",
                protocol_id="sf-zk",
                protocol_version="1.0",
                scheme_id="mock-scheme",
                scheme_version="1",
                policy_version=None,
                aep=path.aep,
            )
        self.assertIn("policy_version", str(ctx.exception))

    def test_direct_construct_early_failure_empty_string_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            OperationEvidence(
                operation_id="op-inv-2",
                protocol_id="",
                protocol_version=None,
                scheme_id=None,
                scheme_version=None,
                policy_version=None,
                aep=None,
                decision=None,
            )
        self.assertIn("protocol_id", str(ctx.exception))

    def test_direct_construct_early_failure_all_none_ok(self) -> None:
        ev = OperationEvidence(
            operation_id="op-inv-3",
            aep=None,
            decision=None,
            enforcement=EnforcementOutcome.HARD_STOPPED,
            path_failure_class=FailureClass.UNAVAILABLE,
            path_reason="test",
        )
        self.assertIsNone(ev.policy_version)
        self.assertIsNone(ev.protocol_id)


class TestTimestampOrdering(unittest.TestCase):
    def test_parse_z_and_offset(self) -> None:
        a = parse_audit_timestamp("2026-10-23T12:00:00Z", field_name="emitted_at")
        b = parse_audit_timestamp("2026-10-23T12:00:00+00:00", field_name="decided_at")
        self.assertEqual(a, b)

    def test_parse_naive_as_utc(self) -> None:
        dt = parse_audit_timestamp("2026-10-23T12:00:00", field_name="emitted_at")
        self.assertEqual(dt.tzinfo is not None, True)

    def test_parse_invalid_rejected(self) -> None:
        with self.assertRaises(EvidenceBindingError) as ctx:
            parse_audit_timestamp("not-a-timestamp", field_name="emitted_at")
        self.assertIn("invalid_timestamp", str(ctx.exception))

    def test_valid_chronological_order_ok(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-ord-1",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_ord_1",
        )
        # Native path emits coherent timestamps; builder must accept.
        evidence = from_path_result(path)
        self.assertIsNotNone(evidence.emitted_at)
        self.assertIsNotNone(evidence.decided_at)

    def test_decision_preceding_emission_rejected(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-ord-2",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_ord_2",
        )
        bad_aep = replace(path.aep, emitted_at="2026-10-23T15:00:00Z")
        bad_decision = replace(path.decision, decided_at="2026-10-23T14:00:00Z")
        bad_path = PathResult(
            operation_id=path.operation_id,
            aep=bad_aep,
            decision=bad_decision,
            enforcement=path.enforcement,
            authorization_success=False,
            path_completed_through_aep=True,
            failure_class=FailureClass.MISMATCHED,
            reason="test_order",
        )
        with self.assertRaises(EvidenceBindingError) as ctx:
            from_path_result(bad_path)
        self.assertIn("ordering_inverted", str(ctx.exception))

    def test_incompatible_timestamp_format_rejected(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-ord-3",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_ord_3",
        )
        bad_aep = replace(path.aep, emitted_at="yesterday evening")
        bad_path = PathResult(
            operation_id=path.operation_id,
            aep=bad_aep,
            decision=path.decision,
            enforcement=path.enforcement,
            authorization_success=False,
            path_completed_through_aep=True,
            failure_class=FailureClass.MISMATCHED,
            reason="test_bad_ts",
        )
        with self.assertRaises(EvidenceBindingError) as ctx:
            from_path_result(bad_path)
        self.assertIn("invalid_timestamp", str(ctx.exception))



class TestDecisionEvidenceRequired(unittest.TestCase):
    def test_missing_verification_result_on_decision_rejected(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-dec-vr",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_dec_vr",
        )
        bad_decision = replace(path.decision, verification_result="")
        bad_path = PathResult(
            operation_id=path.operation_id,
            aep=path.aep,
            decision=bad_decision,
            enforcement=path.enforcement,
            authorization_success=False,
            path_completed_through_aep=True,
            failure_class=FailureClass.MISSING,
            reason="test_missing_vr",
        )
        with self.assertRaises(EvidenceBindingError) as ctx:
            from_path_result(bad_path)
        self.assertIn("verification_result", str(ctx.exception))

    def test_missing_admitted_claims_digest_on_decision_rejected(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-dec-dig",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_dec_dig",
        )
        bad_decision = replace(path.decision, admitted_claims_digest="")
        bad_path = PathResult(
            operation_id=path.operation_id,
            aep=path.aep,
            decision=bad_decision,
            enforcement=path.enforcement,
            authorization_success=False,
            path_completed_through_aep=True,
            failure_class=FailureClass.MISSING,
            reason="test_missing_digest",
        )
        with self.assertRaises(EvidenceBindingError) as ctx:
            from_path_result(bad_path)
        self.assertIn("admitted_claims_digest", str(ctx.exception))

    def test_direct_construct_decision_missing_digest_rejected(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-dec-direct",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_event_id="ve_dec_direct",
        )
        with self.assertRaises(ValueError) as ctx:
            OperationEvidence(
                operation_id=path.operation_id,
                protocol_id=path.decision.protocol_id,
                protocol_version=path.decision.protocol_version,
                scheme_id=path.decision.scheme_id,
                scheme_version=path.decision.scheme_version,
                policy_version=path.decision.policy_version,
                verification_result="valid",
                admitted_claims_digest=None,
                decision_id=path.decision.decision_id,
                decision=path.decision,
                aep=path.aep,
            )
        self.assertIn("admitted_claims_digest", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
