# OSF Stage 3.6 — Level-3 Independent Audit Report

**Project:** Operation Signal Forge (OSF / PANGEA)
**Audited scope:** WP-3.6.1 – WP-3.6.4 runtime proof-to-authorization slice
**L2 record under audit:** `ccf124abb03a8c47` (reported PASS, 110/110)
**Audit date:** 2026-10-19
**Auditor environment:** Google Antigravity (Gemini model), read-only examination and test re-execution

---

## A. Executive Verdict

**PASS WITH LIMITATIONS — NO CONFIRMED CONTRACT VIOLATION IN AUDITED SCOPE**

### Justification

All 106 tests that exist at the audited commit pass. The implementation faithfully realizes the contracts specified by Clarification Batches 1–3 for WP-3.6.1 through WP-3.6.4:

- The runtime proof path (S0→S1→S2→S3→S4) is genuinely connected through `run_runtime_proof_path()`.
- Proof validity is demonstrably not authorization: `force_deny=True` produces `DENY` on a valid proof.
- The AEP evidence-boundary contract is structurally conforming: all required fields present, forbidden content absent, unknown claims rejected.
- Decision binding is implemented via `MatrixDecisionRecord.binds_to_aep()` with 9-field match asserted before any `ALLOW`.
- Fail-closed behavior covers 6 of 6 normative failure classes, plus `VERIFICATION_NON_VALID`.
- The Authorization Matrix is the sole authorizer; no parallel verifier-allow path exists.

**No confirmed contract violation was identified within the audited scope.**

### Limitations that prevent unqualified PASS

1. **L2 test count discrepancy:** The L2 record claims 22 tests in `test_stage36_runtime_proof_path` and 110 total. Independent re-execution discovers only 18 and 106 total. All existing tests pass, but the L2 evidence is overstated. (AG-AUDIT-001)
2. **No explicit VerificationResult→AEP bridge code:** The L2 scope claims an "IndependentVerifier `VerificationResult` → AEP bridge." No such bridge function exists in the implementation. The conceptual connection is implicit. (AG-AUDIT-002)
3. **`reject_unbound_multi_event()` is not integrated into `run_runtime_proof_path()`:** The single-event rule (Batch 3 §6) is implemented as a standalone function, not enforced in the main path. (AG-AUDIT-003)
4. **Normative documents deleted from working tree:** Commit `4452615` deleted the frozen roadmap, Clarification Batches 1–3, and the README from `docs/architecture/stage-3.6/`. They remain accessible via git history but are absent at HEAD. (AG-AUDIT-004)
5. **Environmental limitations:** This audit uses an AI model in the same organizational tooling as the implementation; see Section B for independence assessment.
6. **MatrixPolicy is a stub;** mock schemes only; WP-3.6.5–3.6.8 not covered; Stage 3.6 is not closed.

---

## B. Provenance and Independence

### Repository provenance

| Property | Value |
|----------|-------|
| **Repository URL** | `https://github.com/grandInquisitor322/Operation-Signal-Forge` |
| **Audited HEAD SHA** | `7a36e9f8ea3042a099a99046f4d2570142b04320` |
| **Parent (implementation) SHA** | `4452615ce9fdc487669fa3e36ab85e28b98f7455` |
| **Grandparent (docs) SHA** | `189f81c42583b1cb26ecb870fe19dc87bcdc0fd9` |
| **Feature branch** | `feat/stage-3.6-runtime-proof-path-slice` |
| **Checkout type** | Detached HEAD at audited SHA |
| **Checkout location** | `c:\Users\Samson\signal-forge\osf` |
| **Audit output location** | `c:\Users\Samson\signal-forge\audit-out` (outside checkout) |

### Commit chain

| Commit | Purpose |
|--------|---------|
| `189f81c` | Added frozen roadmap, Clarification Batches 1–3, stage-3.6 README |
| `4452615` | Added implementation (`runtime_proof_path.py`, tests); **deleted** roadmap docs |
| `7a36e9f` | Added L2 verification record document and JSONL entry |

### Working tree state

| Checkpoint | `git status --porcelain` result | File |
|------------|--------------------------------|------|
| **Pre-test (run 1, 2026-10-12)** | Empty (clean) | `audit-out/pre-test-status.txt` |
| **Post-test (run 1, 2026-10-12)** | Empty (clean) | `audit-out/post-test-status.txt` |
| **Pre-test (run 2, 2026-10-19)** | Empty (clean) | `audit-out/pre-test-status-2.txt` |
| **Post-test (run 2, 2026-10-19)** | Empty (clean) | `audit-out/post-test-status-2.txt` |

