# Stage 3.6 Architecture Roadmap — Review Disposition

**Project:** Operation Signal Forge (OSF)  
**Artifact reviewed:** Stage 3.6 — Runtime Proof Path: Architecture Roadmap (WP-3.6.1 to WP-3.6.8)  
**Review type:** Read-only architecture review  
**Review date:** 2026-10-09  
**Disposition recorded:** 2026-10-09  

**Constraints of the review:** No implementation. Stage 3.5 not reopened.

---

## 1. Exact disposition wording

The following wording is **authoritative for this trail entry** and is preserved as issued by the architecture review:

> **Review disposition:** **ACCEPT AS ROADMAP BASELINE** with the gaps and hidden decisions tracked as **pre-implementation clarification**, not as Stage 3.5 defects.

Supporting executive assessment (preserved):

> The roadmap is **coherent and Stage 3.5-compatible** as a normative plan. It is **not yet an implementation or adjudication package**.

> **Verdict:** Suitable to freeze as the **Stage 3.6 architecture roadmap**. Not sufficient alone to start coding without a thin ADR or interface sketch for AEP, Matrix, and enforcement ports. No finding requires reopening Stage 3.5.

| Question | Answer (preserved) |
|----------|-------------------|
| Internal contradictions? | **None material** |
| Gaps between WPs? | **Yes** — AEP schema, claims registry, Matrix/enforcement existence, clock/freshness ownership, C4↔path mapping |
| Hidden decisions? | **Yes** — listed below; make explicit before build |
| Conflicts with Stage 3.5? | **None** that reopen closed gates; two watch items only |
| Safe to treat as Stage 3.6 definition baseline? | **Yes** |

---

## 2. Stage 3.5 boundary result (preserved)

**No material conflict** with frozen Stage 3.5 (Gates 5–7 CLOSED; proof ≠ authorization; PROTO tuple; G7-CI; D-3 deferred; mock schemes non-production).

**Watch items (not current violations):**

1. Do not later equate AEP / path identity fields with **circuit public inputs** without a separate ADR (PROTO-2.1).  
2. Keep Stage 3.5 **C4** (admission to verify) distinct from Stage 3.6 **Matrix** (authorization to act).

---

## 3. Tracked clarification items (pre-implementation)

These items are **tracked for clarification before or at implementation start**. They are **not** Stage 3.5 defects and **do not** block accepting the roadmap as baseline.

### 3.1 Gaps between work packages

| ID | Clarification item |
|----|-------------------|
| **C-3.6-G1** | Freeze or sketch **AEP schema** (field-level) — 3.6.2 rules exist; concrete package shape is only implied via 3.6.5 |
| **C-3.6-G2** | **Claim type registry** (v0) — unknown claim types fail closed, but allowed set is not owned by a WP |
| **C-3.6-G3** | **Authorization Matrix** as a runtime component — assumed throughout; integrated E2E (3.6.7) requires a real Matrix port |
| **C-3.6-G4** | **Enforcement port** — terminal “enforcement” not interfaced; risk of log-only tests |
| **C-3.6-G5** | **Freshness policy owner** — protocol vs policy vs both (3.6.6) |
| **C-3.6-G6** | **Authoritative clock** / time-source policy for freshness checks |
| **C-3.6-G7** | **Ordering guarantees** under concurrency (timestamps vs sequence markers) |
| **C-3.6-G8** | **Escalate** disposition semantics (vs binary DENY) |
| **C-3.6-G9** | Explicit **reuse map** to Stage 3.5 surfaces (catalog, C4, SchemeVerifier) vs new code |
| **C-3.6-G10** | **Operation model** — `operation_id` / `requested_action` vs existing OSF action vocabulary |

### 3.2 Hidden architectural decisions (make explicit before build)

| ID | Decision implicit in the roadmap |
|----|----------------------------------|
| **C-3.6-H1** | **Push model** of evidence — verification emits AEP; Matrix does not pull ambient verifier state |
| **C-3.6-H2** | **Matrix is the only authorizer** on this path — no parallel “verifier allow” path |
| **C-3.6-H3** | **Policy is outside the AEP** — Matrix uses AEP + applicable policy by identity |
| **C-3.6-H4** | **Empty admitted claims are legal** — ALLOW may depend on policy + verification_result only |
| **C-3.6-H5** | **Single verification event per authorizing decision** (ambiguity fail-closed) |
| **C-3.6-H6** | **Durable audit mandatory** for the path — ephemeral-only authz non-conformant |
| **C-3.6-H7** | **Mock schemes in-bounds** for Stage 3.6 E2E when labeled; no production crypto claim |
| **C-3.6-H8** | **D-3 out of Stage 3.6** — catalog semantic execution not required |
| **C-3.6-H9** | **Non-allow includes escalate / hard-stop** — broader than binary DENY |
| **C-3.6-H10** | **Replay** is path-level binding (+ optional nonce), not a full distributed anti-replay platform |

