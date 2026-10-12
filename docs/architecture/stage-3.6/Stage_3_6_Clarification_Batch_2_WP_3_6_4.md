
---

### File 2: `docs/architecture/stage-3.6/Stage_3_6_Clarification_Batch_2_WP_3_6_4.md`

```markdown
# Stage 3.6 — Clarification Batch 2
## WP-3.6.4 — Fail-Closed Runtime Enforcement

**Status:** Normative clarification (architecture)  
**Date:** 2026-10-09  
**Baseline:** Stage 3.6 Architecture Roadmap **FROZEN** (WP-3.6.1–3.6.8)  
**Change control:** Instantiates frozen WP-3.6.4; does **not** unfreeze or redesign the roadmap  

**Does not:** implement code; reopen Stage 3.5; close Stage 3.6; redefine AEP as public inputs or D-3; replace WP-3.6.3 binding field list  

**Depends on:** WP-3.6.1, WP-3.6.2 (Batch 1), WP-3.6.3 baseline (binding rules)

---

## 1. Purpose

Stabilize **when** the runtime MUST **non-authorize**, and how those outcomes are classified, for implementation and E2E (WP-3.6.7).

WP-3.6.4 does **not** redefine what evidence is (3.6.2) or how records correlate (3.6.3). It constrains **authorization disposition** when the path cannot conform.

---

## 2. Frozen normative core (preserved)

When required path state is **missing, ambiguous, mismatched, unsupported, stale, or unavailable**, the runtime:

- **MUST NOT** issue Matrix **ALLOW** for that operation attempt  
- **MUST** non-authorize: **DENY**, **escalate**, or **hard-stop**  
- **MUST NOT** default, infer, soft-skip, open-on-error, or treat absence of proof/AEP/Matrix evaluation as permission  

**Authorization success** = Matrix ALLOW only.  
**Path failure** under this batch ⇒ **not** authorization success.

---

## 3. Non-authorize dispositions

| Disposition | Meaning |
|-------------|---------|
| `DENY` | Explicit denial; operation not authorized |
| `escalate` | Non-allow; escalation path (still **not** ALLOW) |
| `hard_stop` | Path aborted without ALLOW (e.g. unavailable verifier) |

All three are **NON_AUTHORIZE**.

---

## 4. Failure classes (normative)

### 4.1 `missing`

- Missing `operation_id` or verification event  
- No conforming **AEP** (Batch 1 required fields)  
- Missing any five-field identity element  
- Missing Matrix policy identity when required  
- Missing correlation required by WP-3.6.3  

### 4.2 `ambiguous`

- Multiple candidate verification events for one operation without explicit O→V link  
- Decision not uniquely tied to one `verification_event_id`  
- Claims without registered `claim_type` / clear admission  

### 4.3 `mismatched`

- Verification event not bound to the claimed operation  
- AEP `verification_event_id` ≠ event used for Matrix evaluation  
- Protocol/scheme/policy identity on decision ≠ AEP  
- Admitted claims associated with a different verification event  

### 4.4 `unsupported`

- Unsupported protocol/scheme/policy version  
- Unknown `claim_type` in `admitted_claims` (registry v0)  

### 4.5 `stale`

When freshness/reuse rules apply (WP-3.6.6 details):

- Evidence/event outside allowed window  
- Prior ALLOW or prior AEP used for a **new** operation without a new conforming path  
- Historical verification satisfying a different operation  

### 4.6 `unavailable`

- Verifier, catalog, or policy store unavailable  
- Protocol contract integrity/seal failure (G7-CI)  
- Timeout/error such that a complete conforming AEP cannot be emitted  

---

## 5. Trigger → class mapping (aid)

| Condition | `failure_class` | Disposition |
|-----------|-----------------|-------------|
| AEP missing required field | `missing` | NON_AUTHORIZE |
| Unknown claim_type | `unsupported` | NON_AUTHORIZE |
| O/V/AEP identity mismatch | `mismatched` | NON_AUTHORIZE |
| Unbound reuse of V on new O | `stale` or `mismatched` | NON_AUTHORIZE |
| SchemeVerifier/catalog down | `unavailable` | NON_AUTHORIZE |
| Seal mismatch | `unavailable` | NON_AUTHORIZE |

**Invalid proof:** MUST NOT yield ALLOW. Record non-authorization with `verification_result` `invalid` / `error`.

---

## 6. Critical negative requirement

```text
PROHIBITED                         REQUIRED
required state missing / error     missing | ambiguous | mismatched |
   ↓                               unsupported | stale | unavailable
ALLOW / default protocol /            ↓
skip Matrix                        fail closed → NON_AUTHORIZE