# Architecture documentation

Architecture records for Operation Signal Forge (OSF / PANGEA): stage packages, architecture decision records, identity and authorization design, and related technical specifications.

This index is a navigation aid only. It does not redefine Stage or Work Package status, close blockers, or supersede formal adjudications, ADRs, audits, or milestone evidence.

**Start here**

| Need | Go to |
|------|--------|
| Frozen Stage 3.5 baseline (Gates 5–7) | [stage-3.5/](./stage-3.5/) |
| Active Stage 3.6 work | [stage-3.6/](./stage-3.6/) |
| Current and future ADRs | [adr/](./adr/) |
| Identity and authorization architecture | [identity/](./identity/) |
| Phase 2 identity lifecycle archive | [phase-2/](./phase-2/) |
| Project documentation map | [../README.md](../README.md) |

---

## Stage 3.5 — Frozen baseline

**Status: CLOSED / PASS / FROZEN** (Gates 5–7).

Stage 3.5 closure is architectural and verification evidence. It is **not** production cryptographic certification. Recorded closure covers **Gates 5–7** only; it does not invent or close unrecorded Gates 1–4.

| Record | Path |
|--------|------|
| Stage 3.5 formal closure adjudication | [stage-3.5/gate-7-protocol-versioning/Stage_3_5_Formal_Closure_Adjudication.md](./stage-3.5/gate-7-protocol-versioning/Stage_3_5_Formal_Closure_Adjudication.md) |
| Stage 3.5 milestone record | [stage-3.5/Stage_3.5_Milestone_Record.md](./stage-3.5/Stage_3.5_Milestone_Record.md) |
| Gate 7 formal adjudication | [stage-3.5/gate-7-protocol-versioning/Gate_7_Formal_Adjudication.md](./stage-3.5/gate-7-protocol-versioning/Gate_7_Formal_Adjudication.md) |
| Gate 7 chain-of-correction note | [stage-3.5/gate-7-protocol-versioning/Gate_7_Chain_of_Correction_Note.md](./stage-3.5/gate-7-protocol-versioning/Gate_7_Chain_of_Correction_Note.md) |
| ADR-G7 protocol versioning | [stage-3.5/gate-7-protocol-versioning/ADR-G7-Protocol-Versioning-and-Interoperability.md](./stage-3.5/gate-7-protocol-versioning/ADR-G7-Protocol-Versioning-and-Interoperability.md) |
| ADR-G7 contract integrity and seal binding | [stage-3.5/gate-7-protocol-versioning/ADR-G7-Contract-Integrity-and-Seal-Binding.md](./stage-3.5/gate-7-protocol-versioning/ADR-G7-Contract-Integrity-and-Seal-Binding.md) |
| Gate 7 CI implementation plan | [stage-3.5/gate-7-protocol-versioning/Gate_7_Contract_Integrity_and_Seal_Binding_Implementation_Plan.md](./stage-3.5/gate-7-protocol-versioning/Gate_7_Contract_Integrity_and_Seal_Binding_Implementation_Plan.md) |
| Gate 6 formal adjudication | [stage-3.5/gate-6-cryptographic-agility/Gate_6_Formal_Adjudication.md](./stage-3.5/gate-6-cryptographic-agility/Gate_6_Formal_Adjudication.md) |
| Gate 5 / WP-7 adjudication material | [stage-3.5/WP-7/](./stage-3.5/WP-7/) |

Related compliance note on Stage 3.5 status: [../compliance/README.md](../compliance/README.md).

---

## Stage 3.6 — Active development

**Status: OPEN.**

WP-3.6.6 remains **OPEN**. Published R2 work demonstrates the **library boundary only**. External application composition root is **NOT DEMONSTRATED**. R2 publication does **not** establish WP-3.6.6 completion or Stage 3.6 closure.

Standing boundaries (do not invert):

- The Authorization Matrix remains the sole authorizer.
- Proof validity does not establish authorization.
- dapp_api remains a façade unless and until a dedicated Stage 3.6 service is explicitly authorized.

