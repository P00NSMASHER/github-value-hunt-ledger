# COMBINATIONS

Cross-repository product and capability combinations. This file keeps the strongest current combinations; superseded seed combinations are removed rather than duplicated.

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

## Active combinations — 2026-09-19

### Freight recovery v4 — source-to-settlement evidence chain
- Components: `DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1` + `sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc` + `vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408` + `hupe1980/en16931@894a3e0d36dea6d3dc086d066881d9a691b20882` + `sutasmantas/invoice-extraction-pipeline@337cac1fc43af32652683b353cb1cab3c765eb8b` + `getomni-ai/zerox@91bbb20c50de86067670aa13833afa1b8a73c22e` + `microsoft/RulesEngine@5650f93f843865610240e0498b26b68b477a3920` + `benseverndev-oss/goldenmatch@d3516270570fc648759a3cc64ed24d80392d0b50` or benchmarked `dedupeio/dedupe@3f61e79102910bd355e920a2df7e44c14c9cb247` + `apimeister/x12-types@e8238385d9f4a8a21b6e4525f5ab3acc7bed3978` + `yurii1exe/freight-dispatch-board@5128cd9af0e2dbacc37d3030ad8fc605da42168d` + settlement-allocation primitives from `europeanplaice/subset_sum@62fe41b4c8f5d287d1904f573a9594cac254d340` and/or `Etherlabs-dev/multi-processor-reconciliation@2f9397fbe56a76abeee42a01a37536ad1811a806`. No-license `Apeiron-OpenGrace/apeiron_bridge` and `drkcutie/kahayag@15fdcc1d85dce404b1c20de84cab0d4694c85c2f` are requirements/benchmark references only.
- Combined capability: Messy document or structured-invoice intake → page/line/method/reviewer provenance → attributable and effective-dated tariff version → deterministic weight/volume/W-M/minimum/break/accessorial rerating → shipment/EDI 210 comparison → evidence-linked dispute/recovery → X12 820 or other remittance/credit evidence → conservative many-to-many settlement allocation → success-fee proof.
- Why the combination is stronger: Kareya and Qatoto already closed the rights-clean rate-arithmetic/version-control gap. The new extraction pipeline adds an auditable correction trail, `x12-types` adds tested 210/820 typed parsing, `freight-dispatch-board` can generate internally consistent 204/status/210 lifecycle fixtures using explicitly synthetic rates, and the reconciliation kernels add fail-closed split/ambiguous settlement behavior. The remaining high-risk gap is no longer generic EDI or payment matching; it is getting real heterogeneous carrier contract tables and entitlement clauses into the canonical model without inventing terms.
- Likely buyer / user: High-volume shippers, freight-payment teams, 3PLs, manufacturers, distributors, brokers and forwarders.
- Build-time saved: Very high; months of TMS, freight-rate modeling, extraction/review, X12 lifecycle, rules, identity and settlement-allocation infrastructure are represented.
- Rights / license constraints: Open TMS, Qatoto, invoice-extraction-pipeline, Zerox, RulesEngine, GoldenMatch/Dedupe, freight-dispatch-board, subset_sum and Etherlabs reconciliation are MIT; Kareya and EN16931 are Apache-2.0. `x12-types` implementation is MIT OR Apache-2.0, but standards-derived transaction-definition metadata and third-party sample payloads require separate provenance/redistribution review. Carrier contracts/tariffs are customer/authority data with separate confidentiality and use rights. Apeiron/Kahayag remain inspect/clean-room only.
- Validation step: Build at least 20 lawful synthetic/public benchmark cases. Include borderless/transposed XLS/PDF rate tables, future/superseded revisions, 44/45-kg boundaries, volumetric divisors, W/M, minimums, fuel/accessorials, ambiguous clauses, duplicates, a 204→214/status→210 lifecycle, an 820 adjustment/remittance, duplicate/near-tie remittance candidates and one many-to-many credit allocation. Every asserted dollar must cite the exact source revision and rule; parsing, entitlement or settlement ambiguity must produce $0 asserted recovery.
- Status: Highest-priority commercial combination. Contract-table extraction and clause entitlement are now the single biggest product-risk blocker; the EDI/settlement benchmark can be built from rights-clean components now.

