# MASTER

Cross-lane shortlist of the strongest validated discoveries. This is the positive training set for future hunts: deep functioning vertical systems, deterministic audit/recovery engines, evidence-grade public-data infrastructure, standards/protocol implementations, difficult integration substrates and measurable decision engines.

## Rules
- Only include findings with inspected source/tests/schemas/deployments or other concrete evidence.
- Deduplicate across hunters and keep the strongest current opportunity/component when multiple repositories cover the same job.
- Record exact revision and rights status. Public visibility is not a license grant.
- Normal promotion bar: 24/30 on A speed to first revenue, B plausible ACV/ceiling, C build-time/domain compression, D rarity/data/technical advantage, E evidence/completeness, F rights/reuse clarity. Lower scores require a uniquely important role in a stronger combination.
- For each new promotion preserve buyer/problem, monetization path, first paid wedge and why it beats alternatives.
- Do not include or preserve credentials, private/personal data, accidentally exposed confidential information, leaked trade secrets, vulnerabilities or unauthorized-access material.

## Current leaders — 2026-09-19

### qx04222/openrental
- Commit: `013637e77fa9e11ce6aca32fb6218154d7265122`.
- Rights: Apache-2.0; commercially reusable subject to license/notice obligations.
- Inspected capability: Unusually complete equipment-rental ERP with fleet/availability, tiered and contract pricing, deposits represented as liabilities, invoicing/receivables, maintenance, reporting and offline field inspections.
- Buyer/problem: Rental operators need a vertical operating system rather than a generic CRUD shell.
- Monetization: Hosted/managed vertical implementation plus migration/support; it collapses months of rental-specific product work.

### DominicFinn/open_tms
- Commit: `93d8c2b8ff78373ff69bb7ea546743e4703628b1`.
- Rights: MIT.
- Inspected capability: Active TMS/WMS product substrate with shipment, carrier, EDI, reporting, tenancy, deployment and logistics-domain workflows.
- Buyer/problem: Shippers/3PLs/freight-payment teams need operational freight truth and workflow around invoice/audit products.
- Monetization: Core logistics application substrate inside the freight-recovery stack; strongest immediate freight build-time compressor found.

### sengtha/Kareya-Silo
- Commit: `a43eedea03add0728eadfc1f8ea35cc3ca6867cc`.
- Rights: Apache-2.0; commercial carrier rates are separate customer/provider data.
- Inspected capability: Deterministic freight tariff/rating engine with effective-dated carrier/mode/service/origin/destination tariffs, weight bands, minimums, buy/sell rates, disbursements and per-kg/per-CBM/W-M/container/shipment/document/piece/percent bases. Tests cover volumetric divisors, W/M, boundaries, minimums, fuel, margin and overlap rejection.
- Buyer/problem: Recovery claims fail if billed-vs-contracted math is not reproducible.
- Monetization: Core rerating engine for freight recovery or forwarder rate control.

### vidyesh95/qatoto-backend — provider freight-rate subsystem
- Commit: `4f5f270f6ba5ef3ed4b230716997ccea049ce408`.
- Rights: MIT.
- Inspected capability: Provider-owned, versioned freight rate cards with authenticated authorship, origin/destination/mode/currency/effective windows, break ladders, minimum billable weight/volume, minimum charge, transit ranges and explicit volumetric divisors; tests reject spoofed provider/source identity, invalid windows/divisors/floors and bad supersession.
- Buyer/problem: Parsed rates are unsafe unless provider identity, revision/effective period and supersession are provable.
- Monetization: Rate-authoring/versioning control plane paired with Kareya rerating and Open TMS invoice workflow.

### warpfreight/warp-agent-mcp
- Commit: `1850556032b465a0c24839e28564687462067323`.
- Rights: MIT for repository code; live Warp/customer records remain customer-authorized data governed separately by applicable terms/privacy obligations.
- Score: **29/30** — A4, B5, C5, D5, E5, F5.
- Inspected capability: Production-oriented authenticated connector exposing quote/booking history, tracking/events, delivered-shipment invoices and BOL/POD/customs documents. Its read-only review workflow rejects unknown/mismatched requirements, preserves negative savings and does not mislabel invoice variance as realized recovery.
- Buyer/problem: Freight recovery pilots otherwise spend weeks collecting and reconciling transaction evidence before audit logic can even run.
- Monetization path: Authorized live-data bridge inside the freight-recovery service, not a standalone quote product.
- First paid wedge: Read-only audit of already-delivered customer-authorized shipments with quote→booking→event→invoice→BOL/POD lineage; no booking/payment/dispute action.
- Why it beats alternatives: Unlike thin logistics SDKs, this connector reaches multiple evidence objects from one real freight network and already encodes fail-closed comparison behavior. It does not replace contractual rate authority.

