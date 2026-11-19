# OSF WP-3.6.6 Blocker #4  
## Persistence and Recovery Normative Specification

| Field | Value |
|-------|--------|
| **Document ID** | `OSF-WP-3.6.6-B4-PERSIST-RECOVERY-SPEC` |
| **Revision** | **0.3-DRAFT** |
| **Date** | 2026-11-17 (Rev 0.3) |
| **Status** | **WORKING NORMATIVE BASELINE APPROVED (2026-11-17) — formal freeze NOT GRANTED — DRAFT for controlled revision** |
| **Work package** | WP-3.6.6 — Freshness and Replay Contract / Blocker #4 |
| **Normative source of direction** | Owner-approved Blocker #4 Decisions A–F |
| **Implementation authorization** | **NOT GRANTED** |
| **Blocker #4** | **OPEN** |
| **WP-3.6.6 / Stage 3.6** | **OPEN** |
| **Stage 3.5 Gates 5–7** | **CLOSED / PASS / FROZEN** |

This document is the **owner-approved working normative baseline** (2026-11-17) for subsequent controlled revisions. It is **not** formally FROZEN, **not** implementation-authorized, **not** VERIFIED in production, and **not** a Blocker #4 closure.

---

## 1. Purpose, scope, and authority

### 1.1 Purpose

This specification defines the **logical** persistence and recovery contract for verification-event evidence under WP-3.6.6 Blocker #4.

It incorporates owner-approved Decisions **A–F** without altering their meaning.

### 1.2 Scope

**In scope**

- Logical `persist` and `resolve` operations for sealed verification-event records  
- Persistence and resolution result vocabularies  
- Same-ID conflict and exact-payload idempotency rules  
- Mandatory resolution after `UNCERTAIN`  
- Process-restart recovery boundaries  
- Storage-neutral trustworthy-absence rules  
- Separation from AuditPort, Consume Ledger, and Matrix authorization  

**Out of scope**

- Storage engine selection  
- Physical schema or adapter implementation  
- Canonical payload encoding / mechanical equality (D5.3)  
- Production durability demonstration  
- Verification replay policy evaluation  
- Single-use consumption (Consume Ledger)  
- Matrix ALLOW/DENY logic  
- Closure of Blocker #4 or Stage 3.6  

### 1.3 Authority

| Source | Role |
|--------|------|
| Owner Decisions A–F | Normative direction for this draft |
| Inter-Service Contract v2 §10.4 | Retries/recovery require separate specification — this document is that specification class |
| Inter-Service Contract v2 §12.1 | Distinct evidence components; persistence ≠ authorization |
| WP-3.6.3 baseline + owner-accepted path-precondition CC Rev 3.0 | Selection-before-resolution; single-event identity |
| Trust-Boundary ADR Rev 3 (OWNER APPROVED — FROZEN) | Sealed provenance; timestamp non-substitution |
| OAR 2026-11-13 Blockers #7 / #8 | Temporal authority; FailureClass / reason-code discipline |
| WP-3.6.5 AuditPort frozen interface (`WP-3.6.5-AuditPort-Python-Interface-Contract-FROZEN.md`, effective 2026-10-22) | Comparison source for **non-identity** of types and ownership; see §5.1 |

---

## 2. Normative language and terminology

The key words **MUST**, **MUST NOT**, **MAY**, and **REQUIRED** are to be interpreted as requirements of this draft when owner-accepted.

| Term | Meaning |
|------|---------|
| **Sealed verification-event record** | A complete `VerificationEventRecord` (or equivalent logical artifact) whose sealed provenance satisfies the applicable trust-boundary contract |
| **`verification_event_id`** | The unique logical identity of one verification event |
| **Immutable sealed payload** | The sealed event content that Decision A/B treat as the conflict/idempotency subject |
| **Exact payload match** | Logical identity of sealed payload for the same `verification_event_id` under the equality rule applicable at the time of comparison; **mechanical** equality remains subject to deferred D5.3 |
| **Declared durability profile** | The deployment-specific profile that defines what `CONFIRMED` and trustworthy absence mean for a conformant Event Store adapter |
| **Persistence retry** | A subsequent `persist` of the **same** original sealed payload and event ID after resolution |
| **Verification replay** | Policy-controlled re-use of verification evidence under freshness/single-use rules — **not** an Event Store persistence retry |
| **Recovery** | Resumption of a prior persistence attempt for the **same** event ID using a trustworthy copy of the original sealed payload |

---

## 3. Architectural ownership and component boundaries

