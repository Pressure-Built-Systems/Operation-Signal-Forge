# Stage 3.6 — Clarification Batch 1
## WP-3.6.1 & WP-3.6.2

**Status:** Normative clarification (architecture)  
**Date:** 2026-10-09  
**Baseline:** Stage 3.6 Architecture Roadmap **FROZEN** (WP-3.6.1–3.6.8)  
**Change control:** Instantiates tracked items under the frozen baseline; does **not** redesign the roadmap  

**Does not:** implement runtime code; reopen Stage 3.5; close Stage 3.6; specify full decision binding (WP-3.6.3)

**Prerequisite for:** WP-3.6.3 (Runtime Decision Binding)

---

## Narrow scope rule (mandatory)

| AEP / evidence boundary **is** | AEP **is not** |
|--------------------------------|----------------|
| Contract for what may cross **verification → Matrix** | A ZKP **public-input** mechanism |
| Carrier of verification result + explicit identity + **admitted claims** | An expansion of **D-3** (catalog semantic execution) |
| Input surface for **authorization evaluation** | A substitute for SchemeVerifier / circuit I/O design |

**PROTO-2.1:** Five-field identity on the path/AEP is **governance/path identity**. It does **not** become verifier-visible public input merely by appearing in the AEP.

**D-3:** Deferred. Catalog labels/seals may be integrity-checked (G7-CI); the AEP does **not** execute catalog semantic strings.

> **AEP one-liner:** The sole explicit evidence-boundary object emitted by the verification layer for Matrix evaluation—verification result, explicit five-field path identity, and registered admitted claims only. Not a public-input encoding, not a D-3 engine, not an authorization decision.

---

## A. WP-3.6.1 — Runtime Proof Path Definition (stabilized)

### A.1 Frozen definition (substance unchanged)

The **runtime proof path (OSF)** is the ordered runtime process by which an operation request obtains a cryptographic verification result under an explicit `(protocol_id, protocol_version, scheme_id, scheme_version, policy_version)`, emits only admitted authorization-relevant claims across an explicit evidence boundary, and is accepted or rejected solely by the Authorization Matrix, with the final decision durably bound to that verification event.

### A.2 Ordered stages (normative)

| Stage | Name | Output |
|-------|------|--------|
| S0 | Operation accepted for path evaluation | `operation_id`, requested action identity |
| S1 | Cryptographic verification | Verification event + discrete result |
| S2 | Evidence admission | **Admitted Evidence Package (AEP)** |
| S3 | Matrix evaluation | Disposition (ALLOW / DENY / escalate) |
| S4 | Enforcement | Enforce disposition |

### A.3 Success criteria (frozen)

| Term | Meaning |
|------|---------|
| **Path success** | S0–S2 completed fail-closed and the attempt is reconstructible per audit rules |
| **Authorization success** | Matrix issued **ALLOW** |
| **Non-authorization** | No ALLOW (DENY, escalate, or hard-stop) |

Verification `valid` is **never** authorization success.

### A.4 Resolutions under 3.6.1

| ID | Resolution |
|----|------------|
| **C-3.6-H2** | On this path, the **Authorization Matrix is the only authorizer**. No parallel “verifier ALLOW” or proof-only allow API. |
| **C-3.6-H1** | **Push model:** the verification layer **emits** the AEP; the Matrix does **not** read ambient verifier/session state to build evidence. |
| **C-3.6-G9** (partial) | S1 **reuses** Stage 3.5 surfaces where they exist: **SchemeVerifier**; protocol identity/catalog integrity per Gate 7 / G7-CI; **C4** = eligibility to verify, not permission to act. |
| **C-3.6-G10** (minimal) | An **operation** is any runtime request on this path with unique `operation_id`. Finer action taxonomies may refine `requested_action` later. |

### A.5 Non-goals (3.6.1)

- D-3 catalog semantic execution  
- Production cryptographic certification  
- Decision-binding field set (→ WP-3.6.3)  
- Freshness windows (→ WP-3.6.6)

**WP-3.6.1 status after Batch 1:** **Stable for downstream WPs.**

---

## B. WP-3.6.2 — Verification-to-Matrix Evidence Contract (stabilized)

### B.1 Normative requirement (substance unchanged)

The verification layer MUST emit only explicitly admitted authorization-relevant claims and verification results across the evidence boundary. The Matrix MUST evaluate authorization solely from that admitted evidence and its applicable policy, without reconstructing, inferring, or substituting claims from external or undocumented runtime state.

### B.2 AEP field contract (resolves **C-3.6-G1**)

The **only** structure that may cross S1/S2 → S3 is the **AEP**.

#### Required fields

| Field | Rule |
|-------|------|
| `verification_event_id` | Non-empty unique id for this verification event |
| `operation_id` | Operation this verification serves |
| `verification_result` | `valid` \| `invalid` \| `error` |
| `verification_result_code` | Required when result ≠ `valid` |
| `protocol_id` | Explicit; non-empty |
| `protocol_version` | Explicit; non-empty |
| `scheme_id` | Explicit; non-empty |
| `scheme_version` | Explicit; non-empty |
| `policy_version` | Explicit; non-empty |
| `admitted_claims` | Array; **may be empty** |
| `emitted_at` | Timestamp of AEP emission |

#### Optional fields (only if produced by verification)

| Field | Rule |
|-------|------|
| `proof_transcript_digest` | Only if computed by the verifier |
| `verifier_implementation_id` | Adapter/build identity |
| `catalog_contract_seal` | Only if integrity-checked (G7-CI) |

#### Forbidden in the AEP

- Deployment defaults (“current protocol”)  
- Session/UI/location/fusion/sensor state  
- Claims not listed in `admitted_claims`  
- Free-form text the Matrix must parse as a claim  
- Policy document body  

**Incomplete required fields ⇒ no conforming AEP ⇒ non-authorization (not Matrix ALLOW).**

### B.3 Admitted claims — registry v0 (resolves **C-3.6-G2**)

#### Claim object

```text
{
  claim_type: string,    // must be registered
  value: string | number | boolean | object,
  scope?: string,
  validity_window?: { not_before?: timestamp, not_after?: timestamp }
}