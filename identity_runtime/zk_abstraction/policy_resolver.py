# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""
WP-3.6.6 Phase 4.2b — Trusted PolicyResolver and version-pinned catalog.

Logical contract only. Does not integrate into the runtime proof path or Matrix.
Does not authorize operations. D5.3 remains deferred. P0 process-trust only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Sequence

from identity_runtime.zk_abstraction.identity import IdentityTuple


class PolicyResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    NOT_FOUND = "NOT_FOUND"
    UNSUPPORTED = "UNSUPPORTED"
    MALFORMED = "MALFORMED"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    RESOLUTION_ERROR = "RESOLUTION_ERROR"


@dataclass(frozen=True)
class ApplicablePolicyRecord:
    """Immutable policy record issued only after successful resolution."""

    policy_id: str
    policy_version: str
    protocol_id: str
    protocol_version: str
    scheme_id: str
    scheme_version: str
    policy_version_identity: str  # five-field policy_version
    freshness_required: bool
    single_use_required: bool
    explicit_provenance_required: bool
    legacy_non_provenance_permitted: bool
    # Matrix-oriented fields (preserved for later integration)
    allow_when_valid: bool = True
    require_admitted_claim: bool = False
    force_deny: bool = False
    supported_protocol_ids: frozenset[str] = field(default_factory=frozenset)
    supported_scheme_ids: frozenset[str] = field(default_factory=frozenset)
    catalog_version: str = ""

    def requires_verification_event_provenance(self) -> bool:
        return bool(
            self.freshness_required
            or self.single_use_required
            or self.explicit_provenance_required
        )

    def five_field_identity(self) -> IdentityTuple:
        return IdentityTuple(
            protocol_id=self.protocol_id,
            protocol_version=self.protocol_version,
            scheme_id=self.scheme_id,
            scheme_version=self.scheme_version,
            policy_version=self.policy_version_identity,
        )


@dataclass(frozen=True)
class PolicyResolution:
    status: PolicyResolutionStatus
    record: Optional[ApplicablePolicyRecord] = None
    reason: str = ""
    catalog_version: Optional[str] = None

    @property
    def is_resolved(self) -> bool:
        return (
            self.status is PolicyResolutionStatus.RESOLVED
            and self.record is not None
        )


class OriginMark:
    """Process-local origin mark. Recognition is via issuer registry only."""

    __slots__ = ("_sentinel",)

    def __init__(self) -> None:
        self._sentinel = object()


class OriginIssuer:
    """Resolver-owned issuer. Matrix must use the same issuer instance."""

    def __init__(self) -> None:
        # mark -> bound ApplicablePolicyRecord (exact instance)
        self._registry: dict[OriginMark, ApplicablePolicyRecord] = {}

    def issue(self, record: ApplicablePolicyRecord) -> OriginMark:
        if record is None:
            raise ValueError("record_required")
        mark = OriginMark()
        self._registry[mark] = record
        return mark

    def recognizes(self, mark: object, expected_record: ApplicablePolicyRecord) -> bool:
        if not isinstance(mark, OriginMark):
            return False
        if mark not in self._registry:
            return False
        return self._registry[mark] is expected_record


@dataclass(frozen=True)
class ContextResolution:
    """Result of context_for: authorized context or fail-closed resolution."""

    status: PolicyResolutionStatus
    context: Optional[object] = None  # OperationPolicyContext when resolved
    reason: str = ""
    catalog_version: Optional[str] = None
    policy_resolution: Optional[PolicyResolution] = None

    @property
    def is_authorized_context(self) -> bool:
        return (
            self.status is PolicyResolutionStatus.RESOLVED
            and self.context is not None
        )


def _identity_key(identity: IdentityTuple) -> tuple[str, str, str, str, str]:
    return (
        identity.protocol_id,
        identity.protocol_version,
        identity.scheme_id,
        identity.scheme_version,
        identity.policy_version,
    )


def _nonempty_str(value: Any, field_name: str) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _require_bool(value: Any, field_name: str) -> tuple[Optional[bool], Optional[str]]:
    if isinstance(value, bool) and not isinstance(value, int):
        # bool is subclass of int — accept only real bool
        return value, None
    if type(value) is bool:
        return value, None
    # Reject int 0/1 and other types
    if isinstance(value, bool):
        return value, None
    return None, f"field_not_bool:{field_name}"


def _parse_bool_strict(value: Any, field_name: str) -> tuple[Optional[bool], Optional[str]]:
    if type(value) is bool:
        return value, None
    return None, f"field_not_bool:{field_name}"