| Component | Owns | Does not own |
|-----------|------|--------------|
| **Verification Event Store** (this spec) | Persist/resolve of verification-event records; conflict/idempotency; post-`UNCERTAIN` resolution | Authorization; single-use consumption; operation/audit evidence |
| **AuditPort** (WP-3.6.5) | Durable operation/audit evidence keyed by operation attempt | Verification-event store identity or payload equality |
| **Consume Ledger** | Atomic single-use consumption when policy requires | Event Store persist/resolve |
| **Matrix** | Sole ALLOW / DENY / escalation authorization | Evidence persistence |

**MUST NOT** merge Event Store, AuditPort, and Consume Ledger responsibilities.  
**MUST NOT** share enum **type identity** between AuditPort commit/read results and Event Store persist/resolve results, even when English labels coincide.  
**MUST NOT** treat Event Store `CONFIRMED` as Matrix authorization or as Consume Ledger `CONSUMED`.

---

## 4. VerificationEventStorePort — logical interface

Logical operations (not a mandated language signature or schema):

```text
persist(record: VerificationEventRecord) -> PersistResult

resolve(verification_event_id: str) -> ResolveResult
```

- These are **logical** operations.  
- No separate `reconcile()` authority is defined; **`resolve` by original event ID is the reconciliation operation**.  
- Persistence results and resolution results **MUST** remain distinct types/vocabularies.

---

## 5. Persistence result contract

| Result | Meaning |
|--------|---------|
| **`CONFIRMED`** | Under the **Event Store’s declared durability profile**, the adapter has obtained profile-specific commit acknowledgement that the sealed record for this `verification_event_id` is durably held as required by that profile |
| **`FAILED`** | Persistence did not succeed; includes definite contract violations such as Decision A conflicts |
| **`UNCERTAIN`** | The adapter cannot establish whether the record is durably held; caller **MUST** enter the Decision C resolution path before any retry |

### 5.1 Event Store vs AuditPort — mandatory separation

Comparison against the frozen WP-3.6.5 AuditPort interface contract (effective 2026-10-22; document name `WP-3.6.5-AuditPort-Python-Interface-Contract-FROZEN.md` as specified for this revision). **This comparison establishes architectural non-identity of interfaces; it does not establish implementation or conformance evidence.**

| Concern | AuditPort | Event Store (this spec) |
|---------|-----------|-------------------------|
| Logical identity | `operation_id` | `verification_event_id` |
| Commit / persistence result ownership | AuditPort (`AuditCommitResult`) | Event Store (`PersistResult`) |
| Read / resolve result ownership | AuditPort | Event Store |
| Read / resolution vocabulary | `FOUND`, `NOT_FOUND`, `READ_ERROR` | Five outcomes: `FOUND_VALID`, `NOT_FOUND`, `FOUND_INVALID`, `UNAVAILABLE`, `LOOKUP_UNCERTAIN` |
| Commit vocabulary (parallel words, **distinct types**) | `CONFIRMED`, `FAILED`, `UNCERTAIN` | `CONFIRMED`, `FAILED`, `UNCERTAIN` |
| Idempotency key | `operation_id` | `verification_event_id` |
| Primary responsibility | Durable operation/audit evidence | Verification-event persistence and provenance |

**`CONFIRMED` semantics**

- **AuditPort `CONFIRMED`:** Completeness of AuditPort’s **required operation/audit evidence set** is durable under AuditPort’s documented failure model, with authoritative bindings intact and the attempt retrievable (per frozen AuditPort contract).  
- **Event Store `CONFIRMED`:** Profile-specific commit acknowledgement that the **verification-event record** is held as required by the **Event Store’s declared durability profile**.

Event Store **MUST NOT** import AuditPort’s full-evidence-set semantics.  
Event Store **MUST NOT** reuse AuditPort enum **type identity**.  
Event Store resolution outcomes **MUST NOT** be forced into AuditPort’s three-state read model (`FOUND` / `NOT_FOUND` / `READ_ERROR`).  
AuditPort **MUST NOT** be weakened by this specification.



---

## 6. Resolution result contract

| Result | Meaning |
|--------|---------|
| **`FOUND_VALID`** | A record for the ID is present and passes the store’s validity/integrity checks applicable to resolution |
| **`NOT_FOUND`** | Trustworthy **absence** established under the declared storage/consistency profile (Decision F) |
| **`FOUND_INVALID`** | A record is present but fails validity/integrity checks applicable to resolution |
| **`UNAVAILABLE`** | The storage service cannot currently be accessed |
| **`LOOKUP_UNCERTAIN`** | A lookup occurred but cannot establish a trustworthy presence-or-absence result |

