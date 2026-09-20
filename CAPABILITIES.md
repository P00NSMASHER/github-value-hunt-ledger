# CAPABILITIES

Canonical inventory of what the research system can now credibly build, test, combine or deploy because of validated findings.

A repository is not a capability. A capability is a reusable, evidence-backed ability that may be supported by multiple repositories, datasets, standards or tests.

## Capability schema
Each capability should record:
- Capability ID and name
- Plain-English ability
- Maturity: PROVEN / VALIDATED COMPONENT / BENCHMARKED / WATCH
- Evidence basis
- Primary source components
- Known limitations
- Reusable business targets
- Missing piece
- Next falsifiable test
- Last updated

## Current capability inventory — 2026-09-20

### CAP-001 — Evidence-gated document facts
- Ability: turn messy documents into structured facts while separating extraction confidence from authority and refusing unsafe money-bearing assertions.
- Maturity: VALIDATED COMPONENT.
- Evidence basis: selective-prediction extraction, source-span evidence, arithmetic consistency and review routing.
- Primary components: OmarFaig/Assay; A-Jatin/freight-ratecon-extraction; domain-specific source parsers.
- Reusable targets: Freight Recovery, AP assurance, ScopeSignal, CaptureBrief, contract and entitlement analysis.
- Limitation: calibration is domain/buyer specific; extraction confidence does not establish contractual/legal authority.
- Missing piece: buyer-specific false-accept calibration on held-out documents.
- Next test: freeze a labeled domain corpus and measure auto-accept precision at a fixed false-accept ceiling.

### CAP-002 — Reviewed, versioned identity mastering
- Ability: generate candidate matches, route ambiguity to review, promote a versioned canonical registry and replay exact production identity behavior.
- Maturity: VALIDATED COMPONENT.
- Evidence basis: reviewed registry/promotion/replay contracts plus controlled writeback patterns.
- Primary components: cmdrvl/canon; ChelseaKR/constituent-reconciler; challenger resolvers.
- Reusable targets: CaptureBrief entity/parent identity, freight carrier mastering, AP/vendor mastering, CRM/MDM.
- Limitation: source registries and customer identity data remain separately governed; false merge/split frontier still needs buyer-specific tuning.
- Missing piece: common synthetic benchmark covering aliases, mergers, splits and corrections.
- Next test: candidate generation -> review -> promotion -> pinned lookup -> correction/split -> exact replay.

### CAP-003 — Freight contract/rate authority reconstruction
- Ability: reconstruct controlling freight rate authority across agreements, addenda, rate confirmations, tariffs, effective windows and supersession before calculating expected charges.
- Maturity: BENCHMARKED.
- Evidence basis: versioned rate-card semantics, RateCon source grounding, cross-document authority lineage and freight-specific tariff models.
- Primary components: emoss08/Trenova; vidyesh95/qatoto-backend freight-rate subsystem; A-Jatin/freight-ratecon-extraction.
- Reusable targets: Freight Audit Acceptance Test, managed freight recovery.
- Limitation: customer/carrier contract authority must be proven per population.
- Missing piece: external authorized contract/addendum population.
- Next test: freeze a customer-authorized authority set and require deterministic source/effective-date/supersession resolution.

### CAP-004 — Deterministic freight rerating and exception math
- Ability: independently calculate expected freight charges using effective-dated tariffs, minimums, weight/volume/container bases, accessorial logic and correction/rebill semantics.
- Maturity: BENCHMARKED.
- Evidence basis: freight tariff engines, independent audit oracles and regression fixtures.
- Primary components: sengtha/Kareya-Silo; justicebajaj161/Freight-Audit-Console; specialist correction/rebill oracles.
- Reusable targets: Freight Recovery.
- Limitation: correct arithmetic cannot compensate for incorrect authority.
- Missing piece: blind comparison against a real closed buyer period.
- Next test: independent expected-charge freeze before incumbent output is opened.

### CAP-005 — Physical-event-to-entitlement evidence
- Ability: convert geofence/appointment/arrival/departure evidence into reviewable time-based accessorial facts without collapsing physical truth into money.
- Maturity: PROVEN IN STACK.
- Evidence basis: shipment/appointment/dwell state, evidence hashes and independent authority plane.
- Primary components: kodekinetics79/opstrax-enterprise-build plus licensed freight workflow/authority components.
- Reusable targets: detention/accessorial recovery, field-service proof-to-cash.
- Limitation: physical event truth and contractual entitlement remain separate.
- Missing piece: external blind population carried through realized settlement.
- Next test: reproduce known detention cases plus deliberately unsupported/ambiguous cases and require $0 assertion when entitlement is unresolved.