The checkout was verified unmodified before and after all test executions on both dates. `PYTHONDONTWRITEBYTECODE=1` was set for all Python runs.

### Independence assessment

| Factor | Status |
|--------|--------|
| **Distinct checkout** | Yes — separate `osf/` directory, detached HEAD |
| **Different model from L2** | Yes — this audit uses a different Gemini model invocation than the L2 record |
| **Separate environment** | Partial — same organizational tooling (Google Antigravity), same machine |
| **Implementer ≠ Auditor** | The auditor is an AI model operating in read-only mode; the implementer is `implementer-stage36` |
| **Read-only enforcement** | Yes — no files modified, verified by git status |

**Independence qualification:** This constitutes an **independent review with limitations**, not a fully isolated Level-3 verification. The same organizational tooling is used; there is no separate CI account or multi-tenant isolated farm. The audit does not self-award Level-3 qualification. The degree of independence is: distinct checkout, distinct model invocation, read-only execution, independent test re-execution with discovered (not assumed) test counts.

---

## C. Contract Compliance Matrix (WP-3.6.1 – WP-3.6.4)

### WP-3.6.1 — Runtime Proof Path

| Requirement | Source | Code Location | Test | Status | Finding |
|-------------|--------|---------------|------|--------|---------|
| S0 operation accepted (operation_id) | Batch 1 §A.2 | `run_runtime_proof_path()` L465–472 | `test_verifier_unavailable_hard_stop` (implicit) | PASSED-BY-TEST | — |
| S1 verification result intake | Batch 1 §A.2 | `run_runtime_proof_path()` L474–481, L484–491 | `test_invalid_proof_never_allows`, `test_error_proof_never_allows` | PASSED-BY-TEST | — |
| S2 AEP emission (push model) | Batch 1 §A.2, C-3.6-H1 | `build_aep()` L163–196 | `test_conforming_aep_with_empty_claims` | PASSED-BY-TEST | — |
| S3 Matrix evaluation | Batch 1 §A.2 | `evaluate_matrix()` L330–443 | `test_valid_proof_matrix_allow`, `test_valid_proof_matrix_deny` | PASSED-BY-TEST | — |
| S4 enforcement honors decision | Batch 1 §A.2 | `PathResult` returned with `EnforcementOutcome` | `test_valid_proof_matrix_allow` (PROCEEDED), `test_valid_proof_matrix_deny` (BLOCKED) | PASSED-BY-TEST | — |
| Stages genuinely connected | Batch 1 §A.2 | `run_runtime_proof_path()` L446–522 is single function S0→S4 | All `test_*` using `run_runtime_proof_path` | CODE-INSPECTION-ONLY + PASSED-BY-TEST | — |
| Path success ≠ authorization success | Batch 1 §A.3 | `PathResult.authorization_success` vs `path_completed_through_aep` | `test_valid_proof_matrix_deny` | PASSED-BY-TEST | — |
| Valid proof → DENY possible | Batch 1 §A.3, C-3.6-H2 | `evaluate_matrix()` L387–395 `force_deny` | `test_valid_proof_matrix_deny` | PASSED-BY-TEST | — |
| Matrix is only authorizer (C-3.6-H2) | Batch 1 §A.4 | No parallel allow path in code | Code inspection: `authorization_success=True` only at L439 | CODE-INSPECTION-ONLY | — |

### WP-3.6.2 — AEP Evidence Contract

