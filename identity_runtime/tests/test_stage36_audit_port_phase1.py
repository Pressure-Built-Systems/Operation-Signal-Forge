# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""WP-3.6.5 Phase 2 — shared gate_path_result tests (fake AuditPort only)."""

from __future__ import annotations

import unittest
from dataclasses import replace
from typing import List, Optional

from identity_runtime.zk_abstraction.audit_port import (
    AuditCommitResult,
    AuditGatedPathResult,
    AuditPort,
    AuditReadResult,
    AuditReadStatus,
    OperationEvidence,
    from_path_result,
    gate_path_result,
)
from identity_runtime.zk_abstraction.identity import IdentityTuple
from identity_runtime.zk_abstraction.runtime_proof_path import (
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
    base = dict(policy_id=None, policy_version="pol-1", allow_when_valid=True)
    base.update(kwargs)
    return MatrixPolicy(**base)


class _FakePort:
    """Deterministic AuditPort double — not a durability proof."""

    def __init__(
        self,
        commit_result: Optional[AuditCommitResult] = AuditCommitResult.CONFIRMED,
        *,
        raise_on_commit: bool = False,
        return_none: bool = False,
    ) -> None:
        self.commit_result = commit_result
        self.raise_on_commit = raise_on_commit
        self.return_none = return_none
        self.commits: List[OperationEvidence] = []

    def commit_attempt(self, evidence_set: OperationEvidence) -> AuditCommitResult:
        self.commits.append(evidence_set)
        if self.raise_on_commit:
            raise RuntimeError("forced_commit_failure")
        if self.return_none:
            return None  # type: ignore[return-value]
        assert self.commit_result is not None
        return self.commit_result

    def read_attempt(self, operation_id: str) -> AuditReadResult:
        return AuditReadResult(status=AuditReadStatus.NOT_FOUND)


def _allow_path(op: str = "op-gate-allow") -> PathResult:
    return run_runtime_proof_path(
        operation_id=op,
        identity=_identity(),
        verification_result="valid",
        policy=_policy(),
        verification_event_id=f"ve_{op}",
    )


class TestGateClassA(unittest.TestCase):
    def test_allow_confirmed_conformant(self) -> None:
        path = _allow_path("op-a-ok")
        self.assertTrue(path.authorization_success)
        port = _FakePort(AuditCommitResult.CONFIRMED)
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertTrue(gated.conformant_external_allow)
        self.assertIs(gated.audit_commit_result, AuditCommitResult.CONFIRMED)
        self.assertIsNone(gated.failure_class)
        self.assertIs(gated.path, path)
        self.assertEqual(len(port.commits), 1)
        self.assertEqual(port.commits[0].operation_id, "op-a-ok")

    def test_allow_failed_blocks(self) -> None:
        path = _allow_path("op-a-fail")
        port = _FakePort(AuditCommitResult.FAILED)
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.audit_commit_result, AuditCommitResult.FAILED)
        self.assertIs(gated.failure_class, FailureClass.UNAVAILABLE)

    def test_allow_uncertain_blocks(self) -> None:
        path = _allow_path("op-a-unc")
        port = _FakePort(AuditCommitResult.UNCERTAIN)
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.audit_commit_result, AuditCommitResult.UNCERTAIN)
        self.assertIs(gated.failure_class, FailureClass.UNAVAILABLE)

    def test_required_commit_none_blocks(self) -> None:
        path = _allow_path("op-a-skip")
        port = _FakePort(return_none=True)
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.failure_class, FailureClass.UNAVAILABLE)
        self.assertIn("skipped", gated.reason)

    def test_commit_exception_maps_unavailable(self) -> None:
        path = _allow_path("op-a-exc")
        port = _FakePort(raise_on_commit=True)
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.audit_commit_result, AuditCommitResult.FAILED)
        self.assertIs(gated.failure_class, FailureClass.UNAVAILABLE)

    def test_mismatched_binding_blocks_without_commit_success(self) -> None:
        path = _allow_path("op-a-bind")
        bad_decision = replace(path.decision, verification_event_id="ve_other")
        bad_path = PathResult(
            operation_id=path.operation_id,
            aep=path.aep,
            decision=bad_decision,
            enforcement=path.enforcement,
            authorization_success=True,  # path flag alone must not authorize
            path_completed_through_aep=True,
            failure_class=None,
            reason="test_mismatch",
        )
        port = _FakePort(AuditCommitResult.CONFIRMED)
        gated = gate_path_result(bad_path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.failure_class, FailureClass.MISMATCHED)
        self.assertEqual(len(port.commits), 0)

    def test_inverted_ordering_blocks(self) -> None:
        path = _allow_path("op-a-ord")
        bad_aep = replace(path.aep, emitted_at="2026-10-23T15:00:00Z")
        bad_decision = replace(path.decision, decided_at="2026-10-23T14:00:00Z")
        bad_path = PathResult(
            operation_id=path.operation_id,
            aep=bad_aep,
            decision=bad_decision,
            enforcement=path.enforcement,
            authorization_success=True,
            path_completed_through_aep=True,
            failure_class=None,
            reason="test_order",
        )
        port = _FakePort(AuditCommitResult.CONFIRMED)
        gated = gate_path_result(bad_path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.failure_class, FailureClass.MISMATCHED)
        self.assertIn("ordering_inverted", gated.reason)
        self.assertEqual(len(port.commits), 0)


