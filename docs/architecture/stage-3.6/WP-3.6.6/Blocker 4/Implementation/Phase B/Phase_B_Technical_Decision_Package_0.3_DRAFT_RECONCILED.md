# **OSF WP-3.6.6 — Blocker #4**

## **Phase B Technical Decision Package**

**Status:** Working Draft — Owner Decisions Consolidated (Reconciled candidate)  
**Revision of this candidate:** 0.3-DRAFT-RECONCILED  
**Source baseline:** Phase_B_Technical_Decision_Package_0.2_DRAFT_RECONCILED.md  
**Original owner-adjudicated source:** Phase_B_Technical_Decision_Package_0.1_DRAFT_quarantine-retention-clarification.md  
**Reconciled against:** Persistence_and_Recovery_Normative_Specification_0.3_DRAFT.md (Rev 0.3, owner-approved working normative baseline 2026-11-17)  
**Scope:** Event Store Persistence, Durability, Regional Recovery, and Recovery Evidence Protection  
**Authorization:** Phase B implementation NOT AUTHORIZED  
**Normative status:** Not yet frozen — candidate for controlled review only  
**Parent workstream:** WP-3.6.6 Freshness and Replay Contract  
**Blocker #4:** OPEN  
**WP-3.6.6 / Stage 3.6:** OPEN  

**Reconciliation note (documentation only):**  
This candidate incorporates narrow cross-references and clarifications required for consistency with Rev 0.3. This candidate preserves the identified Phase B requirements and provides a 22-unit, section-based decision-preservation crosswalk in Appendix A. The CW labels are traceability conveniences, not original owner decision identifiers. Appendix A's source-verification limitations are stated explicitly within that appendix; it does not independently establish a one-to-one enumeration of the original 22 owner-adjudicated decisions. Sections 6.2 and 9.1 (November 26 quarantine/retention clarifications) are preserved verbatim in meaning. No implementation, normative freeze, or Blocker #4 closure is authorized by this candidate.

**Revision 0.3 correction note (documentation only):**  
Revision 0.3 makes two targeted corrections to revision 0.2 — an explicit unknown/unmapped-outcome fail-closed rule in §4.4 and a Decision B / Decision C interaction clarification in §4.3 — and adds Appendix A (decision-preservation crosswalk). No owner-adjudicated decision is changed, no deferred decision is resolved, and no new technical requirement or storage mechanism is introduced.

---

## **1. Purpose**

This package consolidates the owner-approved architectural decisions governing Blocker #4.

Its purpose is to establish the technical and operational guarantees required of a conformant Event Store persistence and recovery implementation.

It does not select an implementation technology or authorize implementation.

The package is intended to serve as the architectural input for subsequent technical specification, independent review, and implementation planning.

**Cross-reference:** Logical persist/resolve contracts, result vocabularies, Decision A–F conflict/idempotency/recovery rules, and storage-neutral trustworthy-absence rules are defined in the Blocker #4 Persistence and Recovery Normative Specification, Revision 0.3 (working baseline). This Phase B package supplies the regional durability, recovery-operations, quarantine, retention, and authority decisions that sit above that logical contract.

## **2. Architectural boundaries**

The following boundaries remain mandatory:

1. The Event Store is responsible for persistence, resolution, durability, and recovery of sealed verification evidence.  
2. The Event Store does not authorize humanitarian operations.  
3. Matrix remains the sole authorizer of operations.  
4. The Event Store remains distinct from AuditPort and the Consume Ledger.  
5. Event Store recovery cannot create, replace, or reconstruct evidence in a manner that changes its original identity, payload, timestamps, or provenance.  
6. Persistence confirmation does not establish proof validity, operation authorization, or replay eligibility.

### **Explicitly deferred**

* D5.3 mechanical exact-payload equality definition.  
* Database and storage engine selection.  
* Physical schema and adapter design.  
* Replication and consensus technology selection.  
* Cryptographic algorithm and key-management selection.  
* WORM implementation and hash-chain construction.  
* Production implementation and conformance demonstration.

D5.3 remains deferred. `FOUND_VALID` must not be treated as proof of exact mechanical payload equality.

**Cross-reference (Rev 0.3 §8, §9):** Exact-payload idempotency is an owner-approved logical requirement (Decision B). The mechanical method for determining exact payload equality remains deferred under D5.3. An adapter must not claim demonstrated mechanical equality while D5.3 remains unresolved.

## **3. Durability and persistence requirements**

### **3.1 Regional disaster recovery**

The minimum required disaster-recovery boundary is regional.

A conformant deployment must maintain an independent recovery region capable of preserving previously confirmed evidence through the loss of the primary region.