@dataclass(frozen=True)
class CatalogEntry:
    """One catalog row prior to validation against a request identity."""

    policy_id: str
    policy_version: str
    protocol_id: str
    protocol_version: str
    scheme_id: str
    scheme_version: str
    policy_version_identity: str
    freshness_required: bool
    single_use_required: bool
    explicit_provenance_required: bool
    legacy_non_provenance_permitted: bool
    allow_when_valid: bool = True
    require_admitted_claim: bool = False
    force_deny: bool = False
    supported_protocol_ids: frozenset[str] = field(default_factory=frozenset)
    supported_scheme_ids: frozenset[str] = field(default_factory=frozenset)


class VersionPinnedPolicyCatalog:
    """
    Explicitly version-pinned catalog. No floating 'latest'.
    Construction requires a non-empty catalog_version string.
    """

    def __init__(
        self,
        *,
        catalog_version: str,
        entries: Sequence[CatalogEntry] = (),
    ) -> None:
        if not isinstance(catalog_version, str) or not catalog_version.strip():
            raise ValueError("catalog_version_required")
        self._catalog_version = catalog_version.strip()
        self._entries: dict[tuple[str, str, str, str, str], CatalogEntry] = {}
        for entry in entries:
            key = (
                entry.protocol_id,
                entry.protocol_version,
                entry.scheme_id,
                entry.scheme_version,
                entry.policy_version_identity,
            )
            self._entries[key] = entry

    @property
    def catalog_version(self) -> str:
        return self._catalog_version

    def get(self, identity: IdentityTuple) -> Optional[CatalogEntry]:
        return self._entries.get(_identity_key(identity))


class PolicyResolver:
    """
    Trusted policy resolution boundary (Phase 4.2b + E3).

    Production composition root supplies a VersionPinnedPolicyCatalog.
    Origin issuer is owned by this resolver; Matrix must use the same issuer.
    """

    def __init__(self, catalog: VersionPinnedPolicyCatalog) -> None:
        if catalog is None:
            raise ValueError("catalog_required")
        if not isinstance(catalog, VersionPinnedPolicyCatalog):
            raise TypeError("catalog_must_be_VersionPinnedPolicyCatalog")
        self._catalog = catalog
        self._origin_issuer = OriginIssuer()

    @property
    def catalog_version(self) -> str:
        return self._catalog.catalog_version

    @property
    def origin_issuer(self) -> OriginIssuer:
        """Composition root injects this same issuer into Matrix evaluation."""
        return self._origin_issuer

    def resolve_policy(self, identity: Any) -> PolicyResolution:
        cv = self._catalog.catalog_version
        try:
            if identity is None:
                return PolicyResolution(
                    status=PolicyResolutionStatus.MALFORMED,
                    reason="identity_missing",
                    catalog_version=cv,
                )
            if not isinstance(identity, IdentityTuple):
                return PolicyResolution(
                    status=PolicyResolutionStatus.MALFORMED,
                    reason="identity_not_IdentityTuple",
                    catalog_version=cv,
                )
            for fname in (
                "protocol_id",
                "protocol_version",
                "scheme_id",
                "scheme_version",
                "policy_version",
            ):
                val = getattr(identity, fname, None)
                if not isinstance(val, str) or not val.strip():
                    return PolicyResolution(
                        status=PolicyResolutionStatus.MALFORMED,
                        reason=f"identity_field_invalid:{fname}",
                        catalog_version=cv,
                    )

            entry = self._catalog.get(identity)
            if entry is None:
                return PolicyResolution(
                    status=PolicyResolutionStatus.NOT_FOUND,
                    reason="catalog_entry_not_found",
                    catalog_version=cv,
                )

            # Identity mismatch defense if entry fields diverge from key
            if (
                entry.protocol_id != identity.protocol_id
                or entry.protocol_version != identity.protocol_version
                or entry.scheme_id != identity.scheme_id
                or entry.scheme_version != identity.scheme_version
                or entry.policy_version_identity != identity.policy_version
            ):
                return PolicyResolution(
                    status=PolicyResolutionStatus.IDENTITY_MISMATCH,
                    reason="entry_identity_mismatch",
                    catalog_version=cv,
                )

            # Validate entry required strings
            for fname, val in (
                ("policy_id", entry.policy_id),
                ("policy_version", entry.policy_version),
            ):
                if not isinstance(val, str) or not val.strip():
                    return PolicyResolution(
                        status=PolicyResolutionStatus.MALFORMED,
                        reason=f"entry_field_invalid:{fname}",
                        catalog_version=cv,
                    )

            # Bool fields must be real bools (CatalogEntry construction should ensure)
            for fname in (
                "freshness_required",
                "single_use_required",
                "explicit_provenance_required",
                "legacy_non_provenance_permitted",
            ):
                val = getattr(entry, fname)
                if type(val) is not bool:
                    return PolicyResolution(
                        status=PolicyResolutionStatus.MALFORMED,
                        reason=f"entry_field_not_bool:{fname}",
                        catalog_version=cv,
                    )

            record = ApplicablePolicyRecord(
                policy_id=entry.policy_id.strip(),
                policy_version=entry.policy_version.strip(),
                protocol_id=entry.protocol_id.strip(),
                protocol_version=entry.protocol_version.strip(),
                scheme_id=entry.scheme_id.strip(),
                scheme_version=entry.scheme_version.strip(),
                policy_version_identity=entry.policy_version_identity.strip(),
                freshness_required=entry.freshness_required,
                single_use_required=entry.single_use_required,
                explicit_provenance_required=entry.explicit_provenance_required,
                legacy_non_provenance_permitted=entry.legacy_non_provenance_permitted,
                allow_when_valid=entry.allow_when_valid,
                require_admitted_claim=entry.require_admitted_claim,
                force_deny=entry.force_deny,
                supported_protocol_ids=frozenset(entry.supported_protocol_ids),
                supported_scheme_ids=frozenset(entry.supported_scheme_ids),
                catalog_version=cv,
            )
            return PolicyResolution(
                status=PolicyResolutionStatus.RESOLVED,
                record=record,
                reason="",
                catalog_version=cv,
            )
        except Exception as exc:  # noqa: BLE001
            return PolicyResolution(
                status=PolicyResolutionStatus.RESOLUTION_ERROR,
                reason=f"resolution_error:{type(exc).__name__}",
                catalog_version=cv,
            )


    def context_for(self, identity: Any) -> "ContextResolution":
        """
        Sole supported production API for OperationPolicyContext construction (E3 / CC 2.1).

        Issues resolver-origin evidence only on RESOLVED. Never attaches origin on failure.
        """
        # Import locally to avoid circular import at module load
        from identity_runtime.zk_abstraction.runtime_proof_path import (
            OperationPolicyContext,
            _policy_from_resolved,
        )

        resolution = self.resolve_policy(identity)
        cv = resolution.catalog_version
        if not resolution.is_resolved or resolution.record is None:
            return ContextResolution(
                status=resolution.status,
                context=None,
                reason=resolution.reason or f"policy_resolution_{resolution.status.value}",
                catalog_version=cv,
                policy_resolution=resolution,
            )
        record = resolution.record
        origin = self._origin_issuer.issue(record)
        ctx = OperationPolicyContext(
            retained_record=record,
            matrix_view=_policy_from_resolved(record),
            origin=origin,
        )
        return ContextResolution(
            status=PolicyResolutionStatus.RESOLVED,
            context=ctx,
            reason="",
            catalog_version=cv,
            policy_resolution=resolution,
        )


