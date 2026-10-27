# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""
WP-3.6.5 Phase 5C — SQLite file-backed AuditPort adapter.

Scope (approved):
  - Development / non-production
  - Single process / single writer
  - Process-crash durability only (not host power loss / disk / DR)
  - Retention target: 365 days from commit (UTC)

Concurrency (supported model):
  - ONE shared SqliteAuditPort instance per process for a given database file.
  - threading.RLock is per-instance only; it does NOT serialize multiple
    SqliteAuditPort instances or multiple OS processes on the same file.
  - Multiple instances or multiple processes writing the same DB file are
    OUTSIDE the supported concurrency contract.

OperationEvidence reconstruction:
  - Persisted rows store the frozen logical field view without nested AEP or
    MatrixDecisionRecord object graphs.
  - On read-back, OperationEvidence may carry a complete five-field identity
    tuple with aep=None and decision=None. That path exists solely for storage
    reconstruction of the logical evidence contract.
  - It does not allow partial/empty identity fields, weaken from_path_result
    live-path validation, or change Matrix authorization / gate semantics.

Does not claim production readiness, Stage 3.6 PASS, or multi-writer safety.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from identity_runtime.zk_abstraction.audit_port import (
    AuditCommitResult,
    AuditReadResult,
    AuditReadStatus,
    OperationEvidence,
)
from identity_runtime.zk_abstraction.runtime_proof_path import (
    EnforcementOutcome,
    FailureClass,
    MatrixDisposition,
)


# --- SQLite durability configuration (documented process-crash class) ----------
# DELETE journal + FULL synchronous: COMMIT returns after data reaches the DB
# file on a successful process-level write path under normal OS buffering
# assumptions for single-writer dev use. This does NOT guarantee survival of
# sudden host power loss without additional hardware/fs guarantees.
_JOURNAL_MODE = "DELETE"
_SYNCHRONOUS = "FULL"

_DEFAULT_RETENTION_DAYS = 365
_SCHEMA_VERSION = 1


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _binding_fingerprint(ev: OperationEvidence) -> str:
    """Stable fingerprint of authoritative bindings for conflict detection."""
    parts = [
        ev.operation_id or "",
        ev.verification_event_id or "",
        ev.decision_id or "",
        ev.protocol_id or "",
        ev.protocol_version or "",
        ev.scheme_id or "",
        ev.scheme_version or "",
        ev.policy_version or "",
        ev.policy_id or "",
        ev.verification_result or "",
        ev.admitted_claims_digest or "",
        ev.disposition.value if ev.disposition is not None else "",
    ]
    return "|".join(parts)


def _evidence_to_payload(ev: OperationEvidence) -> dict[str, Any]:
    """Serialize logical evidence fields (no nested AEP/decision object graphs)."""
    return {
        "operation_id": ev.operation_id,
        "protocol_id": ev.protocol_id,
        "protocol_version": ev.protocol_version,
        "scheme_id": ev.scheme_id,
        "scheme_version": ev.scheme_version,
        "policy_version": ev.policy_version,
        "policy_id": ev.policy_id,
        "verification_event_id": ev.verification_event_id,
        "verification_result": ev.verification_result,
        "admitted_claims_digest": ev.admitted_claims_digest,
        "emitted_at": ev.emitted_at,
        "decision_id": ev.decision_id,
        "disposition": ev.disposition.value if ev.disposition is not None else None,
        "decided_at": ev.decided_at,
        "enforcement": ev.enforcement.value if ev.enforcement is not None else None,
        "path_failure_class": (
            ev.path_failure_class.value if ev.path_failure_class is not None else None
        ),
        "path_reason": ev.path_reason,
        "path_authorization_success": ev.path_authorization_success,
        "path_completed_through_aep": ev.path_completed_through_aep,
    }