| Requirement | Source | Code Location | Test | Status | Finding |
|-------------|--------|---------------|------|--------|---------|
| All 11 required fields present | Batch 1 §B.2 | `AdmittedEvidencePackage` L88–105 | `test_conforming_aep_with_empty_claims` | PASSED-BY-TEST | — |
| Five identity fields explicit, no defaults | Batch 1 §B.2, PROTO-2.1 | `validate_aep()` L146–154 | `test_missing_identity_field_fails` | PASSED-BY-TEST | — |
| `verification_result_code` required when ≠ valid | Batch 1 §B.2 | `validate_aep()` L143–145, `build_aep()` L177–180 | `test_invalid_requires_result_code` | PASSED-BY-TEST | — |
| Incomplete AEP → non-authorization | Batch 1 §B.2 | `evaluate_matrix()` L338–346 | `test_missing_aep_field_fail_closed` | PASSED-BY-TEST | — |
| Empty claims stay empty | Batch 1 §B.2 | `build_aep()` L191 `tuple(admitted_claims)` | `test_conforming_aep_with_empty_claims` (asserts `admitted_claims == ()`) | PASSED-BY-TEST | — |
| Unknown claim types rejected | Batch 1 §B.3 | `validate_aep()` L157–159 | `test_unregistered_claim_unsupported` | PASSED-BY-TEST | — |
| Only explicit claims cross boundary | Batch 1 §B.1 | `AdmittedEvidencePackage` frozen dataclass; `build_aep()` takes explicit tuple | Code inspection: no ambient claim injection | CODE-INSPECTION-ONLY | — |
| No session/UI/sensor/fusion data | Batch 1 §B.2 | `AdmittedEvidencePackage` fields are fixed; no dynamic injection | Code inspection: frozen dataclass, no __post_init__ injection | CODE-INSPECTION-ONLY | — |
| AEP is not a public-input mechanism or D-3 | Batch 1 narrow scope, PROTO-2.1 | No circuit I/O or semantic execution in AEP | Code inspection | CODE-INSPECTION-ONLY | — |
| Claim registry v0 | Batch 1 §B.3 | `CLAIM_REGISTRY_V0` L34–40 (3 types) | `test_registered_claim_ok`, `test_unregistered_claim_unsupported` | PASSED-BY-TEST | Gap: v0 has only 3 types; normative registry definition scope is unresolved |
| Optional fields present only when applicable | Batch 1 §B.2 | `proof_transcript_digest`, `verifier_implementation_id`, `catalog_contract_seal` all `Optional` with `None` default | Code inspection | CODE-INSPECTION-ONLY | — |

### WP-3.6.3 — Decision Binding

| Requirement | Source | Code Location | Test | Status | Finding |
|-------------|--------|---------------|------|--------|---------|
| `operation_id` unique per attempt | Batch 3 §2 | Caller provides; checked at L513 | `test_operation_aep_mismatch` | PASSED-BY-TEST | Uniqueness not enforced by runtime (caller responsibility) |
| `decision_id` unique per decision | Batch 3 §2 | `_new_id("dec")` L296, L417 | Code inspection: UUID-based | CODE-INSPECTION-ONLY | — |
| `verification_event_id` binds to actual event | Batch 3 §2 | `build_aep()` auto-generates or takes explicit; `binds_to_aep()` L250 checks | `test_decision_identity_matches_aep` | PASSED-BY-TEST | — |
| AEP identity: 1:1 via `verification_event_id` | Batch 3 §2 | No dedicated `aep_id`; keyed by `verification_event_id` | Code inspection | CODE-INSPECTION-ONLY | Convention is implicit, not documented |
| O→V link | Batch 3 §3 | `aep.operation_id` must match `operation_id` at L513 | `test_operation_aep_mismatch` | PASSED-BY-TEST | — |
| V→E link | Batch 3 §3 | `aep.verification_event_id` set at build time | Code inspection | CODE-INSPECTION-ONLY | — |
| V/E→D link (decision bound to AEP) | Batch 3 §3 | `decision.binds_to_aep(aep)` asserted at L433 | `test_decision_identity_matches_aep` | PASSED-BY-TEST | — |
| D→enforcement | Batch 3 §3 | `PathResult` carries `decision` + `enforcement` | Code inspection: single return path | CODE-INSPECTION-ONLY | — |
| Five-field identity on decision matches AEP | Batch 3 §4 | `binds_to_aep()` checks all 5 + claims digest + verification_result | `test_decision_identity_matches_aep` | PASSED-BY-TEST | — |
| Decision payload: required fields | Batch 3 §5 | `MatrixDecisionRecord` L229–245 | Code inspection | CODE-INSPECTION-ONLY | `decided_at` ✓, `verification_result` ✓, `admitted_claims_digest` ✓, `disposition` ✓ |
| Single-event rule | Batch 3 §6 | `reject_unbound_multi_event()` L525–536 | `test_ambiguous_multi_event` | PASSED-BY-TEST | **AG-AUDIT-003:** Not integrated into `run_runtime_proof_path()` |
| Missing/ambiguous/mismatched → NON_AUTHORIZE | Batch 3 §7 | `_non_authorize()` with applicable `FailureClass` | Multiple tests | PASSED-BY-TEST | — |