`UNAVAILABLE` and `LOOKUP_UNCERTAIN` **MUST** remain distinct.  
Both are **non-authorizing** for provenance-required paths.

---

## 7. Immutable event identity and conflict semantics (Decision A)

1. A definite conflict involving the **same** `verification_event_id` but a **different** immutable sealed payload **MUST** cause `persist` to return **`FAILED`**.  
2. The conflict **MUST** carry the stable reason code **`verification_event_payload_conflict`** with `FailureClass` **`MISMATCHED`** (see §13; repository technical reconciliation pending).  
3. The **original** record **MUST NOT** be overwritten.  
4. A definite conflict is a **contract violation**, not an `UNCERTAIN` outcome.

---

## 8. Exact-payload idempotency and D5.3 dependency (Decision B)

1. A retry with the **same** `verification_event_id` and **identical** immutable sealed payload **MAY** be treated as **idempotent confirmation** under the declared durability profile (e.g., return `CONFIRMED` without creating a second logical event).  
2. An exact-match retry **MUST NOT**:  
   - create a second logical event;  
   - regenerate the evidence record;  
   - alter timestamps;  
   - substitute a different event ID.  
3. **Logical vs mechanical equality (normative distinction):**  
   - The **logical** requirement for exact-payload idempotency is **owner-approved** (Decision B).  
   - The **mechanical** method for determining exact payload equality remains **deferred under D5.3**.  
   - This specification **MUST NOT** invent serialization, hashing, normalization, canonical encoding, or comparison rules.  
4. **Adapter restriction:** An adapter **MUST NOT** claim demonstrated mechanical equality, proven byte-equality, or proven conformance to Decision B’s exact-match rule until D5.3 has been owner-adjudicated and an acceptable mechanism established.  
5. Adapters **MUST NOT** treat any privately chosen comparison method as a **normative** equality standard under this specification. Any interim engineering comparison used solely to unblock development is **non-normative**, **non-claimable** as conformance, and **MUST** be disclosed as provisional in the adapter’s profile notes—it does **not** satisfy D5.3 and does **not** weaken or replace the deferred mechanical requirement.

**Execution boundary:** Until D5.3 is adjudicated and an acceptable mechanical equality mechanism is established, the exact-match recovery branch is a defined **logical** contract but is **not** mechanically executable as a demonstrated conformant path.

---

## 9. UNCERTAIN recovery state machine (Decision C)

When `persist()` returns **`UNCERTAIN`**, the caller **MUST** `resolve(original verification_event_id)` **before** any retry.

**Validity vs equality:** `FOUND_VALID` means the store’s resolution-time validity/integrity checks passed for a present record. **`FOUND_VALID` alone does not establish exact payload equality.** Exact-match determination remains **conditional on the unresolved D5.3 mechanism** (§8). An adapter **MUST NOT** claim demonstrated exact-match conformance while D5.3 remains unresolved. The declared durability profile remains an **independent** requirement for treating a persistence as confirmed.

| Resolution outcome | Subsequent behavior |
|--------------------|---------------------|
| `FOUND_VALID` + exact payload match (logical; mechanical method deferred under D5.3) | Original persistence **MAY** be treated as confirmed under the declared durability profile |
| `FOUND_VALID` + payload mismatch | Treat as **`FAILED`** with Decision A conflict reason; **MUST NOT** overwrite |
| `NOT_FOUND` (trustworthy absence) | Retry **MAY** proceed **only** with the **original** sealed payload and event ID |
| `FOUND_INVALID` | **No retry**; fail closed |
| `UNAVAILABLE` | **No retry**; persistence remains unresolved |
| `LOOKUP_UNCERTAIN` | **No retry**; persistence remains unresolved |

Stale, incomplete, or inconclusive reads **MUST NOT** be treated as trustworthy `NOT_FOUND`.

### 9.1 Decision table (readable state machine)