### OmarFaig/Assay
- Commit: `821303935ef2855908a9a9bd1efd4c33f9cd39d2`.
- Rights: MIT; model weights, datasets and external inference runtimes require separate rights review.
- Score: **29/30** — A5, B4, C5, D5, E5, F5.
- Inspected capability: Selective-prediction invoice extraction with field-level constrained-decoding token/logprob evidence, legal-alternative awareness so grammar-forced tokens do not inflate confidence, arithmetic-check penalties, calibrated field gates, review routing and evaluation modules.
- Buyer/problem: Freight/AP recovery cannot tolerate low-confidence OCR/LLM fields silently becoming recoverable dollars.
- Monetization path: Confidence/review-control layer inside high-value document workflows; value is reduced reviewer labor at a measured false-accept ceiling.
- First paid wedge: Calibrate on the freight/AP benchmark and auto-accept only fields meeting an agreed false-accept threshold; send the remainder to a compact review queue.
- Why it beats alternatives: Generic OCR/VLM tools extract fields; Assay addresses the harder commercial control question—when a field is safe enough to drive a deterministic money decision.

### hupe1980/en16931
- Commit: `894a3e0d36dea6d3dc086d066881d9a691b20882`.
- Rights: Apache-2.0; standards/rules update cadence and external artifacts require separate provenance.
- Inspected capability: Canonical EN 16931 semantic invoice model with UBL 2.1, UN/CEFACT CII and ZUGFeRD bindings, conversion/validation/CLI, cross-syntax equivalence tests, conformance tests and hybrid-PDF structured-data extraction.
- Buyer/problem: AP/audit systems should not send structured invoices through lossy OCR.
- Monetization: Structured-invoice validation/conversion gateway and exact evidence path inside AP/freight recovery.

### dedupeio/dedupe
- Commit: `3f61e79102910bd355e920a2df7e44c14c9cb247`.
- Rights: MIT.
- Inspected capability: Mature trainable entity-resolution infrastructure.
- Buyer/problem: Vendor/carrier/property/company identities fragment across operational and public data.
- Monetization: Shared matching layer across PermitPlate, CaptureBrief, freight/AP and public-data products.

### benseverndev-oss/goldenmatch
- Commit: `d3516270570fc648759a3cc64ed24d80392d0b50`.
- Rights: MIT.
- Inspected capability: Fellegi-Sunter/EM linkage plus stable identity, merge/split, provenance/audit concepts, blocking/calibration/evidence gates and parity/out-of-core tests.
- Buyer/problem: Durable identity needs more than one-time fuzzy matching.
- Monetization: Shared identity-control plane/managed master-data cleanup; benchmark against Dedupe/Splink before selecting per workload.

### getomni-ai/zerox
- Commit: `91bbb20c50de86067670aa13833afa1b8a73c22e`.
- Rights: MIT; selected models/providers retain separate terms.
- Inspected capability: Multi-format vision-model OCR/document extraction with Node/Python implementations and tests.
- Buyer/problem: Many vertical workflows still receive unstructured PDFs/images.
- Monetization: Generic extraction fallback beneath evidence-grade vertical workflows; native structured formats should bypass it.

### microsoft/RulesEngine
- Commit: `5650f93f843865610240e0498b26b68b477a3920`.
- Rights: MIT.
- Inspected capability: Mature deterministic rules/workflow execution.
- Buyer/problem: Audit, eligibility, pricing, approval and exception logic must be explainable/versionable rather than hidden in prompts.
- Monetization: Shared decision layer across freight, GovCon, compliance, GST and other assurance products.

### Kentucky-ai/opentakeoff
- Commit: `6ff9cc355e60d6312c0c82e2ddac56cb212cc394`.
- Rights: Apache-2.0.
- Inspected capability: Construction-specific calibrated PDF/image takeoff with count/linear/area measurements, material calculations, browser/MCP surfaces, review states, provenance, exports and dedicated tests/benchmarks.
- Buyer/problem: Specialty contractors/GCs lose time and margin when drawing quantities and revisions are measured manually or cannot be defended.
- Monetization: ScopeSignal quantity-delta engine or standalone takeoff copilot; services-led change-order recovery is the fastest wedge.

### delongwangshu49-hub/bimchange-agent
- Commit: `cd7fd6e6522e060b7847f0daaed00979097da7dd`.
- Rights: MIT.
- Inspected capability: Offline-first IFC4 old/new revision comparison with normalized deterministic change records, old/new evidence selectors, conservative geometry classification, relationship changes, 3D context, JSON/HTML export and held-out revision fixtures.
- Buyer/problem: Scope/change products need to prove exactly which model elements changed before assigning quantity/commercial impact.
- Monetization: Rights-clean IFC revision-evidence module for ScopeSignal.