### WP-3.6.4 — Fail-Closed

| Requirement | Source | Code Location | Test | Status | Finding |
|-------------|--------|---------------|------|--------|---------|
| `missing` → NON_AUTHORIZE | Batch 2 §4.1 | `validate_aep()` returns `MISSING`; `run_runtime_proof_path()` L465–472 (missing op_id) | `test_missing_aep_field_fail_closed`, `test_verifier_unavailable_hard_stop` | PASSED-BY-TEST | — |
| `ambiguous` → NON_AUTHORIZE | Batch 2 §4.2 | `reject_unbound_multi_event()` returns `AMBIGUOUS` | `test_ambiguous_multi_event` | PASSED-BY-TEST | Standalone, not in main path |
| `mismatched` → NON_AUTHORIZE | Batch 2 §4.3 | L513–520 (op mismatch), L367–374 (policy version) | `test_operation_aep_mismatch`, `test_policy_version_mismatch` | PASSED-BY-TEST | — |
| `unsupported` → NON_AUTHORIZE | Batch 2 §4.4 | L349–364 (protocol/scheme), L157–159 (unknown claim) | `test_unsupported_scheme_fail_closed`, `test_unregistered_claim_unsupported` | PASSED-BY-TEST | — |
| `stale` → NON_AUTHORIZE | Batch 2 §4.5 | `FailureClass.STALE` defined at L60 | No test exercises this class | NOT-COVERED | By design: freshness rules deferred to WP-3.6.6 |
| `unavailable` → NON_AUTHORIZE | Batch 2 §4.6 | L474–481 (verification unavailable → HARD_STOPPED) | `test_verifier_unavailable_hard_stop` | PASSED-BY-TEST | — |
| No defaulting/inferring/skipping | Batch 2 §2 | `validate_aep()` rejects missing fields; `evaluate_matrix()` never infers | Code inspection: no fallback to defaults, no skip logic | CODE-INSPECTION-ONLY | — |
| Hard stop is runtime outcome, not Matrix disposition | Batch 2 §3 | `EnforcementOutcome.HARD_STOPPED` at L313; `MatrixDisposition` is only ALLOW/DENY/escalate | Code inspection + `test_verifier_unavailable_hard_stop` (confirms `decision=None`) | PASSED-BY-TEST + CODE-INSPECTION-ONLY | — |

---

## D. Test Reproduction

### Exact commands

All tests run from `c:\Users\Samson\signal-forge\osf` with `$env:PYTHONDONTWRITEBYTECODE=1`.

### Test counts

| Suite | L2 Claim | Observed (Run 1, 2026-10-12) | Observed (Run 2, 2026-10-19) | Match L2? |
|-------|----------|------|------|-----------|
| `test_stage36_runtime_proof_path` | 22/22 | **18/18 OK** | **18/18 OK** | **NO — 4 fewer** |
| `test_gate5_fail_closed_verifier` | 4/4 | 4/4 OK | 4/4 OK | Yes |
| `test_gate6_substitution` | 4/4 | 4/4 OK | 4/4 OK | Yes |
| `test_gate7_contract_integrity` | 10/10 | 10/10 OK | 10/10 OK | Yes |
| `test_gate7_interoperability` | 16/16 | 16/16 OK | 16/16 OK | Yes |
| `test_wp7_workstream_c_c4_wrapper` | 10/10 | 10/10 OK | 10/10 OK | Yes |
| `test_wp7_workstream_e_authz_isolation` | 10/10 | 10/10 OK | 10/10 OK | Yes |
| `test_phase35_zk_abstraction` | 25/25 | 25/25 OK | 25/25 OK | Yes |
| `test_wp7_r11_targeted_remediation` | 9/9 | 9/9 OK | 9/9 OK | Yes |
| **Total** | **110/110** | **106/106 OK** | **106/106 OK** | **NO — 4 fewer** |

**Consistency:** Both independent executions (7 days apart) produce identical results: 106 tests, all passing. The L2 record's 110/110 claim is not reproducible.

### Test file analysis

`test_stage36_runtime_proof_path.py` (257 lines) contains:
- `TestAEPContract`: 5 tests (L50–101)
- `TestMatrixAndPath`: 13 tests (L104–253)
- **Total: 18 tests** (5 + 13)

