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
from identity_runtime.zk_abstraction.verification_event_seal import (
    SealResult,
    SealStatus,
    VerificationEventRecord,
)
from identity_runtime.zk_abstraction.policy_resolver import (
    ContextResolution,
    ApplicablePolicyRecord,
    PolicyResolution,
    PolicyResolutionStatus,
    PolicyResolver,
)


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
    # WP-3.6.6 / CC-WP-3.6.3 provenance flags — bound to this policy object only
    # (not unbound caller kwargs). Default False = no universal provenance default.
    freshness_required: bool = False
    single_use_required: bool = False
    explicit_provenance_required: bool = False

    def requires_verification_event_provenance(self) -> bool:
        """True when this exact policy declares freshness, single-use, or explicit provenance."""
        return bool(
            self.freshness_required
            or self.single_use_required
            or self.explicit_provenance_required
        )




def _policy_from_resolved(record: ApplicablePolicyRecord) -> MatrixPolicy:
    """Adapter: ApplicablePolicyRecord -> MatrixPolicy view (field projection only)."""
    return MatrixPolicy(
        policy_id=record.policy_id,
        policy_version=record.policy_version_identity,
        allow_when_valid=record.allow_when_valid,
        require_admitted_claim=record.require_admitted_claim,
        force_deny=record.force_deny,
        supported_protocol_ids=frozenset(record.supported_protocol_ids),
        supported_scheme_ids=frozenset(record.supported_scheme_ids),
        freshness_required=record.freshness_required,
        single_use_required=record.single_use_required,
        explicit_provenance_required=record.explicit_provenance_required,
    )


@dataclass(frozen=True)
class OperationPolicyContext:
    """Phase 4.2d: retained policy handle for one operation.

    Continuity is object identity of `retained_record` (or this context handle),
    not field equality of a separately constructed ApplicablePolicyRecord.
    """

    retained_record: ApplicablePolicyRecord
    matrix_view: MatrixPolicy
    origin: Optional[OriginMark] = None

    @staticmethod
    def from_resolved(record: ApplicablePolicyRecord) -> "OperationPolicyContext":
        """Test-only. Does NOT register production origin."""
        return OperationPolicyContext(
            retained_record=record,
            matrix_view=_policy_from_resolved(record),
            origin=None,
        )



def _synthetic_record_from_matrix_policy(
    policy: MatrixPolicy, identity: IdentityTuple
) -> ApplicablePolicyRecord:
    """Test-fixture only: build a record so continuity APIs have an object.

    Not a production authority path.
    """
    return ApplicablePolicyRecord(
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        protocol_id=identity.protocol_id,
        protocol_version=identity.protocol_version,
        scheme_id=identity.scheme_id,
        scheme_version=identity.scheme_version,
        policy_version_identity=identity.policy_version,
        freshness_required=policy.freshness_required,
        single_use_required=policy.single_use_required,
        explicit_provenance_required=policy.explicit_provenance_required,
        legacy_non_provenance_permitted=True,  # test fixture treats as explicit legacy
        allow_when_valid=policy.allow_when_valid,
        require_admitted_claim=policy.require_admitted_claim,
        force_deny=policy.force_deny,
        supported_protocol_ids=frozenset(policy.supported_protocol_ids),
        supported_scheme_ids=frozenset(policy.supported_scheme_ids),
        catalog_version="test-fixture",
    )

def _test_matrix_policy_fixture_enabled(allow_flag: bool) -> bool:
    """Test fixture seam: requires both the explicit flag AND env opt-in.

    Production processes must not set OSF_ALLOW_TEST_MATRIX_POLICY=1.
    """
    import os
    if not allow_flag:
        return False
    return os.environ.get("OSF_ALLOW_TEST_MATRIX_POLICY", "") == "1"


