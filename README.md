##**Operation Signal Forge**

Operation Signal Forge (OSF) is a ground-sensor fusion and decision-support platform for search-and-rescue (USAR) operations. Multiple sensor modalities feed a deterministic Fusion Engine, while separate capability, identity, and authorization layers support accountable operational workflows.

The platform is evolving toward **PANGEA**: a broader humanitarian application architecture built around a Core Capability Layer, Trust Layer, and Identity Layer. Its purpose is to support interoperable, privacy-conscious collaboration without allowing advisory intelligence or cryptographic verification to assume operational authority.

---

## Accountable Autonomous Intelligence

**Accountable Autonomous Intelligence (AAI)** is a foundational architectural commitment of Operation Signal Forge.

The objective is to let automated systems assist human operations without becoming unaccountable decision-makers. This requires more than placing a human somewhere in an automated workflow: it requires explicit infrastructure boundaries between intelligence, evidence, identity, and permission.

| Principle | Architectural commitment |
|-----------|--------------------------|
| **Deterministic fusion** | The Fusion Engine scores and combines sensor inputs using inspectable logic. Fusion results do not determine who may act. |
| **Advisory autonomy** | AgentForge and the capability layer represent advisory capability design: investigating, synthesizing, and recommending without independently commanding operations or writing fusion state. Implementation maturity varies by component. |
| **Identity and trust** | Credentials and verification establish identity, trust, and eligibility context. They do not independently grant operational permission. |
| **Authorization isolation** | The Authorization Matrix remains the sole operational authorizer. Missing, failed, or ambiguous verification must never default to permission. |
| **Auditability** | Evidence and decision records are designed to support reconstruction of the path from operational request through verification and authorization. |
| **Human accountability** | Operators retain command responsibility and update field search status. The platform supports USAR decision-making; it does not replace operational command. |

**Guiding principle:** Sensors and models may propose; infrastructure enforces the separation of fusion, advice, proof, and permission.

AAI describes the architecture the platform is designed to uphold. It should **not** be interpreted as a claim that every PANGEA or AgentForge capability is already implemented or production-ready.

---

## What OSF does

| Layer | Responsibility |
|-------|----------------|
| **Sensors → Fusion** | Radar, thermal, acoustic, celltower, and Starlink inputs are normalized and scored, then fused into a probability per geohash cell. |
| **Capability layer** | Advisory workflows and reusable capabilities, separated from fusion and authorization authority. |
| **Identity and authorization** | DID/VC identity, trust information, scopes, and authorization context for capability requests. |
| **Human-facing application** | DApp prototype and dashboard interfaces for operational visibility and workflows. |
| **Verification** | Versioned protocol and scheme identity, verifier boundaries, and eligibility evidence. Verification does not grant permission. |

---

## Core fusion path
Field sensors

│

▼

Sensor ingestion and normalization

│

▼

Deterministic Fusion Engine

│

▼

Probability per geohash cell

│

▼

DynamoDB persistence

│

├──────────────► Dashboard / Leaflet heatmap

│

└──────────────► SNS / notification pathways

Geohash cells provide stable spatial keys so repeated observations of the same area can contribute to an evolving detection probability rather than creating unrelated points.

### Sensor and fusion notes

- **Radar, thermal, and acoustic** — modality-specific scoring, with corroboration when independent modalities agree.
- **Starlink** — dedicated sensor module; the Fusion Engine orchestrates rather than embedding the integration.
- **Celltower** — optional OpenCellID enrichment, not a substitute for ground-truth GNSS.
- **Scoring weights** — heuristic and subject to field calibration before operational use of high-confidence thresholds.

OSF is a **triage aid**, not a substitute for trained search teams, canine units, structural safety protocols, or established USAR procedures.

---

## Architecture principles

The platform maintains several boundaries:

- **Fusion is separate from authorization.** Sensor confidence does not grant an operator permission to act.
- **Advice is separate from command.** Automated capabilities can support investigation and recommendations without acquiring operational authority.
- **Identity is separate from permission.** Identity and eligibility evidence provide context to an authorization decision.
- **Proof validity ≠ authorization.** A valid cryptographic proof can support an eligibility claim; only the Authorization Matrix grants operational permission.
- **Failure is not permission.** Missing, unsupported, invalid, or ambiguous verification must not silently become an ALLOW decision.

