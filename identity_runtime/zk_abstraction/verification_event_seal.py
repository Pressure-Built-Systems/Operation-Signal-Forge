# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""
WP-3.6.6 Blocker #3 — Trusted verification-event sealing boundary (Option B).

Logical contract only for sealing: does not persist, consume replay, authorize,
or call AuditPort. D5.3 equality remains deferred. P0 is non-production metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Mapping, Optional, Union
from uuid import uuid4


# ---------------------------------------------------------------------------
# Schema / P0 metadata
# ---------------------------------------------------------------------------

RECORD_SCHEMA_VERSION = "osf.verification-event.record/v1"

APPROVED_INTEGRITY_MATERIAL: dict[str, Any] = {
    "metadata_schema": "osf.verification-event.integrity-material",
    "metadata_schema_version": 1,
    "integrity_profile_id": "P0",
    "integrity_profile_version": 1,
}

_INTEGRITY_KEYS = frozenset(APPROVED_INTEGRITY_MATERIAL.keys())

# Owner-approved outcome allowlist (explicit). Unlisted → error (never valid).
_VALID_STATUS = frozenset({"OK"})
_ERROR_STATUS = frozenset(
    {
        "STRUCTURAL_FAILURE",
        "UNVERIFIABLE_CONDITION",
    }
)
# Ordinary invalid (non-exhaustive listed family; unlisted still → error)
_INVALID_STATUS = frozenset(
    {
        "INVALID_PROOF",
        "WRONG_CONTEXT",
        "WRONG_REVISION",
        "WRONG_CLAIM",
        "BINDING_MISMATCH",
        "STALE_CONDITION",
        "REVOKED_CONDITION",
        "SUPERSEDED_CONDITION",
        "CONFLICTED_CONDITION",
        "MALFORMED_PROOF",
        "MALFORMED_CONDITION",
        "AMBIGUOUS_CONDITION",
        "UNSUPPORTED_SCHEME",
        "UNSUPPORTED_PROTOCOL",
        "SCHEME_DOWNGRADE",
        "SCHEME_DEPRECATED_DISALLOWED",
        "SCHEME_DISABLED",
        "SCHEME_RETIRED",
        "OUTSIDE_BOUNDARY_LEAK",
        "MISSING_CONDITION",
    }
)


