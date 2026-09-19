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

## Demoted from MASTER this run
- `Fajendagba/Construction-Change-Order-Engine@60f5ab99bfb97647039e6cec280c246a10f8a856`: valuable clean-room state/budget reference but no license and now materially surpassed by rights-clean OpenTakeoff + BIMChange-Agent for ScopeSignal's implemented evidence layers. Keep only as inspect/reference in COMBINATIONS/REJECTED.
- `D-ivy/renewables_indexes@fe31ab507987a38cc9c042cd745d89546b6f25c0`: useful clean-room renewable/BESS screening methodology, but no license plus incomplete visible reproducibility no longer meets the elite positive-training-set bar. Revisit only on clear rights or a reproducible licensed successor.