### blencorp/capture-mcp-server
- Commit: `e91ce243cd6a62e9c2a55609d34a187fca89703b`.
- Rights: MIT for repository code; provider/API terms separate.
- Inspected capability: Tested SAM.gov and USAspending tooling with award-type validation, PIID resolution, award/FPDS verification, recipient/agency/NAICS/PSC aggregation and deployment/auth surfaces.
- Buyer/problem: GovCon capture teams spend costly analyst time reconstructing incumbent and buying history.
- Monetization: Premium evidence-backed CaptureBrief qualification/research layer.

### fedspendingtransparency/usaspending-api
- Commit: `1692d484b38c66361c54faa221548527cae29964`.
- Rights: CC0-1.0 for the official repository; source-system caveats remain.
- Inspected capability: Official USAspending.gov server/ETL schemas and implementation for federal award, procurement, recipient and spending data with procurement/recipient/data-loading tests.
- Buyer/problem: GovCon products otherwise reverse-engineer historical award semantics and risk inconsistent joins.
- Monetization: Authoritative award/incumbent/spend evidence underneath CaptureBrief.

### fedspendingtransparency/data-act-broker-backend
- Commit: `76dcae4ccbf6951223608bc1d8fd0c5b03da5d68`.
- Rights: CC0-1.0; downstream/source-system data caveats remain separate.
- Score: **29/30** — A4, B5, C5, D5, E5, F5.
- Inspected capability: Official DATA Act broker implementation containing canonical procurement/award field semantics and SAM recipient normalization for UEI, legacy DUNS, legal/DBA names, immediate/ultimate parents, addresses/business types, update/delete/deactivation behavior and referenced-IDV/procurement identifiers.
- Buyer/problem: False UEI/DUNS/parent/PIID joins can invalidate incumbent/competition intelligence and are expensive to debug manually.
- Monetization path: Evidence-grade federal identity/award lineage inside CaptureBrief or a supplier/award intelligence API.
- First paid wedge: Add identity-confidence + award-lineage evidence to 10 CaptureBrief solicitation packets and benchmark against manual verification.
- Why it beats alternatives: It exposes the government's own normalization semantics upstream of published spending data, making it more authoritative than another fuzzy-name matcher or SAM wrapper.

### MindPetal/sam-search
- Commit: `019b31dca0f980e79117a7c559777cb357a2a385`.
- Rights: MIT.
- Inspected capability: Functioning tested SAM.gov opportunity ingestion and scheduled-search plumbing.
- Buyer/problem: CaptureBrief needs reliable current-opportunity acquisition before higher-value evidence/decision layers can run.
- Monetization: Acquisition layer, not the commercial moat by itself.

### cliwant/mcp-sam-gov
- Commit: `aaaaa70dcb6a08cf43cb40ece26b79d6d21c2463`.
- Rights: MIT; government-source currency/applicability remains contextual/human-reviewed.
- Inspected capability: Large read-only federal/SLED procurement/spending/regulatory toolset; inspected FAR path resolves exact FAR/DFARS clauses/prescriptions from versioned eCFR XML, rejects stale/blank/future/hollow sources and surfaces overhaul/deviation caveats.
- Buyer/problem: Capture/proposal teams need cited current regulatory evidence rather than hallucinated clause summaries.
- Monetization: CaptureBrief compliance/readiness layer.

### Polycentric-Labs/evidentia
- Commit: `0e0bc8bac7d8e4b71f729ac488fd3b47273f5531`.
- Rights: Apache-2.0; framework/catalog provenance requires separate review.
- Inspected capability: Continuous compliance evidence/control plane with gap analysis, evidence storage, API/UI/MCP/GitHub surfaces, OSCAL assessment/POA&M, SARIF/OCSF/CycloneDX outputs and signing paths.
- Buyer/problem: Regulated SaaS/MSPs repeatedly gather/normalize/prove control evidence.
- Monetization: Managed compliance-evidence service paired with deterministic evidence generators.

### RamazanKara/restore-drill
- Commit: `dea374da3b340f53b798112eee82bd7ed1224572`.
- Rights: Apache-2.0 with LICENSE/NOTICE.
- Inspected capability: Disposable restore verification for PostgreSQL, MySQL/MariaDB, Redis and etcd with provider/runtime abstractions, validation, cleanup, parallel drills, evidence reporters, Helm and CI/security scaffolding.
- Buyer/problem: Backups existing is not the same as proving restorability and recovery objectives.
- Monetization: Recurring continuous-restore-proof service or compliance/resilience add-on.

