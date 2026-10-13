# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""Stage 3.6 runtime proof path — WP-3.6.1–3.6.4 implementation slice tests."""

from __future__ import annotations

import unittest

from identity_runtime.zk_abstraction.identity import IdentityTuple
from identity_runtime.zk_abstraction.runtime_proof_path import (
    AdmittedClaim,
    CLAIM_REGISTRY_V0,
    EnforcementOutcome,
    FailureClass,
    MatrixDisposition,
    MatrixPolicy,
    aep_from_verification_result,
    build_aep,
    evaluate_matrix,
    reject_unbound_multi_event,
    run_path_from_verification,
    run_runtime_proof_path,
    validate_aep,
)
from identity_runtime.zk_abstraction.verifier import VerificationResult


def _identity(**kwargs) -> IdentityTuple:
    base = dict(
        protocol_id="sf-zk",
        protocol_version="1.0.0",
        scheme_id="mock-scheme",
        scheme_version="1.0.0",
        policy_version="1.0.0",
    )
    base.update(kwargs)
    return IdentityTuple(**base)


def _policy(**kwargs) -> MatrixPolicy:
    base = dict(
        policy_id="matrix-default",
        policy_version="1.0.0",
        allow_when_valid=True,
        require_admitted_claim=False,
        force_deny=False,
    )
    base.update(kwargs)
    return MatrixPolicy(**base)


class TestAEPContract(unittest.TestCase):
    def test_conforming_aep_with_empty_claims(self):
        aep = build_aep(
            operation_id="op1",
            verification_result="valid",
            identity=_identity(),
            admitted_claims=(),
        )
        self.assertIsNone(validate_aep(aep))
        self.assertEqual(aep.admitted_claims, ())
        self.assertEqual(aep.verification_result, "valid")

    def test_missing_identity_field_fails(self):
        aep = build_aep(
            operation_id="op1",
            verification_result="valid",
            identity=_identity(protocol_id=""),
        )
        self.assertEqual(validate_aep(aep), FailureClass.MISSING)

    def test_invalid_requires_result_code(self):
        aep = build_aep(
            operation_id="op1",
            verification_result="invalid",
            identity=_identity(),
            verification_result_code=None,
        )
        self.assertIsNone(validate_aep(aep))
        self.assertEqual(aep.verification_result_code, "UNSPECIFIED_NON_VALID")

    def test_unregistered_claim_unsupported(self):
        aep = build_aep(
            operation_id="op1",
            verification_result="valid",
            identity=_identity(),
            admitted_claims=(
                AdmittedClaim(claim_type="not_in_registry", value="x"),
            ),
        )
        self.assertEqual(validate_aep(aep), FailureClass.UNSUPPORTED)

    def test_registered_claim_ok(self):
        self.assertIn("eligibility_predicate_id", CLAIM_REGISTRY_V0)
        aep = build_aep(
            operation_id="op1",
            verification_result="valid",
            identity=_identity(),
            admitted_claims=(
                AdmittedClaim(claim_type="eligibility_predicate_id", value="pred-1"),
            ),
        )
        self.assertIsNone(validate_aep(aep))


