# COMBINATIONS

Cross-repository product and capability combinations.

## Entry format
### Combination
- Components:
- Combined capability:
- Why the combination is stronger:
- Likely buyer / user:
- Build-time saved:
- Rights / license constraints:
- Validation step:
- Status:

## Seeded combinations — 2026-09-19

### Evidence-first freight recovery stack
- Components: DominicFinn/open_tms + getomni-ai/zerox + microsoft/RulesEngine + dedupeio/dedupe.
- Combined capability: Logistics/shipment domain + document ingestion + deterministic audit rules + entity/carrier/vendor matching.
- Why the combination is stronger: It supplies much of the generic product and evidence infrastructure needed for a freight audit/recovery engine while keeping core billing-error rules explainable.
- Likely buyer / user: Shippers, 3PLs, manufacturers, distributors, or freight-payment teams with enough shipment volume to justify audit/recovery.
- Build-time saved: Potentially very high for non-differentiating infrastructure.
- Rights / license constraints: All four are MIT in the revisions inspected.
- Validation step: Find/implement the missing freight-specific rate-contract and accessorial audit rules, then benchmark on lawful synthetic/public invoice and shipment cases.
- Status: Historical seed. Superseded for active design by the rights-clean v3 contract-to-cash stack below.

### CaptureBrief evidence stack
- Components: MindPetal/sam-search + getomni-ai/zerox + dedupeio/dedupe + microsoft/RulesEngine.
- Combined capability: SAM.gov opportunity retrieval + solicitation/document extraction + entity resolution + explainable qualification rules.
- Why the combination is stronger: Converts raw opportunities into structured, evidence-linked, customer-specific qualification rather than a simple feed.
- Likely buyer / user: Small and midsize federal contractors that need faster opportunity triage.
- Build-time saved: High for ingestion, document processing, matching, and deterministic policy logic.
- Rights / license constraints: All four are MIT in the revisions inspected.
- Validation step: Map SAM fields and attached documents into a single opportunity evidence schema and run against a small sample of current opportunities.
- Status: Historical seed. Superseded for active design by the verified procurement intelligence stack below.

### ScopeSignal change-to-change-order pipeline
- Components: getomni-ai/zerox + microsoft/RulesEngine + clean-room concepts from Fajendagba/Construction-Change-Order-Engine.
- Combined capability: Extract scope/document changes, evaluate deterministic triggers, and route accepted changes through a construction-specific approval/budget-impact state model.
- Why the combination is stronger: Connects upstream document intelligence to an operationally credible downstream change-order workflow.
- Likely buyer / user: General contractors and specialty subcontractors that lose margin when scope changes are identified late or documented poorly.
- Build-time saved: High for document ingestion/rules plus substantial architecture guidance.
- Rights / license constraints: Zerox and RulesEngine are MIT. Construction-Change-Order-Engine has no license, so only independently reimplemented concepts may be used absent permission.
- Validation step: Find permissively licensed RFI/submittal/document-diff components and test one end-to-end synthetic scope-change case.
- Status: Historical seed. IFC revision correspondence is now materially stronger in the stack below.

### Field-onboarding + crop-monitoring stack
- Components: superzero11/OpenFarm + RS-iCM/RSCM.
- Combined capability: Automatically derive/ingest field boundaries and crop/non-crop masks, then run recurring vegetation-index, soil, weather and alert workflows inside a deployable field-operations platform.
- Why the combination is stronger: RSCM attacks the expensive label/bootstrap problem, while OpenFarm supplies the missing operational system around it: PostGIS field records, workers, Sentinel-2 processing, boundary detection, alerts and field workflows. Together they can turn a region with weak customer field data into a monitorable portfolio much faster than building both model and platform from scratch.
- Likely buyer / user: Crop insurers, agricultural lenders, agronomy firms, specialty-crop managers, ag retailers/input distributors and land-use monitoring programs.
- Build-time saved: Potentially 9–15 months of remote-sensing, geospatial-backend, worker and field-onboarding scaffolding for a focused MVP.
- Rights / license constraints: OpenFarm is BSD-3-Clause and RSCM is MIT at the inspected revisions. Sentinel-2/STAC endpoints, FTW checkpoint/model, example datasets and other third-party data/model terms require separate verification.
- Validation step: Select a lawful 50–100-field benchmark, compare generated boundaries/crop masks against known polygons, then measure whether the combined system produces stable per-field index histories and useful alert precision without manual field setup.
- Status: Strong agriculture combination; best immediate differentiator is automatic portfolio onboarding followed by exception-driven scouting rather than another generic farm dashboard.