class TestGateClassB(unittest.TestCase):
    def test_deny_retention_fail_still_non_allow(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-b-deny",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(force_deny=True),
            verification_event_id="ve_b_deny",
        )
        self.assertFalse(path.authorization_success)
        self.assertIs(path.decision.disposition, MatrixDisposition.DENY)
        port = _FakePort(raise_on_commit=True)
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(path.decision.disposition, MatrixDisposition.DENY)

    def test_deny_confirmed_still_non_allow(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-b-deny2",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(force_deny=True),
            verification_event_id="ve_b_deny2",
        )
        port = _FakePort(AuditCommitResult.CONFIRMED)
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.audit_commit_result, AuditCommitResult.CONFIRMED)


class TestGateClassC(unittest.TestCase):
    def test_early_failure_always_non_allow(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-c-early",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_unavailable=True,
        )
        self.assertIsNone(path.decision)
        port = _FakePort(AuditCommitResult.CONFIRMED)
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.failure_class, FailureClass.UNAVAILABLE)

    def test_early_failure_retention_error_still_non_allow(self) -> None:
        path = run_runtime_proof_path(
            operation_id="op-c-err",
            identity=_identity(),
            verification_result="valid",
            policy=_policy(),
            verification_unavailable=True,
        )
        port = _FakePort(raise_on_commit=True)
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)


class TestGateInvariants(unittest.TestCase):
    def test_does_not_mutate_path(self) -> None:
        path = _allow_path("op-immut")
        before = (
            path.authorization_success,
            path.operation_id,
            path.decision.decision_id if path.decision else None,
        )
        port = _FakePort(AuditCommitResult.CONFIRMED)
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertIs(gated.path, path)
        self.assertEqual(
            (
                path.authorization_success,
                path.operation_id,
                path.decision.decision_id if path.decision else None,
            ),
            before,
        )

    def test_uses_from_path_result_evidence(self) -> None:
        path = _allow_path("op-builder")
        port = _FakePort(AuditCommitResult.CONFIRMED)
        gate_path_result(path, port)  # type: ignore[arg-type]
        expected = from_path_result(path)
        self.assertEqual(port.commits[0].operation_id, expected.operation_id)
        self.assertEqual(
            port.commits[0].verification_event_id, expected.verification_event_id
        )
        self.assertEqual(port.commits[0].decision_id, expected.decision_id)
        self.assertEqual(
            port.commits[0].admitted_claims_digest, expected.admitted_claims_digest
        )

    def test_authorization_success_alone_not_conformant(self) -> None:
        path = _allow_path("op-flag")
        # Force FAILED commit while path.authorization_success remains True
        self.assertTrue(path.authorization_success)
        gated = gate_path_result(path, _FakePort(AuditCommitResult.FAILED))  # type: ignore[arg-type]
        self.assertTrue(path.authorization_success)
        self.assertFalse(gated.conformant_external_allow)