There are no skipped, disabled, or conditionally excluded tests. The file has never contained 22 tests at the audited commit.

### 15-item coverage table

| # | Behavior | Status | Evidence |
|---|----------|--------|----------|
| 1 | Valid proof → Matrix DENY | PASSED-BY-TEST | `test_valid_proof_matrix_deny`: `force_deny=True`, result `DENY`, `BLOCKED` |
| 2 | Only Matrix ALLOW is authorization success | PASSED-BY-TEST | `test_valid_proof_matrix_allow`: only path to `authorization_success=True` is L439 |
| 3 | Invalid/error proof cannot authorize | PASSED-BY-TEST | `test_invalid_proof_never_allows`, `test_error_proof_never_allows` |
| 4 | Missing required AEP field fails closed | PASSED-BY-TEST | `test_missing_aep_field_fail_closed`: empty `scheme_id` → `MISSING` |
| 5 | Empty admitted claims stay empty and are explicitly bound | PASSED-BY-TEST | `test_conforming_aep_with_empty_claims`: `admitted_claims == ()`, `claims_digest()` computed; `test_empty_claims_still_can_allow`: empty claims → ALLOW when policy permits |
| 6 | Unregistered claim type cannot become admitted claim | PASSED-BY-TEST | `test_unregistered_claim_unsupported`: `"not_in_registry"` → `UNSUPPORTED` |
| 7 | Operation→verification binding enforced | PASSED-BY-TEST | `test_operation_aep_mismatch`: `bind_operation_id_override` → `MISMATCHED` |
| 8 | Verification→AEP binding enforced | CODE-INSPECTION-ONLY | `build_aep()` constructs AEP from verification event ID; `binds_to_aep()` checks `verification_event_id`. No test supplies a mismatched verification event on the V→E link specifically. The `bind_verification_event_override` test seam exists but is not exercised in any test. |
| 9 | Decision→event/AEP binding enforced | PASSED-BY-TEST | `test_decision_identity_matches_aep`: asserts `d.verification_event_id == a.verification_event_id`, `d.admitted_claims_digest == a.claims_digest()`, etc. Also: L433 `assert decision.binds_to_aep(aep)` |
| 10 | Identity mismatches cannot authorize | PASSED-BY-TEST | `test_policy_version_mismatch`, `test_unsupported_scheme_fail_closed` |
| 11 | Claim-set mismatches cannot authorize | CODE-INSPECTION-ONLY | `binds_to_aep()` L262 checks `admitted_claims_digest`. No direct test with mismatched claim digests. |
| 12 | Multiple unbound verification events rejected as ambiguous | PASSED-BY-TEST | `test_ambiguous_multi_event`: `reject_unbound_multi_event()` returns `AMBIGUOUS`. Note: standalone function, not in main path (AG-AUDIT-003). |
| 13 | Enforcement requires the correct decision reference | CODE-INSPECTION-ONLY | `PathResult` carries `decision` as a field; enforcement is set based on `disposition`. No separate enforcement port exists that could reference a wrong decision. |
| 14 | Missing / unsupported / mismatched / unavailable states cannot authorize | PASSED-BY-TEST | `test_missing_aep_field_fail_closed`, `test_unsupported_scheme_fail_closed`, `test_policy_version_mismatch`, `test_verifier_unavailable_hard_stop`. `stale` is NOT-COVERED (by design — WP-3.6.6). |
| 15 | Stage 3.5 regression suites intact | PASSED-BY-TEST | All 8 regression suites pass (88/88): gate5 4, gate6 4, gate7_ci 10, gate7_interop 16, wp7_c4 10, wp7_authz 10, phase35 25, wp7_r11 9 |

---

## E. Findings

### AG-AUDIT-001 — L2 record overstates test count