### joschiservice/RosterSpec
- Commit: `f7e701c694bf1facdc4999e1681a3aa11493614d`.
- Rights: Apache-2.0.
- Score: **29/30** — A4, B5, C5, D5, E5, F5.
- Inspected capability: Deterministic workforce schedule verification/explanation/repair kernel using CP-SAT. It diagnoses infeasibility with stable rule codes, verifies proposed repairs by applying/re-solving them and incrementally replans around published schedules with hard locks and minimum disruption; deep tests include independent oracles, goldens, load and coverage-priority cases.
- Buyer/problem: Contact centers, fulfillment, field service and WFM vendors need rapid callout/replan decisions without silently sacrificing coverage or rewriting the entire published roster.
- Monetization path: Schedule Safety & Replan Audit followed by an embedded verification/replan service around the buyer's existing WFM.
- First paid wedge: Replay a week of callouts against the published roster and compare current/manual repair with verified minimum-disruption repair on uncovered intervals, paid hours/overtime and assignment churn.
- Why it beats alternatives: Most scheduling repos optimize from scratch; RosterSpec treats the existing schedule, locks, objective priority and repair validity as first-class evidence, which is much closer to a sellable assurance layer.

### proforcetech/phparm
- Commit: `a691ebfdea93a20f9de5f8a076430c859f299255`.
- Rights: MIT.
- Inspected capability: Line-of-business platform with customers/estimates/work orders/invoices/time/dispatch and recurring service routes/stops/visits, visit photos, QR-gated field execution, centralized state transitions, completion-photo guards, audit writes and contract-entitlement consumption.
- Buyer/problem: Janitorial/facility-service contractors lose margin when recurring visits are missed, unprovable, consume the wrong entitlement or out-of-scope work never becomes billable evidence.
- Monetization: Proof-of-service + contract-leakage vertical wedge priced per site/crew plus onboarding/migration.

### Tamil-Venthan/Rekvia
- Commit: `158d199e4f08041e587a70926f2ed22d17511431`.
- Rights: MIT; government tax rules/data and taxpayer data are separate.
- Inspected capability: Deterministic Purchase Register↔GSTR-2B reconciliation with duplicate-safe one-to-one matching, GSTIN-scoped fuzzy invoice matching, tax/value discrepancy classification, ITC/RCM fields and Excel exception reporting.
- Buyer/problem: Indian SMEs/accounting firms need repeatable GSTR-2B exception handling without duplicate inflation.
- Monetization: Fixed-price reconciliation diagnostic/recurring exception service; do not claim recovered ITC or automate filing until current IMS rules are validated.

### labiium/pytestlab
- Commit: `8b7f873e29457f05dee7af0de698e27985c98a33`.
- Rights: Apache-2.0; vendor SCPI docs, firmware/SDKs and test data remain separate.
- Score: **29/30** — A5, B4, C5, D5, E5, F5.
- Inspected capability: Multi-instrument test-and-measurement automation with VISA/simulation/recording/replay/session-recording backends, SCPI validation/profiles, bench orchestration, sweeps/results/uncertainty and compliance/verification layers plus strong E2E/safety/replay tests.
- Buyer/problem: Electronics/RF/medical-device/semiconductor test teams cannot afford every regression to occupy scarce physical benches or fail late on instrument dialect/state issues.
- Monetization path: Bench modernization + replayable hardware-independent validation infrastructure and recurring support.
- First paid wedge: Convert one brittle bench script into a recorded known-good session, replay it in CI, inject a command/state regression and deliver a traceable validation report.
- Why it beats alternatives: It combines device abstractions with reproducible record/replay/simulation and compliance semantics; most lab frameworks emphasize control but not hardware-independent regression evidence.

### sciencecorp/galago-tools
- Commit: `7ddf68c7bb7eda0243f6466cfbd6b97fdcfcf782`.
- Rights: Apache-2.0; individual vendor SDK/runtime terms remain separate.
- Inspected capability: Standardized gRPC instrument gateways with concrete mixed-vendor adapters, shared CLI/communications and support for legacy 32-bit Windows instrument environments.
- Buyer/problem: Labs/integrators lose weeks to proprietary instrument software and runtime quirks.
- Monetization: Vendor-neutral instrument edge gateway/appliance plus commissioning/support.

### PyLabRobot/pylabrobot
- Commit: `c3c59eebf45c4f6bb2fc78dbfd30f6e458653494`.
- Rights: MIT.
- Inspected capability: Broad cross-vendor lab-automation SDK.
- Buyer/problem: Heterogeneous lab hardware makes workflow automation integration-heavy.
- Monetization: Hardware abstraction within focused automation cells rather than a generic platform pitch.

### ORNL/flowcept
- Commit: `c000b10ea49659af6c5821b61918f3893bd46a92`.
- Rights: MIT.
- Inspected capability: Runtime provenance/lineage for scientific and AI workflows with adapters, streaming, persistence/query and tests.
- Buyer/problem: R&D teams often cannot reconstruct exact code/config/input/output chains across instrument and compute workflows.
- Monetization: Experiment-evidence/reproducibility layer paired with lab control/scheduling.