### CAP-006 — Settlement-grounded recovery attribution
- Ability: distinguish validated finding, issued adjustment/credit, allocated payment/refund/remittance and realized recovery.
- Maturity: PROVEN IN STACK / external outcome pending.
- Evidence basis: settlement state, partial credits/refunds/remittances and recovery certificates.
- Primary components: licensed freight workflow stack, proof obligations, settlement references.
- Reusable targets: freight, AP, commissions, telecom, utilities, marketplace assurance.
- Limitation: realized-dollar attribution requires actual outcome evidence.
- Missing piece: closed external case with complete settlement lineage.
- Next test: one authorized finding from detection through dispute to final credit/payment evidence.

### CAP-007 — Proof obligations and next-best-evidence routing
- Ability: deterministically decide whether evidence is sufficient, explain why it is blocked and identify evidence most likely to change the decision.
- Maturity: VALIDATED COMPONENT.
- Evidence basis: authority, admissibility, independence, time/deadline and contradiction gates.
- Primary components: srthck/trustmesh.
- Reusable targets: recovery/claims, ScopeSignal, compliance, audit readiness.
- Limitation: domain policy provenance must be independently maintained.
- Missing piece: outcome feedback proving suggested evidence changes decisions efficiently.
- Next test: historical blocked cases with counterfactual evidence acquisition.

### CAP-008 — Structured invoice compliance/validation
- Ability: validate structured invoices across multiple e-invoice syntaxes/rule families while preserving explicit not-evaluated and fatal states.
- Maturity: VALIDATED COMPONENT.
- Evidence basis: multi-format validation and independent rule-oracle challengers.
- Primary components: mgilbir/formalis; attestwire/en16931.
- Reusable targets: AP assurance, marketplace settlement, freight structured invoice intake.
- Limitation: official rule packs/schemas and jurisdiction currency must be pinned independently.
- Missing piece: parity corpus across exact rule-pack versions.
- Next test: identical UBL/CII fixtures through independent validators; disagreements route to source review.

### CAP-009 — Schedule verification and conservative repair
- Ability: verify complex schedules against deterministic constraints, explain violations and produce minimum-disruption repairs under hard locks.
- Maturity: VALIDATED COMPONENT.
- Evidence basis: CP-SAT verification/repair, stable rule codes and golden/oracle/load tests.
- Primary components: joschiservice/RosterSpec.
- Reusable targets: WFM, field service, fulfillment, capacity assurance.
- Limitation: domain constraints and labor rules must be authoritative/current.
- Missing piece: incumbent-vs-repair benchmark on a closed period.
- Next test: compare repair distance, violation elimination and operational acceptance.

### CAP-010 — Recovery proof with mandatory negative controls
- Ability: execute real restore drills, verify content/application invariants, measure RTO/RPO and prove the verifier rejects deliberately wrong recovery states.
- Maturity: VALIDATED COMPONENT / integrated stack pending.
- Evidence basis: mixed-engine restore tooling, PITR drills, negative controls, proof freshness and trust validation.
- Primary components: redrillhq/redrill; duke5am/pg-restore-drill; mixed database restore tools; open-eid/SiVa; policy evaluators.
- Reusable targets: Recovery Proof SLA, regulated SaaS/MSP evidence.
- Limitation: production trust policy and buyer/auditor acceptance remain external.
- Missing piece: one integrated multi-engine adversarial matrix.
- Next test: wrong target, missing history, corrupt checksum, service-up/data-wrong, stale proof and trust failures must all be rejected.

### CAP-011 — Government acquisition authority and lineage
- Ability: reconstruct solicitation packet/history, machine-readable FAR authority, federal award/incumbent lineage and entity identifiers from first-party government sources.
- Maturity: VALIDATED DATA/CAPABILITY.
- Evidence basis: official GSA/SAM/USAspending/DATA Act source implementations and schemas.
- Primary components: GSA/srt-fbo-scraper; GSA/GSA-Acquisition-FAR; fedspendingtransparency/usaspending-api; data-act-broker-backend.
- Reusable targets: CaptureBrief, GovCon readiness/decision support.
- Limitation: agency deviations, current applicability and solicitation-specific authority still require explicit source resolution.
- Missing piece: current live solicitation benchmark.
- Next test: 10 live solicitations with packet completeness, rule currency, entity/award joins and manual verification.

### CAP-012 — Permit event versioning and semantic source QA
- Ability: ingest heterogeneous permit feeds into a canonical schema, keep immutable versions/field diffs and detect semantic mapping errors.
- Maturity: VALIDATED COMPONENT.
- Evidence basis: multi-source connectors, idempotent updates, versioning and source-field corrections.
- Primary components: adamleap02/PermitBuild.
- Reusable targets: PermitPlate, development intelligence, property-event triggers.
- Limitation: jurisdiction completeness and field semantics vary materially.
- Missing piece: multi-jurisdiction held-out completeness benchmark.
- Next test: three-jurisdiction source mapping and revision-detection test.

