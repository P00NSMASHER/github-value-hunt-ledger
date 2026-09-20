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
- Ability: generate candidate matches, preserve durable positive/negative/unsure judgements, route ambiguity to review, correct mistaken clusters through reversible split/remove operations, promote a versioned canonical registry and replay exact production identity behavior.
- Maturity: VALIDATED COMPONENT.
- Evidence basis: reviewed registry/promotion/replay contracts, SQL-backed judgement history with explicit negative blockers and reversible clustering, plus controlled writeback patterns.
- Primary components: `cmdrvl/canon@45e9702ba7f3874c073134c1a6fb74500232b6a1`; `opensanctions/nomenklatura@844dba09fafc8512dc3ce241f44aa5415b367029`; ChelseaKR/constituent-reconciler; challenger resolvers.
- Reusable targets: CaptureBrief entity/parent identity, freight carrier mastering, AP/vendor mastering, CRM/MDM.
- Limitation: source registries/customer identities and OpenSanctions/third-party datasets remain separately governed; false merge/split frontier still needs buyer-specific tuning; Nomenklatura is not itself a promoted-version production registry and has a noncanonical-cluster edge case to characterize.
- Missing piece: common synthetic benchmark covering aliases, explicit non-matches, mergers, mistaken merges, splits, referent additions and corrections across judgement memory plus promoted registry replay.
- Next test: candidate generation -> explicit reject -> merge -> referent addition -> remove/explode mistaken cluster -> reviewed promotion -> pinned lookup -> exact replay; an explicit negative judgement must block an unsupported later merge.

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
- Ability: reconstruct solicitation packet/history, deterministic source/amendment versions and diffs, machine-readable FAR authority, federal award/incumbent lineage and entity identifiers from first-party government sources while distinguishing source/history failure from “no change.”
- Maturity: VALIDATED DATA/CAPABILITY.
- Evidence basis: official GSA/SAM/USAspending/DATA Act source implementations and schemas, plus an independently verified procurement-history architecture showing stateful version hydration, deterministic field-level change events, idempotent reruns and explicit history/source failures.
- Primary components: GSA/srt-fbo-scraper; GSA/GSA-Acquisition-FAR; fedspendingtransparency/usaspending-api; data-act-broker-backend; `slicedearth/contract-delta-au@630d1903507e6f5e47adaf1c690c9d6d4363af54` as a version-lineage architecture pattern only.
- Reusable targets: CaptureBrief, GovCon readiness/decision support.
- Limitation: agency deviations, current applicability and solicitation-specific authority still require explicit source resolution; `contract-delta-au` implements Australian procurement semantics and does not establish U.S. SAM/FAR authority.
- Missing piece: current live solicitation benchmark with planted amendment-order/history/source-failure cases.
- Next test: 10 live solicitations with packet completeness, deterministic amendment/version ordering, idempotent reruns, explicit source/history failure, rule currency, entity/award joins and manual verification.

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

### CAP-014 — Virtual industrial endpoint / pre-FAT acceptance
- Ability: derive virtual industrial endpoints from authorized controller configuration or a frozen protocol profile and test binding/type/state/error behavior before physical hardware is available.
- Maturity: VALIDATED COMPONENT / business benchmark pending.
- Evidence basis: L5K-derived virtual PLC namespace/type behavior plus an independent stateful SECS/GEM host+equipment implementation over real HSMS/TCP with communication/control state, variables/constants, event reports, alarms, remote commands, bounded spooling and error behavior.
- Primary components: `Gaskony-Ignition/module-plc-emulator@518f56b55566d7e20f19ce64003cdae45a08edc8`; `CodeMaru-Dreamine/Dreamine.Gem@82604d6f03c1e95e0558de5c757989b27cd4a3d6`; independent protocol clients/implementations for differential acceptance.
- Reusable targets: industrial pre-FAT, migration, controls integration, semiconductor host/equipment integration.
- Limitation: vendor formats/specifications, SEMI standards/current equipment profiles and formal certification/conformance authority remain external; same-family agreement is not independent proof.
- Missing piece: end-to-end synthetic bind plus independent cross-implementation protocol-state benchmark.
- Next test: planted missing tag/type/array/UDT faults plus a rights-clean frozen SECS/GEM dialogue/error corpus run against Dreamine.Gem and one unrelated implementation; classify every disagreement without inferring formal conformance.

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

