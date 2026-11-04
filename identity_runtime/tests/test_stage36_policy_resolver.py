# Copyright 2026 Operation Signal Forge contributors
# Licensed under the Apache License, Version 2.0
"""WP-3.6.6 Phase 4.2b — PolicyResolver and version-pinned catalog tests."""

from __future__ import annotations

import unittest

from identity_runtime.zk_abstraction.identity import IdentityTuple
from identity_runtime.zk_abstraction.policy_resolver import (
    ApplicablePolicyRecord,
    CatalogEntry,
    PolicyResolutionStatus,
    PolicyResolver,
    VersionPinnedPolicyCatalog,
    catalog_entry_from_mapping,
)


def _id(
    protocol_id: str = "sf-zk",
    protocol_version: str = "1",
    scheme_id: str = "mock-scheme",
    scheme_version: str = "1",
    policy_version: str = "pv-1",
) -> IdentityTuple:
    return IdentityTuple(
        protocol_id=protocol_id,
        protocol_version=protocol_version,
        scheme_id=scheme_id,
        scheme_version=scheme_version,
        policy_version=policy_version,
    )


def _entry(**overrides) -> CatalogEntry:
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
    )
    base.update(overrides)
    return CatalogEntry(**base)


class TestCatalogVersionPinning(unittest.TestCase):
    def test_requires_nonempty_catalog_version(self) -> None:
        with self.assertRaises(ValueError):
            VersionPinnedPolicyCatalog(catalog_version="")
        with self.assertRaises(ValueError):
            VersionPinnedPolicyCatalog(catalog_version="   ")

    def test_explicit_version_exposed(self) -> None:
        cat = VersionPinnedPolicyCatalog(catalog_version="cat-v3", entries=[])
        self.assertEqual(cat.catalog_version, "cat-v3")
        resolver = PolicyResolver(cat)
        self.assertEqual(resolver.catalog_version, "cat-v3")

    def test_no_floating_latest(self) -> None:
        # Catalog has only the version string provided at construction — no latest API
        cat = VersionPinnedPolicyCatalog(catalog_version="pinned-1", entries=[_entry()])
        self.assertEqual(cat.catalog_version, "pinned-1")
        self.assertFalse(hasattr(cat, "latest"))


class TestResolveSuccess(unittest.TestCase):
    def test_exact_five_field_resolution(self) -> None:
        cat = VersionPinnedPolicyCatalog(
            catalog_version="c1",
            entries=[_entry(freshness_required=True, legacy_non_provenance_permitted=False)],
        )
        res = PolicyResolver(cat).resolve_policy(_id())
        self.assertTrue(res.is_resolved)
        self.assertEqual(res.status, PolicyResolutionStatus.RESOLVED)
        assert res.record is not None
        self.assertEqual(res.record.catalog_version, "c1")
        self.assertTrue(res.record.freshness_required)
        self.assertTrue(res.record.requires_verification_event_provenance())
        self.assertFalse(res.record.legacy_non_provenance_permitted)


class TestIdentityFailures(unittest.TestCase):
    def test_none_identity(self) -> None:
        cat = VersionPinnedPolicyCatalog(catalog_version="c1", entries=[_entry()])
        res = PolicyResolver(cat).resolve_policy(None)
        self.assertEqual(res.status, PolicyResolutionStatus.MALFORMED)
        self.assertFalse(res.is_resolved)

    def test_empty_identity_field(self) -> None:
        cat = VersionPinnedPolicyCatalog(catalog_version="c1", entries=[_entry()])
        res = PolicyResolver(cat).resolve_policy(_id(protocol_id=""))
        self.assertEqual(res.status, PolicyResolutionStatus.MALFORMED)

    def test_not_found(self) -> None:
        cat = VersionPinnedPolicyCatalog(catalog_version="c1", entries=[_entry()])
        res = PolicyResolver(cat).resolve_policy(_id(policy_version="other"))
        self.assertEqual(res.status, PolicyResolutionStatus.NOT_FOUND)
        self.assertFalse(res.is_resolved)

    def test_wrong_type_identity(self) -> None:
        cat = VersionPinnedPolicyCatalog(catalog_version="c1", entries=[_entry()])
        res = PolicyResolver(cat).resolve_policy("not-a-tuple")
        self.assertEqual(res.status, PolicyResolutionStatus.MALFORMED)