### NLR-Distribution-Suite/erad
- Commit: `735f7a6baa9fe24878a986a3425bf6d55ad556c3`.
- Rights: BSD-3-Clause; hazard datasets, fragility literature/parameters and dependencies require separate provenance/rights review.
- Score: **29/30** — A4, B5, C5, D5, E5, F5.
- Inspected capability: Distribution-grid resilience engine with graph/network models, asset-specific fragility, flood/wind/wildfire/earthquake hazard-to-failure calculations and restoration/resilience workflows across poles, lines, transformers, substations, switches and rooftop solar; includes multi-hazard logic, ForeFIRE wildfire integration, notebooks and CI.
- Buyer/problem: Utilities/consultants/insurers need to know which assets fail and what network/restoration consequence follows, not merely see hazard overlays.
- Monetization path: Fixed-price resilience/hardening study followed by recurring asset-risk and restoration-prioritization analytics.
- First paid wedge: Run a rights-clean synthetic/customer-authorized feeder through wind/flood/wildfire scenarios and compare planted damage/restoration cases to model output.
- Why it beats alternatives: It provides the hard middle layer from hazard surface→asset fragility→network consequence→restoration decision; generic geospatial risk maps stop before that operational decision.

### agritheory/inventory_tools
- Commit: `dd1e07d98eb81b2388acb922ce9ae3397a5af7ac`.
- Rights: MIT.
- Inspected capability: ERPNext slotting optimizer using movement heat, warehouse-plan walking distance, dimensional fit/capacity and executable putaway/default-warehouse recommendations.
- Buyer/problem: Warehouses incur recurring picker/replenishment labor from poor slot placement.
- Monetization: Fixed-price re-slotting study plus recurring optimization/ERPNext app.

### gokhanozden/gabak
- Commit: `711856814856e1730bd3be1cc7e4468ceca4fd5d`.
- Rights: MIT.
- Inspected capability: Warehouse-layout/pick-tour simulator and evolutionary optimizer with aisle-center/visibility-graph path models and obstacle/picker-clearance handling.
- Buyer/problem: Operators need quantified travel-distance evidence before disruptive re-slotting/layout change.
- Monetization: ROI/simulation layer paired with slotting recommendations.

### freeacs/freeacs
- Commit: `f4c5d056ac6c247e0757de20acacd6046fd0ef0d`.
- Rights: MIT; protocol/data-model/vendor terms separate.
- Inspected capability: Full TR-069/CWMP ACS with session/provisioning decisions, Get/Set, downloads/firmware, reboot/reset/transfer-complete, auth modes and substantial integration fixtures/tests.
- Buyer/problem: Regional ISPs/WISPs/CPE vendors still carry costly legacy CWMP fleets.
- Monetization: Managed ACS modernization, regression lab or TR-069→USP migration service.

### OktopUSP/oktopus
- Commit: `e1f07d71a93c4169421f2e94ce6605746ece37ad`.
- Rights: Apache-2.0; protocol/specification/dependency assets require normal review.
- Inspected capability: Unified TR-369 USP Controller plus TR-069/CWMP ACS in Go with USP 1.2/1.3 protobuf, MQTT/STOMP/WebSocket transports, CWMP modules, NATS bridges, OB-USP-Agent launch assets, containers and protocol tests.
- Buyer/problem: Broadband operators need a bridge from legacy CWMP to USP without unrelated management stacks.
- Monetization: Dual-stack migration/conformance lab or managed controller service.

### srthck/trustmesh
- Commit: `5a93d70b37aafecaf61a5bc0296eaf831e5504ac`.
- Rights: MIT; external payment-network/scheme policy content remains separately governed and must not be assumed reusable merely because the engine is MIT.
- Score: **29/30** — A4, B5, C5, D5, E5, F5.
- Inspected capability: Deterministic evidence-decisioning control plane that decomposes a claim into proof obligations, applies admissibility/authority/independence/temporal/deadline/contradiction gates, emits ACCEPT/REVIEW/CONTEST with versioned traces, preserves blocking evidence and fails safe to REVIEW on exceptions. Its next-best-evidence optimizer filters unavailable, duplicate-source, late or non-impactful evidence actions and re-runs the real adjudicator counterfactually before recommending what evidence to obtain next.
- Buyer/problem: Recovery/claims/compliance teams frequently know a case is incomplete but cannot consistently prove why, what evidence is legally/operationally independent, or which missing item is most likely to change the decision before a deadline.
- Monetization path: Evidence-readiness and next-evidence layer inside high-value recovery, claims, ScopeSignal, CaptureBrief and compliance workflows; sell the domain outcome rather than a generic policy engine.
- First paid wedge: Run a historical recovery/dispute diagnostic and produce a deterministic blocker + next-best-evidence queue, without submitting or altering any live claim.
- Why it beats alternatives: Rules engines can decide on supplied facts and case systems can hold documents; TrustMesh adds explicit proof obligations, conflict/admissibility gates, immutable replayable decision traces and counterfactual evidence acquisition. It is therefore a reusable assurance primitive rather than another workflow shell.

