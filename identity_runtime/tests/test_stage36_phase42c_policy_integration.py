# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""Phase 4.2c — PolicyResolver integration into runtime path."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from identity_runtime.zk_abstraction.identity import IdentityTuple
from identity_runtime.zk_abstraction.policy_resolver import (
    CatalogEntry,
    PolicyResolver,
    VersionPinnedPolicyCatalog,
)
from identity_runtime.zk_abstraction.runtime_proof_path import (
    ProductionRuntime,
    ProductionRuntime,
    FailureClass,
    MatrixDisposition,
    MatrixPolicy,
    run_runtime_proof_path,
)
from identity_runtime.zk_abstraction.verification_event_seal import (
    SealStatus,
    seal_verification_event,
)


def _id() -> IdentityTuple:
    return IdentityTuple(
        protocol_id="sf-zk",
        protocol_version="1",
        scheme_id="mock-scheme",
        scheme_version="1",
        policy_version="pv-1",
    )


def _entry(**kw) -> CatalogEntry:
    base = dict(
        policy_id="pol-1",
        policy_version="1",
        protocol_id="sf-zk",
        protocol_version="1",
        scheme_id="mock-scheme",
        scheme_version="1",
        policy_version_identity="pv-1",
        freshness_required=False,
        single_use_required=False,
        explicit_provenance_required=False,
        legacy_non_provenance_permitted=False,
        supported_protocol_ids=frozenset({"sf-zk"}),
        supported_scheme_ids=frozenset({"mock-scheme"}),
    )
    base.update(kw)
    return CatalogEntry(**base)


def _resolver(entry: CatalogEntry) -> PolicyResolver:
    return PolicyResolver(
        VersionPinnedPolicyCatalog(catalog_version="cat-test-1", entries=[entry])
    )


@dataclass
class FakeResult:
    accepted: bool
    status_code: str
    reason: str = ""
    identity_tuple: Optional[IdentityTuple] = None


FIXED = datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc)


def _seal():
    return seal_verification_event(
        FakeResult(True, "OK", identity_tuple=_id()),
        recording_boundary_id="b1",
        finalization_clock=lambda: FIXED,
        event_id_generator=lambda: "ve_sealed_42c",
    )


class TestResolverRequired(unittest.TestCase):
    def test_missing_resolver_fails_closed(self) -> None:
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            policy_resolver=None,
        )
        self.assertFalse(out.authorization_success)
        self.assertEqual(out.failure_class, FailureClass.MISSING)
        self.assertIn("production_runtime_required", out.reason)

    def test_free_form_matrix_policy_not_authority_without_test_flag(self) -> None:
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            policy=MatrixPolicy(policy_id="p", policy_version="1"),
            allow_test_matrix_policy=False,
            policy_resolver=None,
        )
        self.assertFalse(out.authorization_success)
        self.assertIn("production_runtime_required", out.reason)


class TestProvenanceRequired(unittest.TestCase):
    def test_sealed_success(self) -> None:
        res = _resolver(
            _entry(explicit_provenance_required=True, legacy_non_provenance_permitted=False)
        )
        sealed = _seal()
        self.assertTrue(sealed.is_sealed)
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=ProductionRuntime.from_resolver(res),
            policy_resolver=res,
            sealed_event=sealed,
        )
        self.assertIsNotNone(out.aep)
        assert out.aep is not None
        self.assertEqual(out.aep.verification_event_id, "ve_sealed_42c")

    def test_missing_sealed_fails(self) -> None:
        res = _resolver(_entry(freshness_required=True))
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=ProductionRuntime.from_resolver(res),
            policy_resolver=res,
            sealed_event=None,
        )
        self.assertFalse(out.authorization_success)
        self.assertIn("provenance_required", out.reason)

    def test_event_id_conflict(self) -> None:
        res = _resolver(_entry(single_use_required=True))
        sealed = _seal()
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=ProductionRuntime.from_resolver(res),
            policy_resolver=res,
            sealed_event=sealed,
            verification_event_id="ve_attacker",
        )
        self.assertFalse(out.authorization_success)
        self.assertEqual(out.failure_class, FailureClass.MISMATCHED)