def enforce_policy_and_provenance(
    *,
    operation_id: str,
    identity: IdentityTuple,
    sealed_event: Optional[SealResult],
    verification_event_id: Optional[str],
    runtime: Optional["ProductionRuntime"] = None,
    policy_resolver: Optional[PolicyResolver] = None,
    # Test-only: when True *and* OSF_ALLOW_TEST_MATRIX_POLICY=1, allow MatrixPolicy fixture
    allow_test_matrix_policy: bool = False,
    test_matrix_policy: Optional[MatrixPolicy] = None,
) -> tuple[Optional[PathResult], Optional[OperationPolicyContext], Optional[str]]:
    """
    Phase 4.2c/d: resolve policy, enforce provenance/legacy, retain policy record.

    Returns (early_path_result, operation_policy_context, bound_verification_event_id).
    If early_path_result is not None, caller must return it immediately.
    Continuity: the same OperationPolicyContext.retained_record object is used for
    subsequent Matrix evaluation (Phase 4.2d).
    """
    # E3-A1-D1: production requires retained ProductionRuntime
    if runtime is not None:
        policy_resolver = runtime.policy_resolver
    if policy_resolver is None:
        if _test_matrix_policy_fixture_enabled(allow_test_matrix_policy) and test_matrix_policy is not None:
            # Explicit test fixture mode only — not production authority
            pol = test_matrix_policy
            if pol.requires_verification_event_provenance():
                if (
                    sealed_event is None
                    or sealed_event.status is not SealStatus.SEALED
                    or sealed_event.record is None
                ):
                    return (
                        _non_authorize(
                            operation_id=operation_id,
                            aep=None,
                            failure_class=FailureClass.MISSING,
                            reason="provenance_required_missing_sealed_record",
                            hard_stop=True,
                        ),
                        None,
                        None,
                    )
                rec = sealed_event.record
                if (
                    verification_event_id is not None
                    and verification_event_id != rec.verification_event_id
                ):
                    return (
                        _non_authorize(
                            operation_id=operation_id,
                            aep=None,
                            failure_class=FailureClass.MISMATCHED,
                            reason="caller_event_id_conflicts_sealed_record",
                            hard_stop=True,
                        ),
                        None,
                        None,
                    )
                fx = OperationPolicyContext.from_resolved(
                    _synthetic_record_from_matrix_policy(pol, identity)
                )
                return None, fx, rec.verification_event_id
            # Test MatrixPolicy: treat as explicit legacy for fixture only
            fx = OperationPolicyContext.from_resolved(
                _synthetic_record_from_matrix_policy(pol, identity)
            )
            return None, fx, verification_event_id
        return (
            _non_authorize(
                operation_id=operation_id,
                aep=None,
                failure_class=FailureClass.MISSING,
                reason="production_runtime_required",
                hard_stop=True,
            ),
            None,
            None,
        )

    if runtime is not None:
        cres = runtime.context_for(identity)
    else:
        cres = policy_resolver.context_for(identity)
    if not cres.is_authorized_context or cres.context is None:
        return (
            _non_authorize(
                operation_id=operation_id,
                aep=None,
                failure_class=FailureClass.MISSING,
                reason=f"policy_resolution_{cres.status.value}:{cres.reason}",
                hard_stop=True,
            ),
            None,
            None,
        )

    ctx = cres.context
    record = ctx.retained_record

    if record.requires_verification_event_provenance():
        if (
            sealed_event is None
            or sealed_event.status is not SealStatus.SEALED
            or sealed_event.record is None
        ):
            return (
                _non_authorize(
                    operation_id=operation_id,
                    aep=None,
                    failure_class=FailureClass.MISSING,
                    reason="provenance_required_missing_sealed_record",
                    hard_stop=True,
                ),
                None,
                None,
            )
        srec = sealed_event.record
        if (
            verification_event_id is not None
            and verification_event_id != srec.verification_event_id
        ):
            return (
                _non_authorize(
                    operation_id=operation_id,
                    aep=None,
                    failure_class=FailureClass.MISMATCHED,
                    reason="caller_event_id_conflicts_sealed_record",
                    hard_stop=True,
                ),
                None,
                None,
            )
        return None, ctx, srec.verification_event_id

    # No provenance required — legacy only if explicit
    if record.legacy_non_provenance_permitted is True:
        return None, ctx, verification_event_id

    return (
        _non_authorize(
            operation_id=operation_id,
            aep=None,
            failure_class=FailureClass.MISSING,
            reason="legacy_non_provenance_not_permitted",
            hard_stop=True,
        ),
        None,
        None,
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
    retained_policy_record: Optional[ApplicablePolicyRecord] = None


def _non_authorize(
    *,
    operation_id: str,
    aep: Optional[AdmittedEvidencePackage],
    failure_class: Optional[FailureClass],
    reason: str,
    disposition: MatrixDisposition = MatrixDisposition.DENY,
    policy: Optional[MatrixPolicy] = None,
    hard_stop: bool = False,
    retained_policy_record: Optional[ApplicablePolicyRecord] = None,
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
        retained_policy_record=retained_policy_record,
    )




# ---------------------------------------------------------------------------
# E3-A1-D1: immutable application runtime (resolver + issuer bound)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProductionRuntime:
    """Trusted application-instance runtime. Composition root constructs and retains.

    Binds exact PolicyResolver and its origin_issuer. Immutable after construction.
    Ordinary callers cannot replace dependencies on an existing instance.
    """

    policy_resolver: PolicyResolver
    origin_issuer: OriginIssuer

    def __post_init__(self) -> None:
        if self.policy_resolver is None:
            raise ValueError("policy_resolver_required")
        if self.origin_issuer is None:
            raise ValueError("origin_issuer_required")
        if self.origin_issuer is not self.policy_resolver.origin_issuer:
            raise ValueError("origin_issuer_must_be_resolver_owned")

    @staticmethod
    def from_resolver(resolver: PolicyResolver) -> "ProductionRuntime":
        if resolver is None:
            raise ValueError("resolver_required")
        return ProductionRuntime(
            policy_resolver=resolver,
            origin_issuer=resolver.origin_issuer,
        )

    def context_for(self, identity: Any) -> "ContextResolution":
        return self.policy_resolver.context_for(identity)

    def evaluate_matrix(
        self,
        aep: AdmittedEvidencePackage,
        policy: "MatrixPolicy | OperationPolicyContext",
        *,
        expected_retained_record: Optional[ApplicablePolicyRecord] = None,
        allow_test_matrix_policy: bool = False,
    ) -> "PathResult":
        """Production Matrix entry: uses this runtime's bound issuer only."""
        return _evaluate_matrix_with_issuer(
            aep,
            policy,
            trusted_issuer=self.origin_issuer,
            expected_retained_record=expected_retained_record,
            allow_test_matrix_policy=allow_test_matrix_policy,
        )


def _evaluate_matrix_with_issuer(
    aep: AdmittedEvidencePackage,
    policy: MatrixPolicy | OperationPolicyContext,
    *,
    trusted_issuer: Optional[OriginIssuer],
    expected_retained_record: Optional[ApplicablePolicyRecord] = None,
    allow_test_matrix_policy: bool = False,
) -> PathResult:
    """Internal Matrix evaluation. Production must supply runtime-bound issuer.

    Not a production façade: callers should use ProductionRuntime.evaluate_matrix.
    """
    retained: Optional[ApplicablePolicyRecord] = None
    if isinstance(policy, OperationPolicyContext):
        retained = policy.retained_record
        if retained is None:
            return _non_authorize(
                operation_id=aep.operation_id,
                aep=aep,
                failure_class=FailureClass.MISSING,
                reason="policy_context_missing_retained_record",
                hard_stop=True,
            )
        if trusted_issuer is None:
            return _non_authorize(
                operation_id=aep.operation_id,
                aep=aep,
                failure_class=FailureClass.MISSING,
                reason="trusted_origin_issuer_required",
                hard_stop=True,
                retained_policy_record=retained,
            )
        if not trusted_issuer.recognizes(policy.origin, retained):
            return _non_authorize(
                operation_id=aep.operation_id,
                aep=aep,
                failure_class=FailureClass.MISMATCHED,
                reason="resolver_origin_unrecognized",
                hard_stop=True,
                retained_policy_record=retained,
            )
        # Mandatory 4.2d continuity
        if expected_retained_record is None:
            expected_retained_record = retained
        if retained is not expected_retained_record:
            return _non_authorize(
                operation_id=aep.operation_id,
                aep=aep,
                failure_class=FailureClass.MISMATCHED,
                reason="policy_record_continuity_violation",
                hard_stop=True,
                retained_policy_record=retained,
            )
        policy = policy.matrix_view
    elif isinstance(policy, MatrixPolicy):
        if not _test_matrix_policy_fixture_enabled(allow_test_matrix_policy):
            return _non_authorize(
                operation_id=aep.operation_id,
                aep=aep,
                failure_class=FailureClass.MISSING,
                reason="matrix_requires_operation_policy_context",
                hard_stop=True,
            )
        # Test fixture path only — no retained continuity claim
        retained = None
    else:
        return _non_authorize(
            operation_id=aep.operation_id,
            aep=aep,
            failure_class=FailureClass.MISSING,
            reason="matrix_policy_argument_invalid",
            hard_stop=True,
        )
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
            retained_policy_record=retained,
        )

    # Unsupported protocol/scheme
    if aep.protocol_id not in policy.supported_protocol_ids:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=FailureClass.UNSUPPORTED,
            reason="unsupported_protocol_id",
            policy=policy,
            retained_policy_record=retained,
        )
    if aep.scheme_id not in policy.supported_scheme_ids:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=FailureClass.UNSUPPORTED,
            reason="unsupported_scheme_id",
            policy=policy,
            retained_policy_record=retained,
        )

    # Policy version must match path identity (explicit; no default repair)
    if policy.policy_version != aep.policy_version:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=FailureClass.MISMATCHED,
            reason="policy_version_mismatch",
            policy=policy,
            retained_policy_record=retained,
        )

    # Invalid / error verification never ALLOW
    if aep.verification_result != VerificationResultCode.VALID.value:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=FailureClass.VERIFICATION_NON_VALID,
            reason=f"verification_{aep.verification_result}",
            policy=policy,
            retained_policy_record=retained,
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
            retained_policy_record=retained,
        )

    if policy.require_admitted_claim and len(aep.admitted_claims) == 0:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=None,
            reason="matrix_requires_admitted_claim",
            policy=policy,
            retained_policy_record=retained,
        )

    if not policy.allow_when_valid:
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=None,
            reason="matrix_allow_when_valid_false",
            policy=policy,
            retained_policy_record=retained,
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
    if not decision.binds_to_aep(aep):
        return _non_authorize(
            operation_id=op,
            aep=aep,
            failure_class=FailureClass.MISMATCHED,
            reason="decision_aep_binding_violation",
            policy=policy,
            retained_policy_record=retained,
        )
    return PathResult(
        operation_id=op,
        aep=aep,
        decision=decision,
        enforcement=EnforcementOutcome.PROCEEDED,
        authorization_success=True,
        path_completed_through_aep=True,
        failure_class=None,
        reason="matrix_allow",
        retained_policy_record=retained,
    )