The recovery region must operate in a geographically separate and independently failing regional failure domain. Use of the same cloud provider is permitted; multi-cloud deployment is not mandatory.

### **3.2 Recovery objectives**

| Objective | Requirement |
| ----- | ----- |
| Recovery Point Objective | 0 seconds |
| Recovery Time Objective | No more than 1 hour |
| Confirmed evidence loss | None following regional disaster |
| Recovery evidence identity | Original identity preserved |
| Timestamp and provenance | Original values preserved |

The one-hour RTO applies to regional disaster recovery. It does not automatically apply to failback.

### **3.3 CONFIRMED semantics**

`CONFIRMED` requires durable commitment in both:

* The primary region.  
* The independent recovery region.

A write must not be acknowledged as `CONFIRMED` until both commitments have been established.

The two-region commitment must preserve the original `verification_event_id`, immutable sealed evidence, original timestamps, and provenance.

Partial reconstruction, regenerated timestamps, and replacement evidence are prohibited.

**Clarification relative to Rev 0.3 §5 / §12:**  
`CONFIRMED` is evaluated under the Event Store’s **declared durability profile**. The regional two-region commitment required by this Phase B package is the owner-approved content of that profile for conformant deployments. `CONFIRMED` is not a universal durability claim independent of the declared profile. Production durability demonstration remains future work under separate authorization.

### **3.4 Availability versus durability**

When cross-region durability cannot be established, the deployment must sacrifice write availability rather than acknowledge an unprotected write as `CONFIRMED`.

### **3.5 Persistence latency**

Each deployment must measure and disclose end-to-end persistence confirmation latency.

Disclosure must include:

* p50 latency.  
* p95 latency.  
* p99 latency.  
* Measurement conditions and test configuration.  
* Primary and recovery-region commitment behavior.  
* Degraded-connectivity behavior.

No universal numerical latency ceiling is imposed initially.

Latency optimization must never weaken the approved RPO.

## **4. Persistence outcomes, resolution outcomes, and failure handling**

### **4.1 Distinct result domains (mandatory separation)**

Persistence outcomes and resolution outcomes are distinct vocabularies and must not be collapsed.

**Persistence outcomes** (returned by logical `persist`):

| Outcome | Meaning |
| ----- | ----- |
| `CONFIRMED` | Under the declared durability profile (including the regional two-region commitment required by §3.3), the sealed record for this `verification_event_id` is durably held as required |
| `FAILED` | Definitive persistence failure established (includes Decision A same-ID / different-payload conflicts) |
| `UNCERTAIN` | Persistence outcome cannot be established; caller must enter the resolution path before any retry |