### aiparallel0/freight-audit
- Commit: `e7869162cf9cb23f6d520a0cd71f87cf973d8c28`.
- Rights: MIT for code and committed synthetic/PII-free sample corpus; external CORD-v2 benchmark material remains CC BY 4.0 and requires separate attribution/handling.
- Score: **28/30** — A4, B4, C5, D5, E5, F5.
- Promotion rationale: not an independent business leader; uniquely important benchmark/evaluation component in the highest-priority freight-assurance stack.
- Inspected capability: Freight-specific rate-confirmation + carrier-invoice + POD audit harness using integer-cents money, configurable layouts/rules/vocabulary, OCR, synthetic freight-document generation, benchmark scoring and review tooling. The committed five cases cover clean billing, linehaul overcharge + duplicate fuel, unauthorized liftgate, billed detention without adequate POD evidence, and POD-supported earned detention omitted from billing.
- Buyer/problem: An audit engine can have correct rerating logic and still manufacture recovery dollars if document extraction silently fails. The repository supplies falsifiable freight-specific extraction and rule fixtures rather than generic OCR demonstrations.
- Monetization path: QA/gold-truth infrastructure for the paid Freight Audit Acceptance Test and incumbent-auditor bake-off; use measured error/abstention rates to define which fields can drive automated dollars.
- First paid wedge: Run the synthetic corpus plus a customer-authorized blind invoice/rate/POD sample and report extraction accuracy separately from audit-rule accuracy and incumbent missed dollars.
- Why it beats alternatives: Its docs expose poor out-of-distribution OCR performance instead of hiding it, forcing format-specific calibration and review. That negative evidence is strategically more useful than another polished demo claiming document extraction is solved.

### sandialabs/DREAMS
- Commit: `3eb6c6089eadf09a4bf99961faac11a76ef30ca0`.
- Rights: MIT; OpenDSS plus feeder/input datasets and customer models retain their own terms.
- Score: **29/30** — A4, B5, C5, D5, E5, F5.
- Inspected capability: Distribution-planning software with substantive OpenDSS-based nodal hosting-capacity and quasi-static time-series analysis, including per-node DER capacity searches, configurable power-flow constraints, parallel evaluation and dedicated hosting-capacity/QSTS tests.
- Buyer/problem: Utilities, DER/storage developers and interconnection engineers need defensible feeder-level hosting-capacity evidence rather than a coarse capacity map when deciding where a project can connect or which constraint binds.
- Monetization path: Fixed-price feeder/portfolio hosting-capacity diagnostic followed by recurring interconnection screening and scenario/planning support.
- First paid wedge: Run one rights-clean synthetic/customer-authorized OpenDSS feeder through nodal hosting-capacity/QSTS analysis and deliver constraint-by-constraint capacity thresholds plus a reproducible report.
- Why it beats alternatives: It closes the electrical-analysis middle layer between site/queue intelligence and utility engineering decisions. Unlike a published hosting-capacity map, it can test a customer-owned feeder under explicit voltage/thermal constraints; unlike the broader GPL OMF alternative, the code is permissively reusable.

### google/cybernetic-agent-governance-engine
- Commit: `50b12e7d983db0e3d7faf206ac6aa600294f33ac`.
- Rights: Apache-2.0; dependencies/services and customer remediation actions remain separately governed.
- Score: **28/30** — A4, B5, C5, D4, E5, F5.
- Inspected capability: Deterministic governance/enforcement engine for consequential automated actions with allow/deny/require-approval/defer/narrow/pause outcomes, signed decision/evidence records and an implemented OSCAL Assessment Results bridge. The inspected exporter preserves evidence links/content-address metadata and maps execution errors to explicit `error` state rather than treating blind spots as compliant.
- Buyer/problem: Continuous-compliance and automation products can detect failures but still need a safe, reviewable mechanism for deciding which remediation may run automatically, which needs approval and which must halt.
- Monetization path: Managed detect→govern→remediate→re-prove service layered onto Evidentia/restore-proof or regulated automation workflows.
- First paid wedge: Feed a small set of synthetic failed controls into approved remediation playbooks; harmless action can auto-run, production/destructive action requires human approval, unapproved action blocks, and a subsequent re-test must produce fresh evidence.
- Why it beats alternatives: Evidence collectors prove a state and generic workflow tools can execute actions; CAGE links deterministic authorization, human gating and evidence export into the missing operational loop while preserving error/unknown semantics.

