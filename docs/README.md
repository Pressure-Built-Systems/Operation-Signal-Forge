# Operation Signal Forge — Documentation Guide

Welcome to the Operation Signal Forge documentation directory.

This directory contains the project's architecture documentation, technical decisions, compliance material, audit records, engineering references, and published milestones.

The purpose of this guide is to make those materials easier to locate. It is a navigation index, not a replacement for the underlying technical records.

---

## Documentation Map

| Directory | Purpose |
| --------- | ------- |
| `architecture/` | Architecture documentation, design principles, architecture decision records, stage-specific work, specifications, and technical design references. |
| `audits/` | Audit reports and independent verification records. |
| `briefs/` | Project briefs and supporting overview documents. |
| `compliance/` | Compliance assessments, security assumptions, verification conventions, and compliance-related references. |
| `diagrams/` | Architecture and system diagrams. |
| `engineering/` | Engineering documentation and implementation references. |
| `milestones/` | Published technical milestone reports and associated evidence registers. |
| `roadmap/` | Project roadmaps and planned development work. |

---

## Where to Start

### Architecture and technical decisions

Start with `architecture/` for the system's design and technical direction.

Important areas include:

- `architecture/stage-3.5/` — Stage 3.5 closure material. Gates 5–7 are **CLOSED / PASS / FROZEN**.
- `architecture/stage-3.6/` — Stage 3.6 architecture and implementation work. Stage 3.6 remains **OPEN**.
- `architecture/adr/` — Architecture Decision Records and documented technical decisions.

Use `architecture/adr/` as the preferred location for current and future ADRs. The repository-root `Architecture Decision Records/` directory contains legacy records.

### Audits and verification

Start with `audits/` for audit reports and independent verification material.

Audit reports document examination and verification results; milestone reports publish an owner-recognized body of work and its associated evidence.

For verification-trail conventions and related compliance guidance, consult `compliance/`.

### Published milestones

Start with `milestones/` for published project milestones.

The November 2026 WP-3.6.6 R2 library-boundary publication is located at:

`milestones/2026-11-wp-3-6-6-r2-library-boundary/`

It contains:

- `Technical_Milestone_Report.md`
- `Evidence_and_Claims_Register.md`

**Important status distinction:** Publication of a milestone records a specific body of work and its evidence. It does not, by itself, establish completion of the associated work package or closure of an entire development stage.

### Compliance and security references

Start with `compliance/` for compliance assessments, security assumptions, third-party API and license information, and verification conventions.

Note: some older assessments live under nested `compliance/compliance/` paths. Prefer the top-level documents and the guidance in `compliance/compliance/README.md` when both exist.

Consult the individual documents for their specific scope and authority.

---

## Project Status Reference

The following status distinctions are important when navigating the documentation:

| Area | Status |
| ---- | ------ |
| Stage 3.5, Gates 5–7 | **CLOSED / PASS / FROZEN** |
| Stage 3.6 | **OPEN** |
| WP-3.6.6 R2 library-boundary milestone | **Published** |
| WP-3.6.6 | **OPEN** |

A published report, an accepted technical finding, a completed audit, and formal stage closure are distinct forms of evidence. Do not interpret one as automatically establishing another.

---

## Navigating the Documentation

A few conventions will help when exploring this directory:

1. Use the relevant stage or work-package directory when looking for technical implementation and architecture records.
2. Use `audits/` when looking for independent audit and verification reports.
3. Use `milestones/` when looking for formally published milestone reports and evidence registers.
4. Use `compliance/` when looking for compliance requirements, security assumptions, and verification conventions.
5. Consult the source record before relying on a status, decision, or technical conclusion.

When in doubt, follow the references in the relevant architecture decision, audit report, or milestone record rather than assuming that similarly named documents have the same authority.

---

This guide is intended to provide a practical entry point into the documentation tree. It does not supersede architecture decisions, compliance requirements, audit findings, or formally published evidence.
