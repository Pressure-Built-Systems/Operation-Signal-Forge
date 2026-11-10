# Compliance documentation

**Project:** Operation Signal Forge  
**Nature:** Technical compliance and assurance artifacts — **non-certifying** (not legal advice or regulatory certification)

This folder holds privacy/security-oriented project docs, phase **Compliance Impact Assessments**, and standing guardrails for ZKP and Stage 3.x work.

**Stage 3.5 status:** **CLOSED / PASS** (Gates 5–7). Closure is architectural and verification evidence, **not** production cryptographic certification. Stage 3.6+ runtime proof-path and Authorization Matrix integration remain future work.

---

## Start here (standing references)

| Doc | Purpose |
|-----|---------|
| [zkp-compliance-carry-forward.md](./zkp-compliance-carry-forward.md) | ZKP guardrails; Stage 3.5 CLOSED / PASS; D-3 and 3.6+ deferred |
| [verification-trail-conventions.md](./verification-trail-conventions.md) | How to write and interpret H1 records in `dapp_api/independent_verification.jsonl` |
| [third-party-apis-and-licenses.md](./third-party-apis-and-licenses.md) | External services, licenses, attribution, and deployer obligations |
| [security-assumptions.md](./security-assumptions.md) | Standing security assumptions |

---

## Stage 3.5 architecture & adjudication (outside this folder)

| Artifact | Path |
|----------|------|
| Stage 3.5 formal closure | [`../architecture/stage-3.5/gate-7-protocol-versioning/Stage_3_5_Formal_Closure_Adjudication.md`](../architecture/stage-3.5/gate-7-protocol-versioning/Stage_3_5_Formal_Closure_Adjudication.md) |
| Gate 7 formal adjudication | [`../architecture/stage-3.5/gate-7-protocol-versioning/Gate_7_Formal_Adjudication.md`](../architecture/stage-3.5/gate-7-protocol-versioning/Gate_7_Formal_Adjudication.md) |
| Gate 7 Chain-of-Correction | [`../architecture/stage-3.5/gate-7-protocol-versioning/Gate_7_Chain_of_Correction_Note.md`](../architecture/stage-3.5/gate-7-protocol-versioning/Gate_7_Chain_of_Correction_Note.md) |
| G7-CI ADR (contract integrity) | [`../architecture/stage-3.5/gate-7-protocol-versioning/ADR-G7-Contract-Integrity-and-Seal-Binding.md`](../architecture/stage-3.5/gate-7-protocol-versioning/ADR-G7-Contract-Integrity-and-Seal-Binding.md) |
| G7-CI implementation plan | [`../architecture/stage-3.5/gate-7-protocol-versioning/Gate_7_Contract_Integrity_and_Seal_Binding_Implementation_Plan.md`](../architecture/stage-3.5/gate-7-protocol-versioning/Gate_7_Contract_Integrity_and_Seal_Binding_Implementation_Plan.md) |
| Gate 6 formal adjudication | [`../architecture/stage-3.5/gate-6-cryptographic-agility/Gate_6_Formal_Adjudication.md`](../architecture/stage-3.5/gate-6-cryptographic-agility/Gate_6_Formal_Adjudication.md) |
| Gate 5 re-adjudication | Under `../architecture/stage-3.5/WP-7/Abjudication Reports/` |

**Scope note:** Recorded Stage 3.5 closure covers **Gates 5–7** only. It does not invent or close unrecorded Gates 1–4.

---

## Phase compliance impact assessments

Prefer these **assessment** filenames when citing a phase close:

| Phase | Assessment (canonical where present) |
|-------|--------------------------------------|
| 2.4 | `phase-2.4-compliance-impact-assessment.md.docx` |
| 2.5 | `Phase_2_5_Compliance_Impact_Assessment.docx` |
| 2.6 | `Phase 2.6 Compliance Impact Assessment.docx` |
| 2.7 | `Phase_2.7_Compliance_Impact_Assessment.docx` |
| 2.8 | `Google Gemini's Phase 2.8 Compliance Impact Assessment.docx` |
| 2.9 | `Google Gemini's Phase 2.9 COMPLIANCE IMPACT ASSESSMENT.docx` / `Phase 2.9 Compliance Review.docx` |
| 3.0 | `Phase_3.0_Compliance_Impact_Assessment.md` |
| 3.1 | `Phase_3_1_Compliance_Impact_Assessment.docx` / `Grok Phase 3.1 Compliance Impact Assessment.docx` |
| **3.2** | `Phase_3.2_Compliance_Impact_Assessment.md` |
| **3.3–3.4** | Architecture closed; cite stage packages under `docs/architecture/` |
| **3.5** | Formal closure path above (Gates 5–7 CLOSED / PASS) |

Related architecture packages live under `docs/architecture/zkp/` and `docs/architecture/identity/`. Milestones live under `docs/milestones/`.

Assessment file locations:

- [`compliance/`](./compliance/) — Phase 2.4, 2.5, 2.6, 2.8, and 2.9 compliance assessments.
- [`compliance/compliance/`](./compliance/compliance/) — Phase 2.7 compliance assessment.
---

## Verification evidence (not in this folder)

| Artifact | Location |
|----------|----------|
| Independent verification log | `dapp_api/independent_verification.jsonl` |
| Level / evidence gates | `identity_runtime/verification_levels.py` |
| Record API | `identity_runtime/independent_verification.py` |
| I2 Level 3 environment policy | `docs/architecture/identity/phase-2.9-i2-level3-environment-policy.md` |

---

## Out of scope for this index

- Claiming certification against named regulations  
- Completing post-integration proof-on-path evidence before a proof exists on the path  
- Replacing architecture ADRs or phase milestones