## Integrator combinations — 2026-09-19

### Freight recovery v3 — rights-clean contract-to-cash evidence chain
- Components: `DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1` + `sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc` + `vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408` + `hupe1980/en16931@894a3e0d36dea6d3dc086d066881d9a691b20882` + `getomni-ai/zerox@91bbb20c50de86067670aa13833afa1b8a73c22e` + `microsoft/RulesEngine@5650f93f843865610240e0498b26b68b477a3920` + `benseverndev-oss/goldenmatch@d3516270570fc648759a3cc64ed24d80392d0b50` or benchmarked `dedupeio/dedupe`; use only independently reimplemented parser requirements learned from no-license `Apeiron-OpenGrace/apeiron_bridge@2f854b37435490a102eb9cadb22b0e878f1af17d`.
- Combined capability: Customer/carrier rate-sheet intake → attributable/versioned provider tariff → validated canonical freight-rate model → deterministic weight/volume/W-M/minimum/break/accessorial rerating → shipment/EDI invoice comparison → evidence-linked dispute/recovery → settlement proof.
- Why the combination is stronger: The previous stack had a rights gap exactly where money is determined. Qatoto now supplies permissive authorship, effective-date, supersession and validation controls; Kareya supplies permissive freight-specific rating arithmetic and tested tariff invariants. Open TMS supplies shipment/invoice/EDI context. The remaining hard problem is source-document extraction and contract-clause coverage, not inventing the rate engine or version control plane.
- Likely buyer / user: High-volume shippers, freight-payment teams, 3PLs, manufacturers, distributors and forwarders.
- Build-time saved: Very high; months of freight tariff schema/rating/versioning plus generic TMS/document/rules/identity plumbing are represented in reusable components.
- Rights / license constraints: Open TMS, Qatoto, Zerox, RulesEngine and GoldenMatch are MIT; Kareya and EN16931 are Apache-2.0. Apeiron remains no-license and may contribute only independently reimplemented behavioral requirements. Carrier contracts/tariffs are customer/authority data with separate rights and confidentiality obligations.
- Validation step: Build 20 lawful synthetic contract→invoice→settlement cases. At minimum include borderless/transposed XLS/PDF tables, future supersession, 44/45 kg boundaries, volumetric divisors, W/M, minimums, fuel/accessorials, ambiguous clauses, duplicate charges and one settlement/credit record. Require exact expected dollars, exact source revision, and zero asserted recovery when parsing or entitlement is ambiguous.
- Status: Highest-priority commercial combination. The old “find a rights-clean rating engine” P0 is resolved; the active P0 is messy contract extraction + clause entitlement + settlement benchmark.

### CaptureBrief verified procurement intelligence + regulatory currency
- Components: `MindPetal/sam-search@019b31dca0f980e79117a7c559777cb357a2a385` + `blencorp/capture-mcp-server@e91ce243cd6a62e9c2a55609d34a187fca89703b` + `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964` + `cliwant/mcp-sam-gov@aaaaa70dcb6a08cf43cb40ece26b79d6d21c2463` + `1102tools-dev/federal-contracting-mcps@c3a137ace72dacca8026752820375dc957badc57` + GoldenMatch/Dedupe + Zerox + RulesEngine.
- Combined capability: Current opportunity ingest, solicitation packet evidence, historical award/incumbent/competition intelligence, recipient identity resolution, exact FAR/DFARS clause/prescription evidence, Acquisition.gov agency-deviation/FAR-Overhaul context and explainable bid/no-bid/readiness output.
- Why the combination is stronger: It now answers not only “what is open?” and “who won before?” but also “what exact regulatory text was cited, was the source current, and is an agency deviation operationally controlling?” The two regulatory adapters have explicit failure/currency semantics that are much stronger than generic RAG.
- Likely buyer / user: Federal primes/subcontractors, proposal/capture consultants, outsourced BD/compliance teams and specialist GovCon research firms.
- Build-time saved: Very high—months of source-specific integration, PIID/entity edge cases, procurement/regulatory retrieval, fault handling and evidence packaging are already represented.
- Rights / license constraints: sam-search, capture-mcp, cliwant, 1102tools, GoldenMatch, Zerox and RulesEngine are MIT; official USAspending repo is CC0-1.0. Government-source applicability remains contextual; no tool output should be presented as a binding legal conclusion without human review.
- Validation step: For 10 current solicitations, manually verify opportunity facts, UEI/PIID/IDV joins, incumbent/history, every cited FAR/DFARS clause/prescription, eCFR snapshot currency and any controlling Acquisition.gov agency deviation. Score false joins, unresolved/error honesty and clause/deviation precision.
- Status: High-priority CaptureBrief architecture. Discovery of generic SAM/regulatory wrappers should stop; identity precision, packet completeness and current-deviation correctness are the remaining evidence gaps.