### CaptureBrief verified procurement intelligence + regulatory currency
- Components: `MindPetal/sam-search@019b31dca0f980e79117a7c559777cb357a2a385` + `blencorp/capture-mcp-server@e91ce243cd6a62e9c2a55609d34a187fca89703b` + `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964` + `cliwant/mcp-sam-gov@aaaaa70dcb6a08cf43cb40ece26b79d6d21c2463` + `1102tools-dev/federal-contracting-mcps@c3a137ace72dacca8026752820375dc957badc57` + GoldenMatch/Dedupe + Zerox + RulesEngine.
- Combined capability: Current opportunity ingest, solicitation packet evidence, historical award/incumbent/competition intelligence, recipient identity resolution, exact FAR/DFARS clause/prescription evidence, Acquisition.gov agency-deviation/FAR-Overhaul context and explainable bid/no-bid/readiness output.
- Why the combination is stronger: It can answer what is open, who won before, what exact regulatory text applies, whether the source was current and whether an agency deviation changes the practical answer. That is materially stronger than a generic SAM feed or RAG layer.
- Likely buyer / user: Federal primes/subcontractors, proposal/capture consultants, outsourced BD/compliance teams and specialist GovCon research firms.
- Build-time saved: Very high—months of source-specific integration, PIID/entity edge cases, procurement/regulatory retrieval, fault handling and evidence packaging.
- Rights / license constraints: sam-search, capture-mcp, cliwant, 1102tools, GoldenMatch, Zerox and RulesEngine are MIT; official USAspending is CC0-1.0. Government-source applicability remains contextual and human-reviewed.
- Validation step: For 10 current solicitations, manually verify opportunity facts, UEI/PIID/IDV joins, incumbent/history, every cited FAR/DFARS clause/prescription, eCFR snapshot currency and any controlling Acquisition.gov agency deviation. Score false joins and unresolved/error honesty.
- Status: High-priority CaptureBrief architecture; stop generic SAM/regulatory-wrapper discovery and work correctness/packet-completeness benchmarks.

### ScopeSignal drawing/model-to-dollar change evidence
- Components: `Kentucky-ai/opentakeoff@6ff9cc355e60d6312c0c82e2ddac56cb212cc394` + `delongwangshu49-hub/bimchange-agent@cd7fd6e6522e060b7847f0daaed00979097da7dd` + Zerox + RulesEngine + clean-room state/budget concepts from no-license `Fajendagba/Construction-Change-Order-Engine@60f5ab99bfb97647039e6cec280c246a10f8a856`.
- Combined capability: IFC old/new correspondence with deterministic evidence + calibrated 2D measurements/quantities + extracted contract/spec evidence + deterministic triggers → human-reviewed quantity delta and proposed commercial/schedule impact.
- Why the combination is stronger: BIMChange-Agent closes much of the IFC correspondence problem and OpenTakeoff supplies rights-clean 2D quantity/provenance. Entitlement remains a separate evidence gate instead of assuming every detected change is compensable.
- Likely buyer / user: Specialty subcontractors, GCs, BIM/VDC teams, quantity surveyors, estimators and project-controls/claims teams.
- Build-time saved: Very high across IFC revision matching, plan calibration/measurement, provenance and review.
- Rights / license constraints: BIMChange-Agent, Zerox and RulesEngine are MIT; OpenTakeoff is Apache-2.0. The Fajendagba repository has no license and contributes clean-room requirements only.
- Validation step: One held-out IFC old/new pair and one PDF-plan old/new pair must preserve revision/element identity through quantity delta and attached contract/spec entitlement evidence. Human approval is mandatory before proposed dollars.
- Status: Strong; 2D cross-revision correspondence and entitlement-to-dollar validation remain the gaps.

### Compliance modernization + recovery-evidence proof
- Components: `clay-good/attestful@c445095952d6e1ca27eadc638b1bfe96e8f5f00d` + `williamzujkowski/oscalize@39c283b54e14b71df72e1b8327b593f560adcbe6` + `Polycentric-Labs/evidentia@0e0bc8bac7d8e4b71f729ac488fd3b47273f5531` + `RamazanKara/restore-drill@dea374da3b340f53b798112eee82bd7ed1224572` + optional PostgreSQL/Restic proof worker `techdev-lab/restorelab@24716864885b7201511a7d18d1754a0609a729d5`.
- Combined capability: Collect read-oriented cloud/SaaS evidence, convert legacy artifacts to OSCAL, normalize/store/sign evidence and gap state, then generate operational disaster-recovery evidence from disposable restores with contract-defined checks.
- Why the combination is stronger: Attestful supplies evidence acquisition, Evidentia supplies the evidence/control plane, restore-drill supplies multi-engine restore execution, and RestoreLab adds a hardened narrowly scoped Postgres/Restic proof worker with explicit real-world compatibility findings. The paid outcome becomes reproducible evidence rather than a checklist.
- Likely buyer / user: FedRAMP/ATO consultants, SOC 2/ISO/NIST programs, regulated SaaS, MSP/MSSP and internal compliance/SRE teams.
- Build-time saved: Potentially 7–15 months across collectors, OSCAL conversion, evidence lineage/control mapping, restore orchestration and reporting.
- Rights / license constraints: Attestful and RestoreLab are MIT; Evidentia and restore-drill are Apache-2.0; oscalize treatment is as cataloged. Bundled framework/catalog content, cloud APIs and backup tooling retain separate terms.
- Validation step: Inventory the top collector permissions/read-only semantics, then run one synthetic AWS/GitHub evidence bundle plus one disposable PostgreSQL restore into a versioned control package. Inject one failed restore and one missing-evidence case and require non-pass output.
- Status: Strong standalone challenger; remaining work is permission/provenance hardening and a reproducible paid-pilot evidence package, not more generic collector discovery.

