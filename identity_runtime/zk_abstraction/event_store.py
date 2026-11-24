# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""
WP-3.6.6 Blocker #4 — Phase A: Event Store logical port and types.

Logical interface only. Does not implement storage, durability, idempotency
algorithms, conflict detection, recovery, freshness, replay, authorization,
or failure classification.

Ownership:
  - Event Store / Blocker #4: persistence and resolution outcome domains
  - AuditPort retains operation_id identity and AuditCommitResult
  - Matrix remains the sole authorization authority
  - Blockers #6 / #7 / #8 own conditional resolution, freshness/replay, and
    FailureClass expansion respectively

Persistence outcomes and resolution outcomes are distinct enums and MUST NOT
be combined. Do not reuse AuditCommitResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional, Protocol

from identity_runtime.zk_abstraction.verification_event_seal import (
    SealResult,
    VerificationEventRecord,
    is_trusted_sealed,
)


# ---------------------------------------------------------------------------
# Persistence outcomes (Event Store–owned; labels parallel AuditPort by design)
# ---------------------------------------------------------------------------


class EventStorePersistResult(str, Enum):
    """Outcome of one logical persist attempt. Port-owned surface."""

    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    UNCERTAIN = "UNCERTAIN"


# ---------------------------------------------------------------------------
# Resolution outcomes (Blocker #4 exclusive ownership)
# ---------------------------------------------------------------------------


class EventStoreResolveResult(str, Enum):
    """
    Lookup outcome for one verification_event_id.

    Exclusively owned by Blocker #4. Not a FailureClass. Not a persist result.
    """

    FOUND_VALID = "FOUND_VALID"
    NOT_FOUND = "NOT_FOUND"
    FOUND_INVALID = "FOUND_INVALID"
    UNAVAILABLE = "UNAVAILABLE"
    LOOKUP_UNCERTAIN = "LOOKUP_UNCERTAIN"


# ---------------------------------------------------------------------------
# Trusted evidence view (shared persist input / successful resolve output)
# ---------------------------------------------------------------------------


class _TrustedViewCapability:
    """Module-private capability issued only by from_trusted_sealed.

    Ordinary TrustedEvidenceView(...) construction cannot obtain this.
    Conventional module privacy under P0 — not absolute same-process protection.
    """

    __slots__ = ()


_VIEW_CAPABILITY = _TrustedViewCapability()


@dataclass(frozen=True)
class TrustedEvidenceView:
    """
    Immutable logical view of sealed verification-event evidence.

    One shared representation for persistence input and successful resolution
    output. Does not carry storage metadata. Does not redefine the sealing
    schema; fields are taken from an already-sealed VerificationEventRecord.

    Supported construction path: from_trusted_sealed() only.
    Direct construction does not issue the capability and is not usable for
    persist/resolve handoff. This type is not a sealing authority.
    """

    verification_event_id: str
    verification_finalized_at: str
    verification_outcome: str
    protocol_id: str
    protocol_version: str
    scheme_id: str
    scheme_version: str
    policy_version: str
    record_schema_version: str
    recording_boundary_id: str
    integrity_material: Mapping[str, Any]
    # Issued only by from_trusted_sealed via object.__setattr__.
    _capability: Optional[_TrustedViewCapability] = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not self.verification_event_id or not str(self.verification_event_id).strip():
            raise ValueError("verification_event_id is required and must be non-empty")
        # Deep immutability for integrity_material (Approach A — flat scalar schema).
        # Approved P0 integrity material uses only str keys and immutable scalar
        # values (str | int, excluding bool). Nested mappings/sequences and other
        # mutable objects are rejected rather than partially frozen.
        material = self.integrity_material
        if material is None:
            raise ValueError("integrity_material is required")
        if not isinstance(material, Mapping):
            raise ValueError("integrity_material must be a mapping")
        frozen_pairs: dict[str, Any] = {}
        for key, value in material.items():
            if not isinstance(key, str):
                raise ValueError("integrity_material keys must be str")
            # bool is a subclass of int; reject explicitly (matches sealer discipline).
            if isinstance(value, bool) or not isinstance(value, (str, int)):
                raise ValueError(
                    "integrity_material values must be immutable scalars (str|int); "
                    "nested or mutable values are not permitted"
                )
            frozen_pairs[key] = value
        object.__setattr__(
            self, "integrity_material", MappingProxyType(frozen_pairs)
        )

    @property
    def is_trusted_view(self) -> bool:
        """True only when constructed via from_trusted_sealed."""
        return self._capability is _VIEW_CAPABILITY

    @staticmethod
    def from_trusted_sealed(sealed: SealResult) -> "TrustedEvidenceView":
        """
        Narrow construction boundary: only sealer-origin trusted SealResult.

        Requires is_trusted_sealed(sealed). Does not re-run sealing or mint ids.
        """
        if sealed is None or not is_trusted_sealed(sealed) or sealed.record is None:
            raise ValueError("trusted_evidence_requires_sealer_origin")
        rec: VerificationEventRecord = sealed.record
        if not rec.verification_event_id or not str(rec.verification_event_id).strip():
            raise ValueError("verification_event_id is required and must be non-empty")
        view = TrustedEvidenceView(
            verification_event_id=rec.verification_event_id,
            verification_finalized_at=rec.verification_finalized_at,
            verification_outcome=rec.verification_outcome,
            protocol_id=rec.protocol_id,
            protocol_version=rec.protocol_version,
            scheme_id=rec.scheme_id,
            scheme_version=rec.scheme_version,
            policy_version=rec.policy_version,
            record_schema_version=rec.record_schema_version,
            recording_boundary_id=rec.recording_boundary_id,
            integrity_material=dict(rec.integrity_material),
        )
        object.__setattr__(view, "_capability", _VIEW_CAPABILITY)
        return view