def evaluate_matrix(
    aep: AdmittedEvidencePackage,
    policy: MatrixPolicy | OperationPolicyContext,
    *,
    expected_retained_record: Optional[ApplicablePolicyRecord] = None,
    allow_test_matrix_policy: bool = False,
) -> PathResult:
    """Public Matrix helper.

    OperationPolicyContext requires ProductionRuntime.evaluate_matrix (runtime-bound issuer).
    Direct public evaluation of OperationPolicyContext fails closed (no caller issuer).
    Bare MatrixPolicy remains available only under R1 dual-gate.
    """
    return _evaluate_matrix_with_issuer(
        aep,
        policy,
        trusted_issuer=None,
        expected_retained_record=expected_retained_record,
        allow_test_matrix_policy=allow_test_matrix_policy,
    )



def run_runtime_proof_path(
    *,
    operation_id: str,
    identity: IdentityTuple,
    verification_result: str,
    admitted_claims: Sequence[AdmittedClaim] = (),
    verification_event_id: Optional[str] = None,
    verification_result_code: Optional[str] = None,
    verification_unavailable: bool = False,
    candidate_event_ids: Optional[Sequence[str]] = None,
    selected_event_id: Optional[str] = None,
    bind_operation_id_override: Optional[str] = None,
    bind_verification_event_override: Optional[str] = None,
    sealed_event: Optional[SealResult] = None,
    runtime: Optional[ProductionRuntime] = None,
    policy_resolver: Optional[PolicyResolver] = None,
    # Explicit test fixture only — not production policy authority
    policy: Optional[MatrixPolicy] = None,
    allow_test_matrix_policy: bool = False,
) -> PathResult:
    """
    Integrated S0–S4 slice for Stage 3.6.

    Selection boundary (AG-AUDIT-003):
      - ``candidate_event_ids is None`` → single-event mode (no inventory presented).
      - ``candidate_event_ids == ()`` → explicit empty inventory → MISSING.
      - non-empty inventory → ``select_verification_event`` before AEP/Matrix.

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

    # Phase 4.2c — trusted policy resolution + provenance/legacy enforcement
    early, policy_ctx, verification_event_id = enforce_policy_and_provenance(
        operation_id=operation_id,
        identity=identity,
        runtime=runtime,
        policy_resolver=policy_resolver,
        sealed_event=sealed_event,
        verification_event_id=verification_event_id,
        allow_test_matrix_policy=allow_test_matrix_policy,
        test_matrix_policy=policy,
    )
    if early is not None:
        return early
    assert policy_ctx is not None
    policy = policy_ctx.matrix_view

    if verification_unavailable:
        return _non_authorize(
            operation_id=operation_id,
            aep=None,
            failure_class=FailureClass.UNAVAILABLE,
            reason="verifier_unavailable",
            hard_stop=True,
        )

    # --- AG-AUDIT-003 selection boundary → authoritative V* ---
    v_star: Optional[str] = verification_event_id
    if candidate_event_ids is not None:
        sel = select_verification_event(
            operation_id=operation_id,
            candidate_event_ids=candidate_event_ids,
            selected_event_id=selected_event_id,
        )
        if not sel.ok:
            return _non_authorize(
                operation_id=operation_id,
                aep=None,
                failure_class=sel.failure_class,
                reason=sel.reason,
                hard_stop=True,
            )
        v_star = sel.selected_event_id
        if (
            verification_event_id is not None
            and verification_event_id != v_star
        ):
            return _non_authorize(
                operation_id=operation_id,
                aep=None,
                failure_class=FailureClass.MISMATCHED,
                reason="verification_event_selection_mismatch",
                hard_stop=True,
            )
    else:
        # Single-event mode: optional selected vs verification conflict
        if (
            selected_event_id is not None
            and verification_event_id is not None
            and selected_event_id != verification_event_id
        ):
            return _non_authorize(
                operation_id=operation_id,
                aep=None,
                failure_class=FailureClass.MISMATCHED,
                reason="selected_verification_event_conflict",
                hard_stop=True,
            )
        if selected_event_id is not None and verification_event_id is None:
            v_star = selected_event_id

    # S2 — emit AEP (may be non-conforming; Matrix path will fail closed)
    aep = build_aep(
        operation_id=bind_operation_id_override or operation_id,
        verification_event_id=v_star,
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
        _ret = policy_ctx.retained_record if policy_ctx is not None else None
        return _non_authorize(
            operation_id=operation_id,
            aep=aep,
            failure_class=FailureClass.MISMATCHED,
            reason="operation_aep_mismatch",
            policy=policy_ctx.matrix_view if policy_ctx is not None else None,
            retained_policy_record=_ret,
        )

    if runtime is None:
        return _non_authorize(
            operation_id=operation_id,
            aep=aep,
            failure_class=FailureClass.MISSING,
            reason="production_runtime_required",
            hard_stop=True,
        )
    return runtime.evaluate_matrix(aep, policy_ctx)


@dataclass(frozen=True)
class SelectionResult:
    """Outcome of the upstream single-event selection boundary (AG-AUDIT-003)."""

    ok: bool
    selected_event_id: Optional[str] = None
    failure_class: Optional[FailureClass] = None
    reason: str = ""


def select_verification_event(
    *,
    operation_id: str,
    candidate_event_ids: Sequence[str],
    selected_event_id: Optional[str] = None,
) -> SelectionResult:
    """
    Selection boundary: resolve candidate inventory to a single bound event V*.

    - Explicit empty inventory → MISSING
    - Multiple candidates without selection → AMBIGUOUS (via reject_unbound_multi_event)
    - Selection not in inventory → MISMATCHED
    - Single candidate without selection → that candidate is V*
    - Explicit selection in inventory → that selection is V*
    """
    _ = operation_id  # reserved for audit correlation; selection is event-set relative
    if len(candidate_event_ids) == 0:
        return SelectionResult(
            ok=False,
            failure_class=FailureClass.MISSING,
            reason="empty_candidate_inventory",
        )
    fc = reject_unbound_multi_event(
        operation_id=operation_id,
        candidate_event_ids=candidate_event_ids,
        selected_event_id=selected_event_id,
    )
    if fc is not None:
        reason = (
            "multi_event_ambiguous"
            if fc == FailureClass.AMBIGUOUS
            else "selected_event_not_in_candidates"
        )
        return SelectionResult(ok=False, failure_class=fc, reason=reason)
    if selected_event_id:
        v_star = selected_event_id
    else:
        # len == 1 guaranteed when fc is None and inventory non-empty without selection
        v_star = candidate_event_ids[0]
    return SelectionResult(ok=True, selected_event_id=v_star, reason="selected")


def reject_unbound_multi_event(
    *,
    operation_id: str,
    candidate_event_ids: Sequence[str],
    selected_event_id: Optional[str],
) -> Optional[FailureClass]:
    """Single-event rule (Batch 3): multiple candidates without selection ⇒ ambiguous."""
    _ = operation_id
    if len(candidate_event_ids) > 1 and not selected_event_id:
        return FailureClass.AMBIGUOUS
    if selected_event_id and selected_event_id not in candidate_event_ids:
        return FailureClass.MISMATCHED
    return None



# ---------------------------------------------------------------------------
# IndependentVerifier → AEP bridge (S1 → S2)
# ---------------------------------------------------------------------------


def _verification_result_to_codes(result: Any) -> tuple[str, str]:
    """
    Map Stage 3.5 VerificationResult to AEP verification_result / code.

    accepted True  → valid
    accepted False → invalid (or error when status suggests structural failure)
    Never treats acceptance as authorization.
    """
    accepted = bool(getattr(result, "accepted", False))
    status = str(getattr(result, "status_code", "") or "")
    reason = str(getattr(result, "reason", "") or "")
    code = status or reason or "UNSPECIFIED"
    if accepted:
        return VerificationResultCode.VALID.value, code
    upper = code.upper()
    if any(
        tok in upper
        for tok in (
            "STRUCTURAL",
            "UNVERIFIABLE",
            "UNAVAILABLE",
            "ERROR",
            "EXCEPTION",
        )
    ):
        return VerificationResultCode.ERROR.value, code
    return VerificationResultCode.INVALID.value, code


def claims_from_verification_result(result: Any) -> tuple[AdmittedClaim, ...]:
    """
    Emit only registered admitted claims explicitly supported by verification output.

    - context_binding_id from binding_target.context_id when present
    - Does not invent eligibility from ambient state
    - Does not treat verified_eligibility_claim as Matrix ALLOW
    """
    claims: list[AdmittedClaim] = []
    binding = getattr(result, "binding_target", None)
    if binding is not None:
        ctx = getattr(binding, "context_id", None)
        if ctx:
            claims.append(
                AdmittedClaim(claim_type="context_binding_id", value=str(ctx))
            )
    return tuple(claims)


def aep_from_verification_result(
    result: Any,
    *,
    operation_id: str,
    verification_event_id: Optional[str] = None,
    admitted_claims: Optional[Sequence[AdmittedClaim]] = None,
    verifier_implementation_id: str = "IndependentVerifier",
    proof_transcript_digest: Optional[str] = None,
    catalog_contract_seal: Optional[str] = None,
) -> AdmittedEvidencePackage:
    """
    S1 → S2: build AEP from a Stage 3.5 VerificationResult (e.g. IndependentVerifier).

    Push model only. Does not call the Matrix and does not authorize.
    """
    if result is None:
        raise ValueError("verification result is required")
    identity = getattr(result, "identity_tuple", None)
    if identity is None:
        raise ValueError("verification result missing identity_tuple")

    v_result, v_code = _verification_result_to_codes(result)
    if admitted_claims is None:
        claims = claims_from_verification_result(result)
    else:
        claims = tuple(admitted_claims)

    return build_aep(
        operation_id=operation_id,
        verification_event_id=verification_event_id,
        verification_result=v_result,
        identity=identity,
        admitted_claims=claims,
        verification_result_code=v_code,
        verifier_implementation_id=verifier_implementation_id,
        proof_transcript_digest=proof_transcript_digest,
        catalog_contract_seal=catalog_contract_seal,
    )


def run_path_from_verification(
    result: Any,
    *,
    operation_id: str,
    verification_event_id: Optional[str] = None,
    admitted_claims: Optional[Sequence[AdmittedClaim]] = None,
    candidate_event_ids: Optional[Sequence[str]] = None,
    selected_event_id: Optional[str] = None,
    sealed_event: Optional[SealResult] = None,
    runtime: Optional[ProductionRuntime] = None,
    policy_resolver: Optional[PolicyResolver] = None,
    policy: Optional[MatrixPolicy] = None,
    allow_test_matrix_policy: bool = False,
) -> PathResult:
    """
    S1→S4 convenience: VerificationResult → AEP → Matrix → enforcement disposition.

    Still proof ≠ authorization: policy may DENY on valid verification.
    Honors the same AG-AUDIT-003 selection boundary as run_runtime_proof_path.
    """
    if not operation_id:
        return _non_authorize(
            operation_id="",
            aep=None,
            failure_class=FailureClass.MISSING,
            reason="missing_operation_id",
            hard_stop=True,
        )
    if result is None:
        return _non_authorize(
            operation_id=operation_id,
            aep=None,
            failure_class=FailureClass.UNAVAILABLE,
            reason="verification_result_missing",
            hard_stop=True,
        )

    identity = getattr(result, "identity_tuple", None)
    if identity is None:
        return _non_authorize(
            operation_id=operation_id,
            aep=None,
            failure_class=FailureClass.MISSING,
            reason="missing_identity_on_verification_result",
            hard_stop=True,
        )
    early, policy_ctx, verification_event_id = enforce_policy_and_provenance(
        operation_id=operation_id,
        identity=identity,
        runtime=runtime,
        policy_resolver=policy_resolver,
        sealed_event=sealed_event,
        verification_event_id=verification_event_id,
        allow_test_matrix_policy=allow_test_matrix_policy,
        test_matrix_policy=policy,
    )
    if early is not None:
        return early
    assert policy_ctx is not None
    policy = policy_ctx.matrix_view

    v_star: Optional[str] = verification_event_id
    if candidate_event_ids is not None:
        sel = select_verification_event(
            operation_id=operation_id,
            candidate_event_ids=candidate_event_ids,
            selected_event_id=selected_event_id,
        )
        if not sel.ok:
            return _non_authorize(
                operation_id=operation_id,
                aep=None,
                failure_class=sel.failure_class,
                reason=sel.reason,
                hard_stop=True,
            )
        v_star = sel.selected_event_id
        if verification_event_id is not None and verification_event_id != v_star:
            return _non_authorize(
                operation_id=operation_id,
                aep=None,
                failure_class=FailureClass.MISMATCHED,
                reason="verification_event_selection_mismatch",
                hard_stop=True,
            )
    else:
        if (
            selected_event_id is not None
            and verification_event_id is not None
            and selected_event_id != verification_event_id
        ):
            return _non_authorize(
                operation_id=operation_id,
                aep=None,
                failure_class=FailureClass.MISMATCHED,
                reason="selected_verification_event_conflict",
                hard_stop=True,
            )
        if selected_event_id is not None and verification_event_id is None:
            v_star = selected_event_id

    try:
        aep = aep_from_verification_result(
            result,
            operation_id=operation_id,
            verification_event_id=v_star,
            admitted_claims=admitted_claims,
        )
    except ValueError as exc:
        return _non_authorize(
            operation_id=operation_id,
            aep=None,
            failure_class=FailureClass.MISSING,
            reason=f"aep_build_failed:{exc}",
            hard_stop=True,
        )
    if runtime is None:
        return _non_authorize(
            operation_id=operation_id,
            aep=aep,
            failure_class=FailureClass.MISSING,
            reason="production_runtime_required",
            hard_stop=True,
        )
    return runtime.evaluate_matrix(aep, policy_ctx)