### BestKylin2001/Freight-Rate-Sheet-Generator
- Commit: `78f3b86a2a4a25d9abf11d4addc2feea10667352`.
- Rights: MIT for repository code; carrier/customer rate sheets remain separately authorized commercial data.
- Score: **24/30** — A4, B4, C4, D4, E3, F5.
- Promotion rationale: promoted at the normal threshold because it is the first permissive implementation found that directly closes the highest-priority freight stack's messy-XLS tariff-ingestion gap; production hardening is still required.
- Inspected capability: OpenPyXL/Pandas pipeline that discovers header rows, normalizes heterogeneous carrier/port/destination labels, handles aliases, Excel serial/string dates and formula value reads, and emits canonical ocean-rate records with POL, carrier, destination, effective/expiry dates and container-price fields.
- Buyer/problem: Freight audit/payment teams cannot deterministically rerate customer shipments until messy rate workbooks become reviewed, effective-dated tariff facts.
- Monetization path: Rate-sheet digitization/onboarding bundled into the freight-recovery service; the importer feeds Assay/FactGate-style review, Qatoto versioning and Kareya rerating.
- First paid wedge: Normalize one customer-authorized historical XLS rate-card set, preserve cell-level provenance and rerate a frozen invoice population.
- Why it beats alternatives: Generic OCR/table parsers do not encode spreadsheet-specific alias/date/formula behavior, while the deeper carrier-specific references found this run have no reuse license. This one is lawful, narrow and immediately stack-compatible.

### MassingCloud/massing-pdf
- Commit: `36794b3c54fcfd62e3a0d2d5984cfc45cac83340`.
- Rights: MIT; PDF/OCR/browser dependencies and customer drawings remain separately governed.
- Score: **29/30** — A4, B5, C5, D5, E5, F5.
- Inspected capability: Browser-side construction drawing review engine with calibrated takeoff, structured markups and a revision-comparison core that performs coarse-to-fine old/new sheet registration, optional scale correction, changed-region scoring and transform-aware markup migration; E2E tests cover translation recovery, unchanged/changed sheets, severity ordering and migration verdicts.
- Buyer/problem: GCs and specialty contractors lose expensive review time and change-order evidence when sheet drift, scale changes and stale markups are mistaken for true scope changes.
- Monetization path: ScopeSignal's 2D revision-evidence core; sell a fixed-price revision audit first, then quantity/entitlement/change-order workflow per project.
- First paid wedge: One issued old/new drawing pair → aligned revision clouds + migrated-markup review queue, with analyst time and false-positive rate measured before attaching dollars.
- Why it beats alternatives: It directly attacks revision registration and markup carry-forward—the missing step between raw PDF diff and defensible commercial scope change—and is materially stronger than simple OCR/pixel-diff baselines.

### cybertec-postgresql/pg_hardstorage
- Commit: `b47541b7e1cea69ce6ec63b26e154eb25fc4ca91`.
- Rights: Apache-2.0; PostgreSQL/storage/KMS/container dependencies and customer backups remain separately governed.
- Score: **29/30** — A4, B5, C5, D5, E5, F5.
- Inspected capability: PostgreSQL 15–18 backup/PITR system with a dedicated verifier that restores a candidate into a disposable sandbox, boots PostgreSQL, runs `pg_verifybackup` and `pg_amcheck --all`, and records a signed pass/fail verdict into manifest/audit evidence; Docker is implemented and a Firecracker backend exists behind a build tag.
- Buyer/problem: SaaS/MSPs/regulated teams may have green backup jobs yet still lack independent evidence that a chosen recovery point boots and passes database-integrity checks.
- Monetization path: Managed recurring recovery-proof service layered into the compliance/resilience stack.
- First paid wedge: Restore one recent backup/PITR target in isolation and deliver artifact identity, recovery target/duration, official integrity checks, application checks and signed verdict.
- Why it beats alternatives: Generic backup monitors prove job completion; pg_hardstorage binds actual PITR execution, corruption checks and signed evidence in one rights-clean path.

### tonytonycoder11/stripe-connect-reckon
- Commit: `deb30aabfed84c7b0b2e5ae28c92cc9f85f79193`.
- Rights: MIT; Stripe API/service terms and customer authorization remain separate.
- Score: **29/30** — A5, B5, C4, D5, E5, F5.
- Inspected capability: Read-only Stripe Connect marketplace financial-controls engine that reconciles connected-account balances, payouts, refunds, disputes, events and platform/app state; detects failed payouts, unreconciled refunds, event gaps, negative-balance/reserve/dispute exposure and adds forecasting, alerts, reports, history and monitoring integrations. Direct source inspection confirmed the Stripe adapter performs list/retrieve reads rather than transactional writes.
- Buyer/problem: Marketplace CFO/controller/finance-ops teams can lose cash or spend days on manual reconciliation when payout/refund/event state drifts across Stripe and the application ledger.
- Monetization path: Fixed-price Marketplace Money Safety Audit followed by recurring read-only financial-controls monitoring priced by connected-account, transaction or GMV tier.
- First paid wedge: Connect read-only authorized Stripe/app-state sources, quantify unresolved money-state exposure and deliver a reconciled exception report without touching payouts.
- Why it beats alternatives: It is an independent assurance plane that can prove value without replacing the buyer's payment stack or joining the money-moving write path, sharply reducing pilot friction.