| Prior state | Input | Next handling |
|-------------|-------|----------------|
| Initial | `persist` → `CONFIRMED` | Done (persist confirmed under profile) |
| Initial | `persist` → `FAILED` | Fail closed (including Decision A conflict) |
| Initial | `persist` → `UNCERTAIN` | **Mandatory** `resolve(id)` |
| After `UNCERTAIN` | `FOUND_VALID` + exact match (D5.3 deferred for mechanical equality) | May treat as confirmed under profile; no demonstrated exact-match claim while D5.3 open |
| After `UNCERTAIN` | `FOUND_VALID` mismatch | `FAILED` + conflict reason; no overwrite |
| After `UNCERTAIN` | `NOT_FOUND` trustworthy | Optional retry of **same** payload+id |
| After `UNCERTAIN` | `FOUND_INVALID` | No retry; fail closed |
| After `UNCERTAIN` | `UNAVAILABLE` | No retry; unresolved |
| After `UNCERTAIN` | `LOOKUP_UNCERTAIN` | No retry; unresolved |
| Process restart | Original id **and** trustworthy sealed payload available | May resume via resolve/persist rules above |
| Process restart | Original id **or** trustworthy sealed payload **unavailable** | **Cannot** resume prior operation; require **new** verification event (new id, new finalization timestamp); **MUST NOT** label as recovery of the prior event |

---

## 10. Process restart and recovery boundary (Decision D)

Recovery after process restart **REQUIRES**:

1. The original `verification_event_id`, and  
2. A trustworthy copy of the original sealed payload.

Recovery **MUST NOT**:

- reconstruct a missing evidence record from partial data;  
- generate a replacement finalization timestamp;  
- alter the original finalization timestamp.

If the original event ID or trustworthy sealed payload is unavailable, the previous persistence operation **cannot** safely resume. The system **MUST** require a **new** verification event with a **new** event ID and its **own** finalization timestamp. A new event **MUST NOT** be represented as recovery or continuation of the previous event.

---

## 11. Storage consistency and portability (Decision F)

Owner-approved rule (incorporated verbatim in meaning):

> `NOT_FOUND` is a logical resolution outcome, not a mandated storage-engine consistency primitive. A conformant adapter **MUST** establish trustworthy absence under its declared storage and consistency profile before returning `NOT_FOUND`. If it cannot establish trustworthy absence, it **MUST** return `LOOKUP_UNCERTAIN`. The mechanism used to establish absence is implementation-specific and **MUST NOT** weaken the logical recovery contract.

No database, transaction primitive, consistency model, or vendor mechanism is selected by this specification.

---

## 12. Durability profile and confirmation semantics

1. Each conformant Event Store deployment **MUST** declare a **durability profile** describing what `CONFIRMED` means (profile-specific commit acknowledgement).  
2. `CONFIRMED` **MUST NOT** be read as “universally durable under all failure modes” beyond that profile.  
3. Production durability **claims** and adapter **conformance evidence** are **not** established by this draft.  
4. Profile declaration is an architectural requirement; demonstration is future work under separate authorization.

---

## 13. Stable reason-code requirements

1. Decision A conflicts **MUST** use the stable, machine-readable reason code **`verification_event_payload_conflict`**.  
2. The owner-approved `FailureClass` mapping is **`MISMATCHED`**.  
3. The persistence result is **`FAILED`**.  
4. The original record **MUST NOT** be overwritten.  
5. The conflict is **non-authorizing**.  
6. **No new `FailureClass` enum member** is authorized.  
7. Reason codes follow **Blocker #8** discipline: reuse existing `FailureClass` members where semantics fit; diagnostic human text **MUST NOT** substitute for the stable code.  
8. **Owner approval vs technical reconciliation:** The reason-code string and `MISMATCHED` mapping are **owner-approved**. Repository-level technical reconciliation against actual `FailureClass` definitions, reason-code conventions/registry, existing consumers of `MISMATCHED`, and Blocker #8 requirements remains **pending**. This specification does **not** claim registry insertion, code implementation, consumer compatibility verification, or completion of that reconciliation.

---

## 14. Freshness, replay, and timestamp boundaries

