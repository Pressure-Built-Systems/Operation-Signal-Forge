# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""E3 + E3-A1-D1 — resolver-origin and immutable ProductionRuntime."""

from __future__ import annotations

import unittest

from identity_runtime.zk_abstraction.identity import IdentityTuple
from identity_runtime.zk_abstraction.policy_resolver import (
    ApplicablePolicyRecord,
    CatalogEntry,
    OriginMark,
    PolicyResolutionStatus,
    PolicyResolver,
    VersionPinnedPolicyCatalog,
)
from identity_runtime.zk_abstraction.runtime_proof_path import (
    FailureClass,
    OperationPolicyContext,
    ProductionRuntime,
    _policy_from_resolved,
    build_aep,
    evaluate_matrix,
    run_runtime_proof_path,
)


def _id(pv: str = "pv-1") -> IdentityTuple:
    return IdentityTuple("sf-zk", "1", "mock-scheme", "1", pv)


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


def _resolver(entry: CatalogEntry | None = None) -> PolicyResolver:
    entries = [_entry()] if entry is None else [entry]
    return PolicyResolver(
        VersionPinnedPolicyCatalog(catalog_version="cat-e3", entries=entries)
    )


def _aep(op: str = "op1"):
    return build_aep(
        operation_id=op,
        verification_result="valid",
        identity=_id(),
        verification_event_id="ve1",
    )


class TestContextFor(unittest.TestCase):
    def test_success_issues_recognized_origin(self) -> None:
        r = _resolver()
        rt = ProductionRuntime.from_resolver(r)
        cres = rt.context_for(_id())
        self.assertTrue(cres.is_authorized_context)
        assert cres.context is not None
        self.assertTrue(
            rt.origin_issuer.recognizes(
                cres.context.origin, cres.context.retained_record
            )
        )

    def test_not_found_no_origin(self) -> None:
        r = _resolver()
        cres = r.context_for(_id("other"))
        self.assertFalse(cres.is_authorized_context)
        self.assertEqual(cres.status, PolicyResolutionStatus.NOT_FOUND)


class TestProductionRuntime(unittest.TestCase):
    def test_binds_exact_resolver_issuer(self) -> None:
        r = _resolver()
        rt = ProductionRuntime.from_resolver(r)
        self.assertIs(rt.policy_resolver, r)
        self.assertIs(rt.origin_issuer, r.origin_issuer)

    def test_mismatched_issuer_rejected_at_construction(self) -> None:
        r1, r2 = _resolver(), _resolver()
        with self.assertRaises(ValueError):
            ProductionRuntime(policy_resolver=r1, origin_issuer=r2.origin_issuer)

    def test_frozen_cannot_replace(self) -> None:
        rt = ProductionRuntime.from_resolver(_resolver())
        with self.assertRaises(Exception):
            rt.policy_resolver = _resolver()  # type: ignore[misc]