### CAP-013 — Cross-vendor scientific data normalization
- Ability: normalize heterogeneous analytical-instrument exports into structured scientific evidence before orchestration/analysis.
- Maturity: VALIDATED COMPONENT.
- Evidence basis: broad vendor-reader estate and tests.
- Primary components: Benchling-Open-Source/allotropy.
- Reusable targets: lab integration, campaign governance, provenance.
- Limitation: vendor formats/specifications and installed-base fixtures require separate authorization.
- Missing piece: buyer-specific installed-base fidelity study.
- Next test: authorized sample exports across one laboratory's dominant instrument mix.

### CAP-014 — Virtual controller / pre-FAT acceptance
- Ability: derive a virtual controller/tag namespace from authorized industrial configuration and test HMI/SCADA binding/type/fault behavior before hardware is available.
- Maturity: VALIDATED COMPONENT / business benchmark pending.
- Evidence basis: L5K-derived virtual PLC and protocol simulation.
- Primary components: Gaskony-Ignition/module-plc-emulator plus independent protocol implementations.
- Reusable targets: industrial pre-FAT, migration, controls integration.
- Limitation: vendor format/specification and certification authority remain external.
- Missing piece: end-to-end synthetic bind benchmark.
- Next test: planted missing tag, type drift, array/UDT mismatch and fault cases.

### CAP-015 — Prospective, leakage-resistant prediction evidence
- Ability: separate historical model development from immutable prospective predictions so later outcomes cannot rewrite the original call.
- Maturity: VALIDATED COMPONENT / live calibration parity pending.
- Evidence basis: leakage-safe historical interconnection analysis and append-only prospective prediction ledger.
- Primary components: owgreen-dev/grid-crunch; savabs/queue_attrition.
- Reusable targets: Queue Materialization Intelligence and other decision products where hindsight leakage is a major risk.
- Limitation: live production calibration must exactly match validated estimator contract.
- Missing piece: current out-of-time reproduction plus prospective outcome accumulation.
- Next test: freeze model/features/version, register future predictions and score only after resolution deadlines.

### CAP-016 — Money-state integrity / deterministic close truth
- Ability: replay operational billing events into an independent accounting/close truth plane and detect missing, duplicated, unbalanced or period-invalid money states.
- Maturity: WATCH / high-value cross-vertical component.
- Evidence basis: operational billing-event and independent accounting oracle findings in current opportunity portfolio.
- Reusable targets: AP, commissions, telecom, utilities, marketplaces and vertical SaaS finance assurance.
- Limitation: common differential benchmark not yet completed.
- Missing piece: one shared synthetic month with event-to-journal parity and deliberate faults.
- Next test: replay identical month through operational and accounting planes and classify every disagreement.

### CAP-017 — Sequencing operations evidence bridge
- Ability: connect LIMS workflow state to sequencer operational run metrics and provenance without requiring sequence-content analysis, so labs can validate handoffs, workflow transitions and run-health evidence across an installed Clarity/Illumina estate.
- Maturity: VALIDATED COMPONENT / synthetic integration pending.
- Evidence basis: S4 Clarity `StepRunner` workflow-state machinery, official Illumina InterOp metric parsing across instrument generations, and existing provenance infrastructure.
- Primary components: `SemaphoreSolutions/s4-clarity-lib@ad577fff3a3c4c93f4bb898940a0b45268c7dbe7`; `Illumina/interop@015a85ec100c7a770ed0e27ce7fadc6230a38208`; Flowcept as provenance/evidence layer.
- Reusable targets: sequencing-core workflow automation, genomics CRO operations, installed-base lab integration and run-readiness/evidence services.
- Limitation: Clarity/Illumina runtimes, customer instances/data and vendor services remain separately governed; current evidence verifies components, not an end-to-end customer deployment.
- Missing piece: one synthetic workflow-to-run-metrics integration with a forced bad state/handoff and deterministic evidence report.
- Next test: execute a synthetic multi-step QC/pooling/run-prep workflow, attach lawful InterOp fixtures to the same run identity, deliberately break one transition/metric expectation and require the evidence layer to distinguish workflow error, run-metric exception and unknown state.

## Capability promotion rule
Do not add a capability because a repository sounds useful. Promote only when the system can state a falsifiable ability, evidence basis, known limitation and next test.

## Strategic objective
The count of repositories is not the primary KPI. Track:
- validated reusable capabilities;
- capabilities reused across 2+ businesses;
- capabilities that materially reduce build time;
- capabilities that survive independent tests;
- capabilities that contribute to realized customer value.