1. Trusted **`verification_finalized_at`** remains the temporal authority for freshness (Blocker #7 / applicable freshness contract).  
2. **MUST NOT** substitute: AEP `emitted_at`, Matrix `decided_at`, persistence time, or audit commit time.  
3. Recovery **MUST NOT** refresh or regenerate finalization time.  
4. A new verification event **REQUIRES** its own finalization timestamp.  
5. Persistence retry after `UNCERTAIN` is **not** verification replay and **not** Consume Ledger consumption.  
6. Freshness eligibility does **not** authorize an operation.

---

## 15. Failure behavior and fail-closed requirements

| Condition | Required behavior |
|-----------|-------------------|
| Same-ID / different payload | `FAILED` + distinct reason; no overwrite |
| `FOUND_INVALID` after `UNCERTAIN` | No retry; fail closed |
| `UNAVAILABLE` / `LOOKUP_UNCERTAIN` after `UNCERTAIN` | No retry; unresolved (non-authorizing) |
| Untrustworthy absence | **MUST NOT** return `NOT_FOUND` |
| Missing ID or sealed payload at restart | No recovery; new event required |
| Unknown / unmapped outcome | Fail closed / non-authorizing |

---

## 16. Interactions with AuditPort and Consume Ledger

| Concern | Rule |
|---------|------|
| Type identity | Event Store results **MUST NOT** share enum types with AuditPort |
| Idempotency key | Event Store: `verification_event_id`; AuditPort: `operation_id` — **MUST NOT** conflate |
| Consume Ledger | Event Store **MUST NOT** perform consume/burn; single-use remains Consume Ledger with atomic semantics |
| Persistence retry | **MUST NOT** be described as `CONSUMED` or as successful single-use |

---

## 17. Matrix authorization boundary

1. Matrix remains the **sole** authorizer.  
2. `CONFIRMED` persistence, successful resolve, or successful recovery **MUST NOT** independently authorize an operation.  
3. Proof validity is **not** authorization.  
4. WP-3.6.3 selection-before-resolution is **unchanged**: resolution uses the already-selected `verification_event_id`; no reselection, substitution, or silent fallback.

This specification does **not** amend the frozen WP-3.6.3 baseline. No conflict requiring WP-3.6.3 change control was identified for Decisions A–F as stated.

---

## 18. Required future conformance evidence (non-claims)

Future authorized work **MAY** demonstrate:

- Adapter conformance to persist/resolve vocabularies and Decision C state machine  
- Profile-correct `CONFIRMED` and trustworthy `NOT_FOUND`  
- Conflict non-overwrite tests  
- Restart recovery negative tests (missing ID/payload)  

This draft **does not** claim those tests exist, pass, or that production durability is demonstrated.

---

## 19. Explicit deferrals and non-claims

| Item | Status |
|------|--------|
| D5.3 canonical payload encoding/equality | **Deferred** |
| Storage engine selection | **Deferred** |
| Physical schema | **Deferred** |
| Adapter implementation | **Deferred** |
| Durability profile implementation/demo | **Deferred** |
| Production durability claims | **Not established** |
| Implementation authorization | **NOT GRANTED** |
| Blocker #4 closure | **Not authorized** |
| WP-3.6.6 / Stage 3.6 closure | **Not authorized** |
| WP-3.6.5 SQLite (or any) implementation import | **Forbidden** as Event Store default |
| AuditPort interface non-identity | Specified in §5.1 from frozen AuditPort contract comparison; implementation conformance **not** claimed |

---

## 20. Owner-review disposition (completed 2026-11-17)

| Review item | Owner disposition |
|-------------|-------------------|
| Revision 0.3 accepted as working normative baseline | **APPROVED — 2026-11-17** |
| Conflict reason code and FailureClass mapping | **APPROVED** — `verification_event_payload_conflict` → `MISMATCHED`; technical reconciliation **pending** |
| Event Store resolution outcome ownership | **APPROVED** — exclusively in Blocker #4 specification; `ADR-WP-3.6.6-B4-002` records this boundary |
| Additional resolution outcomes or transitions beyond Decisions A–F | **NONE REQUIRED AT THIS STAGE** — Decisions A–F and five outcomes are substantively complete |
| AuditPort / Event Store separation | **RESOLVED** — architectural separation accepted; no further Revision 0.3 changes required on this point |

**Remaining open matters (not resolved by baseline approval):**

| Matter | Status |
|--------|--------|
| D5.3 mechanical equality / canonical payload encoding | **Deferred** |
| Repository-level technical reconciliation of conflict reason code, `FailureClass.MISMATCHED`, consumers, and Blocker #8 | **Pending** |
| Storage engine selection | **Deferred** |
| Physical schema and adapter implementation | **Deferred** |
| Durability profile implementation and demonstration | **Future work** |
| Formal freeze | **Not granted** |
| Implementation authorization | **Not granted** |
| Blocker #4 closure | **Not granted** |
| WP-3.6.6 / Stage 3.6 | **OPEN** |
| Formal repository incorporation of ADR-WP-3.6.6-B4-002 | **Pending** (if not yet incorporated) |

---

## 21. Document control

| Item | Value |
|------|--------|
| Status | **WORKING NORMATIVE BASELINE APPROVED (2026-11-17); formal freeze NOT GRANTED** |
| Implementation | **NOT GRANTED** |
| Blocker #4 | **OPEN** |
| Next authorized action (owner-gated) | Controlled documentation revisions; formal freeze; technical reconciliation; **not** implement without separate authorization |

**End of draft.**
