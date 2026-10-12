# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""
Stage 3.6 — Runtime proof-to-authorization path (WP-3.6.1–3.6.4 slice).

Implements:
  S0 operation → S1 verification result intake → S2 AEP → S3 Matrix → S4 enforcement disposition

Normative anchors: frozen Stage 3.6 roadmap; Clarification Batches 1–3.
Does not implement full WP-3.6.5 durable audit store, WP-3.6.6 freshness policy,
or Stage 3.6 formal adjudication. Does not reopen Stage 3.5.

AEP is an evidence-boundary object only — not ZKP public inputs, not D-3.
Proof validity ≠ authorization; Matrix is the only authorizer on this path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional, Sequence
import hashlib
import json
import uuid

from identity_runtime.zk_abstraction.identity import IdentityTuple


# ---------------------------------------------------------------------------
# Claim registry v0 (Batch 1)
# ---------------------------------------------------------------------------

CLAIM_REGISTRY_V0: frozenset[str] = frozenset(
    {
        "eligibility_predicate_id",
        "context_binding_id",
        "assurance_level",
    }
)


class VerificationResultCode(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"


class MatrixDisposition(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "escalate"


class FailureClass(str, Enum):
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    MISMATCHED = "mismatched"
    UNSUPPORTED = "unsupported"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    # Verification non-success (not one of the six path classes, but never ALLOW)
    VERIFICATION_NON_VALID = "verification_non_valid"


class EnforcementOutcome(str, Enum):
    PROCEEDED = "proceeded"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    HARD_STOPPED = "hard_stopped"


# ---------------------------------------------------------------------------
# AEP (Batch 1 / WP-3.6.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdmittedClaim:
    claim_type: str
    value: Any
    scope: Optional[str] = None

    def is_registered(self) -> bool:
        return self.claim_type in CLAIM_REGISTRY_V0


@dataclass(frozen=True)
class AdmittedEvidencePackage:
    """Sole structure that may cross verification → Matrix (evidence boundary)."""

    verification_event_id: str
    operation_id: str
    verification_result: str  # valid | invalid | error
    protocol_id: str
    protocol_version: str
    scheme_id: str
    scheme_version: str
    policy_version: str
    admitted_claims: tuple[AdmittedClaim, ...]
    emitted_at: str
    verification_result_code: Optional[str] = None
    proof_transcript_digest: Optional[str] = None
    verifier_implementation_id: Optional[str] = None
    catalog_contract_seal: Optional[str] = None

    def five_field_identity(self) -> IdentityTuple:
        return IdentityTuple(
            protocol_id=self.protocol_id,
            protocol_version=self.protocol_version,
            scheme_id=self.scheme_id,
            scheme_version=self.scheme_version,
            policy_version=self.policy_version,
        )

    def claims_digest(self) -> str:
        payload = [
            {"claim_type": c.claim_type, "value": c.value, "scope": c.scope}
            for c in self.admitted_claims
        ]
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def validate_aep(aep: AdmittedEvidencePackage) -> Optional[FailureClass]:
    """Return failure class if AEP is non-conforming; None if conforming."""
    if not aep.verification_event_id or not aep.operation_id:
        return FailureClass.MISSING
    if aep.verification_result not in (
        VerificationResultCode.VALID.value,
        VerificationResultCode.INVALID.value,
        VerificationResultCode.ERROR.value,
    ):
        return FailureClass.MISSING
    if aep.verification_result != VerificationResultCode.VALID.value:
        if not aep.verification_result_code:
            return FailureClass.MISSING
    for field_name in (
        aep.protocol_id,
        aep.protocol_version,
        aep.scheme_id,
        aep.scheme_version,
        aep.policy_version,
    ):
        if not field_name:
            return FailureClass.MISSING
    if not aep.emitted_at:
        return FailureClass.MISSING
    for claim in aep.admitted_claims:
        if not claim.is_registered():
            return FailureClass.UNSUPPORTED
    return None


def build_aep(
    *,
    operation_id: str,
    verification_event_id: Optional[str] = None,
    verification_result: str,
    identity: IdentityTuple,
    admitted_claims: Sequence[AdmittedClaim] = (),
    verification_result_code: Optional[str] = None,
    proof_transcript_digest: Optional[str] = None,
    verifier_implementation_id: Optional[str] = None,
    catalog_contract_seal: Optional[str] = None,
    emitted_at: Optional[str] = None,
) -> AdmittedEvidencePackage:
    """Emit AEP (push model). Does not authorize."""
    if verification_result == VerificationResultCode.VALID.value:
        code = verification_result_code
    else:
        code = verification_result_code or "UNSPECIFIED_NON_VALID"
    return AdmittedEvidencePackage(
        verification_event_id=verification_event_id or _new_id("ve"),
        operation_id=operation_id,
        verification_result=verification_result,
        verification_result_code=code,
        protocol_id=identity.protocol_id,
        protocol_version=identity.protocol_version,
        scheme_id=identity.scheme_id,
        scheme_version=identity.scheme_version,
        policy_version=identity.policy_version,
        admitted_claims=tuple(admitted_claims),
        emitted_at=emitted_at or _utc_now_iso(),
        proof_transcript_digest=proof_transcript_digest,
        verifier_implementation_id=verifier_implementation_id,
        catalog_contract_seal=catalog_contract_seal,
    )


# ---------------------------------------------------------------------------
# Matrix policy (minimal Stage 3.6 slice — not full product Matrix)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatrixPolicy:
    """Applicable policy selected by identity — content outside AEP (Batch 1)."""

    policy_id: str
    policy_version: str
    # If True, valid verification + usable path may ALLOW; still subject to deny rules
    allow_when_valid: bool = True
    # Require at least one admitted claim (default False: empty claims legal)
    require_admitted_claim: bool = False
    # Explicit deny even when verification_result == valid (proves proof ≠ authz)
    force_deny: bool = False
    supported_protocol_ids: frozenset[str] = field(
        default_factory=lambda: frozenset({"sf-zk"})
    )
    supported_scheme_ids: frozenset[str] = field(
        default_factory=lambda: frozenset({"mock-scheme", "mock-bn254-sfg16a", "mock-digest-v2"})
    )


# ---------------------------------------------------------------------------
# Decision binding (Batch 3 / WP-3.6.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatrixDecisionRecord:
    decision_id: str
    operation_id: str
    verification_event_id: str
    protocol_id: str
    protocol_version: str
    scheme_id: str
    scheme_version: str
    policy_version: str
    disposition: MatrixDisposition
    decided_at: str
    verification_result: str
    admitted_claims_digest: str
    policy_id: Optional[str] = None
    failure_class: Optional[FailureClass] = None
    reason: str = ""

    def binds_to_aep(self, aep: AdmittedEvidencePackage) -> bool:
        if self.operation_id != aep.operation_id:
            return False
        if self.verification_event_id != aep.verification_event_id:
            return False
        if self.protocol_id != aep.protocol_id:
            return False
        if self.protocol_version != aep.protocol_version:
            return False
        if self.scheme_id != aep.scheme_id:
            return False
        if self.scheme_version != aep.scheme_version:
            return False
        if self.policy_version != aep.policy_version:
            return False
        if self.admitted_claims_digest != aep.claims_digest():
            return False
        if self.verification_result != aep.verification_result:
            return False
        return True


@dataclass(frozen=True)
class PathResult:
    """Terminal outcome of one runtime proof-path attempt."""

    operation_id: str
    aep: Optional[AdmittedEvidencePackage]
    decision: Optional[MatrixDecisionRecord]
    enforcement: EnforcementOutcome
    authorization_success: bool
    path_completed_through_aep: bool
    failure_class: Optional[FailureClass]
    reason: str


def _non_authorize(
    *,
    operation_id: str,
    aep: Optional[AdmittedEvidencePackage],
    failure_class: Optional[FailureClass],
    reason: str,
    disposition: MatrixDisposition = MatrixDisposition.DENY,
    policy: Optional[MatrixPolicy] = None,
    hard_stop: bool = False,
) -> PathResult:
    decision: Optional[MatrixDecisionRecord] = None
    if aep is not None and not hard_stop:
        decision = MatrixDecisionRecord(
            decision_id=_new_id("dec"),
            operation_id=operation_id,
            verification_event_id=aep.verification_event_id,
            protocol_id=aep.protocol_id,
            protocol_version=aep.protocol_version,
            scheme_id=aep.scheme_id,
            scheme_version=aep.scheme_version,
            policy_version=aep.policy_version,
            policy_id=policy.policy_id if policy else None,
            disposition=disposition,
            decided_at=_utc_now_iso(),
            verification_result=aep.verification_result,
            admitted_claims_digest=aep.claims_digest(),
            failure_class=failure_class,
            reason=reason,
        )
    if hard_stop:
        enf = EnforcementOutcome.HARD_STOPPED
    elif disposition == MatrixDisposition.ESCALATE:
        enf = EnforcementOutcome.ESCALATED
    else:
        enf = EnforcementOutcome.BLOCKED
    return PathResult(
        operation_id=operation_id,
        aep=aep,
        decision=decision,
        enforcement=enf,
        authorization_success=False,
        path_completed_through_aep=aep is not None and validate_aep(aep) is None,
        failure_class=failure_class,
        reason=reason,
    )


def evaluate_matrix(aep: AdmittedEvidencePackage, policy: MatrixPolicy) -> PathResult:
    """
    S3 Matrix evaluation over conforming AEP + applicable policy only.
    Never infers claims or identity from ambient state.
    """
    op = aep.operation_id

    # Binding precondition: AEP must be conforming
    aep_fail = validate_aep(aep)
    if aep_fail is not None:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=aep_fail,
            reason=f"non_conforming_aep:{aep_fail.value}",
            policy=policy,
        )

    # Unsupported protocol/scheme
    if aep.protocol_id not in policy.supported_protocol_ids:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=FailureClass.UNSUPPORTED,
            reason="unsupported_protocol_id",
            policy=policy,
        )
    if aep.scheme_id not in policy.supported_scheme_ids:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=FailureClass.UNSUPPORTED,
            reason="unsupported_scheme_id",
            policy=policy,
        )

    # Policy version must match path identity (explicit; no default repair)
    if policy.policy_version != aep.policy_version:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=FailureClass.MISMATCHED,
            reason="policy_version_mismatch",
            policy=policy,
        )

    # Invalid / error verification never ALLOW
    if aep.verification_result != VerificationResultCode.VALID.value:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=FailureClass.VERIFICATION_NON_VALID,
            reason=f"verification_{aep.verification_result}",
            policy=policy,
        )

    # Explicit policy deny (valid proof ≠ authorization)
    if policy.force_deny:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=None,
            reason="matrix_policy_force_deny",
            disposition=MatrixDisposition.DENY,
            policy=policy,
        )

    if policy.require_admitted_claim and len(aep.admitted_claims) == 0:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=None,
            reason="matrix_requires_admitted_claim",
            policy=policy,
        )

    if not policy.allow_when_valid:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=None,
            reason="matrix_allow_when_valid_false",
            policy=policy,
        )

    # ALLOW — still bound to this AEP only
    decision = MatrixDecisionRecord(
        decision_id=_new_id("dec"),
        operation_id=op,
        verification_event_id=aep.verification_event_id,
        protocol_id=aep.protocol_id,
        protocol_version=aep.protocol_version,
        scheme_id=aep.scheme_id,
        scheme_version=aep.scheme_version,
        policy_version=aep.policy_version,
        policy_id=policy.policy_id,
        disposition=MatrixDisposition.ALLOW,
        decided_at=_utc_now_iso(),
        verification_result=aep.verification_result,
        admitted_claims_digest=aep.claims_digest(),
        failure_class=None,
        reason="matrix_allow",
    )
    assert decision.binds_to_aep(aep)
    return PathResult(
        operation_id=op,
        aep=aep,
        decision=decision,
        enforcement=EnforcementOutcome.PROCEEDED,
        authorization_success=True,
        path_completed_through_aep=True,
        failure_class=None,
        reason="matrix_allow",
    )


