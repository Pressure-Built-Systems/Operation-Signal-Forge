# AG-AUDIT-003 — Proposed Implementation Plan

**Title:** Single-event selection boundary on the runtime proof path  
**Status:** PROPOSED — awaiting implementation authorization  
**Disposition:** Upstream selector owns candidate resolution  
**Related:** `AG-AUDIT-003` (L3), Clarification Batch 3 §§6–7, `runtime_proof_path.py`

This document is a **proposed** implementation plan only. It does **not** authorize code changes, close AG-AUDIT-003, or close Stage 3.6.

---

## 1. Goal

Enforce Batch 3 §§6–7 on the **main runtime path** so that multiple unbound verification events for one operation **without explicit selection** cannot reach an authorizing outcome.

`reject_unbound_multi_event()` remains the normative predicate. Enforcement is applied at the **selection boundary** (caller or thin pre-step). The runtime path must refuse to authorize when multi-candidate ambiguity is unresolved.

---

## 2. Non-goals

- D-3 / protocol-catalog semantics
- AEP schema changes
- Matrix policy redesign or change of authorizer
- Stage 3.5 / Gates 5–7 modifications
- WP-3.6.5 durable audit, WP-3.6.6 freshness, WP-3.6.7 E2E, WP-3.6.8 formal adjudication
- Stage 3.6 formal closure
- Implicit selection policies (e.g. auto-pick latest or any valid event)

---

## 3. Governing disposition (summary)

| Topic | Decision |
|-------|----------|
| Candidate resolution owner | Upstream selection boundary |
| Runtime path requirement | Verifiable single-event selection |
| Bare singular event id | Not proof that multi-candidate ambiguity was resolved |
| Normative check | `reject_unbound_multi_event()` |
| Failure classes | `ambiguous` / `mismatched` → NON_AUTHORIZE |
| Matrix role | Unchanged — sole authorizer; no ambient inference |

---

## 4. Design

### 4.1 Selection boundary

Add a thin pre-step (name illustrative):

```text
select_verification_event(
  operation_id,
  candidate_event_ids,
  selected_event_id | None
) → SelectionResult
```

**Rules** (via existing `reject_unbound_multi_event` semantics):

| Situation | Result |
|-----------|--------|
| `len(candidates) > 1` and no `selected_event_id` | `AMBIGUOUS` → NON_AUTHORIZE |
| `selected_event_id` not in candidates | `MISMATCHED` → NON_AUTHORIZE |
| `len(candidates) == 0` | `MISSING` (or equivalent fail-closed) |
| `len(candidates) == 1` and selection absent | OK; selected = that sole id |
| `len(candidates) >= 1` and selection ∈ set | OK; selected = `selected_event_id` |

**Invariant:** When a candidate set is supplied and `|candidates| > 1`, selection must be explicit and checked before the path can authorize.

### 4.2 Runtime path wiring

- Extend `run_runtime_proof_path` / `run_path_from_verification` to accept optional:
  - `candidate_event_ids: Sequence[str] = ()`
  - `selected_event_id: Optional[str] = None`
- **If `candidate_event_ids` is non-empty:** run the selection boundary first; on failure return NON_AUTHORIZE with the failure class; do **not** reach Matrix ALLOW.
- **If `candidate_event_ids` is empty:** preserve current single-id behavior for existing tests (caller asserts single-event context). Document this compatibility rule.
- On selection OK: continue S0–S4 using only the **selected** verification event id.

### 4.3 Explicitly unchanged

- `evaluate_matrix` authorization rules
- AEP field set (Batch 1)
- Semantic meaning of `reject_unbound_multi_event`
- Stage 3.5 modules and gate records

---

## 5. Proposed files

| File | Change |
|------|--------|
| `identity_runtime/zk_abstraction/runtime_proof_path.py` | Selection result type (or minimal equivalent), pre-step, path entry wiring |
| `identity_runtime/tests/test_stage36_runtime_proof_path.py` | Main-path multi-event tests |
| Optional docs note | Link disposition → plan; finding remains open until verified |

---

## 6. Required tests

| ID | Case | Expect |
|----|------|--------|
| T1 | Multi candidates, no selection, via **`run_runtime_proof_path`** | `AMBIGUOUS`, not ALLOW |
| T2 | Selection ∉ candidates, via main path | `MISMATCHED`, not ALLOW |
| T3 | Single candidate, no explicit selection | Path proceeds; Matrix may ALLOW or DENY |
| T4 | Multi candidates + valid selection | Path proceeds; selected id bound on AEP/decision |
| T5 | Existing stage36 + Stage 3.5 regression | All green; no Stage 3.5 source edits |

Testing `reject_unbound_multi_event()` only in isolation is **insufficient**.

---

## 7. Verification plan (after authorization)

1. Re-run stage36 suite and Stage 3.5 regression list used in L2/L3.
2. Record results (amendment or new verification row) referencing AG-AUDIT-003.
3. Do **not** mark AG-AUDIT-003 closed until main-path tests prove enforcement.
4. Do **not** declare Stage 3.6 formally closed.

---

## 8. Exit criteria

- [ ] Implementation authorization granted (external review / ChatGPT greenlight)
- [ ] Selection boundary enforced on main path
- [ ] T1–T4 pass
- [ ] No Stage 3.5 file changes
- [ ] Regression green
- [ ] Verification note recorded
- [ ] AG-AUDIT-003 status: implemented / pending independent verify — **not** Stage 3.6 CLOSED

---

## 9. Suggested commit message (when authorized)

```text
fix(stage36): enforce single-event selection at runtime path boundary (AG-AUDIT-003)
```

---

## 10. Document control

| Field | Value |
|-------|--------|
| Plan type | Proposed only |
| Implementation | Not authorized by this document |
| Supersedes | None |
| Depends on | AG-AUDIT-003 architecture disposition; Batch 3 §§6–7 |
| Next step | Obtain implementation greenlight; then execute §§4–8 without scope expansion |
```