| Area | Path |
|------|------|
| Stage 3.6 directory | [stage-3.6/](./stage-3.6/) |
| Stage 3.6 stub notes | [stage-3.6/README.md](./stage-3.6/README.md) |
| Roadmap review disposition | [stage-3.6/Stage_3_6_Architecture_Roadmap_Review_Disposition.md](./stage-3.6/Stage_3_6_Architecture_Roadmap_Review_Disposition.md) |
| Clarification Batch 1 (WP-3.6.1 / 3.6.2) | [stage-3.6/Stage_3_6_Clarification_Batch_1_WP_3_6_1_and_3_6_2.md](./stage-3.6/Stage_3_6_Clarification_Batch_1_WP_3_6_1_and_3_6_2.md) |
| Clarification Batch 2 (WP-3.6.4) | [stage-3.6/Stage_3_6_Clarification_Batch_2_WP_3_6_4.md](./stage-3.6/Stage_3_6_Clarification_Batch_2_WP_3_6_4.md) |
| Clarification Batch 3 (WP-3.6.3) | [stage-3.6/Stage_3_6_Clarification_Batch_3_WP_3_6_3.md](./stage-3.6/Stage_3_6_Clarification_Batch_3_WP_3_6_3.md) |
| WP-3.6.6 package (incl. Blocker 3 adjudication) | [stage-3.6/WP-3.6.6/](./stage-3.6/WP-3.6.6/) |
| Post-R2 owner adjudication | [stage-3.6/WP-3.6.6/Blocker 3/Phase A Remediation/Adjudication/OSF_WP_3_6_6_E3_A1_D1_Post_R2_Owner_Adjudication.md](./stage-3.6/WP-3.6.6/Blocker%203/Phase%20A%20Remediation/Adjudication/OSF_WP_3_6_6_E3_A1_D1_Post_R2_Owner_Adjudication.md) |
| Post-R2 disposition summary | [stage-3.6/WP-3.6.6/Blocker 3/Phase A Remediation/Adjudication/OSF_WP_3_6_6_E3_A1_D1_Post_R2_Disposition_Summary.md](./stage-3.6/WP-3.6.6/Blocker%203/Phase%20A%20Remediation/Adjudication/OSF_WP_3_6_6_E3_A1_D1_Post_R2_Disposition_Summary.md) |
| L3 audit report | [stage-3.6/OSF_Stage_3_6_L3_Audit_Report.md](./stage-3.6/OSF_Stage_3_6_L3_Audit_Report.md) |

**Published R2 milestone (library boundary only)** — under milestones, not this folder:

- [../milestones/2026-11-wp-3-6-6-r2-library-boundary/Technical_Milestone_Report.md](../milestones/2026-11-wp-3-6-6-r2-library-boundary/Technical_Milestone_Report.md)
- [../milestones/2026-11-wp-3-6-6-r2-library-boundary/Evidence_and_Claims_Register.md](../milestones/2026-11-wp-3-6-6-r2-library-boundary/Evidence_and_Claims_Register.md)
- Index: [../milestones/README.md](../milestones/README.md)

Note: `stage-3.6/Stage_3_6_Architecture_Roadmap_BASELINE_FREEZE.md` exists on main but is empty (0 bytes). Prefer the review disposition and clarification batches for roadmap context.

---

## Architecture Decision Records

Preferred location for **current and future** ADRs:

- [adr/](./adr/)

Examples present under `adr/` include recovery authority model, risk-based verification levels, Starlink sensor module, Capability Layer independence, and AgentForge integration plan. Consult each ADR for its own scope and authority.

**Legacy location (do not treat as invalid solely by path):**

- Repository root: [`Architecture Decision Records/`](../../Architecture%20Decision%20Records/)  
  Signpost: [`Architecture Decision Records/README.md`](../../Architecture%20Decision%20Records/README.md)

Do not move or duplicate legacy ADRs as part of navigation work.

---

## Identity and authorization

| Document | Path |
|----------|------|
| Authorization Matrix | [identity/Authorization Matrix (1).docx](./identity/Authorization%20Matrix%20(1).docx) |
| Authorization Workflow Specification | [identity/Authorization Workflow Specification.docx](./identity/Authorization%20Workflow%20Specification.docx) |
| Identity & Authorization Architecture Specification | [identity/Identity & Authorization Architecture Specification.docx](./identity/Identity%20%26%20Authorization%20Architecture%20Specification.docx) |
| Credential lifecycle governance | [identity/credential- lifecycle- governance.md.docx](./identity/credential-%20lifecycle-%20governance.md.docx) |
| Trust registry | [identity/trust-registry.md.docx](./identity/trust-registry.md.docx) |

Related: recovery and verification ADRs under [adr/](./adr/); Phase 2 identity specs under [phase-2/](./phase-2/).

---

## Historical architecture material

| Area | Path | Note |
|------|------|------|
| Phase 2 identity lifecycle & assurance | [phase-2/](./phase-2/) | Archive index in [phase-2/README.md](./phase-2/README.md) |
| Design principles | [design-principles/](./design-principles/) | Supporting principles |
| Checklists | [checklists/](./checklists/) | Architecture checklists |
| Dashboard architecture | [dashboard/](./dashboard/) | Dashboard-related records |
| Architecture diagrams (under this tree) | [diagrams/](./diagrams/) | Distinct from `docs/diagrams/` |
| Top-level architecture files | (this directory) | e.g. Identity Layer Expansion Gap Analysis, trust-registry governance |

These paths provide historical or supporting context. Do not assume a record is obsolete or non-authoritative solely because it sits outside `stage-3.5/` or `stage-3.6/`. Consult the document for its own scope.

---

## Related documentation outside architecture/

| Resource | Path |
|----------|------|
| Documentation landing page | [../README.md](../README.md) |
| Compliance index | [../compliance/README.md](../compliance/README.md) |
| Milestone index (incl. R2) | [../milestones/README.md](../milestones/README.md) |
| Audits | [../audits/](../audits/) |

---

This index does not supersede formal stage closure, ADR decisions, owner adjudications, audit findings, or published milestone evidence.
