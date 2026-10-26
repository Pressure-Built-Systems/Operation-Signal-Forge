# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""
WP-3.6.5 Phase 1 — AuditPort contract types and shared evidence builder.

Logical evidence view and port-owned result types only.
Does not implement gate_path_result, storage adapters, or runtime rewiring.
Does not claim durable-audit conformance or Stage 3.6 PASS.

Normative anchors: accepted Thin Evidence Schema; AuditPort Python Interface Contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Protocol

from identity_runtime.zk_abstraction.identity import IdentityTuple
from identity_runtime.zk_abstraction.runtime_proof_path import (
    AdmittedEvidencePackage,
    EnforcementOutcome,
    FailureClass,
    MatrixDecisionRecord,
    MatrixDisposition,
    PathResult,
)


# ---------------------------------------------------------------------------
# Port-owned commit / read results
# ---------------------------------------------------------------------------


class AuditCommitResult(str, Enum):
    """Durable-commit outcome for one logical attempt. Port-owned surface."""

    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    UNCERTAIN = "UNCERTAIN"


class AuditReadStatus(str, Enum):
    """Read outcome; distinguishes absence from inability to read."""

    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    READ_ERROR = "READ_ERROR"


# ---------------------------------------------------------------------------
# Logical operation evidence (reconstruction view — not a storage row mandate)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OperationEvidence:
    """
    Logical reconstruction view for one operation attempt.

    Physical layout may be linked native records. This type does not imply
    durability; durability is only established by a later AuditPort adapter
    returning AuditCommitResult.CONFIRMED.

    Identity fields (protocol_id, protocol_version, scheme_id, scheme_version,
    policy_version):
      - When AEP and/or Matrix decision is present: each MUST be a non-empty str
        (policy_version is mandatory on those records per the frozen schema).
      - When neither AEP nor decision is present (early failure / hard-stop):
        each MUST be None. Empty strings are never used as a stand-in for
        missing identity evidence.
      - policy_id remains Optional; None means no named policy (no sentinel).
      - When decision is present: verification_result, admitted_claims_digest,
        and decision_id MUST each be non-empty str (frozen schema first-class
        decision evidence).
    """

    operation_id: str
    protocol_id: Optional[str] = None
    protocol_version: Optional[str] = None
    scheme_id: Optional[str] = None
    scheme_version: Optional[str] = None
    policy_version: Optional[str] = None
    policy_id: Optional[str] = None
    verification_event_id: Optional[str] = None
    verification_result: Optional[str] = None
    admitted_claims_digest: Optional[str] = None
    emitted_at: Optional[str] = None
    decision_id: Optional[str] = None
    disposition: Optional[MatrixDisposition] = None
    decided_at: Optional[str] = None
    enforcement: Optional[EnforcementOutcome] = None
    path_failure_class: Optional[FailureClass] = None
    path_reason: str = ""
    path_authorization_success: bool = False
    path_completed_through_aep: bool = False
    # Native record references (not copies of mutable state — frozen sources)
    aep: Optional[AdmittedEvidencePackage] = None
    decision: Optional[MatrixDecisionRecord] = None

    def __post_init__(self) -> None:
        """Enforce identity and decision-evidence contract on all construction paths."""
        if not self.operation_id:
            raise ValueError("operation_id is required and must be non-empty")

        has_stage = self.aep is not None or self.decision is not None
        identity_fields = (
            ("protocol_id", self.protocol_id),
            ("protocol_version", self.protocol_version),
            ("scheme_id", self.scheme_id),
            ("scheme_version", self.scheme_version),
            ("policy_version", self.policy_version),
        )
        if has_stage:
            for name, val in identity_fields:
                if val is None or val == "":
                    raise ValueError(
                        f"{name} must be a non-empty str when AEP or decision is present"
                    )
        else:
            for name, val in identity_fields:
                if val is not None:
                    raise ValueError(
                        f"{name} must be None when neither AEP nor decision is present "
                        f"(got {val!r}; empty string is not permitted)"
                    )

        # Frozen schema: when a Matrix decision is reached, verification_result
        # and admitted_claims_digest are first-class required evidence fields.
        if self.decision is not None:
            if self.verification_result is None or self.verification_result == "":
                raise ValueError(
                    "verification_result must be a non-empty str when decision is present"
                )
            if self.admitted_claims_digest is None or self.admitted_claims_digest == "":
                raise ValueError(
                    "admitted_claims_digest must be a non-empty str when decision is present"
                )
            if self.decision_id is None or self.decision_id == "":
                raise ValueError(
                    "decision_id must be a non-empty str when decision is present"
                )