class TestMatrixAndPath(unittest.TestCase):
    def test_valid_proof_matrix_allow(self):
        result = run_runtime_proof_path(
            operation_id="op-allow",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
        )
        self.assertTrue(result.authorization_success)
        self.assertEqual(result.decision.disposition, MatrixDisposition.ALLOW)
        self.assertEqual(result.enforcement, EnforcementOutcome.PROCEEDED)
        self.assertTrue(result.decision.binds_to_aep(result.aep))

    def test_valid_proof_matrix_deny(self):
        """Critical: valid verification must not imply authorization."""
        result = run_runtime_proof_path(
            operation_id="op-deny",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(force_deny=True),
        )
        self.assertFalse(result.authorization_success)
        self.assertEqual(result.decision.disposition, MatrixDisposition.DENY)
        self.assertEqual(result.enforcement, EnforcementOutcome.BLOCKED)
        self.assertEqual(result.aep.verification_result, "valid")
        self.assertIn("force_deny", result.reason)

    def test_invalid_proof_never_allows(self):
        result = run_runtime_proof_path(
            operation_id="op-inv",
            identity=_identity(),
            verification_result="invalid",
            policy=_policy(),
            verification_result_code="PROOF_INVALID",
        )
        self.assertFalse(result.authorization_success)
        self.assertNotEqual(
            getattr(result.decision, "disposition", None), MatrixDisposition.ALLOW
        )

    def test_error_proof_never_allows(self):
        result = run_runtime_proof_path(
            operation_id="op-err",
            identity=_identity(),
            verification_result="error",
            policy=_policy(),
            verification_result_code="VERIFIER_ERROR",
        )
        self.assertFalse(result.authorization_success)

    def test_missing_aep_field_fail_closed(self):
        aep = build_aep(
            operation_id="op-miss",
            verification_result="valid",
            identity=_identity(scheme_id=""),
        )
        result = evaluate_matrix(aep, _policy())
        self.assertFalse(result.authorization_success)
        self.assertEqual(result.failure_class, FailureClass.MISSING)

    def test_unsupported_scheme_fail_closed(self):
        result = run_runtime_proof_path(
            operation_id="op-unsup",
            identity=_identity(scheme_id="unknown-scheme"),
            verification_result="valid",
            policy=_policy(),
        )
        self.assertFalse(result.authorization_success)
        self.assertEqual(result.failure_class, FailureClass.UNSUPPORTED)

    def test_policy_version_mismatch(self):
        result = run_runtime_proof_path(
            operation_id="op-pol",
            identity=_identity(policy_version="1.0.0"),
            verification_result="valid",
            policy=_policy(policy_version="9.9.9"),
        )
        self.assertFalse(result.authorization_success)
        self.assertEqual(result.failure_class, FailureClass.MISMATCHED)

    def test_operation_aep_mismatch(self):
        result = run_runtime_proof_path(
            operation_id="op-real",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            bind_operation_id_override="op-other",
        )
        self.assertFalse(result.authorization_success)
        self.assertEqual(result.failure_class, FailureClass.MISMATCHED)

    def test_verifier_unavailable_hard_stop(self):
        result = run_runtime_proof_path(
            operation_id="op-down",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_unavailable=True,
        )
        self.assertFalse(result.authorization_success)
        self.assertEqual(result.failure_class, FailureClass.UNAVAILABLE)
        self.assertEqual(result.enforcement, EnforcementOutcome.HARD_STOPPED)
        self.assertIsNone(result.decision)

    def test_ambiguous_multi_event(self):
        fc = reject_unbound_multi_event(
            operation_id="op1",
            candidate_event_ids=("ve1", "ve2"),
            selected_event_id=None,
        )
        self.assertEqual(fc, FailureClass.AMBIGUOUS)

    def test_empty_claims_still_can_allow(self):
        result = run_runtime_proof_path(
            operation_id="op-empty",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(require_admitted_claim=False),
            admitted_claims=(),
        )
        self.assertTrue(result.authorization_success)

    def test_require_claim_denies_empty(self):
        result = run_runtime_proof_path(
            operation_id="op-need",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(require_admitted_claim=True),
            admitted_claims=(),
        )
        self.assertFalse(result.authorization_success)

    def test_decision_identity_matches_aep(self):
        result = run_runtime_proof_path(
            operation_id="op-bind",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            admitted_claims=(
                AdmittedClaim(claim_type="context_binding_id", value="ctx-9"),
            ),
        )
        self.assertTrue(result.authorization_success)
        d = result.decision
        a = result.aep
        self.assertEqual(d.operation_id, a.operation_id)
        self.assertEqual(d.verification_event_id, a.verification_event_id)
        self.assertEqual(d.protocol_id, a.protocol_id)
        self.assertEqual(d.admitted_claims_digest, a.claims_digest())


class _Binding:
    def __init__(self, context_id: str):
        self.context_id = context_id


class TestVerifierToAEPBridge(unittest.TestCase):
    def test_accepted_verification_emits_valid_aep(self):
        vr = VerificationResult(
            accepted=True,
            status_code="OK",
            reason="verified",
            identity_tuple=_identity(),
            binding_target=_Binding("SF-2026-001"),
            verified_eligibility_claim=True,
            authorization_permitted=False,
        )
        aep = aep_from_verification_result(vr, operation_id="op-bridge")
        self.assertEqual(aep.verification_result, "valid")
        self.assertEqual(aep.operation_id, "op-bridge")
        self.assertEqual(aep.protocol_id, "sf-zk")
        self.assertTrue(
            any(
                c.claim_type == "context_binding_id" and c.value == "SF-2026-001"
                for c in aep.admitted_claims
            )
        )
        self.assertIsNone(validate_aep(aep))
        self.assertFalse(vr.authorization_permitted)

    def test_rejected_verification_emits_invalid_aep_and_matrix_denies(self):
        vr = VerificationResult(
            accepted=False,
            status_code="INVALID_PROOF",
            reason="scheme_proof_check_failed",
            identity_tuple=_identity(),
            binding_target=None,
            verified_eligibility_claim=False,
            authorization_permitted=False,
        )
        path = run_path_from_verification(
            vr, operation_id="op-bad", policy=_policy()
        )
        self.assertFalse(path.authorization_success)
        self.assertEqual(path.aep.verification_result, "invalid")
        self.assertNotEqual(
            getattr(path.decision, "disposition", None), MatrixDisposition.ALLOW
        )

    def test_valid_verification_matrix_can_still_deny(self):
        vr = VerificationResult(
            accepted=True,
            status_code="OK",
            reason="verified",
            identity_tuple=_identity(),
            binding_target=_Binding("ctx-1"),
            verified_eligibility_claim=True,
            authorization_permitted=False,
        )
        path = run_path_from_verification(
            vr, operation_id="op-deny-bridge", policy=_policy(force_deny=True)
        )
        self.assertEqual(path.aep.verification_result, "valid")
        self.assertFalse(path.authorization_success)
        self.assertEqual(path.decision.disposition, MatrixDisposition.DENY)

    def test_missing_result_hard_stops(self):
        path = run_path_from_verification(
            None, operation_id="op-none", policy=_policy()
        )
        self.assertFalse(path.authorization_success)
        self.assertEqual(path.failure_class, FailureClass.UNAVAILABLE)


if __name__ == "__main__":
    unittest.main()