### TR-069 → USP dual-stack modernization and regression lab
- Components: `freeacs/freeacs@f4c5d056ac6c247e0757de20acacd6046fd0ef0d` + `OktopUSP/oktopus@e1f07d71a93c4169421f2e94ce6605746ece37ad` + `BroadbandForum/obuspa@59028beba21471d19bd3842ef2632ceb6ca8c7fc` + `OktopUSP/agent-sim@d90b08dfa59276f28dfcc18cb35c522f356227a5`.
- Combined capability: Legacy CWMP ACS management + unified CWMP/USP controller + official modern USP agent + rights-clean simulated USP fleet for migration rehearsal, interoperability, regression and controller load testing.
- Why the combination is stronger: It provides a complete rights-clean bridge from legacy management through modern device-side USP plus simulation rather than relying on unrelated stacks or an unlicensed simulator.
- Likely buyer / user: Regional ISPs/WISPs, broadband/CPE OEMs, ACS/USP vendors and telecom QA/certification labs.
- Build-time saved: Many months of controller, agent, transport and simulation plumbing.
- Rights / license constraints: FreeACS is MIT; Oktopus and agent-sim are Apache-2.0; OB-USP-Agent is BSD-3-Clause. Broadband Forum data-model/specification redistribution terms and device-vendor firmware terms remain separate.
- Validation step: Reproduce CWMP Get/Set/download and USP Get/Set/Operate/Notify over MQTT/WebSocket, then run concurrent simulated agents and verify tenant isolation/migration-state behavior.
- Status: Rights-clean technical path exists; focus on scale, tenancy, migration fixtures and buyer urgency rather than generic component discovery.

### GST input-tax reconciliation and exception recovery
- Components: `Tamil-Venthan/Rekvia@158d199e4f08041e587a70926f2ed22d17511431` + `microsoft/RulesEngine@5650f93f843865610240e0498b26b68b477a3920` + GoldenMatch/Dedupe + authoritative GST/GSTR-2B/IMS rules and taxpayer-owned purchase-register data; Zerox only for supporting documents when structured exports are unavailable.
- Combined capability: Deterministic purchase-register↔GSTR-2B matching, duplicate-safe invoice correspondence, supplier identity normalization, versioned eligibility/control rules, exception queues and human-reviewed follow-up for missing/mismatched ITC-related records.
- Why the combination is stronger: Rekvia supplies a functioning vertical reconciliation core; RulesEngine separates changing tax logic from matching code and entity resolution reduces supplier/GSTIN fragmentation.
- Likely buyer / user: Indian SMEs, outsourced accounting firms, chartered-accountant practices and finance shared-services teams.
- Build-time saved: Medium-high; weeks to months on ingestion, matching, duplicate handling, exception reporting and operator UX.
- Rights / license constraints: Rekvia, RulesEngine and GoldenMatch are MIT. Government rules/data, taxpayer records and portal/API access are separate; no automated filing or tax-recovery representation without authoritative-rule validation and human review.
- Validation step: A versioned corpus must cover exact/fuzzy/duplicate match, credit note, IMS accepted/rejected/pending state, amendment and ineligible/reversal cases with accountant review before monetary claims.
- Status: Strong recovery-category challenger, but below freight until current IMS rule coverage and buyer economics are measured.

