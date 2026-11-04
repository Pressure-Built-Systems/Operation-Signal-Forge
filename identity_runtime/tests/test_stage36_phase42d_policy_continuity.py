# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""Phase 4.2d — same retained ApplicablePolicyRecord continuity."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from identity_runtime.zk_abstraction.identity import IdentityTuple
from identity_runtime.zk_abstraction.policy_resolver import (
    ApplicablePolicyRecord,
    CatalogEntry,
    PolicyResolver,
    VersionPinnedPolicyCatalog,
)
from identity_runtime.zk_abstraction.runtime_proof_path import (
    ProductionRuntime,
    
    FailureClass,
    OperationPolicyContext,
    evaluate_matrix,
    run_runtime_proof_path,
)
from identity_runtime.zk_abstraction.verification_event_seal import seal_verification_event


def _id() -> IdentityTuple:
    return IdentityTuple("sf-zk", "1", "mock-scheme", "1", "pv-1")


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
        legacy_non_provenance_permitted=True,
        supported_protocol_ids=frozenset({"sf-zk"}),
        supported_scheme_ids=frozenset({"mock-scheme"}),
    )
    base.update(kw)
    return CatalogEntry(**base)


@dataclass
class FakeResult:
    accepted: bool
    status_code: str
    reason: str = ""
    identity_tuple: Optional[IdentityTuple] = None


FIXED = datetime(2026, 10, 30, 18, 0, 0, tzinfo=timezone.utc)


class TestContinuity(unittest.TestCase):
    def test_same_instance_reaches_path_result(self) -> None:
        entry = _entry(legacy_non_provenance_permitted=True)
        resolver = PolicyResolver(
            VersionPinnedPolicyCatalog(catalog_version="c-42d", entries=[entry])
        )
        # capture record object from resolver
        res = resolver.resolve_policy(_id())
        self.assertTrue(res.is_resolved)
        retained = res.record
        assert retained is not None

        # custom resolver that returns the same resolution
        class OnceResolver(PolicyResolver):
            def __init__(self):
                super().__init__(
                    VersionPinnedPolicyCatalog(catalog_version="c-42d", entries=[entry])
                )
                self.calls = 0

            def resolve_policy(self, identity):
                self.calls += 1
                return res

        once = OnceResolver()
        rt = ProductionRuntime.from_resolver(once)
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=rt,
            policy_resolver=once,
        )
        self.assertEqual(once.calls, 1)
        self.assertIsNotNone(out.retained_policy_record)
        # R3: path stamps evaluation record; not same object as prior resolve_policy()

    def test_equal_field_substitute_rejected_by_evaluate_matrix(self) -> None:
        entry = _entry(legacy_non_provenance_permitted=True)
        resolver = PolicyResolver(
            VersionPinnedPolicyCatalog(catalog_version="c-42d", entries=[entry])
        )
        cres = resolver.context_for(_id())
        assert cres.context is not None
        ctx = cres.context
        rec = ctx.retained_record
        clone = ApplicablePolicyRecord(
            **{f: getattr(rec, f) for f in rec.__dataclass_fields__}
        )
        self.assertEqual(clone.policy_id, rec.policy_id)
        self.assertIsNot(clone, rec)

        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=ProductionRuntime.from_resolver(resolver),
            policy_resolver=resolver,
        )
        self.assertIsNotNone(out.aep)
        rt = ProductionRuntime.from_resolver(resolver)
        bad = rt.evaluate_matrix(
            out.aep,  # type: ignore[arg-type]
            ctx,
            expected_retained_record=clone,
        )
        self.assertFalse(bad.authorization_success)
        self.assertIn("policy_record_continuity_violation", bad.reason)

    def test_expected_same_object_ok(self) -> None:
        entry = _entry(legacy_non_provenance_permitted=True)
        resolver = PolicyResolver(
            VersionPinnedPolicyCatalog(catalog_version="c-42d", entries=[entry])
        )
        cres = resolver.context_for(_id())
        assert cres.context is not None
        ctx = cres.context
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=ProductionRuntime.from_resolver(resolver),
            policy_resolver=resolver,
        )
        rt = ProductionRuntime.from_resolver(resolver)
        ok = rt.evaluate_matrix(
            out.aep,  # type: ignore[arg-type]
            ctx,
            expected_retained_record=ctx.retained_record,
        )
        self.assertNotIn("policy_record_continuity_violation", ok.reason)


if __name__ == "__main__":
    unittest.main()


class TestRemediation42d(unittest.TestCase):
    def test_bare_matrix_policy_fails_without_fixture_gate(self) -> None:
        import os
        from identity_runtime.zk_abstraction.runtime_proof_path import MatrixPolicy
        os.environ.pop("OSF_ALLOW_TEST_MATRIX_POLICY", None)
        entry = _entry(legacy_non_provenance_permitted=True)
        resolver = PolicyResolver(
            VersionPinnedPolicyCatalog(catalog_version="c-42d", entries=[entry])
        )
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=ProductionRuntime.from_resolver(resolver),
            policy_resolver=resolver,
        )
        self.assertIsNotNone(out.aep)
        bad = evaluate_matrix(
            out.aep,  # type: ignore[arg-type]
            MatrixPolicy(policy_id="p", policy_version="pv-1"),
        )
        self.assertFalse(bad.authorization_success)
        self.assertIn("matrix_requires_operation_policy_context", bad.reason)

    def test_context_enforces_identity_against_clone(self) -> None:
        entry = _entry(legacy_non_provenance_permitted=True)
        resolver = PolicyResolver(
            VersionPinnedPolicyCatalog(catalog_version="c-42d", entries=[entry])
        )
        cres = resolver.context_for(_id())
        assert cres.context is not None
        ctx = cres.context
        clone = ApplicablePolicyRecord(
            **{f: getattr(ctx.retained_record, f) for f in ctx.retained_record.__dataclass_fields__}
        )
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=ProductionRuntime.from_resolver(resolver),
            policy_resolver=resolver,
        )
        rt = ProductionRuntime.from_resolver(resolver)
        bad = rt.evaluate_matrix(
            out.aep,  # type: ignore[arg-type]
            ctx,
            expected_retained_record=clone,
        )
        self.assertFalse(bad.authorization_success)
        self.assertIn("policy_record_continuity_violation", bad.reason)

    def test_production_path_stamps_same_record(self) -> None:
        entry = _entry(legacy_non_provenance_permitted=True)
        resolver = PolicyResolver(
            VersionPinnedPolicyCatalog(catalog_version="c-42d", entries=[entry])
        )
        res = resolver.resolve_policy(_id())
        class R(PolicyResolver):
            def __init__(self):
                super().__init__(
                    VersionPinnedPolicyCatalog(catalog_version="c-42d", entries=[entry])
                )
            def resolve_policy(self, identity):
                return res
        r = R()
        rt = ProductionRuntime.from_resolver(r)
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=rt,
            policy_resolver=r,
        )
        self.assertIsNotNone(out.retained_policy_record)
        # R3: per-evaluation stamp