class TestLegacyPermission(unittest.TestCase):
    def test_legacy_true(self) -> None:
        cat = VersionPinnedPolicyCatalog(
            catalog_version="c1",
            entries=[_entry(legacy_non_provenance_permitted=True)],
        )
        res = PolicyResolver(cat).resolve_policy(_id())
        assert res.record is not None
        self.assertTrue(res.record.legacy_non_provenance_permitted)

    def test_legacy_false(self) -> None:
        cat = VersionPinnedPolicyCatalog(
            catalog_version="c1",
            entries=[_entry(legacy_non_provenance_permitted=False)],
        )
        res = PolicyResolver(cat).resolve_policy(_id())
        assert res.record is not None
        self.assertFalse(res.record.legacy_non_provenance_permitted)

    def test_all_false_provenance_without_legacy(self) -> None:
        cat = VersionPinnedPolicyCatalog(
            catalog_version="c1",
            entries=[
                _entry(
                    freshness_required=False,
                    single_use_required=False,
                    explicit_provenance_required=False,
                    legacy_non_provenance_permitted=False,
                )
            ],
        )
        res = PolicyResolver(cat).resolve_policy(_id())
        assert res.record is not None
        self.assertFalse(res.record.requires_verification_event_provenance())
        self.assertFalse(res.record.legacy_non_provenance_permitted)
        # Path integration would fail closed; resolver still RESOLVED with flags

    def test_mapping_legacy_missing_raises(self) -> None:
        data = {
            "policy_id": "p",
            "policy_version": "1",
            "protocol_id": "sf-zk",
            "protocol_version": "1",
            "scheme_id": "mock-scheme",
            "scheme_version": "1",
            "policy_version_identity": "pv-1",
            "freshness_required": False,
            "single_use_required": False,
            "explicit_provenance_required": False,
            # legacy_non_provenance_permitted missing
        }
        with self.assertRaises(ValueError):
            catalog_entry_from_mapping(data)

    def test_mapping_legacy_not_bool(self) -> None:
        data = {
            "policy_id": "p",
            "policy_version": "1",
            "protocol_id": "sf-zk",
            "protocol_version": "1",
            "scheme_id": "mock-scheme",
            "scheme_version": "1",
            "policy_version_identity": "pv-1",
            "freshness_required": False,
            "single_use_required": False,
            "explicit_provenance_required": False,
            "legacy_non_provenance_permitted": "true",
        }
        with self.assertRaises(ValueError):
            catalog_entry_from_mapping(data)


class TestImmutability(unittest.TestCase):
    def test_record_frozen(self) -> None:
        cat = VersionPinnedPolicyCatalog(catalog_version="c1", entries=[_entry()])
        res = PolicyResolver(cat).resolve_policy(_id())
        assert res.record is not None
        with self.assertRaises(Exception):
            res.record.freshness_required = True  # type: ignore[misc]


class TestNoFallbackVersion(unittest.TestCase):
    def test_different_policy_version_not_found(self) -> None:
        cat = VersionPinnedPolicyCatalog(
            catalog_version="c1",
            entries=[_entry(policy_version_identity="pv-1")],
        )
        res = PolicyResolver(cat).resolve_policy(_id(policy_version="pv-2"))
        self.assertEqual(res.status, PolicyResolutionStatus.NOT_FOUND)


class TestCatalogRequired(unittest.TestCase):
    def test_resolver_requires_catalog(self) -> None:
        with self.assertRaises((ValueError, TypeError)):
            PolicyResolver(None)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