### Vendor-neutral lab automation + experiment evidence fabric
- Components: `sciencecorp/galago-tools@7ddf68c7bb7eda0243f6466cfbd6b97fdcfcf782` + `PyLabRobot/pylabrobot@c3c59eebf45c4f6bb2fc78dbfd30f6e458653494` + `swisscatplus/glas@764f79daabad5abc48ffe10c4b60db2f9270c8f9` + `qpillars/openapi-to-sila2@eff6e33e72be003eac3dd57e66333dac4e0a48e5` + `ORNL/flowcept@c000b10ea49659af6c5821b61918f3893bd46a92`.
- Combined capability: Heterogeneous legacy/vendor instrument gateways + broader hardware abstractions + workflow control plane + generated SiLA2 adapters + end-to-end runtime provenance/lineage.
- Why the combination is stronger: It attacks the expensive part of lab automation—vendor/runtime integration, scheduling and reproducibility—rather than another dashboard.
- Likely buyer / user: Biotech/pharma R&D labs, CROs, core facilities, assay teams and lab-automation integrators.
- Build-time saved: Very high for a focused automation cell; potentially many months.
- Rights / license constraints: Galago and OpenAPI-to-SiLA2 are Apache-2.0; PyLabRobot, GLAS and Flowcept are MIT. Individual instrument SDKs/runtimes require per-adapter rights review.
- Validation step: One simulated or lawfully accessible instrument plus one OpenAPI service must execute a multi-step workflow with complete Flowcept lineage and measured integration/failure-recovery time.
- Status: Strong high-ticket integration opportunity; likely slower sales than freight.

### Warehouse slotting + layout ROI engine
- Components: `agritheory/inventory_tools@dd1e07d98eb81b2388acb922ce9ae3397a5af7ac` + `gokhanozden/gabak@711856814856e1730bd3be1cc7e4468ceca4fd5d`.
- Combined capability: Inventory movement/heat + dimensional fit/capacity + executable SKU/bin recommendations, independently evaluated against pick-list tours and alternate warehouse layouts/path models.
- Why the combination is stronger: Inventory Tools can recommend what to move while GABAK supplies an ERP-independent simulation/ROI layer to prove travel reduction before operational disruption.
- Likely buyer / user: Distributors, 3PL warehouses, light manufacturers, warehouse consultants and ERPNext partners.
- Build-time saved: High—months of slotting logic, warehouse geometry/tour simulation and experiment design.
- Rights / license constraints: Both are MIT; ERPNext/Frappe dependencies apply only where that integration is used.
- Validation step: Neutral CSV geometry + pick-list benchmark comparing current vs suggested slotting/layout, with transparent capacity violations, travel savings and labor-dollar assumptions. No automatic write-back in the first pilot.
- Status: Technical discovery substantially resolved; next question is measured ROI and willingness-to-pay.

### Contact-center workforce assurance
- Components: `rodrigo-arenas/pyworkforce@ca4892502d2d92cc996c9fde96293ff90b560426` + clean-room operational invariants from no-license `davescalante/LCC-WFM@d11905dafb7dced6e889c4f3f9c491863770f4f6` + clean-room evaluation methodology from no-license `Emma-V/support-triage@f12f682eda87ddbf1593200ad515b464b04c00ff`.
- Combined capability: Demand/intent forecast → required staffing → skill mix → shifts/rosters/breaks → planned-vs-actual/adherence/overtime/payroll assurance with abstention on uncertain classification.
- Why the combination is stronger: Pyworkforce supplies the rights-clean optimization core while the two inspect-only repositories contribute domain edge cases/evaluation discipline for an independent implementation.
- Likely buyer / user: BPOs, contact centers and support operations with multiskill queues and high labor costs.
- Build-time saved: Months on solver primitives plus weeks of domain discovery.
- Rights / license constraints: pyworkforce is MIT. LCC-WFM and support-triage are inspect/learn/clean-room only; their source/test text/data must not be copied absent permission.
- Validation step: Customer-owned or synthetic half-hour demand/AHT/SLA data; compare paid hours, SLA coverage and overtime against spreadsheet baseline.
- Status: Promising but lower priority than freight, GovCon, construction and compliance until a paid buyer problem is validated.

### Field onboarding + crop monitoring
- Components: `superzero11/OpenFarm@884a61567dd0d149214090baf9edebc533a2a0df` + `RS-iCM/RSCM` at the cataloged revision.
- Combined capability: Derive/ingest field boundaries and crop/non-crop masks, then run recurring vegetation-index, soil, weather and alert workflows inside a deployable field-operations platform.
- Why the combination is stronger: RSCM attacks label/bootstrap while OpenFarm supplies the operational PostGIS/worker/Sentinel-2/alert workflow around it.
- Likely buyer / user: Crop insurers, agricultural lenders, agronomy firms, specialty-crop managers, ag retailers and land-use monitoring programs.
- Build-time saved: Potentially 9–15 months for a focused MVP.
- Rights / license constraints: OpenFarm is BSD-3-Clause and RSCM is MIT at the inspected revisions; data/model/source terms remain separate.
- Validation step: Lawful 50–100-field benchmark comparing derived boundaries/masks against known polygons and alert precision/stability.
- Status: Strong agriculture combination but below faster-cash leaders until paid demand is proven.