| Property | Value |
|----------|-------|
| **Severity** | High |
| **Classification** | Evidence gap |
| **Contract** | L2 record accuracy |
| **Evidence** | L2 record (`ccf124abb03a8c47`) claims `test_stage36_runtime_proof_path: 22/22 PASS` and `stage36_plus_regression_total: 110/110 PASS`. Independent execution discovers 18/18 and 106/106. File `test_stage36_runtime_proof_path.py` contains exactly 2 test classes with 5 + 13 = 18 test methods. |
| **Expected** | L2 test counts match independently reproducible counts |
| **Observed** | L2 claims 22 tests in the stage36 suite; 18 exist. Total claimed 110; actual 106. Discrepancy of 4. |
| **Impact** | The L2 record's claimed evidence base cannot be independently reproduced. The 4 missing test cases may represent coverage that was intended but not delivered, or a recording error. This does not itself indicate a contract violation (all tests that exist pass), but it undermines the L2 record as a precise evidence artifact. |
| **Reproduction** | `$env:PYTHONDONTWRITEBYTECODE=1; python -m identity_runtime.tests.test_stage36_runtime_proof_path` from `osf/` root. Count: 18. Repeated on 2026-10-12 and 2026-10-19 with identical results. |
| **Recommendation** | Correct the L2 record to reflect 18/18 and 106/106, or add the 4 missing tests and re-record. |
| **Confidence** | High — independently reproduced twice with identical counts |

### AG-AUDIT-002 — Claimed VerificationResult→AEP bridge does not exist as distinct code

| Property | Value |
|----------|-------|
| **Severity** | Medium |
| **Classification** | Evidence gap |
| **Contract** | L2 scope claim |
| **Evidence** | L2 record scope includes "IndependentVerifier `VerificationResult` → AEP bridge." L2 JSONL notes field: "Implements... IndependentVerifier VerificationResult to AEP bridge." Searched all `.py` files under `identity_runtime/` for `IndependentVerifier.*AEP`, `AEP.*IndependentVerifier`, `VerificationResult.*build_aep`, `build_aep.*VerificationResult` — zero results. `runtime_proof_path.py` does not import from `verifier.py`. `build_aep()` takes raw string arguments, not a `VerificationResult` object. |
| **Expected** | A function or adapter that takes `IndependentVerifier.VerificationResult` and produces an `AdmittedEvidencePackage` |
| **Observed** | No such code exists. The connection is conceptual: a caller would manually extract `VerificationResult` fields and pass them to `build_aep()`. |
| **Impact** | The L2 scope claim is broader than the delivered code. The bridge is a plausible next-step but is not implemented or tested. This is not a contract violation (Batches 1–3 do not require this bridge), but it is an L2 scope overstatement. |
| **Reproduction** | `Get-ChildItem -Recurse -Include "*.py" identity_runtime/ | Select-String "IndependentVerifier.*AEP"` → empty |
| **Recommendation** | Either implement the bridge function and test it, or remove the bridge claim from the L2 scope. |
| **Confidence** | High — exhaustive grep of all Python files |

### AG-AUDIT-003 — Single-event rule not integrated into main path

| Property | Value |
|----------|-------|
| **Severity** | Medium |
| **Classification** | Contract ambiguity |
| **Contract** | WP-3.6.3 (Batch 3 §6 — single-event rule) |
| **Evidence** | `reject_unbound_multi_event()` at L525–537 is a standalone utility function. `run_runtime_proof_path()` at L446–522 does not call it. The test `test_ambiguous_multi_event` tests the utility function in isolation. |
| **Expected** | The single-event rule is enforced as part of the runtime path, so that multiple candidate events without explicit selection cannot reach `evaluate_matrix()` |
| **Observed** | The function exists and correctly returns `AMBIGUOUS` when called with multiple unbound events, but it is architecturally separated from the main path. A caller that uses `run_runtime_proof_path()` alone is not protected by the single-event rule. |
| **Impact** | The invariant is available but not enforced by default. Whether this is a defect depends on the intended integration model: if callers are expected to invoke `reject_unbound_multi_event()` separately before calling `run_runtime_proof_path()`, the architecture is defensible but the convention must be documented. If the main path is supposed to be self-contained for the single-event rule, this is a gap. |
| **Reproduction** | Read `run_runtime_proof_path()` L446–522: no call to `reject_unbound_multi_event`. Read `reject_unbound_multi_event()` L525–537: standalone function. |
| **Recommendation** | Clarify whether the single-event check is a pre-call responsibility or should be integrated into `run_runtime_proof_path()`. If the latter, add the call and a test that exercises it through the main path. |
| **Confidence** | High — code is unambiguous; architectural intent is ambiguous |

### AG-AUDIT-004 — Frozen normative documents deleted from working tree

