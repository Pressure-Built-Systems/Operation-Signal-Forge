# **OSF WP-3.6.6 — Blocker \#4**

## **Phase B Technical Decision Package**

**Status:** Working Draft — Owner Decisions Consolidated  
**Scope:** Event Store Persistence, Durability, Regional Recovery, and Recovery Evidence Protection  
**Authorization:** Phase B implementation NOT AUTHORIZED  
**Normative status:** Not yet frozen  
**Parent workstream:** WP-3.6.6 Freshness and Replay Contract

---

## **1\. Purpose**

This package consolidates the owner-approved architectural decisions governing Blocker \#4.

Its purpose is to establish the technical and operational guarantees required of a conformant Event Store persistence and recovery implementation.

It does not select an implementation technology or authorize implementation.

The package is intended to serve as the architectural input for subsequent technical specification, independent review, and implementation planning.

## **2\. Architectural boundaries**

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

## **3\. Durability and persistence requirements**

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

## **4\. Persistence outcomes and failure handling**

The existing logical outcome model remains:

| Outcome | Meaning |
| ----- | ----- |
| `CONFIRMED` | Both required regional durable commitments established |
| `FAILED` | Definitive persistence failure established |
| `UNCERTAIN` | Persistence outcome cannot be established |

After `UNCERTAIN`, the original `verification_event_id` must be resolved before retry.

A retry must not create a replacement event or silently overwrite an existing record.

A `NOT_FOUND` result is permitted only when trustworthy absence has been established under the deployment's declared storage and consistency profile.

Otherwise, the result must remain uncertain.

The following handling is mandatory:

* Fail closed.  
* Preserve original evidence and diagnostics.  
* Do not overwrite conflicting evidence.  
* Do not reconstruct partial evidence.  
* Do not treat inconclusive lookup as proof of absence.

## **5\. Regional authority, fencing, and promotion**

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

## **6\. Recovery integrity and quarantine**

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

## **7\. Recovery exercises and conformance**

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

## **8\. Operational authority**

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

## **9\. Recovery authorization evidence retention**

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

## **10\. Recovery evidence integrity protection**

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

## **11\. Integrity-verification scheduling**

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

## **12\. Independent recovery verification**

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

## **13\. Implementation-independent acceptance criteria**

A future implementation must demonstrate, at minimum:

1. No `CONFIRMED` result before both regional durable commitments.  
2. No loss of previously confirmed evidence following regional disaster.  
3. Regional recovery within one hour.  
4. Original evidence identity, timestamps, and provenance preserved.  
5. No concurrent writers during failover or failback.  
6. Verified fencing before write-authority transfer.  
7. Explicit authorization for promotion, Recovery Complete, and failback.  
8. Correct `CONFIRMED`, `FAILED`, and `UNCERTAIN` behavior.  
9. Resolution of the original event after uncertain persistence.  
10. Quarantine and preservation of integrity-conflicted evidence.  
11. Auditable retention, integrity checks, recovery exercises, and findings.  
12. Successful independent verification at the level required by deployment risk.

These criteria describe required outcomes, not a selected implementation design.

## **14\. Outstanding matters and dependencies**

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

These matters must be resolved or explicitly dispositioned before implementation readiness is claimed.

## **15\. Governance and authorization status**

This package consolidates owner-approved architectural decisions. It is not yet a frozen normative specification.

The current governance position remains:

* Phase A: Accepted as PASS.  
* Blocker \#4: OPEN.  
* EC-3.6.6-01: ACTIVE.  
* Phase B: PREPARATION ONLY.  
* Phase B implementation: NOT AUTHORIZED.  
* WP-3.6.6: OPEN.  
* Stage 3.6: OPEN.

The next steps are:

1. Reconcile this package against the existing Blocker \#4 normative draft and ADRs.  
2. Resolve or disposition outstanding dependencies.  
3. Produce a formal technical specification candidate.  
4. Obtain independent readiness assessment against the exact candidate and acceptance criteria.  
5. Obtain separate owner authorization before Phase B implementation.

No implementation technology is selected or approved by this package.

---

**End of Working Draft**
