# Stage 3.6 — Clarification Batch 3
## WP-3.6.3 — Runtime Decision Binding

**Status:** Normative clarification (architecture)  
**Date:** 2026-10-09  
**Baseline:** Stage 3.6 Architecture Roadmap **FROZEN** (WP-3.6.1–3.6.8)  
**Change control:** Instantiates frozen WP-3.6.3; does **not** redesign the roadmap  

**Depends on:** Batch 1 (WP-3.6.1 path, WP-3.6.2 AEP)  
**Aligns with:** Batch 2 (WP-3.6.4 non-authorize on broken binding)  

**Does not:** implement code; reopen Stage 3.5; redefine AEP fields/registry; introduce public inputs or D-3; define full audit store (3.6.5) or freshness windows (3.6.6)

---

## Narrow scope

| WP-3.6.3 **is** | WP-3.6.3 **is not** |
|-----------------|---------------------|
| Binding of **decision D** to **operation O**, **verification event V**, and **AEP E** | A new evidence type |
| Match rules and rejection of bad association | ZKP public-input design |
| Correlation ids for reconstructibility | D-3 catalog semantic execution |
| Input to fail-closed classes `missing` / `ambiguous` / `mismatched` | Replacement of Matrix policy |

---

## 1. Critical invariant (preserved)

```text
REQUIRED                              PROHIBITED
Operation O                           Operation O
  └─ Verification Event V               ├─ Verification Event V
       └─ AEP E                         └─ unrelated / stale E′
            └─ Matrix Evaluation M               ↓
                 └─ Decision D               Matrix ALLOW
```

**D MUST be specifically derived from V and E for O under the applicable policy identity.**

---

## 2. Binding identifiers (required)

| Field | Rule |
|-------|------|
| `operation_id` | Unique per operation attempt on the path |
| `verification_event_id` | Unique per verification event; must be the event that served this operation |
| `decision_id` | Unique per Matrix decision record |
| AEP identity | Either dedicated `aep_id` **or** 1:1 keying of AEP by `verification_event_id` (exactly one convention per deployment; document which) |

---

## 3. Required links (normative)

| Link | MUST hold |
|------|-----------|
| O → V | V was produced for `operation_id` |
| V → E | E was emitted from that `verification_event_id` (Batch 1 AEP) |
| V/E → D | D evaluated that V and that E only |
| D → enforcement | Enforcement references `decision_id` (port detail may lag; disposition must not float free of D) |

Ambiguous or missing links ⇒ **NON_AUTHORIZE** (Batch 2: `missing` / `ambiguous` / `mismatched`).

---

## 4. Identity on the decision (must match AEP)

Decision record MUST carry (or cryptographically reference an immutable snapshot of) the five-field path identity from the AEP:

| Field | Match rule |
|-------|------------|
| `protocol_id` | = AEP |
| `protocol_version` | = AEP |
| `scheme_id` | = AEP |
| `scheme_version` | = AEP |
| `policy_version` | = AEP |
| `policy_id` | If Matrix uses a policy id distinct from version — explicit on D; must match selected policy |

Mismatch ⇒ `mismatched` ⇒ **NON_AUTHORIZE**. No silent repair from defaults.

---

## 5. Decision payload (required)

| Field | Rule |
|-------|------|
| `disposition` | `ALLOW` \| `DENY` \| `escalate` (Batch 2: `escalate` is non-allow) |
| `decided_at` | Timestamp of decision |
| `verification_result` | Snapshot of AEP result (`valid` / `invalid` / `error`) for audit only — not a second crypto check |
| `admitted_claims` binding | Reference to the claim set used: full list, **or** `admitted_claims_digest` over the AEP claims as emitted |

Empty admitted claims remain legal if the bound AEP had an empty list; D still binds to that empty set.

---

## 6. Single-event rule (resolves C-3.6-H5)

For an authorizing path attempt:

- Exactly **one** `verification_event_id` is bound to O for that decision.
- If multiple candidates exist without explicit selection recorded in the binding ⇒ `ambiguous` ⇒ **NON_AUTHORIZE**.

---

## 7. Rejection conditions (binding-specific)

| Condition | `failure_class` (Batch 2) |
|-----------|---------------------------|
| Missing `operation_id` or `verification_event_id` on decision path | `missing` |
| Missing O→V or V→E link | `missing` |
| Multiple unbound V for one O | `ambiguous` |
| D cites V′ ≠ AEP's verification event | `mismatched` |
| Five-field identity on D ≠ AEP | `mismatched` |
| Claims used ≠ claims on bound AEP | `mismatched` |
| Prior V/AEP reused for different O without new path | `stale` or `mismatched` (prefer `stale` when reuse/freshness applies) |

---

## 8. Minimum decision record sketch

```text
MatrixDecisionRecord {
  decision_id,
  operation_id,
  verification_event_id,
  // aep_id optional if 1:1 with verification_event_id
  protocol_id, protocol_version,
  scheme_id, scheme_version,
  policy_version,
  policy_id?,
  disposition,
  decided_at,
  verification_result,
  admitted_claims_digest? | admitted_claims_ref?
}
```

Storage layout is WP-3.6.5; these fields and match rules are WP-3.6.3.

---

## 9. Explicit non-goals

- Changing Batch 1 AEP required fields or claim registry v0
- Public inputs / circuit I/O
- D-3
- Max-age / nonce algorithms (WP-3.6.6 may use these binding fields)
- Full enforcement API (must honor `decision_id` + `disposition` when present)

---

## 10. Tracked items advanced

| ID | Effect |
|----|--------|
| C-3.6-H5 | Single verification event per authorizing decision — clarified |
| WP-3.6.3 baseline | Binding fields, links, match/reject rules instantiated |
| C-3.6-G3 / G4 | Still open as runtime ports; binding record shape is stable for them to consume |

---

## 11. Batch 3 statement

**Clarification Batch 3 (WP-3.6.3):** Under the frozen Stage 3.6 roadmap, every Matrix decision on the runtime proof path MUST be durably bound to exactly one operation, one verification event, and the AEP emitted for that event, with five-field path identity matching the AEP. Missing, ambiguous, or mismatched association MUST NON_AUTHORIZE. This batch does not alter the AEP evidence-boundary contract, public-input rules, or D-3.

**WP-3.6.3 status after Batch 3:** Stabilized for audit (3.6.5), freshness (3.6.6), and E2E (3.6.7) planning.