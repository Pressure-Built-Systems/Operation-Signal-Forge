# ADR-WP-3.6.6-B4-002 — Event Store Resolution Outcome Ownership

| Field | Value |
|-------|--------|
| **ADR ID** | `ADR-WP-3.6.6-B4-002` |
| **Title** | Event Store Resolution Outcome Ownership |
| **Date** | 2026-11-17 |
| **Status** | **OWNER APPROVED** — formal repository incorporation pending |
| **Work package** | WP-3.6.6 Blocker #4 |
| **Related specification** | Blocker #4 Persistence and Recovery Normative Specification, Revision 0.3 (working baseline) |
| **Implementation authorization** | **NOT GRANTED** by this ADR |

---

## 1. Context

Blocker #4 defines persistence and resolution behavior for the Verification Event Store, including five distinct resolution outcomes and a recovery state machine after `UNCERTAIN` persistence results.

The Inter-Service Contract (ISC) v2 remains the owner-approved inter-service logical contract. Care is required so that ISC documentation does not re-define or dilute Event Store resolution semantics owned by Blocker #4.

---

## 2. Decision (owner-approved 2026-11-17)

1. The five Event Store resolution outcomes are defined **exclusively** in the Blocker #4 Persistence and Recovery specification:  
   `FOUND_VALID`, `NOT_FOUND`, `FOUND_INVALID`, `UNAVAILABLE`, `LOOKUP_UNCERTAIN`.  
2. An ISC v2 textual annex **MUST NOT** duplicate the resolution outcome enumeration, definitions, or associated recovery state-machine semantics.  
3. An ISC v2 textual annex **MUST NOT** contradict, weaken, or imply alternative semantics to the Blocker #4 specification. It **MAY** reference the Blocker #4 specification where necessary.  
4. Formal incorporation of this ADR into the repository is a **documentation** task and does **not** by itself authorize an ISC amendment, implementation, or Blocker #4 closure.

---

## 3. Rationale

- Single ownership of resolution vocabulary prevents divergent definitions between ISC prose and the Event Store contract.  
- ISC §10.4 already requires separate specification for retry/recovery after uncertain outcomes; Blocker #4 is that specification class for Event Store persistence/recovery.  
- Cross-reference from ISC is sufficient for discoverability without duplicating normative outcome lists.

---

## 4. Consequences

| Consequence | Detail |
|-------------|--------|
| Positive | Clear ownership; reduced risk of ISC/Blocker #4 semantic drift |
| Positive | ISC remains free of Event Store state-machine detail |
| Constraint | Future ISC edits must not restate the five outcomes as ISC-owned norms |
| Non-consequence | Does not select storage engines, resolve D5.3, or authorize implementation |

---

## 5. Status and boundaries

| Item | Status |
|------|--------|
| Owner approval | **2026-11-17** |
| Repository landing | **Not performed** by this drafting step |
| ISC amendment authorized | **No** |
| Implementation authorized | **No** |
| Blocker #4 | **OPEN** |

---

*End of ADR-WP-3.6.6-B4-002.*