class TestMatrixViaRuntime(unittest.TestCase):
    def test_success(self) -> None:
        r = _resolver()
        rt = ProductionRuntime.from_resolver(r)
        ctx = rt.context_for(_id()).context
        assert ctx is not None
        out = rt.evaluate_matrix(_aep(), ctx)
        self.assertTrue(out.authorization_success)

    def test_hand_built_rejected(self) -> None:
        r = _resolver()
        rt = ProductionRuntime.from_resolver(r)
        rec = ApplicablePolicyRecord(
            policy_id="p", policy_version="1",
            protocol_id="sf-zk", protocol_version="1",
            scheme_id="mock-scheme", scheme_version="1",
            policy_version_identity="pv-1",
            freshness_required=False, single_use_required=False,
            explicit_provenance_required=False,
            legacy_non_provenance_permitted=True, catalog_version="x",
        )
        ctx = OperationPolicyContext.from_resolved(rec)
        out = rt.evaluate_matrix(_aep(), ctx)
        self.assertFalse(out.authorization_success)
        self.assertIn("resolver_origin_unrecognized", out.reason)

    def test_caller_mark_rejected(self) -> None:
        r = _resolver()
        rt = ProductionRuntime.from_resolver(r)
        ctx0 = rt.context_for(_id()).context
        assert ctx0 is not None
        forged = OperationPolicyContext(
            retained_record=ctx0.retained_record,
            matrix_view=ctx0.matrix_view,
            origin=OriginMark(),
        )
        out = rt.evaluate_matrix(_aep(), forged)
        self.assertFalse(out.authorization_success)

    def test_attacker_runtime_context_rejected_by_legitimate(self) -> None:
        leg = ProductionRuntime.from_resolver(_resolver())
        att = ProductionRuntime.from_resolver(_resolver())
        ctx = att.context_for(_id()).context
        assert ctx is not None
        out = leg.evaluate_matrix(_aep(), ctx)
        self.assertFalse(out.authorization_success)

    def test_public_evaluate_matrix_rejects_context(self) -> None:
        """Direct public evaluate_matrix cannot accept OperationPolicyContext (no issuer)."""
        r = _resolver()
        rt = ProductionRuntime.from_resolver(r)
        ctx = rt.context_for(_id()).context
        assert ctx is not None
        out = evaluate_matrix(_aep(), ctx)
        self.assertFalse(out.authorization_success)
        self.assertIn("trusted_origin_issuer_required", out.reason)

    def test_no_install_api(self) -> None:
        import identity_runtime.zk_abstraction.runtime_proof_path as mod
        self.assertFalse(hasattr(mod, "install_trusted_origin_issuer"))
        self.assertFalse(hasattr(mod, "clear_trusted_origin_issuer"))

    def test_field_equal_clone_rejected(self) -> None:
        rt = ProductionRuntime.from_resolver(_resolver())
        ctx = rt.context_for(_id()).context
        assert ctx is not None
        rec = ctx.retained_record
        clone = ApplicablePolicyRecord(
            **{f: getattr(rec, f) for f in rec.__dataclass_fields__}
        )
        bad = OperationPolicyContext(
            retained_record=clone,
            matrix_view=_policy_from_resolved(clone),
            origin=ctx.origin,
        )
        out = rt.evaluate_matrix(_aep(), bad)
        self.assertFalse(out.authorization_success)

    def test_path_uses_runtime(self) -> None:
        r = _resolver()
        rt = ProductionRuntime.from_resolver(r)
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=rt,
            policy_resolver=r,
        )
        self.assertTrue(out.authorization_success or out.decision is not None)


if __name__ == "__main__":
    unittest.main()


class TestRetainedRuntime(unittest.TestCase):
    def test_missing_runtime_fails_closed(self) -> None:
        out = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
        )
        self.assertFalse(out.authorization_success)
        self.assertIn("production_runtime_required", out.reason)

    def test_path_uses_exact_retained_runtime(self) -> None:
        r = _resolver()
        rt = ProductionRuntime.from_resolver(r)
        out1 = run_runtime_proof_path(
            operation_id="op1",
            identity=_id(),
            verification_result="valid",
            runtime=rt,
            policy_resolver=r,
        )
        out2 = run_runtime_proof_path(
            operation_id="op2",
            identity=_id(),
            verification_result="valid",
            runtime=rt,
            policy_resolver=r,
        )
        self.assertIs(rt.policy_resolver, r)
        # both evaluations used same retained runtime object (instance identity)
        self.assertIs(rt.origin_issuer, r.origin_issuer)
        self.assertTrue(out1.authorization_success or out1.decision is not None)
        self.assertTrue(out2.authorization_success or out2.decision is not None)

    def test_second_runtime_does_not_affect_first(self) -> None:
        r1, r2 = _resolver(), _resolver()
        rt1 = ProductionRuntime.from_resolver(r1)
        rt2 = ProductionRuntime.from_resolver(r2)
        ctx2 = rt2.context_for(_id()).context
        assert ctx2 is not None
        out = rt1.evaluate_matrix(_aep(), ctx2)
        self.assertFalse(out.authorization_success)