def run_runtime_proof_path(
    *,
    operation_id: str,
    identity: IdentityTuple,
    verification_result: str,
    policy: MatrixPolicy,
    admitted_claims: Sequence[AdmittedClaim] = (),
    verification_event_id: Optional[str] = None,
    verification_result_code: Optional[str] = None,
    verification_unavailable: bool = False,
    bind_operation_id_override: Optional[str] = None,
    bind_verification_event_override: Optional[str] = None,
) -> PathResult:
    """
    Integrated S0–S4 slice for Stage 3.6.

    ``bind_*_override`` parameters support negative tests for mismatched binding
    without ambient inference.
    """
    if not operation_id:
        return _non_authorize(
            operation_id=operation_id or "",
            aep=None,
            failure_class=FailureClass.MISSING,
            reason="missing_operation_id",
            hard_stop=True,
        )

    if verification_unavailable:
        return _non_authorize(
            operation_id=operation_id,
            aep=None,
            failure_class=FailureClass.UNAVAILABLE,
            reason="verifier_unavailable",
            hard_stop=True,
        )

    # S2 — emit AEP (may be non-conforming; Matrix path will fail closed)
    aep = build_aep(
        operation_id=bind_operation_id_override or operation_id,
        verification_event_id=verification_event_id,
        verification_result=verification_result,
        identity=identity,
        admitted_claims=admitted_claims,
        verification_result_code=verification_result_code,
    )

    # Optional deliberate binding mismatch for tests
    if bind_verification_event_override is not None:
        aep = AdmittedEvidencePackage(
            verification_event_id=bind_verification_event_override,
            operation_id=aep.operation_id,
            verification_result=aep.verification_result,
            verification_result_code=aep.verification_result_code,
            protocol_id=aep.protocol_id,
            protocol_version=aep.protocol_version,
            scheme_id=aep.scheme_id,
            scheme_version=aep.scheme_version,
            policy_version=aep.policy_version,
            admitted_claims=aep.admitted_claims,
            emitted_at=aep.emitted_at,
            proof_transcript_digest=aep.proof_transcript_digest,
            verifier_implementation_id=aep.verifier_implementation_id,
            catalog_contract_seal=aep.catalog_contract_seal,
        )

    # Operation / AEP operation mismatch → mismatched
    if aep.operation_id != operation_id:
        return _non_authorize(
            operation_id=operation_id,
            aep=aep,
            failure_class=FailureClass.MISMATCHED,
            reason="operation_aep_mismatch",
            policy=policy,
        )

    return evaluate_matrix(aep, policy)


def reject_unbound_multi_event(
    *,
    operation_id: str,
    candidate_event_ids: Sequence[str],
    selected_event_id: Optional[str],
) -> Optional[FailureClass]:
    """Single-event rule (Batch 3): multiple candidates without selection ⇒ ambiguous."""
    if len(candidate_event_ids) > 1 and not selected_event_id:
        return FailureClass.AMBIGUOUS
    if selected_event_id and selected_event_id not in candidate_event_ids:
        return FailureClass.MISMATCHED
    return None