### ScopeSignal drawing/model-to-dollar change evidence
- Components: `Kentucky-ai/opentakeoff@6ff9cc355e60d6312c0c82e2ddac56cb212cc394` + `delongwangshu49-hub/bimchange-agent@cd7fd6e6522e060b7847f0daaed00979097da7dd` + Zerox + RulesEngine + clean-room state/budget concepts from `Fajendagba/Construction-Change-Order-Engine@60f5ab99bfb97647039e6cec280c246a10f8a856`; Bidwright only under AGPL-compatible deployment or as clean-room reference.
- Combined capability: IFC old/new correspondence with deterministic before/after evidence + calibrated 2D measurements/quantities + extracted contract/spec evidence + deterministic triggers → human-reviewed quantity delta and proposed commercial/schedule impact.
- Why the combination is stronger: BIMChange-Agent materially closes the IFC revision-correspondence gap with held-out/synthetic evidence and stable element identity, while OpenTakeoff supplies rights-clean 2D quantity/provenance. The product can now distinguish “this element changed” from “this quantity/dollar is commercially entitled,” keeping entitlement as a separate evidence gate.
- Likely buyer / user: Specialty subcontractors, GCs, BIM/VDC teams, quantity surveyors, estimators and project controls/claims teams.
- Build-time saved: Very high across IFC revision matching, plan rendering/calibration, geometry/quantity handling, provenance and review.
- Rights / license constraints: BIMChange-Agent, Zerox and RulesEngine are MIT; OpenTakeoff is Apache-2.0. Fajendagba has no license and Bidwright is AGPL-3.0-only, so only clean-room concepts may enter a proprietary path unless the relevant license obligations are deliberately accepted.
- Validation step: Use BIMChange-Agent's generated/held-out pairs and a known 2D revision pair. Preserve revision/element identity through quantity calculations, then attach contract/spec entitlement evidence. Require human approval before any proposed dollar recovery/change order.
- Status: Strong. IFC revision detection is no longer the main technical blocker; cross-format 2D revision correspondence and entitlement-to-dollar validation remain.

### Compliance modernization + continuous evidence/restore proof
- Components: `clay-good/attestful@c445095952d6e1ca27eadc638b1bfe96e8f5f00d` + `williamzujkowski/oscalize@39c283b54e14b71df72e1b8327b593f560adcbe6` + `Polycentric-Labs/evidentia@0e0bc8bac7d8e4b71f729ac488fd3b47273f5531` + `RamazanKara/restore-drill@dea374da3b340f53b798112eee82bd7ed1224572`; optionally use selected rights-clean normalization/evidence adapters after individual review.
- Combined capability: Collect read-oriented evidence from cloud/SaaS systems, convert legacy compliance artifacts to OSCAL, normalize/store/sign evidence and gap state, then generate operational disaster-recovery evidence from real disposable restore drills.
- Why the combination is stronger: Attestful closes the previous collector gap: the stack can now acquire evidence instead of merely storing/transforming it. A fixed-price modernization/assessment can become recurring evidence collection plus restore-proof monitoring.
- Likely buyer / user: FedRAMP/ATO consultants, SOC 2/ISO/NIST programs, regulated SaaS, MSP/MSSP and internal compliance/SRE teams.
- Build-time saved: Potentially 7–15 months across collectors, OSCAL conversion, evidence lineage/control mapping, restore orchestration, reporting and deployment.
- Rights / license constraints: Attestful is MIT; Evidentia and restore-drill are Apache-2.0; oscalize has NIST/public-domain/CC0-style treatment as cataloged. Bundled framework/control/catalog content and third-party service APIs must be reviewed independently; minimize collector scopes and preserve read-only guarantees where possible.
- Validation step: Inventory top-10 collector scopes/read-only behavior, then run one synthetic AWS/GitHub evidence bundle plus one disposable Postgres restore into a versioned control package. Measure evidence completeness, manual corrections and time saved.
- Status: Strong standalone challenger. The primary gap is no longer “find collectors”; it is permissions/provenance hardening plus a reproducible paid-pilot evidence package.

