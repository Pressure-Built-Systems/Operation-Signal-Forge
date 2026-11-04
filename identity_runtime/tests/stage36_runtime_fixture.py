# Copyright 2026 Operation Signal Forge contributors
"""R2 Option 1: catalog-backed retained ProductionRuntime test fixtures."""
from __future__ import annotations

from typing import Optional

from identity_runtime.zk_abstraction.identity import IdentityTuple
from identity_runtime.zk_abstraction.policy_resolver import (
    CatalogEntry,
    PolicyResolver,
    VersionPinnedPolicyCatalog,
)
from identity_runtime.zk_abstraction.runtime_proof_path import ProductionRuntime


def catalog_entry(**kw) -> CatalogEntry:
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
        allow_when_valid=True,
        require_admitted_claim=False,
        force_deny=False,
        supported_protocol_ids=frozenset({"sf-zk"}),
        supported_scheme_ids=frozenset({"mock-scheme"}),
    )
    base.update(kw)
    return CatalogEntry(**base)


def make_retained_runtime(
    *,
    catalog_version: str = "test-cat",
    entry: Optional[CatalogEntry] = None,
    entries: Optional[list] = None,
    **entry_kw,
) -> tuple[PolicyResolver, ProductionRuntime]:
    ents = list(entries) if entries is not None else [entry or catalog_entry(**entry_kw)]
    resolver = PolicyResolver(
        VersionPinnedPolicyCatalog(catalog_version=catalog_version, entries=ents)
    )
    return resolver, ProductionRuntime.from_resolver(resolver)


def default_identity(pv: str = "pv-1") -> IdentityTuple:
    return IdentityTuple("sf-zk", "1", "mock-scheme", "1", pv)
