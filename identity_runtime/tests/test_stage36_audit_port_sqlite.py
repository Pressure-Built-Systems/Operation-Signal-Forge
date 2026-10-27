# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""WP-3.6.5 Phase 5C — SQLite AuditPort adapter conformance tests."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from identity_runtime.zk_abstraction.audit_port import (
    AuditCommitResult,
    AuditReadStatus,
    from_path_result,
    gate_path_result,
)
from identity_runtime.zk_abstraction.audit_port_sqlite import SqliteAuditPort
from identity_runtime.zk_abstraction.identity import IdentityTuple
from identity_runtime.zk_abstraction.runtime_proof_path import (
    MatrixPolicy,
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


def _allow_evidence(op: str = "op-sqlite-1"):
    path = run_runtime_proof_path(
        operation_id=op,
        identity=_identity(),
        verification_result="valid",
        policy=_policy(),
        verification_event_id=f"ve_{op}",
    )
    return path, from_path_result(path)


class TestSqliteCommitRestart(unittest.TestCase):
    def test_confirmed_survives_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "audit.sqlite"
            port = SqliteAuditPort(db, retention_days=365)
            path, ev = _allow_evidence("op-restart-1")
            self.assertIs(port.commit_attempt(ev), AuditCommitResult.CONFIRMED)
            # New instance = process restart simulation
            port2 = SqliteAuditPort(db, retention_days=365, purge_on_open=False)
            read = port2.read_attempt("op-restart-1")
            self.assertIs(read.status, AuditReadStatus.FOUND)
            self.assertIsNotNone(read.evidence)
            self.assertEqual(read.evidence.operation_id, "op-restart-1")
            self.assertEqual(
                read.evidence.verification_event_id, path.aep.verification_event_id
            )


class TestSqliteIdempotencyConflict(unittest.TestCase):
    def test_identical_replay_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            port = SqliteAuditPort(Path(td) / "a.sqlite")
            _, ev = _allow_evidence("op-idem-1")
            self.assertIs(port.commit_attempt(ev), AuditCommitResult.CONFIRMED)
            self.assertIs(port.commit_attempt(ev), AuditCommitResult.CONFIRMED)
            read = port.read_attempt("op-idem-1")
            self.assertIs(read.status, AuditReadStatus.FOUND)

    def test_conflicting_bindings_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            port = SqliteAuditPort(Path(td) / "a.sqlite")
            _, ev = _allow_evidence("op-conflict-1")
            self.assertIs(port.commit_attempt(ev), AuditCommitResult.CONFIRMED)
            # Same operation_id, different verification_event_id fingerprint
            path2 = run_runtime_proof_path(
                operation_id="op-conflict-1",
                identity=_identity(),
                verification_result="valid",
                policy=_policy(),
                verification_event_id="ve_other_conflict",
            )
            ev2 = from_path_result(path2)
            self.assertIs(port.commit_attempt(ev2), AuditCommitResult.FAILED)
            read = port.read_attempt("op-conflict-1")
            self.assertIs(read.status, AuditReadStatus.FOUND)
            self.assertEqual(
                read.evidence.verification_event_id, "ve_op-conflict-1"
            )


class TestSqliteReadStatuses(unittest.TestCase):
    def test_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            port = SqliteAuditPort(Path(td) / "a.sqlite")
            r = port.read_attempt("missing-op")
            self.assertIs(r.status, AuditReadStatus.NOT_FOUND)
            self.assertIsNone(r.evidence)

    def test_found_has_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            port = SqliteAuditPort(Path(td) / "a.sqlite")
            _, ev = _allow_evidence("op-found-1")
            port.commit_attempt(ev)
            r = port.read_attempt("op-found-1")
            self.assertIs(r.status, AuditReadStatus.FOUND)
            self.assertIsNotNone(r.evidence)


class TestSqliteUncertainReconcile(unittest.TestCase):
    def test_read_after_confirmed_is_found(self) -> None:
        """Reconciliation path: after CONFIRMED, read_attempt establishes presence."""
        with tempfile.TemporaryDirectory() as td:
            port = SqliteAuditPort(Path(td) / "a.sqlite")
            _, ev = _allow_evidence("op-unc-1")
            result = port.commit_attempt(ev)
            self.assertIs(result, AuditCommitResult.CONFIRMED)
            self.assertIs(port.read_attempt("op-unc-1").status, AuditReadStatus.FOUND)


class TestSqliteRetention(unittest.TestCase):
    def test_expired_not_found_and_reuse_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "a.sqlite"
            port = SqliteAuditPort(db, retention_days=365, purge_on_open=False)
            _, ev = _allow_evidence("op-ret-1")
            self.assertIs(port.commit_attempt(ev), AuditCommitResult.CONFIRMED)
            # Force expiry
            import sqlite3

            past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            conn = sqlite3.connect(str(db))
            conn.execute(
                "UPDATE operation_evidence SET retained_until = ? WHERE operation_id = ?",
                (past, "op-ret-1"),
            )
            conn.commit()
            conn.close()
            # Read before purge treats expired as NOT_FOUND
            self.assertIs(
                port.read_attempt("op-ret-1").status, AuditReadStatus.NOT_FOUND
            )
            purged = port.purge_expired()
            self.assertGreaterEqual(purged, 1)
            self.assertIs(
                port.read_attempt("op-ret-1").status, AuditReadStatus.NOT_FOUND
            )
            # Reuse same operation_id after purge → FAILED (tombstone)
            self.assertIs(port.commit_attempt(ev), AuditCommitResult.FAILED)


class TestSqliteGateIntegration(unittest.TestCase):
    def test_allow_confirmed_conformant(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            port = SqliteAuditPort(Path(td) / "a.sqlite")
            path, _ = _allow_evidence("op-gate-sql-1")
            self.assertTrue(path.authorization_success)
            gated = gate_path_result(path, port)
            self.assertTrue(gated.conformant_external_allow)
            self.assertIs(gated.audit_commit_result, AuditCommitResult.CONFIRMED)

    def test_conflict_second_path_not_conformant(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            port = SqliteAuditPort(Path(td) / "a.sqlite")
            path1, _ = _allow_evidence("op-gate-sql-2")
            self.assertTrue(gate_path_result(path1, port).conformant_external_allow)
            path2 = run_runtime_proof_path(
                operation_id="op-gate-sql-2",
                identity=_identity(),
                verification_result="valid",
                policy=_policy(),
                verification_event_id="ve_different",
            )
            gated2 = gate_path_result(path2, port)
            self.assertFalse(gated2.conformant_external_allow)



class TestSqliteReadError(unittest.TestCase):
    def test_read_error_not_found_or_found(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            port = SqliteAuditPort(Path(td) / "a.sqlite")
            _, ev = _allow_evidence("op-re-1")
            self.assertIs(port.commit_attempt(ev), AuditCommitResult.CONFIRMED)
            port._test_fail_read = True
            r = port.read_attempt("op-re-1")
            self.assertIs(r.status, AuditReadStatus.READ_ERROR)
            self.assertIsNone(r.evidence)
            self.assertIn("test_forced_read_failure", r.reason or "")

    def test_commit_readback_failure_not_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            port = SqliteAuditPort(Path(td) / "a.sqlite")
            port._test_fail_read = True
            _, ev = _allow_evidence("op-re-2")
            # Insert may succeed but read-back fails → must not CONFIRMED
            result = port.commit_attempt(ev)
            self.assertIsNot(result, AuditCommitResult.CONFIRMED)
            self.assertIn(result, (AuditCommitResult.UNCERTAIN, AuditCommitResult.FAILED))


class TestSqliteUncertainReconcileInjected(unittest.TestCase):
    def test_uncertain_then_reconcile_found(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            port = SqliteAuditPort(Path(td) / "a.sqlite")
            _, ev = _allow_evidence("op-unc-inj-1")
            port._test_force_uncertain_after_write = True
            result = port.commit_attempt(ev)
            self.assertIs(result, AuditCommitResult.UNCERTAIN)
            port._test_force_uncertain_after_write = False
            # Reconciliation: row is present and matching
            read = port.read_attempt("op-unc-inj-1")
            self.assertIs(read.status, AuditReadStatus.FOUND)
            self.assertEqual(read.evidence.operation_id, "op-unc-inj-1")
            # Idempotent retry after reconcile → CONFIRMED
            self.assertIs(port.commit_attempt(ev), AuditCommitResult.CONFIRMED)

    def test_uncertain_does_not_overwrite_on_conflict_retry(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            port = SqliteAuditPort(Path(td) / "a.sqlite")
            _, ev = _allow_evidence("op-unc-inj-2")
            self.assertIs(port.commit_attempt(ev), AuditCommitResult.CONFIRMED)
            path2 = run_runtime_proof_path(
                operation_id="op-unc-inj-2",
                identity=_identity(),
                verification_result="valid",
                policy=_policy(),
                verification_event_id="ve_conflict_unc",
            )
            ev2 = from_path_result(path2)
            self.assertIs(port.commit_attempt(ev2), AuditCommitResult.FAILED)
            read = port.read_attempt("op-unc-inj-2")
            self.assertIs(read.status, AuditReadStatus.FOUND)
            self.assertEqual(read.evidence.verification_event_id, "ve_op-unc-inj-2")


class TestSqlitePreservationHold(unittest.TestCase):
    def test_hold_prevents_purge_of_expired(self) -> None:
        """Hold is schema-level; set via controlled SQL fixture (no product hold API)."""
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "a.sqlite"
            port = SqliteAuditPort(db, retention_days=365, purge_on_open=False)
            _, ev = _allow_evidence("op-hold-1")
            self.assertIs(port.commit_attempt(ev), AuditCommitResult.CONFIRMED)
            import sqlite3
            past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            conn = sqlite3.connect(str(db))
            conn.execute(
                "UPDATE operation_evidence SET retained_until = ?, hold = 1 WHERE operation_id = ?",
                (past, "op-hold-1"),
            )
            conn.commit()
            conn.close()
            purged = port.purge_expired()
            self.assertEqual(purged, 0)
            read = port.read_attempt("op-hold-1")
            self.assertIs(read.status, AuditReadStatus.FOUND)
            self.assertEqual(read.evidence.operation_id, "op-hold-1")


if __name__ == "__main__":
    unittest.main()