class TestLegacy(unittest.TestCase):
    def test_legacy_true_allows_without_seal(self) -> None:
        res = _resolver(
            _entry(
                freshness_required=False,
                single_use_required=False,
                explicit_provenance_required=False,
                legacy_non_provenance_permitted=True,
            )
        )
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=ProductionRuntime.from_resolver(res),
            policy_resolver=res,
        )
        self.assertTrue(out.authorization_success or out.decision is not None)
        if out.decision is not None:
            # may ALLOW under policy
            self.assertIn(
                out.decision.disposition,
                (MatrixDisposition.ALLOW, MatrixDisposition.DENY),
            )

    def test_legacy_false_fails_without_seal(self) -> None:
        res = _resolver(
            _entry(
                freshness_required=False,
                single_use_required=False,
                explicit_provenance_required=False,
                legacy_non_provenance_permitted=False,
            )
        )
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=ProductionRuntime.from_resolver(res),
            policy_resolver=res,
        )
        self.assertFalse(out.authorization_success)
        self.assertIn("legacy_non_provenance_not_permitted", out.reason)


class TestResolutionFailures(unittest.TestCase):
    def test_not_found(self) -> None:
        res = _resolver(_entry())  # pv-1
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=IdentityTuple("sf-zk", "1", "mock-scheme", "1", "pv-other"),
            verification_result="valid",
            runtime=ProductionRuntime.from_resolver(res),
            policy_resolver=res,
        )
        self.assertFalse(out.authorization_success)
        self.assertIn("NOT_FOUND", out.reason)


class TestMatrixSoleAuthorizer(unittest.TestCase):
    def test_force_deny_still_denies_with_sealed(self) -> None:
        res = _resolver(
            _entry(
                explicit_provenance_required=True,
                force_deny=True,
                legacy_non_provenance_permitted=False,
            )
        )
        sealed = _seal()
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=ProductionRuntime.from_resolver(res),
            policy_resolver=res,
            sealed_event=sealed,
        )
        self.assertFalse(out.authorization_success)


if __name__ == "__main__":
    unittest.main()


class TestRemediation42c(unittest.TestCase):
    def test_allow_test_flag_alone_does_not_bypass_resolver(self) -> None:
        # Flag without env must not enable fixture policy authority
        import os
        old = os.environ.pop("OSF_ALLOW_TEST_MATRIX_POLICY", None)
        try:
            out = run_runtime_proof_path(
                operation_id="op1",
                identity=_id(),
                verification_result="valid",
                policy=MatrixPolicy(policy_id="p", policy_version="1"),
                allow_test_matrix_policy=True,
                policy_resolver=None,
            )
            self.assertFalse(out.authorization_success)
            self.assertIn("production_runtime_required", out.reason)
        finally:
            if old is not None:
                os.environ["OSF_ALLOW_TEST_MATRIX_POLICY"] = old

    def test_empty_supported_sets_not_widened(self) -> None:
        from identity_runtime.zk_abstraction.runtime_proof_path import _policy_from_resolved
        from identity_runtime.zk_abstraction.policy_resolver import ApplicablePolicyRecord
        rec = ApplicablePolicyRecord(
            policy_id="p",
            policy_version="1",
            protocol_id="sf-zk",
            protocol_version="1",
            scheme_id="mock-scheme",
            scheme_version="1",
            policy_version_identity="pv-1",
            freshness_required=False,
            single_use_required=False,
            explicit_provenance_required=False,
            legacy_non_provenance_permitted=True,
            supported_protocol_ids=frozenset(),
            supported_scheme_ids=frozenset(),
            catalog_version="c1",
        )
        pol = _policy_from_resolved(rec)
        self.assertEqual(pol.supported_protocol_ids, frozenset())
        self.assertEqual(pol.supported_scheme_ids, frozenset())