# ---------------------------------------------------------------------------
# Request / outcome envelopes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventStorePersistRequest:
    """Persist request keyed solely by verification_event_id (via evidence)."""

    evidence: TrustedEvidenceView

    @property
    def verification_event_id(self) -> str:
        return self.evidence.verification_event_id

    def __post_init__(self) -> None:
        if self.evidence is None:
            raise ValueError("evidence is required")
        if not isinstance(self.evidence, TrustedEvidenceView):
            raise ValueError("evidence must be a TrustedEvidenceView")
        if not self.evidence.is_trusted_view:
            raise ValueError("evidence_requires_trusted_view")
        if not self.evidence.verification_event_id.strip():
            raise ValueError("verification_event_id is required and must be non-empty")


@dataclass(frozen=True)
class EventStorePersistOutcome:
    """Result of persist. reason is path-local (e.g. verification_event_payload_conflict)."""

    result: EventStorePersistResult
    reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.result, EventStorePersistResult):
            raise ValueError("result must be an EventStorePersistResult enum member")


@dataclass(frozen=True)
class EventStoreResolveOutcome:
    """
    Result of resolve.

    Coherent result/evidence combinations (Phase A):
      FOUND_VALID      → evidence required (TrustedEvidenceView, trusted)
      FOUND_INVALID    → evidence optional; if present must be trusted view
                         (diagnostic only; not treated as valid success)
      NOT_FOUND        → evidence must be None
      UNAVAILABLE      → evidence must be None
      LOOKUP_UNCERTAIN → evidence must be None

    FOUND_INVALID optional evidence is the narrowest safe behavior while the
    normative contract does not require a separate diagnostic model.
    """

    result: EventStoreResolveResult
    evidence: Optional[TrustedEvidenceView] = None
    reason: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.result, EventStoreResolveResult):
            raise ValueError("result must be an EventStoreResolveResult enum member")

        if self.result is EventStoreResolveResult.FOUND_VALID:
            if self.evidence is None:
                raise ValueError("FOUND_VALID requires TrustedEvidenceView evidence")
            if not isinstance(self.evidence, TrustedEvidenceView):
                raise ValueError("FOUND_VALID evidence must be a TrustedEvidenceView")
            if not self.evidence.is_trusted_view:
                raise ValueError("FOUND_VALID evidence_requires_trusted_view")
            return

        if self.result is EventStoreResolveResult.FOUND_INVALID:
            if self.evidence is not None:
                if not isinstance(self.evidence, TrustedEvidenceView):
                    raise ValueError("FOUND_INVALID evidence must be a TrustedEvidenceView")
                if not self.evidence.is_trusted_view:
                    raise ValueError("FOUND_INVALID evidence_requires_trusted_view")
            return

        # NOT_FOUND, UNAVAILABLE, LOOKUP_UNCERTAIN
        if self.evidence is not None:
            raise ValueError(
                f"{self.result.value} must not contain evidence"
            )


# ---------------------------------------------------------------------------
# Port
# ---------------------------------------------------------------------------


class EventStore(Protocol):
    """
    Logical Event Store port (Phase A).

    Identity: verification_event_id only (not operation_id).

    persist:
      Idempotent by verification_event_id (behavioral implementation deferred).
      Uncertainty: UNCERTAIN requires resolve of the original id before retry
      (behavioral implementation deferred).
      Payload conflict: FAILED with reason verification_event_payload_conflict;
      original evidence MUST NOT be overwritten (behavioral implementation deferred).
      Does not authorize, classify FailureClass, or evaluate freshness/replay.

    resolve:
      Lookup by verification_event_id.
      Returns exactly one EventStoreResolveResult.
      Does not implement Blocker #6 conditional policy or Blocker #7 freshness/replay.
    """

    def persist(self, request: EventStorePersistRequest) -> EventStorePersistOutcome:
        """Attempt durable retention of trusted sealed evidence for one event id."""
        ...

    def resolve(self, verification_event_id: str) -> EventStoreResolveOutcome:
        """Look up stored evidence by verification_event_id."""
        ...