### TR-069 → USP dual-stack modernization and regression lab
- Components: `freeacs/freeacs@f4c5d056ac6c247e0757de20acacd6046fd0ef0d` + `OktopUSP/oktopus@e1f07d71a93c4169421f2e94ce6605746ece37ad` + `BroadbandForum/obuspa@59028beba21471d19bd3842ef2632ceb6ca8c7fc` + `OktopUSP/agent-sim@d90b08dfa59276f28dfcc18cb35c522f356227a5`; `netcwmp` remains a permissive legacy device comparator.
- Combined capability: Legacy CWMP ACS management + unified CWMP/USP controller + official modern USP agent + rights-clean simulated USP fleet for migration rehearsal, interoperability, regression and controller load testing.
- Why the combination is stronger: The previous stack had a credible legacy ACS but no clean successor path. Oktopus supplies a dual-stack bridge, OB-USP-Agent supplies an official rights-clear device implementation, and agent-sim removes the need to depend on the no-license synthetic-fleet reference on the modern side.
- Likely buyer / user: Regional ISPs/WISPs, broadband/CPE OEMs, ACS/USP vendors and telecom QA/certification labs.
- Build-time saved: Many months of controller, agent, transport and simulation plumbing.
- Rights / license constraints: FreeACS is MIT; Oktopus and agent-sim are Apache-2.0; OB-USP-Agent is BSD-3-Clause. Broadband Forum data-model/specification redistribution terms and all device-vendor firmware terms remain separate.
- Validation step: In an isolated lab, reproduce legacy CWMP Get/Set/download flows and modern USP Get/Set/Operate/Notify over MQTT/WebSocket, then run concurrent simulated agents and compare migration-state/parameter behavior. Measure tenant isolation and dependency health before hosted use.
- Status: Rights-clean technical path now exists. Shift search from generic USP discovery to fleet-scale/tenant production validation and buyer urgency/pricing.

### Contact-center workforce assurance
- Components: `rodrigo-arenas/pyworkforce@ca4892502d2d92cc996c9fde96293ff90b560426` + clean-room operational invariants from no-license `davescalante/LCC-WFM@d11905dafb7dced6e889c4f3f9c491863770f4f6` + clean-room evaluation methodology from no-license `Emma-V/support-triage@f12f682eda87ddbf1593200ad515b464b04c00ff`.
- Combined capability: Demand/intent forecast → required staffing → skill mix → shifts/rosters/breaks → planned-vs-actual/adherence/overtime/payroll assurance with abstention on uncertain classification.
- Why the combination is stronger: Pyworkforce supplies the rights-clean optimization core, while the two no-license repositories expose realistic edge cases and evaluation discipline that a generic scheduler lacks.
- Likely buyer / user: BPOs, contact centers and support operations with multiskill queues and high labor cost.
- Build-time saved: Months on solver primitives plus weeks of domain discovery/acceptance-test design.
- Rights / license constraints: pyworkforce is MIT. LCC-WFM and support-triage are inspect/learn/clean-room only; no source, creative test text or dataset content should be copied absent permission.
- Validation step: Use customer-owned or synthetic half-hour demand/AHT/SLA data to produce staffing/roster/break plans, then compare paid hours, SLA coverage and overtime against a spreadsheet baseline.
- Status: Promising but lower priority than freight, GovCon, construction and compliance until a paid buyer problem is validated.

### GST input-tax reconciliation and exception recovery
- Components: `Tamil-Venthan/Rekvia@158d199e4f08041e587a70926f2ed22d17511431` + `microsoft/RulesEngine@5650f93f843865610240e0498b26b68b477a3920` + `benseverndev-oss/goldenmatch@d3516270570fc648759a3cc64ed24d80392d0b50` (or benchmarked `dedupeio/dedupe`) + authoritative GST/GSTR-2B/IMS rules and taxpayer-owned purchase-register data; Zerox only for supporting invoice documents when structured exports are unavailable.
- Combined capability: Deterministic purchase-register ↔ GSTR-2B matching, duplicate-safe invoice correspondence, supplier identity normalization, versioned eligibility/control rules, exception queues, evidence packets and human-reviewed follow-up for missing/mismatched ITC-related records.
- Why the combination is stronger: Rekvia supplies a functioning rights-clean reconciliation core rather than a generic AP matcher. RulesEngine can separate changing tax logic from matching code, while a stable identity layer reduces supplier/GSTIN fragmentation. This creates a plausible services-led tax-control product without depending on OCR for the primary reconciliation path.
- Likely buyer / user: Indian SMEs, outsourced accounting firms, chartered-accountant practices and finance shared-services teams managing multiple GSTINs.
- Build-time saved: Medium-high; likely weeks to months on ingestion, matching, duplicate handling, exception reporting and operator UX. The remaining expensive work is current-rule coverage, IMS state handling and accountant-grade validation.
- Rights / license constraints: Rekvia, RulesEngine and GoldenMatch are MIT. Government data/rule publications, taxpayer records and any portal/API access remain separate; do not automate filing or represent tax recoveries without current authoritative-rule validation and human review.
- Validation step: Build a synthetic/current-format corpus covering exact match, duplicate invoice number, fuzzy number typo, tax-head mismatch, credit note, IMS accepted/rejected/pending state, ineligible ITC and supplier amendment. Require deterministic expected outcomes and accountant review before any monetary recovery claim.
- Status: Strong recovery-category challenger; potentially fast to pilot, but below freight until current IMS/GSTR-2B rule coverage and buyer economics are independently validated.