### 3.3 E2E / adjudication sharpening (recommended)

| ID | Item |
|----|------|
| **C-3.6-E1** | Require at least one **freshness-required** profile in E2E so WP-3.6.6 is not vacuously satisfied |
| **C-3.6-E2** | Ensure principles **3.6-A/B/C** full text is frozen and linked from the 3.6.8 package |
| **C-3.6-E3** | ALLOW without required audit evidence is a **conformance failure** (enforce in tests) |

---

## 4. Recommendations retained from the review (non-implementing)

1. Freeze the roadmap as the Stage 3.6 WP spine.  
2. Before implementation: short interface note (AEP fields, Matrix input port, enforcement port, claim-type list v0).  
3. Explicitly reuse Stage 3.5 catalog / C4 / SchemeVerifier boundaries in that note.  
4. In E2E plan: require valid + Matrix DENY and at least one freshness/replay case.  
5. Keep D-3 deferred footnote next to the roadmap in the stage folder.  
6. Do not reopen Gates 5–7 based on this roadmap.

---

## 5. Trail metadata

| Field | Value |
|-------|--------|
| **Disposition** | ACCEPT AS ROADMAP BASELINE |
| **Clarifications** | Tracked as C-3.6-G*, C-3.6-H*, C-3.6-E* (pre-implementation) |
| **Stage 3.5** | Unchanged (CLOSED / PASS); not reopened |
| **Next architectural step** | Optional interface / ADR note addressing tracked items; then implementation against WP-3.6.1+ |

---

## 6. Baseline freeze (change control)

**Freeze date:** 2026-10-09  
**Freeze status:** **FROZEN**

### 6.1 What is frozen

The Stage 3.6 Runtime Proof Path **Architecture Roadmap** (WP-3.6.1 through WP-3.6.8), as accepted under:

> **Review disposition:** **ACCEPT AS ROADMAP BASELINE** with the gaps and hidden decisions tracked as **pre-implementation clarification**, not as Stage 3.5 defects.

is the **frozen normative baseline** for Stage 3.6 work-package scope, ordering, and exit intent.

Also frozen under this baseline:

- Path vs authorization success distinction (WP-3.6.1)
- Evidence-boundary / AEP role as **verification → Matrix only** (not public-input mechanism; not D-3)
- Narrow-scope rule: subsequent clarifications MUST NOT redefine AEP as ZKP public inputs or D-3 semantic execution without explicit change control

### 6.2 What is not frozen by this act

- Implementation code
- Claim registry contents beyond explicitly recorded clarification batches
- Formal Stage 3.6 adjudication (WP-3.6.8)
- Stage 3.5 artifacts (already CLOSED; not reopened)

### 6.3 Change control (mandatory)

After this freeze, **informal redesign of the roadmap is prohibited**.

Any change to frozen roadmap substance MUST:

1. Be proposed as an explicit **delta** (what changes, why, which WPs);
2. Record impact on Stage 3.5 boundaries (default: **no reopen**);
3. Update this trail (or a successor change-control note) with date and disposition;
4. Not silently edit historical disposition wording.

**Allowed without roadmap unfreeze:**

- Pre-implementation clarifications that **narrow or instantiate** tracked items (e.g. AEP field lists, binding fields) without contradicting frozen WP objectives
- Editorial typo fixes that do not change normative meaning

**Requires explicit change control:**

- Adding/removing/reordering WPs
- Changing mandatory E2E scenario classes
- Weakening fail-closed or proof ≠ authorization
- Expanding AEP into public inputs or D-3 semantics
- Merging Matrix authorization into verification success

### 6.4 Freeze statement (exact)

> **The Stage 3.6 Architecture Roadmap (WP-3.6.1–3.6.8) is FROZEN as the normative baseline effective 2026-10-09. Subsequent changes SHALL proceed only through explicit change control, not informal redesign.**

---

*End of disposition record.*