@dataclass(frozen=True)
class AuditReadResult:
    status: AuditReadStatus
    evidence: Optional[OperationEvidence] = None
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status is AuditReadStatus.FOUND:
            if self.evidence is None:
                raise ValueError("FOUND requires evidence")
            if self.reason is not None:
                raise ValueError("FOUND must not carry an error reason")
        elif self.status is AuditReadStatus.NOT_FOUND:
            if self.evidence is not None:
                raise ValueError("NOT_FOUND must not carry evidence")
            if self.reason is not None:
                raise ValueError("NOT_FOUND must not carry an error reason")
        elif self.status is AuditReadStatus.READ_ERROR:
            if self.evidence is not None:
                raise ValueError("READ_ERROR must not carry evidence")
            if not self.reason:
                raise ValueError("READ_ERROR requires a non-empty reason")


@dataclass(frozen=True)
class AuditGatedPathResult:
    """
    Post-commit external result shape (Phase 1 type only).

    Phase 1 does not implement gate_path_result. Manual construction of this
    type is allowed for tests and type-checking only.

    Phase 2 requirement: only the shared gate_path_result (or facades that
    call it exclusively) may set conformant_external_allow=True on a supported
    execution path. Callers must not treat a hand-built
    AuditGatedPathResult(conformant_external_allow=True) as an authorizing API.
    """

    path: PathResult
    audit_commit_result: Optional[AuditCommitResult]
    conformant_external_allow: bool
    failure_class: Optional[FailureClass]
    reason: str


class AuditPort(Protocol):
    """Port protocol — adapters implement this in a later phase."""

    def commit_attempt(self, evidence_set: OperationEvidence) -> AuditCommitResult:
        """Commit or idempotently reconcile one logical attempt keyed by operation_id."""
        ...

    def read_attempt(self, operation_id: str) -> AuditReadResult:
        """Read one logical attempt; distinguish absence from read failure."""
        ...


# ---------------------------------------------------------------------------
# Shared evidence builder
# ---------------------------------------------------------------------------