### suoten/ProtoForge
- Commit: `7c61b10d9ae406224c86741d9c0a450b561b40ca`.
- Rights: MIT for repository code; industrial protocol standards, optional libraries, vendor marks/patents and customer traces remain separate.
- Score: **29/30** — A5, B5, C5, D5, E5, F4.
- Inspected capability: Multi-protocol industrial simulation/testing platform with virtual-device templates, fault injection, recording/replay, test plans/reports, metrics, RBAC, persistence and deployment tooling. Deep inspection confirmed a substantive IEC 60870-5-104 state machine—APCI I/S/U frames, STARTDT/STOPDT/TESTFR, ASDU monitor/control types, select-before-operate, general interrogation, clock sync, sequence windows/timers—and current Modbus socket/edge-case tests.
- Buyer/problem: Industrial gateway/SCADA/OEM integration teams need repeatable pre-cutover validation without monopolizing scarce PLC/RTU hardware or discovering protocol failures in production.
- Monetization path: Fixed-price gateway regression/interoperability pack followed by managed protocol-lab subscriptions or integration support.
- First paid wedge: Model 3–10 authorized device types, exercise normal + disconnect/timeout/write/fault cases and deliver a reproducible compatibility/evidence matrix.
- Why it beats alternatives: It packages simulator breadth, fault/replay and reporting into a rights-clean acceptance-lab substrate rather than another single-protocol library; protocol-by-protocol external validation remains mandatory.

### clicon/clixon-controller
- Commit: `36ecc0fd8787750978652495a39d0d01db2c7474`.
- Rights: Apache-2.0; vendor/customer YANG models and extensions remain separate rights surfaces.
- Score: **28/30** — A4, B5, C5, D4, E5, F5.
- Inspected capability: Active NETCONF/YANG multi-device controller with device lifecycle, candidate/running-style state, validation/commit transactions, locking, templates/groups, device profiles and Python service APIs. Extensive tests cover dead connections, timeouts, lock/commit failures, rollback/revert, NACM, services and transaction progress.
- Buyer/problem: Telecom/network automation teams need to prove multi-device change semantics before controller/NMS migrations touch production routers.
- Monetization path: Controller migration acceptance service using synthetic and independent NETCONF/YANG endpoints rather than selling raw protocol plumbing.
- First paid wedge: Replay one OpenConfig service/config workflow across controlled endpoints and report validate/lock/commit/rollback/disconnect/timeout behavior before cutover.
- Why it beats alternatives: The difficult reusable asset is transaction coordination and failure semantics across devices; paired with notconf/Netopeer2/gnmic it becomes a high-value evidence lab rather than a standalone controller demo.

### novonordisk-research/OptiHPLCHandler
- Commit: `96399dcddc1457a5b942f61585b9e8fcf78b9a72`.
- Rights: BSD-3-Clause for repository code; Waters Empower/API/customer installation rights remain separate prerequisites.
- Score: **29/30** — A4, B5, C5, D5, E5, F5.
- Inspected capability: Actively maintained Python SDK for Waters Empower Web API that authenticates, reads/modifies instrument methods, enumerates projects/nodes/systems/plates, constructs sample-set methods, posts methods with audit-trail messages and issues runs; source, tests, CI and executable analytical-development notebooks cover robustness, stability, linearity and multi-vial workflows.
- Buyer/problem: Pharma/biotech analytical-development and QC labs already own powerful CDS infrastructure but still spend expert time manually constructing method variants/sample sets and bespoke integrations.
- Monetization path: Fixed-price 'automate one assay/stability/robustness workflow in your existing Empower estate' implementation, followed by validated workflow packs/support.
- First paid wedge: Use a mock/synthetic Empower workflow to define prerequisites, then automate one customer-authorized assay workflow while preserving Empower as the system of record and measuring manual touches removed.
- Why it beats alternatives: It compresses specialized vendor-CDS integration and embeds real analytical-development workflow knowledge without trying to replace the customer's validated chromatography system.

## Demoted from MASTER this run
- `Fajendagba/Construction-Change-Order-Engine@60f5ab99bfb97647039e6cec280c246a10f8a856`: valuable clean-room state/budget reference but no license and now materially surpassed by rights-clean OpenTakeoff + BIMChange-Agent for ScopeSignal's implemented evidence layers. Keep only as inspect/reference in COMBINATIONS/REJECTED.
- `D-ivy/renewables_indexes@fe31ab507987a38cc9c042cd745d89546b6f25c0`: useful clean-room renewable/BESS screening methodology, but no license plus incomplete visible reproducibility no longer meets the elite positive-training-set bar. Revisit only on clear rights or a reproducible licensed successor.