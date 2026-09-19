# MASTER

Cross-lane shortlist of the strongest validated discoveries.

## Rules
- Only include findings with inspected evidence.
- Deduplicate across lanes.
- Keep the strongest current opportunities near the top.
- Record commit/revision and license status.
- Do not include exposed secrets, private data, or accidentally published confidential material.

## Current leaders
## Seeded validated findings — 2026-09-19

### qx04222/openrental
- Commit: 013637e77fa9e11ce6aca32fb6218154d7265122
- Rights: Apache-2.0; commercially reusable subject to license/notice obligations.
- Why it is here: One-star but unusually complete equipment-rental ERP with fleet/availability, tiered and contract pricing, deposits treated correctly as liabilities, invoicing/receivables, maintenance, reporting and offline field inspections. A rare permissively licensed vertical system that can collapse months of rental-specific product work and support a hosted or managed offering.

### DominicFinn/open_tms
- Commit: 93d8c2b8ff78373ff69bb7ea546743e4703628b1
- Rights: MIT; directly reusable subject to license terms.
- Why it is here: Substantial active TMS/WMS product substrate with current EDI, shipment, carrier, reporting, tenancy, deployment, and logistics-domain work. Strongest immediate build-time compressor found in this pass for logistics products.

### dedupeio/dedupe
- Commit: 3f61e79102910bd355e920a2df7e44c14c9cb247
- Rights: MIT; directly reusable subject to license terms.
- Why it is here: Mature entity-resolution infrastructure that can become a shared matching layer across PermitPlate, CaptureBrief, freight/AP, and public-data products.

### getomni-ai/zerox
- Commit: 91bbb20c50de86067670aa13833afa1b8a73c22e
- Rights: MIT; directly reusable subject to license terms.
- Why it is here: Multi-format vision-model OCR/document extraction with Node/Python implementations and tests; useful across invoices, contracts, solicitation documents, permits, and scopes.

### MindPetal/sam-search
- Commit: 019b31dca0f980e79117a7c559777cb357a2a385
- Rights: MIT; directly reusable subject to license terms.
- Why it is here: Functioning, tested SAM.gov opportunity ingestion and scheduled-search plumbing that can shorten CaptureBrief's acquisition layer.

### microsoft/RulesEngine
- Commit: 5650f93f843865610240e0498b26b68b477a3920
- Rights: MIT; directly reusable subject to license terms.
- Why it is here: Mature deterministic rules/workflow execution layer suited to explainable audit, eligibility, pricing, approval, and exception logic.

### PyLabRobot/pylabrobot
- Commit: c3c59eebf45c4f6bb2fc78dbfd30f6e458653494
- Rights: MIT; directly reusable subject to license terms.
- Why it is here: Rare, broad cross-vendor lab-automation SDK that compresses specialized hardware-integration work; commercial fit needs a narrower buyer/workflow wedge.

### Fajendagba/Construction-Change-Order-Engine
- Commit: 60f5ab99bfb97647039e6cec280c246a10f8a856
- Rights: No license detected; inspect/learn/clean-room only unless permission is established.
- Why it is here: Concrete construction-domain reference for change-order state transitions, budget impacts, auditability, and event-driven workflows that can inform ScopeSignal.

### superzero11/OpenFarm
- Commit: 884a61567dd0d149214090baf9edebc533a2a0df
- Rights: BSD-3-Clause for repository code; third-party model and satellite/data-source terms require separate verification.
- Why it is here: Low-attention but unusually complete precision-ag substrate: PostGIS/FastAPI/Celery field platform plus real Sentinel-2 vegetation-index processing and FTW-based automatic field-boundary detection. It can compress months of geospatial/backend/worker work for a managed crop-health, field-onboarding or agronomy-monitoring product.

### D-ivy/renewables_indexes
- Commit: fe31ab507987a38cc9c042cd745d89546b6f25c0
- Rights: No license detected; inspect/learn/clean-room only unless permission is established. Upstream/derived dataset rights must be separately verified.
- Why it is here: 0-star national renewable-site screening artifact with committed CONUS resource × wholesale-price × revenue layers, negative-price/volatility features and spatial smoothing. Even though direct reuse is blocked and the visible build scripts are not fully reproducible, the data model and screening methodology expose a commercially useful clean-room blueprint for renewable/BESS development intelligence.

## Integrator promotions — 2026-09-19

### Kentucky-ai/opentakeoff
- Commit: `6ff9cc355e60d6312c0c82e2ddac56cb212cc394`.
- Rights: Apache-2.0; directly reusable subject to notice/license obligations.
- Inspected capability: Construction-specific calibrated PDF/image takeoff with count/linear/area measurements, material/roll-good calculations, browser and MCP surfaces, human/agent review states, provenance, exports and dedicated tests/benchmarks.
- Buyer/problem: Specialty contractors, estimators and GCs lose time and margin when drawing quantities and revisions are measured manually or cannot be defended later.
- Monetization path: Takeoff copilot or evidence-backed quantity-delta module for ScopeSignal; per-seat/project pricing or services-led change-order recovery. Commercial demand is plausible but still requires buyer/pilot validation.

### blencorp/capture-mcp-server
- Commit: `e91ce243cd6a62e9c2a55609d34a187fca89703b`.
- Rights: MIT for repository code; third-party provider/API terms remain separate.
- Inspected capability: Tested SAM.gov and USAspending tooling with award-type validation, PIID resolution, award/FPDS verification, recipient/agency/NAICS/PSC aggregation, plus deployment/auth surfaces and optional HigherGov/Tango connectors.
- Buyer/problem: GovCon capture teams spend expensive analyst hours reconstructing incumbent, competition, set-aside and agency buying history before deciding whether to pursue an opportunity.
- Monetization path: Premium evidence-backed CaptureBrief research/qualification layer or consultant workspace. Strong build-time compression; willingness-to-pay still needs direct pilot evidence.