class TestGateClassAPathFailureStillCommits(unittest.TestCase):
    def test_matrix_allow_path_failed_still_commits_not_conformant(self) -> None:
        path = _allow_path("op-a-pathfail")
        # Synthesize Matrix ALLOW with native path failure (unusual but contract-relevant).
        failed_path = PathResult(
            operation_id=path.operation_id,
            aep=path.aep,
            decision=path.decision,
            enforcement=EnforcementOutcome.BLOCKED,
            authorization_success=False,
            path_completed_through_aep=True,
            failure_class=FailureClass.MISMATCHED,
            reason="synthetic_path_failure_with_allow_disposition",
        )
        self.assertIs(failed_path.decision.disposition, MatrixDisposition.ALLOW)
        port = _FakePort(AuditCommitResult.CONFIRMED)
        gated = gate_path_result(failed_path, port)  # type: ignore[arg-type]
        self.assertEqual(len(port.commits), 1)
        self.assertIs(gated.audit_commit_result, AuditCommitResult.CONFIRMED)
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.failure_class, FailureClass.MISMATCHED)

    def test_matrix_allow_path_failed_commit_failed_preserves_path_class(self) -> None:
        path = _allow_path("op-a-pathfail2")
        failed_path = PathResult(
            operation_id=path.operation_id,
            aep=path.aep,
            decision=path.decision,
            enforcement=EnforcementOutcome.BLOCKED,
            authorization_success=False,
            path_completed_through_aep=True,
            failure_class=FailureClass.MISMATCHED,
            reason="synthetic_path_failure",
        )
        port = _FakePort(AuditCommitResult.FAILED)
        gated = gate_path_result(failed_path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.failure_class, FailureClass.MISMATCHED)


class TestGateInvalidCommitReturn(unittest.TestCase):
    def test_invalid_commit_return_not_conformant(self) -> None:
        path = _allow_path("op-a-badret")
        port = _FakePort(commit_result=AuditCommitResult.CONFIRMED)

        def bad_commit(evidence_set: OperationEvidence):
            return object()  # violates protocol

        port.commit_attempt = bad_commit  # type: ignore[method-assign]
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.audit_commit_result, AuditCommitResult.FAILED)
        self.assertIs(gated.failure_class, FailureClass.UNAVAILABLE)

    def test_string_confirmed_fail_closed(self) -> None:
        path = _allow_path("op-a-str")
        port = _FakePort()

        def str_commit(evidence_set: OperationEvidence):
            return "CONFIRMED"  # not an enum instance — must not authorize

        port.commit_attempt = str_commit  # type: ignore[method-assign]
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.audit_commit_result, AuditCommitResult.FAILED)
        self.assertIs(gated.failure_class, FailureClass.UNAVAILABLE)



class TestGateClassBEscalate(unittest.TestCase):
    def _escalate_path(self, op: str) -> PathResult:
        """Native escalate disposition via synthetic PathResult (no force_escalate policy)."""
        path = _allow_path(op)
        escalated_decision = replace(
            path.decision,
            disposition=MatrixDisposition.ESCALATE,
            reason="matrix_escalate_synthetic",
        )
        return PathResult(
            operation_id=path.operation_id,
            aep=path.aep,
            decision=escalated_decision,
            enforcement=EnforcementOutcome.ESCALATED,
            authorization_success=False,
            path_completed_through_aep=True,
            failure_class=None,
            reason="matrix_escalate_synthetic",
        )

    def test_escalate_retention_fail_still_non_allow(self) -> None:
        path = self._escalate_path("op-b-esc-fail")
        self.assertIs(path.decision.disposition, MatrixDisposition.ESCALATE)
        self.assertEqual(path.decision.disposition.value, "escalate")
        port = _FakePort(raise_on_commit=True)
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(path.decision.disposition, MatrixDisposition.ESCALATE)
        self.assertEqual(path.decision.disposition.value, "escalate")
        self.assertIsNot(path.decision.disposition, MatrixDisposition.ALLOW)

    def test_escalate_confirmed_still_non_allow(self) -> None:
        path = self._escalate_path("op-b-esc-ok")
        self.assertEqual(path.decision.disposition.value, "escalate")
        port = _FakePort(AuditCommitResult.CONFIRMED)
        gated = gate_path_result(path, port)  # type: ignore[arg-type]
        self.assertFalse(gated.conformant_external_allow)
        self.assertIs(gated.audit_commit_result, AuditCommitResult.CONFIRMED)
        self.assertIs(path.decision.disposition, MatrixDisposition.ESCALATE)
        self.assertEqual(path.decision.disposition.value, "escalate")


if __name__ == "__main__":
    unittest.main()
