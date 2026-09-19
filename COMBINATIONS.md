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
- Status: High-priority combination for deeper validation.

### CaptureBrief evidence stack
- Components: MindPetal/sam-search + getomni-ai/zerox + dedupeio/dedupe + microsoft/RulesEngine.
- Combined capability: SAM.gov opportunity retrieval + solicitation/document extraction + entity resolution + explainable qualification rules.
- Why the combination is stronger: Converts raw opportunities into structured, evidence-linked, customer-specific qualification rather than a simple feed.
- Likely buyer / user: Small and midsize federal contractors that need faster opportunity triage.
- Build-time saved: High for ingestion, document processing, matching, and deterministic policy logic.
- Rights / license constraints: All four are MIT in the revisions inspected.
- Validation step: Map SAM fields and attached documents into a single opportunity evidence schema and run against a small sample of current opportunities.
- Status: High-priority enhancement to CaptureBrief.

### ScopeSignal change-to-change-order pipeline
- Components: getomni-ai/zerox + microsoft/RulesEngine + clean-room concepts from Fajendagba/Construction-Change-Order-Engine.
- Combined capability: Extract scope/document changes, evaluate deterministic triggers, and route accepted changes through a construction-specific approval/budget-impact state model.
- Why the combination is stronger: Connects upstream document intelligence to an operationally credible downstream change-order workflow.
- Likely buyer / user: General contractors and specialty subcontractors that lose margin when scope changes are identified late or documented poorly.
- Build-time saved: High for document ingestion/rules plus substantial architecture guidance.
- Rights / license constraints: Zerox and RulesEngine are MIT. Construction-Change-Order-Engine has no license, so only independently reimplemented concepts may be used absent permission.
- Validation step: Find permissively licensed RFI/submittal/document-diff components and test one end-to-end synthetic scope-change case.
- Status: Strong concept; upstream detection component still incomplete.

### Field-onboarding + crop-monitoring stack
- Components: superzero11/OpenFarm + RS-iCM/RSCM.
- Combined capability: Automatically derive/ingest field boundaries and crop/non-crop masks, then run recurring vegetation-index, soil, weather and alert workflows inside a deployable field-operations platform.
- Why the combination is stronger: RSCM attacks the expensive label/bootstrap problem, while OpenFarm supplies the missing operational system around it: PostGIS field records, workers, Sentinel-2 processing, boundary detection, alerts and field workflows. Together they can turn a region with weak customer field data into a monitorable portfolio much faster than building both model and platform from scratch.
- Likely buyer / user: Crop insurers, agricultural lenders, agronomy firms, specialty-crop managers, ag retailers/input distributors and land-use monitoring programs.
- Build-time saved: Potentially 9–15 months of remote-sensing, geospatial-backend, worker and field-onboarding scaffolding for a focused MVP.
- Rights / license constraints: OpenFarm is BSD-3-Clause and RSCM is MIT at the inspected revisions. Sentinel-2/STAC endpoints, FTW checkpoint/model, example datasets and other third-party data/model terms require separate verification.
- Validation step: Select a lawful 50–100-field benchmark, compare generated boundaries/crop masks against known polygons, then measure whether the combined system produces stable per-field index histories and useful alert precision without manual field setup.
- Status: Strong new agriculture combination; best immediate differentiator is automatic portfolio onboarding followed by exception-driven scouting rather than another generic farm dashboard.

## Integrator combinations — 2026-09-19

### Freight recovery v2 — contract-to-cash evidence chain
- Components: `DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1` + `hupe1980/en16931@894a3e0d36dea6d3dc086d066881d9a691b20882` + `getomni-ai/zerox@91bbb20c50de86067670aa13833afa1b8a73c22e` + `microsoft/RulesEngine@5650f93f843865610240e0498b26b68b477a3920` + `benseverndev-oss/goldenmatch@d3516270570fc648759a3cc64ed24d80392d0b50` (or benchmarked `dedupeio/dedupe`) + clean-room rate-card parser requirements learned from `Apeiron-OpenGrace/apeiron_bridge@2f854b37435490a102eb9cadb22b0e878f1af17d`.
- Combined capability: Shipment/EDI context, exact structured-invoice parsing when available, OCR fallback, canonical vendor/carrier identity, versioned contract/rate ingestion, deterministic rerating, evidence-linked exceptions and recovery workflow.
- Why the combination is stronger: The earlier freight stack was missing the hardest domain-specific input: negotiated rate-card/clause ingestion. The Apeiron inspection supplies a concrete clean-room specification for borderless/transposed carrier tables while EN16931 lets structured invoices bypass OCR entirely. This moves the stack from “generic invoice anomaly detection” toward defensible billed-vs-contracted recovery.
- Likely buyer / user: 3PLs, manufacturers, distributors, freight-payment teams and high-volume shippers.
- Build-time saved: Very high; most generic TMS/document/rules/identity plumbing is reusable, leaving carrier-contract adapters, exact freight audit rules and settlement workflow as the differentiated build.
- Rights / license constraints: open_tms, Zerox and RulesEngine are MIT; EN16931 is Apache-2.0; GoldenMatch is MIT. Apeiron Bridge has no detected license, so no source may be copied—only independently reimplemented behavior/specification. Carrier contracts/tariffs remain customer/authority data with their own terms.
- Validation step: Create 20 synthetic but realistic contract+invoice cases covering borderless tables, transposed zones, weight breaks, accessorial clauses and effective-date changes; require exact rerating and evidence citations with zero recovery on ambiguous parses.
- Status: Highest-priority commercial combination; materially stronger than the seeded freight stack.