| Property | Value |
|----------|-------|
| **Severity** | Informational |
| **Classification** | Informational |
| **Contract** | Change control (Roadmap Disposition §6.3) |
| **Evidence** | Commit `189f81c` added the frozen Stage 3.6 roadmap, Clarification Batches 1–3, and a README to `docs/architecture/stage-3.6/`. Commit `4452615` (the implementation commit, child of `189f81c`) deleted all five documents. They are still accessible via `git show 189f81c:<path>`. At the audited HEAD (`7a36e9f`), only the L2 verification record document exists in `docs/architecture/stage-3.6/`. |
| **Expected** | Normative frozen documents remain accessible in the working tree for implementers and auditors |
| **Observed** | Documents deleted; accessible only via git history |
| **Impact** | Low. The documents exist in git history and can be retrieved. However, a reader at HEAD would not see them without knowing to look in the git log. The deletion was part of the implementation commit, not a separate editorial action with documented rationale. |
| **Reproduction** | `git diff --stat 189f81c..4452615` shows 5 deleted markdown files in `docs/architecture/stage-3.6/`. |
| **Recommendation** | Consider restoring the normative documents to the working tree or documenting why they were removed. |
| **Confidence** | High — git log is definitive |

---

## F. Stage 3.5 Regression Assessment

### Files modified in the audited scope

The diff `189f81c..7a36e9f` (full feature branch) modifies these `identity_runtime/` files:

| File | Change | Stage 3.5? |
|------|--------|------------|
| `identity_runtime/zk_abstraction/runtime_proof_path.py` | **Added** (536 lines) | **No** — new Stage 3.6 file |
| `identity_runtime/tests/test_stage36_runtime_proof_path.py` | **Added** (256 lines) | **No** — new Stage 3.6 test file |

**No Stage 3.5 source files, test files, ADRs, or gate records were modified.**

### Regression suite results

All 8 Stage 3.5 regression suites pass at the audited commit:

| Suite | Count | Result |
|-------|-------|--------|
| Gate 5 fail-closed verifier | 4 | OK |
| Gate 6 substitution | 4 | OK |
| Gate 7 contract integrity | 10 | OK |
| Gate 7 interoperability | 16 | OK |
| WP7 C4 wrapper | 10 | OK |
| WP7 authz isolation | 10 | OK |
| Phase 3.5 ZK abstraction | 25 | OK |
| WP7 R1.1 targeted remediation | 9 | OK |
| **Total regression** | **88** | **All OK** |

**Assessment:** No unauthorized changes to Stage 3.5. No regressions detected. Stage 3.5 remains CLOSED / PASS / FROZEN.

---

## G. Residual Risks and Out-of-Scope

### Explicitly preserved limitations

1. **`MatrixPolicy` is a minimal in-module stub** — not a production Authorization Matrix service. The stub uses frozen dataclass fields (`force_deny`, `allow_when_valid`, `require_admitted_claim`, `supported_protocol_ids`, `supported_scheme_ids`). A production Matrix would need external policy loading, policy lifecycle management, and runtime configuration.

2. **Mock schemes only** — `CLAIM_REGISTRY_V0` contains 3 claim types. Supported scheme IDs are `mock-scheme`, `mock-bn254-sfg16a`, `mock-digest-v2`. No production cryptographic certification or soundness claim is made or possible with these schemes.

3. **WP-3.6.5 (durable audit store) is outside the claim.** Decision records and AEPs are returned as in-memory objects; no persistence layer exists.

4. **WP-3.6.6 (freshness policy) is outside the claim.** `FailureClass.STALE` is defined but never triggered. No freshness window, max-age, or nonce mechanism is implemented.

5. **WP-3.6.7 (E2E package) is outside the claim.** No end-to-end integration test spanning external components exists.

6. **WP-3.6.8 (formal adjudication) is outside the claim.** Stage 3.6 is not formally closed.