### Vendor-neutral lab automation + experiment evidence fabric
- Components: `sciencecorp/galago-tools@7ddf68c7bb7eda0243f6466cfbd6b97fdcfcf782` + `PyLabRobot/pylabrobot@c3c59eebf45c4f6bb2fc78dbfd30f6e458653494` + `swisscatplus/glas@764f79daabad5abc48ffe10c4b60db2f9270c8f9` + `qpillars/openapi-to-sila2@eff6e33e72be003eac3dd57e66333dac4e0a48e5` + `ORNL/flowcept@c000b10ea49659af6c5821b61918f3893bd46a92`.
- Combined capability: Heterogeneous legacy/vendor instrument gateways + broader hardware abstractions + workflow control plane + generated SiLA2 adapters for OpenAPI-capable instruments + end-to-end runtime provenance/lineage.
- Why the combination is stronger: The scarce part of lab automation is not a dashboard; it is getting incompatible instruments, legacy vendor runtimes and workflow state into one reliable, auditable execution fabric. Galago supplies unusually expensive device-specific integration work, GLAS supplies a permissive scheduler/control plane, OpenAPI-to-SiLA2 turns existing REST devices into standard endpoints, and Flowcept closes the reproducibility/evidence gap.
- Likely buyer / user: Biotech/pharma R&D labs, CROs, core facilities, assay-development teams and lab-automation integrators with heterogeneous instrument fleets.
- Build-time saved: Very high for a focused cell—potentially many months across instrument adapters, scheduling/control-plane plumbing and provenance. Hardware commissioning and vendor SDK validation remain unavoidable.
- Rights / license constraints: Galago and OpenAPI-to-SiLA2 are Apache-2.0; PyLabRobot, GLAS and Flowcept are MIT. Individual instrument SDKs/drivers, vendor runtimes and protocol implementations may impose separate terms; each adapter needs a rights/runtime matrix before commercial deployment.
- Validation step: Pick one simulated or lawfully accessible instrument plus one OpenAPI-described service, execute a multi-step workflow through the common control plane, record every command/input/output in Flowcept, and measure integration time, failure recovery and evidence completeness. Do not claim broad hardware support until each driver is hardware-validated.
- Status: Strong high-ticket integration opportunity with exceptional build-time compression; likely slower enterprise sales than freight recovery, so keep below the current fastest-cash leaders until a paid lab-integration wedge is validated.

### Warehouse slotting + layout ROI engine
- Components: `agritheory/inventory_tools@dd1e07d98eb81b2388acb922ce9ae3397a5af7ac` + `gokhanozden/gabak@711856814856e1730bd3be1cc7e4468ceca4fd5d`.
- Combined capability: Inventory movement/heat + dimensional fit/capacity + executable SKU/bin recommendations, independently evaluated against real/generated pick-list tours and alternate warehouse layouts/path models.
- Why the combination is stronger: Inventory Tools tells an ERPNext warehouse what to move; GABAK supplies the ERP-independent simulation/ROI layer needed to prove that the proposed slotting/layout actually lowers travel distance before physical disruption or write-back.
- Likely buyer / user: Distributors, 3PL warehouses, light manufacturers, warehouse consultants and ERPNext implementation partners.
- Build-time saved: High—months of slotting logic, warehouse geometry/tour simulation and experimental layout search are represented.
- Rights / license constraints: Both are MIT at the inspected revisions; Frappe/ERPNext dependencies apply only where that integration is used.
- Validation step: Create a neutral CSV geometry + pick-list adapter, compare current vs suggested slotting/layout on the same workload, report travel distance/capacity violations and translate distance reduction into transparent labor-dollar assumptions. Do not write changes automatically in the first pilot.
- Status: P1 technical discovery substantially resolved; next question is measured ROI and buyer willingness-to-pay, not finding another generic slotting algorithm.