These boundaries are architectural requirements. Their implementation and verification status are tracked in the stage and work-package records.

---

## PANGEA and quantum-resilient design

PANGEA is designed with cryptographic agility and future migration in mind. OSF's architecture separates cryptographic contracts and versioned scheme identity from application and domain semantics.

This is a **readiness and architectural flexibility** position, not a claim that any component is quantum-proof or certified for post-quantum security.

Stage 3.5 established architecture and verification evidence for cryptographic abstraction, scheme agility, and protocol versioning. The applicable closure conditions use **mock adapters**; **no production cryptographic soundness claim is made**. **No post-quantum certification claim is made.**

A future post-quantum migration would require selecting, integrating, and independently evaluating an appropriate construction. Architectural agility can reduce migration coupling; it does not make that work automatic.

---

## Development status

| Area | Current status |
|------|----------------|
| **Stage 3.5 — Gates 5–7** | CLOSED / PASS / FROZEN — architecture and verification evidence only; not production cryptographic certification. |
| **Stage 3.6 roadmap** | Review disposition and clarification batches published; baseline-freeze file present but empty. Implementation and verification work remain **OPEN**. |
| **WP-3.6.5 — AuditPort** | Contract established; development implementation work has been exercised in a non-production, single-process/single-writer context. |
| **WP-3.6.6 — Freshness and Replay** | OPEN. |
| **WP-3.6.6 R2 library-boundary milestone** | Published. Demonstrates the **library boundary only**. |
| **External composition-root integration** | **NOT DEMONSTRATED**. |
| **Stage 3.6 overall** | **OPEN**. |

The R2 publication records a bounded technical milestone and its evidence. It does **not** establish completion of WP-3.6.6, demonstrate external composition-root integration, or close Stage 3.6.

See [`docs/architecture/stage-3.6/`](docs/architecture/stage-3.6/) (review disposition and clarification batches). Do not treat the empty `Stage_3_6_Architecture_Roadmap_BASELINE_FREEZE.md` as a populated freeze record.

For Stage 3.5 formal closure, see the [Stage 3.5 Formal Closure Adjudication](docs/architecture/stage-3.5/gate-7-protocol-versioning/Stage_3_5_Formal_Closure_Adjudication.md).

---

## Documentation

The documentation indexes are the preferred starting points for technical records, decisions, audits, and implementation references.

| Index | Path |
|-------|------|
| Documentation Guide | [docs/README.md](docs/README.md) |
| Architecture | [docs/architecture/README.md](docs/architecture/README.md) |
| Audits | [docs/audits/README.md](docs/audits/README.md) |
| Compliance | [docs/compliance/README.md](docs/compliance/README.md) |
| Milestones | [docs/milestones/README.md](docs/milestones/README.md) |
| Engineering | [docs/engineering/README.md](docs/engineering/README.md) |
| Diagrams | [docs/diagrams/README.md](docs/diagrams/README.md) |
| Briefs | [docs/briefs/README.md](docs/briefs/README.md) |

Indexes provide navigation, not independent technical authority. Consult the underlying decision, specification, audit, or milestone record for the authoritative scope and status of a claim.

---

## Repository overview

| Path | Purpose |
|------|---------|
| `lambda/` | Fusion engine, sensor modules, and dashboard API. |
| `capability_layer/` | Advisory capabilities and ports/adapters. |
| `identity_runtime/` | Identity, trust, presentation, and verification runtime. |
| `dapp/` and `dapp_api/` | Human-facing application prototype and API. |
| `Daytona/` | Non-production sandbox and test material. |
| `infra/` | Infrastructure and deployment templates. |
| `docs/` | Architecture, audits, compliance, engineering, milestones, and supporting documentation. |
| `dashboard/` | Operational dashboard and map interface. |

---

## Operational limitations

- Sensor scoring is heuristic and requires field calibration.
- A detection probability is a triage signal, not confirmation of a person or a declaration that an area is clear.
- Cell status (`unassigned` → `searching` → `cleared` / `confirmed`) is updated by operators.
- Structural safety and secondary-collapse risks require independent assessment.
- Operational decisions must follow the responsible organization's established USAR command and safety procedures.

---

## License

Apache-2.0. See the root [`LICENSE`](LICENSE) and [third-party API and license references](docs/compliance/third-party-apis-and-licenses.md).