class EvidenceBindingError(ValueError):
    """Raised when PathResult-linked evidence is missing or contradictory."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}:{message}")


def _five_field_from_aep(aep: AdmittedEvidencePackage) -> IdentityTuple:
    return aep.five_field_identity()


def _require_nonempty(field_name: str, value: Optional[str]) -> str:
    if value is None or value == "":
        raise EvidenceBindingError(
            "missing_identity_field",
            f"{field_name} is required and must be non-empty when AEP or decision is present",
        )
    return value


def parse_audit_timestamp(value: str, *, field_name: str) -> datetime:
    """
    Parse an audit timestamp into an aware UTC datetime.

    Accepted forms (normalized to UTC):
      - ISO-8601 with explicit offset, e.g. 2026-10-23T12:00:00+00:00
      - ISO-8601 with Z suffix, e.g. 2026-10-23T12:00:00Z
      - ISO-8601 naive (treated as UTC), e.g. 2026-10-23T12:00:00

    Microseconds optional. Rejects empty strings and unparseable values.
    """
    if value is None or value == "":
        raise EvidenceBindingError(
            "invalid_timestamp",
            f"{field_name} is empty",
        )
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise EvidenceBindingError(
            "invalid_timestamp",
            f"{field_name}={value!r} is not a supported ISO-8601 timestamp: {exc}",
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def _assert_causal_order(*, emitted_at: str, decided_at: str) -> None:
    """Require decided_at >= emitted_at under parsed UTC instants."""
    t_emit = parse_audit_timestamp(emitted_at, field_name="emitted_at")
    t_dec = parse_audit_timestamp(decided_at, field_name="decided_at")
    if t_dec < t_emit:
        raise EvidenceBindingError(
            "ordering_inverted",
            f"decided_at={decided_at!r} precedes emitted_at={emitted_at!r}",
        )




def from_path_result(path: PathResult) -> OperationEvidence:
    """
    Map a completed PathResult to the logical OperationEvidence view.

    - Does not mint substitute operation_id, verification_event_id, or decision_id.
    - Does not mutate source records.
    - Does not authorize; does not claim durability.
    - Omits conditional fields when the corresponding path stage was not reached.
    - Fails explicitly on contradictory bindings between path, AEP, and decision.
    - Never uses empty strings for five-field identity / policy_version; either
      non-empty values (when AEP/decision present) or None (early failure only).
    """
    if path is None:
        raise EvidenceBindingError("missing_path", "PathResult is required")

    operation_id = path.operation_id
    if not operation_id:
        raise EvidenceBindingError("missing_operation_id", "operation_id is required")

    aep = path.aep
    decision = path.decision

    # Default: absent identity (early failure). Never "" placeholders.
    protocol_id: Optional[str] = None
    protocol_version: Optional[str] = None
    scheme_id: Optional[str] = None
    scheme_version: Optional[str] = None
    policy_version: Optional[str] = None
    policy_id: Optional[str] = None
    verification_event_id: Optional[str] = None
    verification_result: Optional[str] = None
    admitted_claims_digest: Optional[str] = None
    emitted_at: Optional[str] = None
    decision_id: Optional[str] = None
    disposition: Optional[MatrixDisposition] = None
    decided_at: Optional[str] = None

    if aep is not None:
        if aep.operation_id != operation_id:
            raise EvidenceBindingError(
                "operation_aep_mismatch",
                f"path.operation_id={operation_id!r} aep.operation_id={aep.operation_id!r}",
            )
        if not aep.verification_event_id:
            raise EvidenceBindingError(
                "missing_verification_event_id",
                "AEP present without verification_event_id",
            )
        identity = _five_field_from_aep(aep)
        protocol_id = _require_nonempty("protocol_id", identity.protocol_id)
        protocol_version = _require_nonempty("protocol_version", identity.protocol_version)
        scheme_id = _require_nonempty("scheme_id", identity.scheme_id)
        scheme_version = _require_nonempty("scheme_version", identity.scheme_version)
        policy_version = _require_nonempty("policy_version", identity.policy_version)
        verification_event_id = aep.verification_event_id
        verification_result = aep.verification_result
        admitted_claims_digest = aep.claims_digest()
        emitted_at = aep.emitted_at or None

    if decision is not None:
        if decision.operation_id != operation_id:
            raise EvidenceBindingError(
                "operation_decision_mismatch",
                f"path.operation_id={operation_id!r} "
                f"decision.operation_id={decision.operation_id!r}",
            )
        # First-class decision evidence (frozen schema) before binding match checks.
        decision_id = _require_nonempty("decision_id", decision.decision_id)
        verification_result = _require_nonempty(
            "verification_result", decision.verification_result
        )
        admitted_claims_digest = _require_nonempty(
            "admitted_claims_digest", decision.admitted_claims_digest
        )
        if aep is not None:
            if decision.verification_event_id != aep.verification_event_id:
                raise EvidenceBindingError(
                    "verification_event_mismatch",
                    f"decision.verification_event_id={decision.verification_event_id!r} "
                    f"aep.verification_event_id={aep.verification_event_id!r}",
                )
            if not decision.binds_to_aep(aep):
                raise EvidenceBindingError(
                    "decision_aep_binding_violation",
                    "MatrixDecisionRecord does not bind_to_aep",
                )
        # Prefer decision-carried identity when decision exists (must match AEP if both)
        protocol_id = _require_nonempty("protocol_id", decision.protocol_id)
        protocol_version = _require_nonempty("protocol_version", decision.protocol_version)
        scheme_id = _require_nonempty("scheme_id", decision.scheme_id)
        scheme_version = _require_nonempty("scheme_version", decision.scheme_version)
        policy_version = _require_nonempty("policy_version", decision.policy_version)
        policy_id = decision.policy_id  # None means no named policy
        verification_event_id = decision.verification_event_id
        disposition = decision.disposition
        decided_at = decision.decided_at or None

    # Early failure: neither AEP nor decision — identity fields stay None.
    # Empty strings are never emitted for five-field identity / policy_version.

    # Decision-path ordering: parse accepted timestamp forms; reject inverted order.
    if emitted_at and decided_at:
        _assert_causal_order(emitted_at=emitted_at, decided_at=decided_at)

    return OperationEvidence(
        operation_id=operation_id,
        protocol_id=protocol_id,
        protocol_version=protocol_version,
        scheme_id=scheme_id,
        scheme_version=scheme_version,
        policy_version=policy_version,
        policy_id=policy_id,
        verification_event_id=verification_event_id,
        verification_result=verification_result,
        admitted_claims_digest=admitted_claims_digest,
        emitted_at=emitted_at,
        decision_id=decision_id,
        disposition=disposition,
        decided_at=decided_at,
        enforcement=path.enforcement,
        path_failure_class=path.failure_class,
        path_reason=path.reason or "",
        path_authorization_success=path.authorization_success,
        path_completed_through_aep=path.path_completed_through_aep,
        aep=aep,
        decision=decision,
    )


def _collect_public_attr_names(obj: object) -> set[str]:
    """Collect public dataclass field names (and nested dataclass field names one level deep)."""
    from dataclasses import fields, is_dataclass

    names: set[str] = set()
    if obj is None or not is_dataclass(obj):
        return names
    for f in fields(obj):
        names.add(f.name)
        val = getattr(obj, f.name)
        if is_dataclass(val):
            for nf in fields(val):
                names.add(nf.name)
        elif isinstance(val, (list, tuple)):
            for item in val:
                if is_dataclass(item):
                    for nf in fields(item):
                        names.add(nf.name)
                    # Claim-type strings are part of the public reconstruction surface
                    claim_type = getattr(item, "claim_type", None)
                    if isinstance(claim_type, str) and claim_type:
                        names.add(claim_type)
    return names


def assert_no_forbidden_evidence_keys(evidence: OperationEvidence) -> None:
    """
    Ensure the logical evidence view does not surface forbidden secret/witness keys
    on public attribute names used for reconstruction.

    Checks:
      - OperationEvidence field names
      - nested AdmittedEvidencePackage field names (when aep is present)
      - nested MatrixDecisionRecord field names (when decision is present)
      - nested AdmittedClaim field names and claim_type strings

    Does not deep-scan arbitrary claim *values* for secret material (values may be
    non-secret registered claims). Matches Stage 3.5 FORBIDDEN_AUDIT_KEYS substring
    policy on key/name paths, not payload contents.
    """
    from identity_runtime.zk_abstraction.audit import FORBIDDEN_AUDIT_KEYS

    names = _collect_public_attr_names(evidence)
    if evidence.aep is not None:
        names |= _collect_public_attr_names(evidence.aep)
    if evidence.decision is not None:
        names |= _collect_public_attr_names(evidence.decision)

    for n in sorted(names):
        lk = n.lower()
        for forbidden in FORBIDDEN_AUDIT_KEYS:
            if forbidden in lk:
                raise ValueError(f"forbidden_evidence_field:{n}")


# ---------------------------------------------------------------------------
# Phase 2 — Shared authorization gate (no storage adapter)
# ---------------------------------------------------------------------------


def gate_path_result(path: PathResult, port: AuditPort) -> AuditGatedPathResult:
    """
    Single shared authorization gate.

    Class A (Matrix disposition ALLOW): MUST commit for retention;
    conformant_external_allow only if path.authorization_success and CONFIRMED
    and evidence/order/bindings OK. Path failure never yields conformant ALLOW
    but does not waive the mandatory commit.
    Class B (DENY / escalate): SHOULD retain; never upgrades to ALLOW.
    Class C (early failure / no decision): MAY minimal retain; always non-allow.

    Does not mutate path. Does not reinterpret PathResult.authorization_success
    as audit confirmation. Commit is not caller-bypassable.
    """
    if path is None:
        raise TypeError("path is required")
    if port is None:
        raise TypeError("port is required")

    # --- Class C: no Matrix decision ---
    if path.decision is None:
        audit_result: Optional[AuditCommitResult] = None
        reason = path.reason or "early_failure_no_decision"
        failure = path.failure_class
        try:
            evidence = from_path_result(path)
            try:
                audit_result = port.commit_attempt(evidence)
            except Exception as exc:
                # Optional retention failure must not authorize.
                audit_result = AuditCommitResult.FAILED
                reason = f"{reason};audit_commit_error:{exc}"
        except EvidenceBindingError as exc:
            # Minimal path still non-authorizing; keep path failure class.
            reason = f"{reason};evidence_build:{exc}"
        return AuditGatedPathResult(
            path=path,
            audit_commit_result=audit_result,
            conformant_external_allow=False,
            failure_class=failure,
            reason=reason,
        )

    disposition = path.decision.disposition

    # --- Class B: DENY or escalate ---
    if disposition is not MatrixDisposition.ALLOW:
        audit_result = None
        reason = path.reason or f"matrix_{disposition.value}"
        failure = path.failure_class
        try:
            evidence = from_path_result(path)
            try:
                audit_result = port.commit_attempt(evidence)
            except Exception as exc:
                audit_result = AuditCommitResult.FAILED
                reason = f"{reason};audit_retention_failed:{exc}"
        except EvidenceBindingError as exc:
            reason = f"{reason};evidence_build:{exc}"
        return AuditGatedPathResult(
            path=path,
            audit_commit_result=audit_result,
            conformant_external_allow=False,
            failure_class=failure,
            reason=reason,
        )

    # --- Class A: Matrix disposition ALLOW (mandatory retention) ---
    # Class A is defined by Matrix disposition ALLOW, not by path success alone.
    # - MUST attempt evidence build + audit commit (retention obligation).
    # - conformant_external_allow requires path.authorization_success AND
    #   CONFIRMED and valid evidence; native path failure is never conformant ALLOW.
    # - When path.authorization_success is False, preserve path.failure_class
    #   (do not replace with UNAVAILABLE solely due to a successful retention commit).

    reason = path.reason or "matrix_ALLOW"
    path_failed = not path.authorization_success

    try:
        evidence = from_path_result(path)
    except EvidenceBindingError as exc:
        code = getattr(exc, "code", "") or ""
        if code in ("ordering_inverted", "invalid_timestamp"):
            fc = FailureClass.MISMATCHED
        elif code in (
            "missing_identity_field",
            "missing_operation_id",
            "missing_verification_event_id",
            "missing_decision_id",
            "missing_path",
        ):
            fc = FailureClass.MISSING
        elif code in (
            "operation_aep_mismatch",
            "operation_decision_mismatch",
            "verification_event_mismatch",
            "decision_aep_binding_violation",
        ):
            fc = FailureClass.MISMATCHED
        else:
            fc = path.failure_class or FailureClass.MISSING
        # Prefer existing native path failure class when path already failed.
        if path_failed and path.failure_class is not None:
            fc = path.failure_class
        return AuditGatedPathResult(
            path=path,
            audit_commit_result=None,
            conformant_external_allow=False,
            failure_class=fc,
            reason=str(exc),
        )

    try:
        assert_no_forbidden_evidence_keys(evidence)
    except ValueError as exc:
        fc = path.failure_class if path_failed and path.failure_class else FailureClass.MISMATCHED
        return AuditGatedPathResult(
            path=path,
            audit_commit_result=None,
            conformant_external_allow=False,
            failure_class=fc,
            reason=str(exc),
        )

    # Mandatory commit for Class A — no bypass.
    try:
        commit_raw = port.commit_attempt(evidence)
    except Exception as exc:
        fc = path.failure_class if path_failed and path.failure_class else FailureClass.UNAVAILABLE
        return AuditGatedPathResult(
            path=path,
            audit_commit_result=AuditCommitResult.FAILED,
            conformant_external_allow=False,
            failure_class=fc,
            reason=f"audit_commit_error:{exc}",
        )

    commit = _normalize_commit_result(commit_raw)
    if commit is None:
        fc = path.failure_class if path_failed and path.failure_class else FailureClass.UNAVAILABLE
        return AuditGatedPathResult(
            path=path,
            audit_commit_result=None,
            conformant_external_allow=False,
            failure_class=fc,
            reason="required_audit_commit_skipped_or_none",
        )

    if commit is not AuditCommitResult.CONFIRMED:
        fc = path.failure_class if path_failed and path.failure_class else FailureClass.UNAVAILABLE
        return AuditGatedPathResult(
            path=path,
            audit_commit_result=commit,
            conformant_external_allow=False,
            failure_class=fc,
            reason=f"audit_commit_{commit.value}",
        )

    # CONFIRMED retention succeeded. Conformant external ALLOW still requires
    # native path success; Matrix ALLOW + failed path never authorizes.
    if path_failed:
        return AuditGatedPathResult(
            path=path,
            audit_commit_result=AuditCommitResult.CONFIRMED,
            conformant_external_allow=False,
            failure_class=path.failure_class,
            reason=reason or "matrix_ALLOW_path_not_successful",
        )

    return AuditGatedPathResult(
        path=path,
        audit_commit_result=AuditCommitResult.CONFIRMED,
        conformant_external_allow=True,
        failure_class=None,
        reason=reason or "conformant_external_allow",
    )


def _normalize_commit_result(commit_raw: object) -> Optional[AuditCommitResult]:
    """
    Map AuditPort commit outcomes to AuditCommitResult or None.

    Only actual AuditCommitResult enum instances are accepted as valid outcomes.
    None means skipped/absent required commit.
    Every other return value (including the string "CONFIRMED") is normalized
    to FAILED so malformed returns cannot produce conformant_external_allow.
    """
    if commit_raw is None:
        return None
    if isinstance(commit_raw, AuditCommitResult):
        return commit_raw
    return AuditCommitResult.FAILED