**Resolution outcomes** (returned by logical `resolve`; defined exclusively in Rev 0.3 and owned by Blocker #4 — see ADR-WP-3.6.6-B4-002):

| Outcome | Meaning |
| ----- | ----- |
| `FOUND_VALID` | A record for the ID is present and passes the store’s validity/integrity checks applicable to resolution |
| `NOT_FOUND` | Trustworthy absence established under the declared storage/consistency profile |
| `FOUND_INVALID` | A record is present but fails validity/integrity checks applicable to resolution |
| `UNAVAILABLE` | The storage service cannot currently be accessed |
| `LOOKUP_UNCERTAIN` | A lookup occurred but cannot establish a trustworthy presence-or-absence result |

`UNAVAILABLE` and `LOOKUP_UNCERTAIN` remain distinct. Neither establishes absence. Both are non-authorizing for provenance-required paths.

Event Store result types must not share enum type identity with AuditPort commit/read results (Rev 0.3 §5.1).

### **4.2 Mandatory resolution after UNCERTAIN (Decision C)**

After `persist` returns `UNCERTAIN`, the caller **must** `resolve(original verification_event_id)` **before** any retry.

| Resolution outcome | Subsequent behavior |
| ----- | ----- |
| `FOUND_VALID` + exact payload match (logical; mechanical method deferred under D5.3) | Original persistence may be treated as confirmed under the declared durability profile; no demonstrated exact-match claim while D5.3 remains open |
| `FOUND_VALID` + payload mismatch | Treat as `FAILED` with Decision A conflict reason (`verification_event_payload_conflict` / `MISMATCHED`); must not overwrite |
| `NOT_FOUND` (trustworthy absence) | Retry may proceed only with the original sealed payload and event ID |
| `FOUND_INVALID` | No retry; fail closed |
| `UNAVAILABLE` | No retry; persistence remains unresolved |
| `LOOKUP_UNCERTAIN` | No retry; persistence remains unresolved |

Stale, incomplete, or inconclusive reads must not be treated as trustworthy `NOT_FOUND`.

A retry must not create a replacement event or silently overwrite an existing record.

### **4.3 Conflict and idempotency boundaries**

* Same `verification_event_id` with a different immutable sealed payload **must** return `FAILED` with stable reason code `verification_event_payload_conflict` and `FailureClass` `MISMATCHED`. The original record must not be overwritten. (Decision A; Rev 0.3 §7, §13.)  
* Exact-payload retry of the same ID and identical sealed payload may be treated as idempotent confirmation under the declared durability profile. Mechanical equality remains deferred under D5.3. (Decision B; Rev 0.3 §8.)  
* `FOUND_VALID` alone does not establish exact payload equality.

Exact-payload idempotency remains subject to the mandatory Decision C resolution requirement. Following `UNCERTAIN`, the caller MUST resolve the original event ID before retrying.

### **4.4 Fail-closed and recovery identity rules**

The following handling is mandatory:

* Fail closed.  
* Preserve original evidence and diagnostics.  
* Do not overwrite conflicting evidence.  
* Do not reconstruct partial evidence.  
* Do not treat inconclusive lookup as proof of absence.  
* Process-restart recovery requires both the original `verification_event_id` and a trustworthy copy of the original sealed payload. If either is unavailable, a new verification event (new ID, new finalization timestamp) is required; it must not be labelled recovery of the prior event. (Decision D; Rev 0.3 §10.)  
* Any unknown, unsupported, or unmapped persistence or resolution outcome MUST fail closed and remain non-authorizing. Such an outcome MUST NOT be coerced into `NOT_FOUND`, `FOUND_VALID`, or another defined result. (Rev 0.3 §15.) This rule does not merge or reinterpret the persistence outcome set (`CONFIRMED`, `FAILED`, `UNCERTAIN`) or the resolution outcome set (`FOUND_VALID`, `NOT_FOUND`, `FOUND_INVALID`, `UNAVAILABLE`, `LOOKUP_UNCERTAIN`), which remain distinct per §4.1.

## **5. Regional authority, fencing, and promotion**

### **5.1 Single-writer requirement**

Only one region may hold write authority at a time.

The recovery region must not accept writes until the former primary has been reliably fenced.

Restoration of connectivity alone does not restore write authority.

### **5.2 Controlled promotion**

Regional promotion requires all of the following:

1. Primary failure or unavailability has been established.  
2. The former primary has been reliably fenced.  
3. Previously confirmed evidence has been verified as recoverable.  
4. The designated operational authority explicitly authorizes promotion.  
5. Promotion evidence is recorded.

Automatic promotion is permitted only when every required condition can be established automatically and safely.

Otherwise, controlled intervention is required.

### **5.3 Controlled failback**

The recovery region remains the sole writer until failback is authorized.

Failback requires:

* The original primary to return as a non-writable recovery target.  
* Reconciliation and integrity validation.  
* Preservation of all confirmed evidence generated during recovery.  
* Demonstrated synchronization with the authoritative recovery region.  
* Explicit authorization from the designated operational authority.  
* Fencing of the former recovery-region writer before the original primary resumes writing.

Automatic failback merely because the original primary has returned is prohibited.

Failback verification must provide the same integrity, evidence-completeness, and authority assurances as regional disaster recovery.

## **6. Recovery integrity and quarantine**

Integrity issues include missing, invalid, conflicting, and inconclusive evidence.

Such issues must fail closed.

Affected evidence must be quarantined without silently discarding, repairing, or overwriting the original record.

Quarantine is indefinite and condition-based, not time-based.

Release requires:

* Documented integrity verification.  
* Resolution of the relevant integrity issue.  
* Approval by the designated authority.  
* Preservation of the original evidence and diagnostic history.

Unresolved evidence remains quarantined and subject to the applicable retention policy.

### **6.1 Recovery Complete**

A deployment may declare Recovery Complete only when:

1. All previously confirmed records are accounted for.  
2. RPO zero has been demonstrated.  
3. Integrity and provenance checks pass.  
4. No unresolved evidence conflicts remain.  
5. Single-writer authority is established and verified.  
6. The recovery region is authorized to resume persistence.  
7. Recovery has completed within the one-hour RTO.

Unresolved material integrity findings prevent a full Recovery Complete declaration.

### **6.2 Quarantine and ordinary retention**

Quarantine has no time-based expiry. Evidence remains quarantined until all of the release conditions listed in §6 are satisfied.

The passage or expiry of an ordinary retention period does not satisfy those release conditions and does not release quarantined evidence.

Retention expiry alone does not authorize deletion of unresolved quarantined evidence.

While evidence is quarantined, the original evidence and its diagnostic history must remain preserved.

The statement in §6 that unresolved evidence is "subject to the applicable retention policy" is to be read together with this section and §9. It does not make quarantine expire when an ordinary retention period expires.

## **7. Recovery exercises and conformance**

A successful regional recovery exercise is mandatory evidence of deployment conformance.

Architecture documentation alone is insufficient.

The exercise must demonstrate:

* Preservation of every previously confirmed record.  
* Zero RPO.  
* Recovery within one hour.  
* Preservation of identity, timestamps, and provenance.  
* Correct fencing and single-writer behavior.  
* Safe persistence resumption.  
* Auditable exercise results.

### **7.1 Exercise frequency**

Exercises are required:

* Before initial production conformance.  
* At least annually.  
* After material changes to storage, replication, recovery infrastructure, or recovery procedures.  
* Following a significant regional recovery failure.

A changed system cannot inherit a previous exercise result as proof of conformance.

### **7.2 Recovery findings**

Findings must be classified as:

* **Deviation:** Procedure departed from an approved expectation, but the mandatory outcome was achieved.  
* **Failure:** A mandatory requirement or acceptance criterion was demonstrably violated.  
* **Unresolved finding:** Available evidence is insufficient to establish whether a requirement was satisfied.

Each finding also receives a disposition:

* Open.  
* Under Investigation.  
* Remediated.  
* Accepted by Authorized Authority.  
* Closed.

Mandatory RPO, RTO, integrity, and fencing requirements cannot be waived while claiming conformance.

## **8. Operational authority**

### **8.1 Risk-based deployment classification**

Deployment classification must consider:

* Operational scale.  
* Criticality.  
* Organizational capacity.  
* Risk exposure.

Arbitrary thresholds such as user count, transaction volume, or database size must not independently determine a deployment tier.

The approved framework is:

| Tier | Operational authority expectations |
| ----- | ----- |
| Tier 1 — Limited operational capacity | Role consolidation permitted with documented safeguards and independent verification of mandatory controls |
| Tier 2 — Established operational deployment | Separation of execution and authorization expected; exceptions require documented risk justification |
| Tier 3 — High-criticality deployment | Detection, execution, authorization, and verification independently assigned |

Each deployment must document its classification and justify any role consolidation.

Role consolidation cannot eliminate mandatory integrity, durability, fencing, or authorization controls.

### **8.2 Designation and authorization**

Each deployment must maintain documented delegation of operational authority, including succession and emergency delegation.

Regional promotion, Recovery Complete, and failback require explicit recorded authorization.

Authorization evidence must identify:

* Authorizing identity.  
* Authority basis.  
* Decision.  
* Timestamp.  
* Supporting recovery evidence.

The recovery mechanism must verify authorization before executing the relevant transition.

Infrastructure access and job title alone do not confer decision-making authority.

## **9. Recovery authorization evidence retention**

The approved retention policy is:

| Requirement | Policy |
| ----- | ----- |
| Minimum retention | 365 days |
| Universal maximum | None |
| Extended retention | Required where applicable legal, regulatory, investigative, or accountability obligations apply |
| Deletion | Authorized, documented, and auditable |

Each deployment must declare and periodically review its retention policy.

The absence of a universal maximum does not mean indefinite retention by default.

### **9.1 Ordinary retention and quarantine**

Ordinary retention and quarantine are distinct. Ordinary retention is governed by this section. Quarantine is governed by §6 and §6.2.

An ordinary retention period expiring does not independently release or authorize deletion of unresolved quarantined evidence.

Quarantine does not convert the retention policy into a blanket indefinite-retention rule. The absence of a universal maximum and the default position that retention is not indefinite continue to apply to recovery authorization evidence that is not quarantined.

Deletion of recovery authorization evidence that is not quarantined remains subject to the authorized, documented, and auditable deletion requirement above. Evidence subject to quarantine remains governed by §6 and §6.2; the general deletion requirement in this section does not override the quarantine preservation requirements.

## **10. Recovery evidence integrity protection**

Recovery and authorization records must receive the following protections:

1. Append-only recording. Committed records cannot be silently modified or overwritten.  
2. Cryptographic integrity verification.  
3. Independent regional preservation.  
4. Explicit access controls and auditable administrative access.  
5. Periodic integrity verification, with quarantine on failure.  
6. Independent verification by a reviewer other than the recovery executor.

Corrections must be recorded as new linked entries while preserving original records.

Cryptographic integrity alone does not prove the identity of the creator or legitimacy of an authorization. Appropriate identity and authorization controls remain necessary.

Implementation-specific mechanisms remain deferred.

## **11. Integrity-verification scheduling**

Each deployment must maintain a documented, risk-based integrity-verification schedule.

The schedule must reflect:

* Evidence volume and write frequency.  
* Operational criticality.  
* Threat exposure.  
* Storage and replication characteristics.  
* Recovery objectives.  
* Operational capacity.

The schedule may change as the deployment evolves.

Changes to verification frequency require documented risk reassessment and appropriate operational approval.

Mandatory event-triggered checks apply regardless of the periodic schedule, including:

* Before Recovery Complete.  
* Before failback authorization.  
* Following restoration of an unavailable evidence store.  
* Following suspected integrity violations.  
* Before release of quarantined evidence.  
* During independent recovery exercises.

Schedules, results, failures, remediation, and policy changes must remain auditable.

A deployment must not reduce verification frequency solely to reduce operational cost without a fresh documented risk assessment and appropriate approval.

## **12. Independent recovery verification**

Independent verification is the baseline. External verification is required when deployment risk or circumstances justify it.

Three levels are recognized:

| Level | Arrangement |
| ----- | ----- |
| Internal | Organizationally independent reviewer outside the recovery execution team |
| Enhanced | Independent reviewer with documented technical competence and no conflicting recovery responsibility |
| External | Qualified reviewer outside the deploying organization |

External verification is triggered by:

* High-criticality deployment.  
* Insufficient internal independence.  
* Material recovery failure.  
* Integrity violation or unresolved evidence discrepancy.  
* Significant recovery infrastructure or control changes.  
* Applicable regulatory or contractual requirements.  
* Credible conflicts of interest.

Tier 3 deployments ordinarily require external verification for initial production conformance and material recovery-control changes.

Reviewers assess evidence and report findings. They do not inherit operational recovery authority.

Unresolved material integrity findings prevent a successful recovery-conformance determination.

Verification findings and dispositions must be retained as auditable evidence.

## **13. Implementation-independent acceptance criteria**

A future implementation must demonstrate, at minimum:

1. No `CONFIRMED` result before both regional durable commitments.  
2. No loss of previously confirmed evidence following regional disaster.  
3. Regional recovery within one hour.  
4. Original evidence identity, timestamps, and provenance preserved.  
5. No concurrent writers during failover or failback.  
6. Verified fencing before write-authority transfer.  
7. Explicit authorization for promotion, Recovery Complete, and failback.  
8. Correct `CONFIRMED`, `FAILED`, and `UNCERTAIN` behavior.  
9. Resolution of the original event after uncertain persistence (using the five resolution outcomes and Decision C state machine defined in Rev 0.3).  
10. Quarantine and preservation of integrity-conflicted evidence.  
11. Auditable retention, integrity checks, recovery exercises, and findings.  
12. Successful independent verification at the level required by deployment risk.

These criteria describe required outcomes, not a selected implementation design.

## **14. Outstanding matters and dependencies**

The following remain outside this package's authority or unresolved:

* D5.3 mechanical exact-payload equality.  
* F-B4-GB-002 MES canonical publication and independent verification.  
* F-B4-GB-003 compatibility amendment incorporation and independent inspection.  
* Physical Event Store architecture and storage technology.  
* Replication protocol and consistency implementation.  
* Fencing mechanism and authority-transfer implementation.  
* Cryptographic construction and key-management design.  
* Detailed deployment-tier assessment methodology.  
* Concrete operational evidence formats and retention-policy implementation.  
* Repository-level technical reconciliation of conflict reason code `verification_event_payload_conflict` / `FailureClass.MISMATCHED` against existing registry and consumers (Rev 0.3 §13 — owner-approved mapping; technical reconciliation pending).

These matters must be resolved or explicitly dispositioned before implementation readiness is claimed.

**Chronology and authority of the `MISMATCHED` mapping:** The mapping of the Decision A conflict to reason code `verification_event_payload_conflict` / `FailureClass.MISMATCHED` is owner-approved in the Persistence and Recovery Normative Specification Rev 0.3 (working baseline, 2026-11-17). Any earlier specification language that left this mapping as TBD predates that approval and is superseded by Rev 0.3 as to the owner-approved logical mapping. That approval does not complete the repository-level technical reconciliation against the existing registry and consumers, which remains pending as stated above.

No registry insertion, implementation, consumer compatibility check, or Blocker #8 reconciliation is claimed as completed by this candidate.

**Cross-reference:** ADR-WP-3.6.6-B4-002 records exclusive ownership of the five resolution outcomes by the Blocker #4 Persistence and Recovery specification. Formal repository incorporation status of that ADR is tracked separately and does not authorize ISC amendment, implementation, or Blocker #4 closure.

## **15. Governance and authorization status**

This package consolidates owner-approved architectural decisions. It is not yet a frozen normative specification.

The current governance position remains:

* Phase A: Accepted as PASS.  
* Blocker #4: OPEN.  
* EC-3.6.6-01: ACTIVE.  
* Phase B: PREPARATION ONLY.  
* Phase B implementation: NOT AUTHORIZED.  
* WP-3.6.6: OPEN.  
* Stage 3.6: OPEN.  
* Normative freeze of this package: NOT GRANTED.  
* D5.3: Deferred.

The next steps are:

1. Owner / independent review of this reconciled candidate against Rev 0.3.  
2. Resolve or disposition outstanding dependencies.  
3. Produce a formal technical specification candidate.  
4. Obtain independent readiness assessment against the exact candidate and acceptance criteria.  
5. Obtain separate owner authorization before Phase B implementation.

No implementation technology is selected or approved by this package.

---

## **Appendix A — Decision-Preservation Crosswalk (0.1 → 0.3)**

**Verification status: PARTIAL — COMPARED AGAINST REVISION 0.2 TEXT ONLY.** The comparison underlying this appendix was performed against the text of revision 0.2. The 0.1 source and Persistence and Recovery Specification 0.3 were not available to the preparer of this appendix, so source-section references to 0.1 remain assumed. The 22 rows below are section-based traceability units derived from the section structure of revision 0.2. They are not original decision IDs, and they have not been substantiated as a one-to-one enumeration of the owner's 22 decisions.

**Numbering convention:** The Phase B source does not assign identifiers to its 22 owner-adjudicated decisions. The "CW-nn" labels below are section-based traceability units and crosswalk conveniences only, not original source identifiers. Each row is identified by a concise description of the decision content of its section. A clarification is not a new owner decision. This crosswalk does not reopen or renegotiate any decision.

**Traceability limitation:** The enumeration and the "Original source section" column were reconstructed from the section structure of revision 0.2 and its statement that sections 6.2 and 9.1 are preserved from the 0.1 baseline. Section references for 0.1 are assumed to match the 0.2 numbering and have not been verified against the 0.1 text. Dispositions are assessed against the visible 0.2 text. The Decision A–F rules (Rev 0.3) are defined in the Persistence and Recovery Specification and are cross-referenced in §4; they are not counted among the 22 in this reconstruction.

| Traceability unit (section-based; not a source decision ID) | Decision (descriptive) | Original Phase B source section | Rev 0.3 section | Disposition | How preserved |
| ----- | ----- | ----- | ----- | ----- | ----- |
| CW-01 | Minimum DR boundary is regional; independent, geographically separate recovery region; same provider permitted | 0.1 §3.1 (assumed) | §3.1 | UNCHANGED | Text unchanged |
| CW-02 | Recovery objectives: RPO 0 s, RTO ≤ 1 hour, no confirmed-evidence loss, identity/timestamps/provenance preserved; RTO not automatic for failback | 0.1 §3.2 (assumed) | §3.2 | UNCHANGED | Table and RTO/failback sentence unchanged |
| CW-03 | `CONFIRMED` requires durable commitment in both primary and recovery regions, no reconstruction or regenerated timestamps | 0.1 §3.3 (assumed) | §3.3 | CLARIFIED | Dual-region requirement intact; rev 0.2 added the clarification that `CONFIRMED` is evaluated under the declared durability profile |
| CW-04 | Sacrifice write availability rather than acknowledge unprotected write | 0.1 §3.4 (assumed) | §3.4 | UNCHANGED | Text unchanged |
| CW-05 | Persistence latency measured and disclosed (p50/p95/p99, conditions); no universal ceiling; never weaken RPO | 0.1 §3.5 (assumed) | §3.5 | UNCHANGED | Text unchanged |
| CW-06 | Single-writer requirement; no recovery-region writes until former primary fenced; connectivity alone does not restore authority | 0.1 §5.1 (assumed) | §5.1 | UNCHANGED | Text unchanged |
| CW-07 | Controlled promotion: five conditions; automatic only if all provable automatically and safely | 0.1 §5.2 (assumed) | §5.2 | UNCHANGED | Text unchanged |
| CW-08 | Controlled failback: recovery region sole writer until authorized; listed requirements; no automatic failback | 0.1 §5.3 (assumed) | §5.3 | UNCHANGED | Text unchanged |
| CW-09 | Integrity issues fail closed; affected evidence quarantined without discard/repair/overwrite; release requires four conditions | 0.1 §6 (assumed) | §6 | UNCHANGED | Text unchanged |
| CW-10 | Quarantine is indefinite and condition-based; retention expiry neither releases nor authorizes deletion of unresolved quarantined evidence (Nov 26 clarification) | 0.1 §6, §6.2 (assumed) | §6, §6.2 | UNCHANGED | Preserved verbatim in meaning; §6.2 untouched |
| CW-11 | Recovery Complete: seven conditions; unresolved material findings prevent full declaration | 0.1 §6.1 (assumed) | §6.1 | UNCHANGED | Text unchanged |
| CW-12 | Successful regional recovery exercise is mandatory conformance evidence; documentation alone insufficient | 0.1 §7 (assumed) | §7 | UNCHANGED | Text unchanged |
| CW-13 | Exercise frequency: pre-production, annual, after material change, after significant failure; no inherited results | 0.1 §7.1 (assumed) | §7.1 | UNCHANGED | Text unchanged |
| CW-14 | Finding classification (Deviation/Failure/Unresolved), dispositions, no waiver of RPO/RTO/integrity/fencing | 0.1 §7.2 (assumed) | §7.2 | UNCHANGED | Text unchanged |
| CW-15 | Risk-based three-tier deployment classification; no arbitrary thresholds; role consolidation limits | 0.1 §8.1 (assumed) | §8.1 | UNCHANGED | Text unchanged |
| CW-16 | Documented delegation and explicit recorded authorization for promotion, Recovery Complete, failback; authorization evidence fields | 0.1 §8.2 (assumed) | §8.2 | UNCHANGED | Text unchanged |
| CW-17 | Retention: 365-day minimum, no universal maximum, extended where obligations apply, deletion authorized/documented/auditable; not indefinite by default | 0.1 §9 (assumed) | §9 | UNCHANGED | Text unchanged |
| CW-18 | Ordinary retention and quarantine are distinct; no blanket indefinite retention; non-quarantined evidence stays under ordinary deletion policy (Nov 26 clarification) | 0.1 §9.1 (assumed) | §9.1 | UNCHANGED | Preserved verbatim in meaning; §9.1 untouched |
| CW-19 | Recovery evidence integrity protection: six protections, linked corrections, identity caveat | 0.1 §10 (assumed) | §10 | UNCHANGED | Text unchanged |
| CW-20 | Risk-based integrity-verification schedule with mandatory event-triggered checks; no cost-only reduction | 0.1 §11 (assumed) | §11 | UNCHANGED | Text unchanged |
| CW-21 | Independent verification baseline; Internal/Enhanced/External levels; external triggers; reviewers hold no operational authority | 0.1 §12 (assumed) | §12 | UNCHANGED | Text unchanged |
| CW-22 | Twelve implementation-independent acceptance criteria | 0.1 §13 (assumed) | §13 | CLARIFIED | Criteria unchanged; rev 0.2 added the Rev 0.3 cross-reference to criterion 9 (five resolution outcomes, Decision C) |


---

## **Appendix B — Numbered Owner Decision Register: Decisions 16–22**

**Purpose:** This register records the numbered Phase B decisions discussed during owner adjudication. It is separate from Appendix A's section-based preservation crosswalk. Decision numbers below are decision-history identifiers; they are not derived from section numbers or CW labels.

**Evidence rule:** A requirement already appearing in the package is not, by itself, proof that the corresponding numbered decision was individually adopted. The status column distinguishes directly recovered owner approval, adoption, or confirmation from any inferred mapping. No missing approval is inferred.

| Decision | Decision title | Decision content recorded for traceability | Current evidence status |
|---|---|---|---|
| **16** | **Failback Verification** | Failback must receive integrity, evidence-completeness, and authority verification equivalent to regional disaster recovery. Verification includes preservation of all confirmed evidence, no confirmed-evidence loss, single-writer authority and fencing, explicit authorization, timestamp/reconciliation integrity, and safe persistence resumption. The one-hour regional disaster-recovery RTO does **not** automatically apply to failback. | **OWNER-APPROVED.** Direct approval recovered from the 2026-11-26 decision discussion. |
| **17** | **Operational Authority Boundaries** | Exact owner-supplied text (preserved without paraphrase):<br>1. Deployment classification is risk-based, not determined by arbitrary thresholds such as user count, transaction volume, or database size.<br>2. Classification considers operational scale, criticality, organizational capacity, and risk exposure.<br>3. Tier 1 — Limited operational capacity: role consolidation may be permitted with documented safeguards and independent verification of mandatory controls.<br>4. Tier 2 — Established operational deployment: separation of execution and authorization is expected; exceptions require documented risk justification.<br>5. Tier 3 — High-criticality deployment: detection, execution, authorization, and verification must be independently assigned.<br>6. Every deployment must document its classification and justify any role consolidation.<br>7. One important invariant applies across all tiers: **role consolidation cannot eliminate mandatory integrity, durability, fencing, or authorization controls.** No individual may bypass those controls simply because a deployment has limited staffing. | **OWNER-CONFIRMED** — exact decision text recovered and supplied directly by the owner on 2026-11-27. |
| **18** | **Operational Authority Designation and Verification** | Each deployment must maintain documented delegation of operational authority, including succession and emergency delegation. Promotion, Recovery Complete, and failback require explicit recorded authorization. The record identifies the authorizing identity, authority basis, decision, timestamp, and supporting recovery evidence. Authorization is verified before the transition executes. Infrastructure access or job title alone does not confer decision-making authority. Role consolidation must retain mandatory safeguards; Matrix remains the sole authorizer of humanitarian operations. | **OWNER-ADOPTED.** Direct adoption recovered from the 2026-11-26 decision discussion. |
| **19** | **Recovery Authorization Evidence Retention** | The package records a minimum retention period of 365 days; no universal maximum; extended retention where legal, regulatory, investigative, or accountability obligations apply; and deletion that is authorized, documented, and auditable. Each deployment declares and periodically reviews its retention policy. The absence of a universal maximum does not mean indefinite retention by default. Quarantined evidence remains governed by §§6 and 6.2, not ordinary expiry. | **OWNER-CONFIRMED.** The owner confirms Decision 19, including the complete retention-policy entry recorded here. |
| **20** | **Recovery Evidence Integrity Protection** | Recovery and authorization records receive append-only protection; cryptographic integrity verification; independent regional preservation; explicit access controls and auditable administrative access; periodic integrity verification with quarantine on failure; and independent verification by a reviewer other than the recovery executor. Corrections are new linked entries that preserve original records. Cryptographic integrity alone does not establish creator identity or authorization legitimacy. Implementation mechanisms remain deferred. | **OWNER-CONFIRMED.** The owner confirms Decision 20 as recorded here; implementation mechanisms remain deferred as stated. |
| **21** | **Risk-Based Integrity Verification Scheduling** | Each deployment maintains a documented, risk-based integrity-verification schedule reflecting evidence volume and write frequency, operational criticality, threat exposure, storage and replication characteristics, recovery objectives, and operational capacity. Schedule changes require documented risk reassessment and appropriate approval. Mandatory event-triggered checks apply before Recovery Complete, before failback authorization, after restoration of an unavailable evidence store, after suspected integrity violations, before quarantine release, and during independent recovery exercises. Frequency must not be reduced solely to reduce cost without fresh documented risk assessment and approval. | **OWNER-CONFIRMED.** The owner confirms Decision 21 as recorded here; the stated risk-based scheduling and event-triggered verification requirements are retained. |
| **22** | **Risk-Based Independent Recovery Verification** | Independent verification is the baseline. Internal, Enhanced, and External verification levels are recognized. External verification is triggered by high criticality, insufficient internal independence, material recovery failure, integrity violation or unresolved discrepancy, significant infrastructure/control changes, regulatory or contractual requirements, or credible conflicts of interest. Tier 3 deployments ordinarily require external verification for initial production conformance and material recovery-control changes. Reviewers assess evidence and report findings but do not inherit operational recovery authority. Unresolved material integrity findings prevent successful recovery-conformance determination; findings and dispositions are retained as auditable evidence. | **OWNER-CONFIRMED.** The owner confirms Decision 22 as recorded here. |

### Register reconciliation rules

1. Decisions **16 and 18** retain their previously recorded owner-approval/adoption evidence. Decisions **19, 20, 21, and 22** remain owner-confirmed.
2. Decision **17** is now owner-confirmed as **Operational Authority Boundaries**. Its exact seven-point wording was supplied directly by the owner on 2026-11-27 and is the controlling source for the Decision 17 entry. The former provisional mapping of Decision 17 to "Recovery Complete Determination" is withdrawn. Recovery Complete remains an existing package requirement governed by §6.1; it is not numbered Decision 17.
3. The owner confirmation of Decisions 19–22 confirms the entries as recorded in this register. It does not authorize implementation or resolve any separately deferred implementation mechanism.
4. These evidence-status labels are documentary controls. They prevent an inferred mapping from being represented as an owner-approved decision.
5. The owner confirmation of Decision 17 confirms the entry as recorded here. It does not create additional implementation mechanisms or resolve any separately deferred technical matter. Do not renumber Decisions A–F from the separate Persistence and Recovery logical contract as Phase B decisions.
6. Appendix A remains a section-based preservation crosswalk. Appendix B is the numbered decision-history register. The two appendices serve different purposes and must not be conflated.

**Governance:** This appendix is a documentation-only register. It does not grant implementation authorization, normative freeze, repository incorporation, or closure of Blocker #4, WP-3.6.6, or Stage 3.6.

---

**End of Working Draft (0.3-DRAFT-RECONCILED candidate)**  
**This document is a candidate only. It does not freeze Phase B, authorize implementation, or close Blocker #4.**