### CaptureBrief verified procurement intelligence
- Components: `MindPetal/sam-search@019b31dca0f980e79117a7c559777cb357a2a385` + `blencorp/capture-mcp-server@e91ce243cd6a62e9c2a55609d34a187fca89703b` + `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964` + `benseverndev-oss/goldenmatch@d3516270570fc648759a3cc64ed24d80392d0b50`/`dedupeio/dedupe` + Zerox + RulesEngine; optional vendor-screening module from `nasa/889-Compliance-SAM-Tool-@4ab7be882b2d9687a0e863652cefce8d10581339` after current-rule revalidation.
- Combined capability: Current opportunity ingest, solicitation-document evidence, historical award/incumbent/competition intelligence, vendor/recipient identity resolution and explainable bid/no-bid or partner-risk decisions.
- Why the combination is stronger: SAM feeds alone answer “what is open”; USAspending/capture-mcp answer “who buys, who won, how competitive, under what set-aside/award structure,” turning CaptureBrief into decision support rather than another opportunity alert service.
- Likely buyer / user: Small/midsize federal primes, proposal/capture consultants and outsourced BD teams.
- Build-time saved: High—months of source adapters, award normalization, PIID/entity edge cases, document extraction and rules plumbing are already represented in permissive components.
- Rights / license constraints: sam-search/capture-mcp/GoldenMatch/Zerox/RulesEngine are MIT; official USAspending repo is CC0-1.0; NASA tool Apache-2.0. Third-party API terms (e.g. optional HigherGov/Tango) remain separate and are not required for the rights-clean core.
- Validation step: For 10 current solicitations, generate a cited packet containing opportunity facts, incumbent/recipient history, agency/NAICS/PSC spend, competition/set-aside evidence and confidence-linked entity joins; manually score factual precision and decision usefulness.
- Status: High-priority; strongest CaptureBrief architecture found so far.

### ScopeSignal drawing-to-dollar change evidence
- Components: `Kentucky-ai/opentakeoff@6ff9cc355e60d6312c0c82e2ddac56cb212cc394` + Zerox + RulesEngine + clean-room state/budget concepts from `Fajendagba/Construction-Change-Order-Engine@60f5ab99bfb97647039e6cec280c246a10f8a856`; `braedonsaunders/bidwright@6f33cdd41d1e3e1aafd31a73f684980b552ffd96` only as AGPL-compliant deployment or clean-room reference for estimating/revision linkage.
- Combined capability: Calibrated old/new plan measurement with provenance, extracted scope/spec evidence, deterministic change triggers, quantity deltas and a defensible path into priced/approved change-order workflow.
- Why the combination is stronger: OpenTakeoff closes the earlier upstream measurement gap with a rights-clean 2D quantity substrate and explicit review/provenance. The remaining differentiator is revision correspondence and contract entitlement, not basic takeoff mechanics.
- Likely buyer / user: Specialty subcontractors, GCs, estimators and project controls teams that lose margin on undocumented scope growth.
- Build-time saved: High; months of plan rendering/calibration/geometry/export/review plumbing plus generic document/rules work can be reused.
- Rights / license constraints: OpenTakeoff is Apache-2.0; Zerox/RulesEngine MIT. Fajendagba repo has no license and Bidwright is AGPL-3.0-only, so closed-source use must be clean-room unless AGPL obligations are deliberately accepted.
- Validation step: Run a known old/new drawing pair, preserve calibration/provenance, detect quantity deltas, link each delta to changed drawing/spec evidence, and require a human reviewer to approve before any dollar impact is asserted.
- Status: Strong; now blocked more by revision/entitlement validation than takeoff technology.