def _payload_to_evidence(data: dict[str, Any]) -> OperationEvidence:
    disp = data.get("disposition")
    enf = data.get("enforcement")
    fc = data.get("path_failure_class")
    return OperationEvidence(
        operation_id=data["operation_id"],
        protocol_id=data.get("protocol_id"),
        protocol_version=data.get("protocol_version"),
        scheme_id=data.get("scheme_id"),
        scheme_version=data.get("scheme_version"),
        policy_version=data.get("policy_version"),
        policy_id=data.get("policy_id"),
        verification_event_id=data.get("verification_event_id"),
        verification_result=data.get("verification_result"),
        admitted_claims_digest=data.get("admitted_claims_digest"),
        emitted_at=data.get("emitted_at"),
        decision_id=data.get("decision_id"),
        disposition=MatrixDisposition(disp) if disp else None,
        decided_at=data.get("decided_at"),
        enforcement=EnforcementOutcome(enf) if enf else None,
        path_failure_class=FailureClass(fc) if fc else None,
        path_reason=data.get("path_reason") or "",
        path_authorization_success=bool(data.get("path_authorization_success")),
        path_completed_through_aep=bool(data.get("path_completed_through_aep")),
        aep=None,
        decision=None,
    )


class SqliteAuditPort:
    """
    Single-writer SQLite AuditPort.

    Thread lock serializes access within one process. Multiple OS processes
    writing the same file are OUT OF SCOPE and unsupported.
    """

    def __init__(
        self,
        db_path: Path | str,
        *,
        retention_days: int = _DEFAULT_RETENTION_DAYS,
        purge_on_open: bool = True,
    ) -> None:
        self.db_path = Path(db_path)
        self.retention_days = int(retention_days)
        self._lock = threading.RLock()
        # Test-only hooks (default off). Not a public product API.
        self._test_fail_read: bool = False
        self._test_force_uncertain_after_write: bool = False
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        if purge_on_open:
            self.purge_expired()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA journal_mode={_JOURNAL_MODE}")
        conn.execute(f"PRAGMA synchronous={_SYNCHRONOUS}")
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS operation_evidence (
                        operation_id TEXT PRIMARY KEY,
                        binding_fp TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        committed_at TEXT NOT NULL,
                        retained_until TEXT NOT NULL,
                        hold INTEGER NOT NULL DEFAULT 0,
                        schema_version INTEGER NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS operation_tombstone (
                        operation_id TEXT PRIMARY KEY,
                        purged_at TEXT NOT NULL,
                        binding_fp TEXT NOT NULL
                    )
                    """
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            finally:
                conn.close()

    def purge_expired(self, *, now: Optional[datetime] = None) -> int:
        """Delete expired rows without hold; write tombstones for post-expiry idempotency."""
        now = now or _utc_now()
        now_s = _iso(now)
        purged = 0
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                rows = conn.execute(
                    """
                    SELECT operation_id, binding_fp FROM operation_evidence
                    WHERE retained_until < ? AND hold = 0
                    """,
                    (now_s,),
                ).fetchall()
                for row in rows:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO operation_tombstone
                        (operation_id, purged_at, binding_fp) VALUES (?, ?, ?)
                        """,
                        (row["operation_id"], now_s, row["binding_fp"]),
                    )
                    conn.execute(
                        "DELETE FROM operation_evidence WHERE operation_id = ?",
                        (row["operation_id"],),
                    )
                    purged += 1
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            finally:
                conn.close()
        return purged

    def commit_attempt(self, evidence_set: OperationEvidence) -> AuditCommitResult:
        if evidence_set is None or not evidence_set.operation_id:
            return AuditCommitResult.FAILED

        fp = _binding_fingerprint(evidence_set)
        payload = _evidence_to_payload(evidence_set)
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        committed_at = _utc_now()
        retained_until = committed_at + timedelta(days=self.retention_days)

        try:
            with self._lock:
                conn = self._connect()
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    existing = conn.execute(
                        "SELECT binding_fp, payload_json FROM operation_evidence WHERE operation_id = ?",
                        (evidence_set.operation_id,),
                    ).fetchone()
                    if existing is not None:
                        if existing["binding_fp"] == fp:
                            conn.execute("COMMIT")
                            # Idempotent replay of identical bindings
                            return AuditCommitResult.CONFIRMED
                        conn.execute("COMMIT")
                        return AuditCommitResult.FAILED

                    tomb = conn.execute(
                        "SELECT binding_fp FROM operation_tombstone WHERE operation_id = ?",
                        (evidence_set.operation_id,),
                    ).fetchone()
                    if tomb is not None:
                        # Post-expiry: reject reuse that would look like a new attempt
                        # under the same operation_id without an explicit new key.
                        conn.execute("COMMIT")
                        return AuditCommitResult.FAILED

                    conn.execute(
                        """
                        INSERT INTO operation_evidence (
                            operation_id, binding_fp, payload_json,
                            committed_at, retained_until, hold, schema_version
                        ) VALUES (?, ?, ?, ?, ?, 0, ?)
                        """,
                        (
                            evidence_set.operation_id,
                            fp,
                            payload_json,
                            _iso(committed_at),
                            _iso(retained_until),
                            _SCHEMA_VERSION,
                        ),
                    )
                    conn.execute("COMMIT")
                except sqlite3.IntegrityError:
                    try:
                        conn.execute("ROLLBACK")
                    except Exception:
                        pass
                    return AuditCommitResult.FAILED
                except Exception:
                    try:
                        conn.execute("ROLLBACK")
                    except Exception:
                        pass
                    # Ambiguous if COMMIT may have completed
                    return AuditCommitResult.UNCERTAIN
                finally:
                    conn.close()

            # Read-back to establish retrievability before CONFIRMED
            if self._test_force_uncertain_after_write:
                # Write may have committed; caller cannot treat as CONFIRMED without
                # reconciliation via read_attempt (test-injected ambiguity).
                return AuditCommitResult.UNCERTAIN
            read = self.read_attempt(evidence_set.operation_id)
            if read.status is AuditReadStatus.FOUND and read.evidence is not None:
                if _binding_fingerprint(read.evidence) == fp:
                    return AuditCommitResult.CONFIRMED
                return AuditCommitResult.FAILED
            if read.status is AuditReadStatus.READ_ERROR:
                return AuditCommitResult.UNCERTAIN
            return AuditCommitResult.UNCERTAIN
        except Exception:
            return AuditCommitResult.UNCERTAIN

    def read_attempt(self, operation_id: str) -> AuditReadResult:
        if not operation_id:
            return AuditReadResult(
                status=AuditReadStatus.READ_ERROR,
                reason="missing_operation_id",
            )
        try:
            if self._test_fail_read:
                return AuditReadResult(
                    status=AuditReadStatus.READ_ERROR,
                    reason="test_forced_read_failure",
                )
            with self._lock:
                conn = self._connect()
                try:
                    row = conn.execute(
                        """
                        SELECT payload_json, retained_until, hold
                        FROM operation_evidence WHERE operation_id = ?
                        """,
                        (operation_id,),
                    ).fetchone()
                finally:
                    conn.close()
            if row is None:
                return AuditReadResult(status=AuditReadStatus.NOT_FOUND)
            # Expired but not yet purged: treat as NOT_FOUND for read semantics
            if row["hold"] == 0:
                try:
                    if _parse_iso(row["retained_until"]) < _utc_now():
                        return AuditReadResult(status=AuditReadStatus.NOT_FOUND)
                except Exception:
                    return AuditReadResult(
                        status=AuditReadStatus.READ_ERROR,
                        reason="invalid_retained_until",
                    )
            data = json.loads(row["payload_json"])
            evidence = _payload_to_evidence(data)
            return AuditReadResult(status=AuditReadStatus.FOUND, evidence=evidence)
        except Exception as exc:
            return AuditReadResult(
                status=AuditReadStatus.READ_ERROR,
                reason=f"read_error:{exc}",
            )