### CAP-018 — Provider-to-bank settlement ambiguity and payout-proof state machine
- Ability: move money safely from payout intent through provider send state into independently observed bank/payroll settlement and later counter-events, while refusing ambiguous mappings, unsafe retries and unsupported finality.
- Maturity: VALIDATED COMPONENT / synthetic provider-to-bank benchmark pending.
- Evidence basis: tested claim-before-send and unknown-outcome hold; definite-failure release; provider payout identity and settled amount/currency; bank-derived transaction/reference surfaces; exact-vs-ambiguous-vs-not-found return linkage; later return/reversal lineage; and concurrent/idempotent protection.
- Primary components: `spree/spree@2a419d42e86dea30a69a3c5b7764185cea132b3f`; `getcoherence/openpartner@eeff532ee758dc6221b4d03af852e5705a2328fb`; `Modern-Treasury/modern-treasury-python@406f354a06a98060df0c9f4c242fe56cc65e1526` as the strongest current bank-derived observation bridge; `szapata85/ACHInterbank@395a359230eff35e49cc196b49995ed4c49509b9` as an Exact/Ambiguous/NotFound return-correlation oracle; `moov-io/ach` for post-success return-entry lineage.
- Reusable targets: commission/affiliate payouts, marketplaces, rebates, vendor/partner disbursements and other payment workflows where timeout/unknown-result, weak reconciliation or later returns can create duplicate or falsely final money states.
- Limitation: Modern Treasury's hosted API/bank connections/service data and all bank/payroll data remain external; its server-side automatic reconciliation algorithm is not public; ACH trace/reference values are not inherently unique economic identities; feed freshness/completeness is provider/bank specific; ACHInterbank is a controlled-UAT/reference architecture and its jurisdiction-specific normative materials remain separately governed. No external buyer outcome has yet been recorded.
- Missing piece: one provider-neutral corpus proving provider-ID -> network/reference -> independently observed transaction -> later return/reversal under explicit source-health semantics, with ambiguity and missing coverage remaining non-final.
- Next test: execute EXP-003 with duplicate trace, substring/fuzzy reference collision, equal-total swapped identities, unparseable amount, stale cursor, provider-completed/bank-absent, bank-posted-then-returned, duplicate return and unavailable-source cases. Only exact unique linkage inside a verified observation window may advance finality.

## Capability promotion rule
Do not add a capability because a repository sounds useful. Promote only when the system can state a falsifiable ability, evidence basis, known limitation and next test.

## Strategic objective
The count of repositories is not the primary KPI. Track:
- validated reusable capabilities;
- capabilities reused across 2+ businesses;
- capabilities that materially reduce build time;
- capabilities that survive independent tests;
- capabilities that contribute to realized customer value.

<!-- INTEGRATOR-R11-2026-09-20T0856-0400 -->
## Integration delta — 2026-09-20 08:56 ET
- **CAP-006 realized-settlement proof strengthened:** `lailarallc/edi-reconciliation-tool@11740303...` contributes planted-fault 812/820/remittance-grain tests. The accepted capability remains stricter than the repository: realized recovery requires an issued adjustment plus uniquely attributable allocated credit/refund/remittance; ambiguous partial/many-to-many allocation remains REVIEW / $0 realized.
- **AP trusted-fact replay strengthened:** `project-minigraf/minigraf@ccdc85e...` adds tested bitemporal transaction-time/valid-time replay, enabling an AP finding to be reproduced against the exact facts known when it was issued and against later corrected validity state. `mujeeb-k/AP-Three-Way-Matching-Agent@c15a4cc...` adds useful PO/GR/invoice exception semantics but its source-outage→empty/null behavior is a fail-open negative case, not authority truth.
- **CAP-007 Scope/change evidence strengthened:** `egovernments/DIGIT-Works@7c44e963...` adds contract-bounded physical measurement: active accepted baseline, estimate-line identity, time window and cumulative quantity ceiling. Measurement validity remains distinct from entitlement, certified bill and paid outcome.
- **CAP-011 CaptureBrief source/version truth strengthened:** official SAM documentation now proves latest opportunity search is structurally not full amendment history; complete packets require a separate version/history plane with explicit lag/access states. Subaward Published/Deleted semantics extend award/entity lineage into reported team networks.
- **CAP-014 industrial pre-FAT strengthened:** `bparzella/secsgem@59a5242...` provides the first mature unrelated SECS/GEM implementation family for differential testing against Dreamine.Gem; certification remains separate.
- **CAP-018 payout money-state integrity strengthened:** `chase-sets/chase-sets@32aa260...` adds durable provider-operation/idempotency ownership, stale/lost-webhook reconciliation and post-payment receivable/clawback semantics. The remaining missing edge is actual bank/payroll settlement and return/reversal evidence after provider success.
- **Cross-domain temporal capability added at component level:** bitemporal facts now give recovery/procurement/scope systems a reusable mechanism to distinguish transaction-time knowledge from real-world valid time without destructive correction. Keep below standalone MASTER status until a live experiment demonstrates material decision/audit value.