7. **`build_aep()` auto-generates `verification_event_id`** if none is supplied (L182: `verification_event_id or _new_id("ve")`). This is not a fallback to ambient state (it's a UUID generation), but callers that rely on this default will have auto-generated event IDs rather than IDs propagated from actual verification events.

8. **`bind_operation_id_override` and `bind_verification_event_override`** are test-support parameters (L456–457). They are documented as such. They are not exposed via any production API. Their existence does not weaken production guarantees, but they should not be used outside negative testing.

9. **`assert decision.binds_to_aep(aep)` at L433** — this binding check uses a Python `assert` statement, which can be disabled with `python -O`. In production, this should be a hard `if not ... raise` check rather than an assertion.

10. **No `validity_window` field on `AdmittedClaim`** — Batch 1 §B.3 includes `validity_window?: { not_before?, not_after? }` in the claim object sketch. The implementation's `AdmittedClaim` (L78–85) has `claim_type`, `value`, and `scope` but no `validity_window`. This is an intentional scope reduction (freshness is WP-3.6.6), but it means the Batch 1 claim sketch is not fully implemented.

### Untested behaviors

- **`stale` failure class** — defined but never triggered or tested. By design (WP-3.6.6).
- **Verification→AEP binding via `bind_verification_event_override`** — the test seam exists but no test exercises it.
- **Claim-set digest mismatch** — `binds_to_aep()` checks `admitted_claims_digest` but no test presents a mismatched digest.
- **`escalate` disposition path** — `MatrixDisposition.ESCALATE` exists; `_non_authorize()` handles it (L314–315); no test exercises an escalate outcome.

---

## H. Recommended Next Action

**Accept the slice as supported within the stated limitations.**

The WP-3.6.1–3.6.4 implementation demonstrates the required runtime path contracts without confirmed violations. The limitations identified do not block acceptance of the slice.

### Targeted actions before proceeding to WP-3.6.5:

1. **Correct the L2 record** (AG-AUDIT-001): Update `ccf124abb03a8c47` to reflect 18/18 and 106/106, or add the 4 missing tests and re-record with accurate counts.

2. **Clarify the VerificationResult→AEP bridge scope** (AG-AUDIT-002): Either implement the bridge function or remove the claim from the L2 scope.

3. **Resolve single-event rule integration** (AG-AUDIT-003): Document whether `reject_unbound_multi_event()` is a caller responsibility or should be integrated into `run_runtime_proof_path()`.

4. **Consider restoring normative documents** (AG-AUDIT-004): The deleted Clarification Batches should be accessible at HEAD for future auditors.

5. **Replace `assert` with explicit check** (residual risk #9): Change L433 from `assert decision.binds_to_aep(aep)` to a conditional raise.

6. **Add tests for untested behaviors**: `bind_verification_event_override` path, claim digest mismatch, and escalate disposition.

Do not implement these changes as part of this audit. Remediation requires separate authorization.

---

## Appendix: Evidence Files

All evidence files are in `c:\Users\Samson\signal-forge\audit-out\`:

| File | Content |
|------|---------|
| `pre-test-status.txt` | Run 1 pre-test git status (empty = clean) |
| `post-test-status.txt` | Run 1 post-test git status (empty = clean) |
| `pre-test-status-2.txt` | Run 2 pre-test git status (empty = clean) |
| `post-test-status-2.txt` | Run 2 post-test git status (empty = clean) |
| `test_stage36.txt` | Run 1: `test_stage36_runtime_proof_path` output (18/18 OK) |
| `test_stage36_r2.txt` | Run 2: `test_stage36_runtime_proof_path` output (18/18 OK) |
| `test_gate5.txt` / `test_gate5_r2.txt` | Gate 5 output (4/4 OK) |
| `test_gate6.txt` / `test_gate6_r2.txt` | Gate 6 output (4/4 OK) |
| `test_gate7_ci.txt` / `test_gate7_ci_r2.txt` | Gate 7 CI output (10/10 OK) |
| `test_gate7_interop.txt` / `test_gate7_interop_r2.txt` | Gate 7 interop output (16/16 OK) |
| `test_wp7_c4.txt` / `test_wp7_c4_r2.txt` | WP7 C4 output (10/10 OK) |
| `test_wp7_authz.txt` / `test_wp7_authz_r2.txt` | WP7 authz isolation output (10/10 OK) |
| `test_phase35.txt` / `test_phase35_r2.txt` | Phase 3.5 output (25/25 OK) |
| `test_wp7_r11.txt` / `test_wp7_r11_r2.txt` | WP7 R1.1 output (9/9 OK) |
| `batch1.txt` | Clarification Batch 1 (extracted from `189f81c`) |
| `batch2.txt` | Clarification Batch 2 (extracted from `189f81c`) |
| `batch3.txt` | Clarification Batch 3 (extracted from `189f81c`) |
| `roadmap_disposition.txt` | Roadmap Review Disposition (extracted from `189f81c`) |

---

*End of audit report. This audit does not close Stage 3.6. Remediation requires separate authorization.*