### Compliance modernization + continuous recovery proof
- Components: `williamzujkowski/oscalize@39c283b54e14b71df72e1b8327b593f560adcbe6` + `Polycentric-Labs/evidentia@0e0bc8bac7d8e4b71f729ac488fd3b47273f5531` + `RamazanKara/restore-drill@dea374da3b340f53b798112eee82bd7ed1224572` + selected MIT credential-separation patterns/components from `danieltamas/fortified@c677ef30f750e1cc0b761dd9eed3bab2b40d18f4`.
- Combined capability: Convert legacy SSP/POA&M artifacts to machine-readable OSCAL, maintain continuous signed evidence/gap state, and generate actual disaster-recovery control evidence from automated restore drills rather than screenshots/checklists.
- Why the combination is stronger: It creates a services-to-recurring-SaaS ladder: a fixed-price modernization project opens the account, then continuous evidence and restore proof create ongoing value and measurable control outcomes.
- Likely buyer / user: FedRAMP/ATO consultants, regulated SaaS vendors, MSP/MSSPs and internal compliance/SRE teams.
- Build-time saved: Potentially 4–9 months across conversion, evidence lineage, standards outputs, restore orchestration, reporting and deployment.
- Rights / license constraints: oscalize states NIST/public-domain/CC0-style treatment; Evidentia and restore-drill are Apache-2.0; Fortified is MIT. Evidentia framework/catalog content and any third-party templates still need provenance/redistribution review.
- Validation step: Convert one synthetic/public SSP+POA&M package, validate OSCAL output, run one Postgres restore drill, map that evidence into the control package, and measure manual corrections plus time saved versus spreadsheet evidence gathering.
- Status: Strong new standalone opportunity; commercially promising but not yet buyer-validated.

### TR-069 fleet modernization and regression lab
- Components: `freeacs/freeacs@f4c5d056ac6c247e0757de20acacd6046fd0ef0d` + `netcwmp/netcwmp@c0f7cb0d9ebf7178f96c705741ac137d6c9ba16f` + independently reimplemented synthetic-fleet behavior learned from no-license `Viasat/cwmp-cpe-horde@aa29d259a290dc16b06951c17af628fb739829b0` + externally referenced Broadband Forum CWMP data models after rights verification.
- Combined capability: Working ACS server + controllable CPE client + synthetic regression fleet + standards-aware parameter/model compatibility checks for provisioning changes and migration programs.
- Why the combination is stronger: FreeACS alone manages devices; adding a reproducible virtual fleet and model-version diff turns it into a safer preflight/certification/migration service with obvious operational buyers.
- Likely buyer / user: Regional ISPs/WISPs, CPE/router vendors, ACS vendors and telecom QA teams.
- Build-time saved: Many months of CWMP session/provisioning/device-side protocol logic; synthetic-fleet and standards layers still need clean-room/rights work.
- Rights / license constraints: FreeACS is MIT; netcwmp Apache-2.0. cwmp-cpe-horde has no detected license, so source is reference-only. Broadband Forum model redistribution rights are unresolved and must be verified before bundling.
- Validation step: Isolated lab with FreeACS + netcwmp; reproduce bootstrap/boot/periodic inform, Get/Set, download and connection-request flows, then add 100+ synthetic devices and compare parameter coverage against an external BBF model source without republishing restricted content.
- Status: Specialist high-ticket opportunity; queue for market/rights validation before major build effort.

### Contact-center workforce assurance
- Components: `rodrigo-arenas/pyworkforce@ca4892502d2d92cc996c9fde96293ff90b560426` + clean-room operational invariants from no-license `davescalante/LCC-WFM@d11905dafb7dced6e889c4f3f9c491863770f4f6` + clean-room evaluation methodology from no-license `Emma-V/support-triage@f12f682eda87ddbf1593200ad515b464b04c00ff`.
- Combined capability: Demand/intent forecast → required staffing → skill mix → shifts/rosters/breaks → planned-vs-actual/adherence/overtime/payroll assurance with abstention on uncertain classification.
- Why the combination is stronger: Pyworkforce supplies the rights-clean optimization core, while the two no-license repositories expose realistic edge cases and evaluation discipline that a generic scheduler lacks.
- Likely buyer / user: BPOs, contact centers and support operations with multiskill queues and high labor cost.
- Build-time saved: Months on solver primitives plus weeks of domain discovery/acceptance-test design.
- Rights / license constraints: pyworkforce is MIT. LCC-WFM and support-triage are inspect/learn/clean-room only; no source, creative test text or dataset content should be copied absent permission.
- Validation step: Use customer-owned or synthetic half-hour demand/AHT/SLA data to produce staffing/roster/break plans, then compare paid hours, SLA coverage and overtime against a spreadsheet baseline.
- Status: Promising but lower priority than freight, GovCon, construction and compliance until a paid buyer problem is validated.