### Polycentric-Labs/evidentia
- Commit: `0e0bc8bac7d8e4b71f729ac488fd3b47273f5531`.
- Rights: Apache-2.0 for repository code; verify framework/catalog content provenance independently.
- Inspected capability: Continuous compliance evidence/control plane with gap analysis, evidence storage, API/UI/MCP/GitHub surfaces, OSCAL assessment/POA&M, SARIF/OCSF/CycloneDX outputs and cryptographic signing paths.
- Buyer/problem: Regulated SaaS/MSPs and compliance consultants repeatedly gather, normalize and prove control evidence across audit cycles.
- Monetization path: Managed compliance-evidence service priced by environment/framework, especially when paired with deterministic evidence-generating controls such as restore drills. Buyer economics remain a hypothesis until a paid pilot.

### RamazanKara/restore-drill
- Commit: `dea374da3b340f53b798112eee82bd7ed1224572`.
- Rights: Apache-2.0 with LICENSE/NOTICE.
- Inspected capability: Automated disposable restore verification for PostgreSQL, MySQL/MariaDB, Redis and etcd with provider/runtime abstractions, validation, cleanup, parallel drills, evidence reporters, tests, Helm and CI/security scaffolding.
- Buyer/problem: SRE, regulated SaaS and MSP teams often know backups exist but cannot continuously prove that they are restorable within expected recovery objectives.
- Monetization path: Recurring “continuous restore proof” managed service or compliance/resilience evidence add-on. This is unusually close to a measurable operational outcome, but market/pricing validation is still required.

### benseverndev-oss/goldenmatch
- Commit: `d3516270570fc648759a3cc64ed24d80392d0b50`.
- Rights: MIT.
- Inspected capability: Fellegi-Sunter/EM entity resolution plus stable identity, merge/split, provenance/audit concepts, blocking/calibration/evidence gates and parity/out-of-core tests across a broader identity-control-plane architecture.
- Buyer/problem: AP, procurement, permit/property and public-data products lose precision when the same vendor/company/property exists under changing or inconsistent identities.
- Monetization path: Shared identity/matching service or managed data-cleanup layer; also a major cross-product build-time compressor. It is a challenger/complement to `dedupeio/dedupe`, not a replacement until an independent benchmark proves better precision/stability.

### hupe1980/en16931
- Commit: `894a3e0d36dea6d3dc086d066881d9a691b20882`.
- Rights: Apache-2.0; standards/rules update cadence and external artifacts must be tracked separately.
- Inspected capability: Canonical EN 16931 semantic invoice model with UBL 2.1, UN/CEFACT CII and ZUGFeRD bindings, conversion/validation/CLI, cross-syntax equivalence tests, conformance tests and hybrid-PDF structured-data extraction.
- Buyer/problem: AP/audit systems otherwise duplicate brittle format-specific parsers or send structured invoices through lossy OCR.
- Monetization path: Structured-invoice validation/conversion gateway and exact evidence path inside AP/freight recovery products; strongest as a component rather than a standalone U.S.-first business.

### fedspendingtransparency/usaspending-api
- Commit: `1692d484b38c66361c54faa221548527cae29964`.
- Rights: CC0-1.0 as reported for the official repository; preserve source-specific caveats.
- Inspected capability: Official USAspending.gov server/ETL implementation and schemas for federal award, procurement, recipient and spending data, with integration tests around procurement transactions, recipients and Delta-style data loading.
- Buyer/problem: GovCon intelligence products otherwise reverse-engineer historical award/recipient semantics from API output and risk inconsistent joins.
- Monetization path: Authoritative historical award/incumbent/spend evidence underneath CaptureBrief. The commercial moat comes from decisions/evidence and entity linkage, not from reselling public data alone.

### agritheory/inventory_tools
- Commit: `dd1e07d98eb81b2388acb922ce9ae3397a5af7ac`.
- Rights: MIT.
- Inspected capability: ERPNext warehouse-location optimizer using item movement heat, warehouse-plan walk distance, dimensional fit/capacity and executable putaway/default-warehouse updates, with tests.
- Buyer/problem: Distributors and light-manufacturing warehouses incur recurring picker/replenishment labor from poor slot placement but often lack specialist slotting software.
- Monetization path: Fixed-price re-slotting study plus recurring optimization or ERPNext app; measurable travel/labor ROI makes this a credible services-led wedge pending independent benchmark.

### freeacs/freeacs
- Commit: `f4c5d056ac6c247e0757de20acacd6046fd0ef0d`.
- Rights: MIT; dependency and standards/data-model terms remain separate.
- Inspected capability: Full TR-069/CWMP ACS with session/provisioning decisions, Get/Set parameter flows, downloads/firmware, reboot/factory-reset/transfer-complete paths, authentication modes, deployment assets and substantial integration fixtures/tests.
- Buyer/problem: Regional ISPs/WISPs and CPE vendors still carry legacy CWMP fleets that are operationally costly to provision, test and migrate.
- Monetization path: Managed ACS modernization, regression lab or TR-069-to-newer-management migration service. Technically strong and rights-clean; current buyer urgency and market size need explicit validation before outranking freight/GovCon/construction opportunities.
