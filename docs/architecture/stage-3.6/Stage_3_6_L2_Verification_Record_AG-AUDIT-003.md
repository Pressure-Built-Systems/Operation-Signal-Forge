# Stage 3.6 — Level-2 Verification Record (AG-AUDIT-003)

| Field | Value |
|-------|--------|
| **verification_id** | *(assign on record — e.g. 8-hex from local generator)* |
| **level** | 2 (`independent_test_re_execution`) |
| **result** | **PASS** |
| **scope** | `stage-3.6-ag-audit-003-single-event-selection-boundary` |
| **timestamp** | *(ISO-8601 UTC of suite re-execution)* |
| **implementation_sha** | *(git rev-parse HEAD of the AG-AUDIT-003 commit on main)* |
| **trail** | `dapp_api/independent_verification.jsonl` |
| **finding** | AG-AUDIT-003 |

## Scope

Remediation of L3 finding **AG-AUDIT-003**: enforce the Batch 3 §§6–7 single-event rule on the **main runtime proof path**, not only via the standalone helper.

Delivered under the approved disposition and implementation plan:

- Upstream selection boundary owns candidate resolution (`select_verification_event`)
- `reject_unbound_multi_event()` remains the normative multi-candidate predicate
- Explicit empty inventory (`candidate_event_ids=()`) → `MISSING` / NON_AUTHORIZE
- Multi candidates without selection → `AMBIGUOUS` / NON_AUTHORIZE
- Selection outside inventory → `MISMATCHED` / NON_AUTHORIZE
- Successful selection binds authoritative **V\*** on AEP and Matrix decision
- ALLOW path uses hard `binds_to_aep` check (not `assert`)
- Main-path tests T1–T8 (not helper-only)

**Not claimed:** Stage 3.6 formal closure; WP-3.6.5–3.6.8; production crypto assurance; isolated Level-3 farm verification.

## Suites

| Suite | Result |
|-------|--------|
| `test_stage36_runtime_proof_path` | 30/30 PASS |
| Gate 5 fail-closed | 4/4 PASS |
| Gate 6 substitution | 4/4 PASS |
| Gate 7 contract integrity | 10/10 PASS |
| Gate 7 interoperability | 16/16 PASS |
| WP7 C4 wrapper | 10/10 PASS |
| WP7 authz isolation | 10/10 PASS |
| Phase 35 ZK abstraction | 25/25 PASS |
| WP7 R1.1 remediation | 9/9 PASS |
| **Combined** | **118/118 PASS** |

## Limitations

- Level 2 developer-controlled local re-execution; **not** Level-3 isolated environment.
- AG-AUDIT-003 remains **open for independent verification** until a distinct L3 (or policy-equivalent) re-execution confirms this SHA.
- Omitted `candidate_event_ids` (default `None`) is single-event mode by caller contract; the path cannot detect ambient multi-candidate sets that were never presented.
- `MatrixPolicy` remains an in-module stub; mock schemes only.
- Stage 3.5 Gates 5–7 remain closed; not reopened.
- **Stage 3.6 is not formally closed** by this record.

## Commands

```text
python -m identity_runtime.tests.test_stage36_runtime_proof_path
python -m identity_runtime.tests.test_gate5_fail_closed_verifier
python -m identity_runtime.tests.test_gate6_substitution
python -m identity_runtime.tests.test_gate7_contract_integrity
python -m identity_runtime.tests.test_gate7_interoperability
python -m identity_runtime.tests.test_wp7_workstream_c_c4_wrapper
python -m identity_runtime.tests.test_wp7_workstream_e_authz_isolation
python -m identity_runtime.tests.test_phase35_zk_abstraction
python -m identity_runtime.tests.test_wp7_r11_targeted_remediation