<!-- INTEGRATOR-R11-SHADOW-COM-2026-09-20T0914-0400 -->
## Revenue-to-receivable trace capability delta — 2026-09-20
- `cyber-entrepreneur/wingcaster@0d97a4ab...` materially strengthens the internal transaction chain around effective-dated contract/price authority, immutable rating facts, invoice close, idempotent allocation/reversal and reconciliation.
- Treat this as a **VALIDATED COMPONENT**, not external money truth. Its current end-to-end proof is internally coherent but partially circular because contract rows, payment records and reconciler checks live inside the same authority domain.
- Cross-product reuse: SaaS Revenue Integrity, contract billing, commission/payout close and AP/AR trace diagnostics.
- Missing piece: externally sourced signed/order-system contract amendments plus PSP/bank settlement and later return/reversal evidence that the system under test cannot manufacture.
- Next falsifiable test: inject frozen external contract and settlement evidence with deliberate contradictions; the internal loop must fail closed and surface the mismatch rather than preserve an all-green result.

<!-- INTEGRATOR-R12-2026-09-20T0946-0400 -->
## Capability delta — 2026-09-20 09:46 ET

### CAP-019 — Source-authority observation receipts
- Ability: prove whether a queried source/object/window is `PRESENT`, `VERIFIED_EMPTY` or `UNAVAILABLE`, and advance source cursors only after durable downstream commit so absence cannot be manufactured by connector failure.
- Maturity: **VALIDATED COMPONENT**.
- Evidence basis: `bsaffel/moneybin@fd34d999...` tests successful zero-result snapshot receipts while failed/no-window sources receive no receipt; `scolladon/dataset-loader@5039257...` tests finalize-before-watermark, abort/no-watermark on failures and partial/all-failed exit codes.
- Reusable targets: AP Leakage, CaptureBrief, freight/settlement imports, permit/public-data intelligence and any money-bearing source adapter.
- Limitation: neither component alone supplies a universal whole-run completeness protocol; moneybin consumers must still fail closed on per-source partial failure and dataset-loader does not durably attest an empty read.
- Missing piece / next test: one synthetic ERP PO/GR lifecycle with source receipts, cursor identity and bitemporal corrections; transport/auth failure must never produce `VERIFIED_EMPTY`, and cursor advancement must occur only after exact source query plus durable target state are proven.

### Cross-capability upgrades
- **CAP-006 Settlement-grounded recovery attribution:** add PayOps-style immutable claim/event identity, exact unique auto-allocation and one-use persistence; reviewed split/partial settlement becomes explicit pairwise allocation edges with residual capacity and reversible history. A deterministic subset-sum/tie-break is only a proposal, never settlement proof.
- **CAP-010 Recovery proof:** add Mukuroji's DynamoDB/S3 historical-state/semantic verification and nearai/pg-backup's verifier-self-test requirement. The verifier itself must be mutation/fault tested; a broken assertion helper that yields green is a failed recovery-proof system.
- **CAP-011 Government acquisition authority/lineage:** add DHS APFS source-native dated change history and SAM official operational-health intervals. Preserve source event time separately from collector observation time; a known degraded source interval taints negative/completeness conclusions.
- **CAP-014 Industrial pre-FAT:** the Dreamine↔secsgem shared tested intersection now supports a frozen 10-case differential corpus plus `EC-ATOMIC-PROBE` (valid first EC update + invalid second) predicted to expose all-or-nothing vs partial-mutation semantics. Repository collection is no longer the bottleneck; execution is.
- **CAP-017 Sequencing operations evidence bridge:** add `scilifelab_epps` as the concrete Clarity process→flowcell/run-directory→RunParameters/RunInfo→InterOp→Clarity-writeback implementation and `samplesheet-parser` as an independent pre-run compatibility/diff gate. Missing behavioral regression/evidence packaging remains explicit.
- **CAP-018 Provider-settlement ambiguity / payout proof:** add `moov-io/ach` post-success Return Entry/reversal lineage and statement-normalizer bank-readback input. Provider `paid` is now explicitly revocable until external network/bank evidence plus later-return window/source freshness are accounted for.

<!-- INTEGRATOR-R13-2026-09-20T1207-0400 -->
## Capability delta — 2026-09-20 12:07 ET
- **CAP-018 external-finality gap materially narrowed:** `Modern-Treasury/modern-treasury-python@406f354a...` supplies bank-derived Transaction/Transaction-Line-Item and Return/Reversal lineage around provider/payment-order references; `szapata85/ACHInterbank@395a359...` independently supplies fail-closed `Exact / Ambiguous / NotFound` return correlation with no money-state mutation under ambiguity. The capability is now specific enough to execute rather than search broadly.
- **CAP-019 must govern settlement absence:** stale/unavailable bank/payroll observation can never become `no transaction` or `no return`. Last-seen cursors are continuity hints, not completeness proof.
- **Negative acceptance rule:** substring/fuzzy reference matching, equal amount, first-unmatched-row choice or a label named `EXACT_REFERENCE` cannot establish realized money. These may generate review candidates only.
- **Portfolio effect:** no new capability ID and no MASTER promotion. The value is closing the CAP-018 architecture and converting EXP-003 from component discovery into a falsifiable provider-to-bank finality matrix.