def catalog_entry_from_mapping(data: Mapping[str, Any]) -> CatalogEntry:
    """
    Build a CatalogEntry from a mapping with strict bool and string checks.
    Raises ValueError on malformed input (caller may translate to MALFORMED).
    """
    def s(key: str) -> str:
        v = data.get(key)
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"missing_or_invalid:{key}")
        return v.strip()

    def b(key: str) -> bool:
        v = data.get(key)
        if type(v) is not bool:
            raise ValueError(f"not_bool:{key}")
        return v

    protocols = data.get("supported_protocol_ids", ())
    schemes = data.get("supported_scheme_ids", ())
    return CatalogEntry(
        policy_id=s("policy_id"),
        policy_version=s("policy_version"),
        protocol_id=s("protocol_id"),
        protocol_version=s("protocol_version"),
        scheme_id=s("scheme_id"),
        scheme_version=s("scheme_version"),
        policy_version_identity=s("policy_version_identity"),
        freshness_required=b("freshness_required"),
        single_use_required=b("single_use_required"),
        explicit_provenance_required=b("explicit_provenance_required"),
        legacy_non_provenance_permitted=b("legacy_non_provenance_permitted"),
        allow_when_valid=b("allow_when_valid") if "allow_when_valid" in data else True,
        require_admitted_claim=(
            b("require_admitted_claim") if "require_admitted_claim" in data else False
        ),
        force_deny=b("force_deny") if "force_deny" in data else False,
        supported_protocol_ids=frozenset(protocols) if protocols else frozenset(),
        supported_scheme_ids=frozenset(schemes) if schemes else frozenset(),
    )