class VerificationOutcome(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    ERROR = "error"


class SealStatus(str, Enum):
    SEALED = "SEALED"
    REFUSED = "REFUSED"


@dataclass(frozen=True)
class VerificationEventRecord:
    """Immutable schema-v1 verification-event record (logical)."""

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


@dataclass(frozen=True)
class SealResult:
    status: SealStatus
    record: Optional[VerificationEventRecord] = None
    reason: Optional[str] = None

    @property
    def is_sealed(self) -> bool:
        return self.status is SealStatus.SEALED and self.record is not None


def _refuse(reason: str) -> SealResult:
    return SealResult(status=SealStatus.REFUSED, record=None, reason=reason)


def default_event_id_generator() -> str:
    return f"ve_{uuid4().hex}"


def map_verification_outcome(accepted: bool, status_code: str) -> VerificationOutcome:
    """Exact allowlist mapping. Unlisted statuses → error (never valid)."""
    code = (status_code or "").strip()
    if accepted is True and code in _VALID_STATUS:
        return VerificationOutcome.VALID
    if accepted is True:
        # accepted with non-OK code is not on the allowlist for valid
        return VerificationOutcome.ERROR
    if code in _ERROR_STATUS:
        return VerificationOutcome.ERROR
    if code in _INVALID_STATUS:
        return VerificationOutcome.INVALID
    # Unlisted / empty / ambiguous → error (fail closed toward valid)
    return VerificationOutcome.ERROR


def _validate_integrity_material(material: Any) -> Optional[str]:
    if not isinstance(material, Mapping):
        return "integrity_material_not_object"
    keys = frozenset(material.keys())
    if keys != _INTEGRITY_KEYS:
        return "integrity_material_key_set_mismatch"
    if material.get("metadata_schema") != APPROVED_INTEGRITY_MATERIAL["metadata_schema"]:
        return "integrity_material_schema_mismatch"
    ms = material.get("metadata_schema_version")
    if isinstance(ms, bool) or type(ms) is not int or ms != 1:
        return "integrity_material_schema_version_invalid"
    if material.get("integrity_profile_id") != "P0":
        return "integrity_material_profile_id"
    pv = material.get("integrity_profile_version")
    if isinstance(pv, bool) or type(pv) is not int or pv != 1:
        return "integrity_material_profile_version_invalid"
    return None


def _normalize_utc_timestamp(value: Any) -> Optional[str]:
    """Return ISO-8601 UTC string or None if invalid.

    Requires timezone-aware datetime with zero UTC offset. Naive and non-UTC
    offsets are refused (no silent local-time conversion).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return None
        offset = value.utcoffset()
        if offset is None or offset.total_seconds() != 0:
            return None
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return None


def seal_verification_event(
    result: Any,
    *,
    recording_boundary_id: str,
    finalization_clock: Callable[[], Any],
    event_id_generator: Optional[Callable[[], str]] = None,
    integrity_material: Optional[Mapping[str, Any]] = None,
) -> SealResult:
    """
    Designated trusted sealing boundary.

    Assigns verification_event_id and verification_finalized_at only after
    validation. Returns SEALED(record) or REFUSED(reason). Never partial.
    """
    # --- shape ---
    if result is None:
        return _refuse("missing_verification_result")
    if isinstance(result, str):
        return _refuse("string_status_not_trusted_provenance")
    accepted = getattr(result, "accepted", None)
    status_code = getattr(result, "status_code", None)
    identity = getattr(result, "identity_tuple", None)
    if accepted is None or status_code is None:
        return _refuse("unsupported_result_shape")
    if not isinstance(accepted, bool):
        return _refuse("accepted_not_bool")
    if not isinstance(status_code, str):
        return _refuse("status_code_not_str")

    # --- identity from result only ---
    if identity is None:
        return _refuse("missing_identity")
    for field in (
        "protocol_id",
        "protocol_version",
        "scheme_id",
        "scheme_version",
        "policy_version",
    ):
        val = getattr(identity, field, None)
        if not isinstance(val, str) or not val.strip():
            return _refuse(f"identity_field_invalid:{field}")

    # --- boundary id presence-only ---
    if not isinstance(recording_boundary_id, str) or not recording_boundary_id.strip():
        return _refuse("recording_boundary_id_invalid")

    # --- integrity material ---
    material = (
        dict(APPROVED_INTEGRITY_MATERIAL)
        if integrity_material is None
        else integrity_material
    )
    mat_err = _validate_integrity_material(material)
    if mat_err is not None:
        return _refuse(mat_err)

    # --- outcome allowlist ---
    outcome = map_verification_outcome(bool(accepted), status_code)

    # --- event id (sealer-owned) ---
    gen = event_id_generator or default_event_id_generator
    try:
        event_id = gen()
    except Exception as exc:  # noqa: BLE001
        return _refuse(f"event_id_generator_error:{type(exc).__name__}")
    if not isinstance(event_id, str) or not event_id.strip():
        return _refuse("event_id_generator_invalid")

    # --- clock (sealer-owned, once) ---
    try:
        raw_ts = finalization_clock()
    except Exception as exc:  # noqa: BLE001
        return _refuse(f"finalization_clock_error:{type(exc).__name__}")
    finalized_at = _normalize_utc_timestamp(raw_ts)
    if finalized_at is None:
        return _refuse("finalization_clock_invalid_timestamp")

    record = VerificationEventRecord(
        verification_event_id=event_id.strip(),
        verification_finalized_at=finalized_at,
        verification_outcome=outcome.value,
        protocol_id=identity.protocol_id.strip(),
        protocol_version=identity.protocol_version.strip(),
        scheme_id=identity.scheme_id.strip(),
        scheme_version=identity.scheme_version.strip(),
        policy_version=identity.policy_version.strip(),
        record_schema_version=RECORD_SCHEMA_VERSION,
        recording_boundary_id=recording_boundary_id.strip(),
        integrity_material=dict(material),
    )
    return SealResult(status=SealStatus.SEALED, record=record, reason=None)


def policy_requires_verification_event_provenance(
    *,
    freshness_required: bool = False,
    single_use_required: bool = False,
    explicit_provenance_required: bool = False,
) -> bool:
    """Path-level predicate: provenance-required when any governing flag is true."""
    return bool(freshness_required or single_use_required or explicit_provenance_required)


def assert_sealed_provenance(
    sealed: Optional[SealResult],
    *,
    freshness_required: bool = False,
    single_use_required: bool = False,
    explicit_provenance_required: bool = False,
) -> Optional[str]:
    """
    Guard for provenance-required paths.

    Returns None if OK, or a refusal reason string.
    Does not resolve an event store (Blocker #4 not implemented).
    """
    if not policy_requires_verification_event_provenance(
        freshness_required=freshness_required,
        single_use_required=single_use_required,
        explicit_provenance_required=explicit_provenance_required,
    ):
        return None
    if sealed is None or not sealed.is_sealed or sealed.record is None:
        return "provenance_required_missing_sealed_record"
    return None
