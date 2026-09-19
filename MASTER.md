# MASTER

Elite cross-lane positive training set. This file is intentionally smaller than the hunter catalogs: only discoveries that materially compress a high-value product, provide rare evidence/data/protocol/decision infrastructure, or directly strengthen an active commercial stack belong here. Lane-local strong/watch candidates remain in `hunters/*.md`.

## Rules
- Promotion normally requires **24+/30** on A speed to first revenue, B plausible ACV/ceiling, C build-time/domain compression, D rarity/data/technical advantage, E evidence/completeness and F rights/reuse clarity.
- Preserve exact revision and rights. Public visibility is not a reuse grant; no-license/proprietary code remains clean-room/reference only unless separate permission exists.
- Prefer source/tests/schemas/deployments over README claims. Unknown or conflicting evidence remains unknown/review.
- A promoted component must have a named buyer/problem, monetization path and first paid wedge, or be uniquely important to a stronger stack.
- Commodity OCR, generic rules, generic CRUD and generic fuzzy matching are combination dependencies, not MASTER leaders unless a future finding proves a rare advantage.

## Current leaders — 2026-09-19

### kodekinetics79/opstrax-enterprise-build
- Commit: `fec2ba1432d6f8b4ba4c48be3d58e7e096819045`.
- Rights: no public repository license; on 2026-09-19 the user stated they hold separate permission for commercial modification and deployment. Do not infer redistribution/sublicensing rights.
- Score: **29/30** — A5 B5 C5 D5 E5 F4.
- Capability: production-oriented logistics platform with geofence Entry/Exit evidence, appointment-linked dwell, later-of appointment/arrival billable clocks, tenant/customer detention rules, pre-expiry notices, fail-closed pricing, SHA-linked evidence bundles, approval and exactly-once detention billing.
- Buyer/problem: shippers, brokers, carriers and freight-payment teams need physical proof for detention/accessorial decisions rather than invoice text alone.
- Monetization / first paid wedge: physical-evidence layer inside Freight Recovery; run one authorized blind shipment population and quantify missed/unsupported detention dollars.
- Why it wins: connects real-world movement and appointment events to entitlement, evidence, approval and billing—the hardest part of time-based accessorial recovery.
- Implementation proof: the permissioned Opstrax semantics remain the physical-truth plane in Freight Recovery v11. The full v11 suite passes **85/85 tests**. A new bridge freezes Opstrax dwell facts into a physical-only SHA, then lets the separately licensed Trenova policy plane calculate money under the controlling contract, avoiding circular proof. The original 3-hour/2-free-hour/$75 regression remains intact.

### emoss08/Trenova
- Commit: `95fcf816562025ad9af864ded4a5fce8a555bd65`.
- Rights: the public repository revision is FSL-1.1-ALv2, but on 2026-09-19 the user stated they hold a separate commercial license for this exact revision. Treat commercial integration for the user's project as authorized; do not infer redistribution, sublicensing, hosted-service or other rights beyond that separate agreement.
- Score: **29/30** — A5 B5 C5 D5 E4 F5.
- Capability: unusually complete trucking money/workflow plane spanning shipments/dispatch, rate agreements and rate confirmations, versioned RateCon parsing rules/fixtures, auto-rating, detention policy/evidence/notice/tiering/caps, billing queue rerating and rate-departure leakage, inbound EDI 210 carrier-invoice matching with variance tolerance/audit/reconciliation, disputes/adjustments/settlement, documents, reporting, RBAC and tenant controls.
- Buyer/problem: Freight Recovery needs one coherent transaction/evidence/settlement state machine around its independent audit math, not another disconnected parser or calculator.
- Monetization / first paid wedge: commercial operating substrate inside the Freight Audit Acceptance Test and managed recovery workflow; keep independent evidence/rerating oracles around it to prevent circular truth.
- Why it wins: it directly covers several hard policy/workflow dimensions that previously forced `REVIEW_ZERO_ASSERTION`, while also collapsing TMS, billing, carrier-settlement, document and reporting plumbing into one freight-native system.
- Implementation proof: Freight Recovery v11 core v1.0 commercially integrates the licensed detention-policy and inbound carrier-invoice matching semantics while preserving separate physical-truth and policy/calculation hashes. Regression suite passes **85/85 tests**. Artifact: `freight-v11-core-v1.0-trenova-integrated.zip`.
- Caveat: Trenova describes itself as pre-release/source-available software; exact production deployment, redistribution and hosted-service rights remain governed by the user's separate commercial agreement.

### DominicFinn/open_tms
- Commit: `93d8c2b8ff78373ff69bb7ea546743e4703628b1`.
- Rights: MIT.
- Capability: active freight/TMS/WMS substrate with shipment, carrier, EDI, reporting, tenancy, deployment and financial/logistics workflows.
- Buyer/problem: freight-payment, shipper and 3PL teams need operational truth and workflow around audit/recovery.
- Monetization / first paid wedge: operational substrate for the paid freight-audit acceptance test rather than a standalone generic TMS launch.
- Why it still matters: broad MIT logistics plumbing remains useful as an independent rights-clean comparator/reference, but the licensed Trenova revision now supersedes it as the primary commercial freight workflow substrate.

### sengtha/Kareya-Silo
- Commit: `a43eedea03add0728eadfc1f8ea35cc3ca6867cc`.
- Rights: Apache-2.0; commercial carrier/customer rates are separate authorized data.
- Capability: deterministic freight tariff/rating engine with effective-dated carrier/mode/service/lane tariffs, weight bands, minimums and per-kg/per-CBM/W-M/container/shipment/document/piece/percent bases; tests cover key boundary math.
- Buyer/problem: a recovery claim is not defensible if contracted-vs-billed math cannot be reproduced exactly.
- Monetization / first paid wedge: rerate a frozen customer-authorized invoice population against reviewed tariff facts.
- Why it wins: freight-specific deterministic money math is much stronger than generic rules or LLM pricing.

### vidyesh95/qatoto-backend — provider freight-rate subsystem
- Commit: `4f5f270f6ba5ef3ed4b230716997ccea049ce408`.
- Rights: MIT.
- Capability: provider-authored, versioned freight rate cards with origin/destination/mode/currency/effective windows, break ladders, minimums, volumetric divisors and explicit supersession validation.
- Buyer/problem: parsed rates are unsafe unless author, effective period and supersession are provable.
- Monetization / first paid wedge: tariff-authority/version plane ahead of Kareya rerating.
- Why it wins: controls the provenance/version error that can manufacture false recovery dollars even when arithmetic is correct.

### A-Jatin/freight-ratecon-extraction
- Commit: `a3dbbfec7f6b042176880d06c5114f81f29e57eb`.
- Rights: MIT for code; bundled/sample document provenance is not assumed commercially reusable without separate confirmation.
- Score: **29/30** — A5 B5 C5 D5 E5 F4.
- Capability: evidence-gated freight Rate Confirmation parser separating model span selection from deterministic interpretation, arithmetic and normalization; roughly 206 offline tests cover incomplete stops, ambiguous dates/totals, multiple totals, charge reconciliation and wrong-document cases.
- Buyer/problem: Freight Recovery still needs controlling contract/rate-confirmation truth from messy authorized PDFs without silently turning uncertain extraction into money.
- Monetization / first paid wedge: process one customer-authorized RateCon batch into source-grounded reviewed facts before Qatoto/Kareya rerating.
- Why it wins: it directly closes the highest-value remaining freight document-authority gap and already treats money-relevant ambiguity as a review condition rather than a guess.

### warpfreight/warp-agent-mcp
- Commit: `1850556032b465a0c24839e28564687462067323`.
- Rights: MIT; live customer/Warp records require authorization and applicable provider terms.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Capability: authenticated read-only access to quote/booking history, tracking/events, delivered-shipment invoices and BOL/POD/customs documents with conservative comparison behavior.
- Buyer/problem: freight pilots otherwise lose weeks assembling transaction evidence.
- Monetization / first paid wedge: read-only delivered-shipment evidence bridge for an authorized blind audit population.
- Why it wins: one connector reaches multiple real freight evidence objects without joining the money-moving path.

### OmarFaig/Assay
- Commit: `821303935ef2855908a9a9bd1efd4c33f9cd39d2`.
- Rights: MIT; model weights/datasets/inference runtimes remain separate.
- Score: **29/30** — A5 B4 C5 D5 E5 F5.
- Capability: selective-prediction document extraction with field-level constrained-decoding evidence, legal-alternative awareness, arithmetic penalties, calibration, review routing and evaluation.
- Buyer/problem: audit/recovery products cannot tolerate low-confidence extracted facts silently becoming dollars.
- Monetization / first paid wedge: calibrate auto-accept versus review on the freight benchmark at a fixed false-accept ceiling.
- Why it wins: answers when an extracted fact is safe enough to drive a deterministic money decision, not merely whether a model can emit a field.

### aiparallel0/freight-audit
- Commit: `e7869162cf9cb23f6d520a0cd71f87cf973d8c28`.
- Rights: MIT for code and committed synthetic/PII-free corpus; external benchmark assets retain separate attribution/rights.
- Score: **28/30** — A4 B4 C5 D5 E5 F5.
- Promotion rationale: uniquely important benchmark/evaluation component in the #1 freight stack, not a standalone business leader.
- Capability: freight-specific rate-confirmation + invoice + POD audit harness, integer-cents money, OCR/evaluation/review tooling and synthetic challenge cases including clean billing, duplicate fuel, unauthorized liftgate and detention evidence cases.
- First paid wedge: use as the gold-truth/challenge layer in the blind incumbent-auditor bake-off.
- Why it wins: exposes extraction and rule failure separately and forces falsifiable freight-specific acceptance tests.

### srthck/trustmesh
- Commit: `5a93d70b37aafecaf61a5bc0296eaf831e5504ac`.
- Rights: MIT; domain policy/scheme content remains separately governed.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Capability: deterministic proof-obligation engine with authority/admissibility/independence/temporal/deadline/contradiction gates, replayable decisions and counterfactual next-best-evidence selection.
- Buyer/problem: recovery/claims teams need to know why a case is blocked and what missing evidence could actually change the decision.
- Monetization / first paid wedge: historical recovery-readiness diagnostic and next-evidence queue.
- Why it wins: stronger than generic rules/workflow because it models proof sufficiency and evidence acquisition explicitly.

### mgilbir/formalis
- Commit: `2b3895a0c2c54e4f25ccb46e131d215ad4457eb2`.
- Rights: MIT for code; official schemas/Schematrons/code lists/test corpora retain separate rights/provenance.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Capability: multi-jurisdiction e-invoice validation across EN16931, XRechnung, Factur-X/ZUGFeRD, Peppol/PINT and national CIUS with syntax detection, CII/UBL-neutral paths, authority-parity and omission tests, and explicit `NotEvaluated`/fatal states.
- Buyer/problem: AP/recovery products need native structured-invoice truth and jurisdiction-aware validation rather than lossy OCR.
- Monetization / first paid wedge: structured-invoice validation gateway feeding audit/recovery with exact field/rule evidence.
- Why it wins: materially broader and more fail-closed than a single-format validator while remaining permissively licensed.

### MassingCloud/massing-pdf
- Commit: `36794b3c54fcfd62e3a0d2d5984cfc45cac83340`.
- Rights: MIT; dependencies/customer drawings separate.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Capability: construction drawing review with calibrated takeoff plus coarse-to-fine old/new registration, scale correction, changed-region scoring and transform-aware markup migration with E2E tests.
- Buyer/problem: GCs/specialty contractors lose time and change evidence when sheet drift is mistaken for scope change.
- Monetization / first paid wedge: one issued drawing revision pair → aligned change evidence and review queue before attaching dollars.
- Why it wins: directly addresses registration/correspondence, the key step between naive PDF diff and defensible scope change.

### Kentucky-ai/opentakeoff
- Commit: `6ff9cc355e60d6312c0c82e2ddac56cb212cc394`.
- Rights: Apache-2.0.
- Capability: calibrated PDF/image count, linear and area takeoff with material calculations, review/provenance/export surfaces and tests/benchmarks.
- Buyer/problem: construction teams need measured quantity deltas tied to revision evidence.
- Monetization / first paid wedge: quantity engine inside ScopeSignal revision/change diagnostic.
- Why it wins: construction-specific measurement and review semantics are deeper than generic vision/OCR tools.

### delongwangshu49-hub/bimchange-agent
- Commit: `cd7fd6e6522e060b7847f0daaed00979097da7dd`.
- Rights: MIT.
- Capability: offline IFC4 old/new comparison with normalized deterministic change records, evidence selectors, relationship/geometry changes, 3D context and held-out revision fixtures.
- Buyer/problem: BIM/VDC/change teams need exact changed model elements before quantity/commercial impact.
- Monetization / first paid wedge: IFC revision-evidence module inside ScopeSignal.
- Why it wins: preserves element-level before/after evidence instead of treating model difference as a visual annotation only.

### finnertallon-png/contract-deadline-agent
- Commit: `c891f5ff391abc58b874675783a7ff2c3775c7bb`.
- Rights: MIT; customer contracts remain confidential/customer-controlled and legal applicability still requires human review.
- Score: **28/30** — A4 B5 C5 D5 E4 F5.
- Capability: construction/commercial contract deadline extraction with clause provenance, structured trigger+duration semantics, human-supplied trigger dates, SharePoint/Outlook reconciliation and fail-closed date handling. Exact tests prove strict parsing, idempotent create/update/delete behavior, trigger-date recomputation and explicit refusal of unsupported business-day/month/hour arithmetic.
- Buyer/problem: contractors and claims/change teams can lose otherwise valid change recovery when notice/cure/priced-claim clocks are buried in contracts or guessed incorrectly.
- Monetization / first paid wedge: fixed-price change-notice preservation audit on one contract plus active RFI/change log, then recurring per-project deadline monitoring.
- Why it wins: closes ScopeSignal's claim-preservation gap without pretending the software decides legal applicability; unsupported timing semantics remain visible gaps rather than invented due dates.

### alanbld/utf8proj
- Commit: `92d96268159035cc2b53a34467dab6c64d1f0a98`.
- Rights: dual MIT / Apache-2.0 at the user's option.
- Score: **28/30** — A4 B4 C5 D5 E5 F5.
- Promotion rationale: uniquely important deterministic schedule-evidence component for ScopeSignal rather than a generic project-management product.
- Capability: explainable CPM scheduling with FS/SS/FF/SF + lag, deterministic resource leveling, calendars, status-date/progress/EVM, diagnostics, renderers and Microsoft Project import. The pinned revision specifically fixes `.mpp` PhysicalPercentComplete/PercentageComplete preservation with expanded tests.
- Buyer/problem: change/claims teams need reproducible schedule-impact evidence; opaque scheduler output or dropped progress fields can manufacture false delay conclusions.
- Monetization / first paid wedge: normalize one customer-authorized baseline/update schedule, reproduce critical-path/progress state, then attach only reviewer-approved schedule impact to a ScopeSignal change packet.
- Why it wins: versionable deterministic schedules and explicit diagnostics create a much better audit trail than another Gantt UI; it does not itself prove entitlement or compensable delay.

### GSA/srt-fbo-scraper
- Commit: `fbdfa86a2bce4323a5afacda04f083698cab02e1`.
- Rights: CC0-1.0 for repository work; SAM/source data terms/status remain separate.
- Score: **28/30** — A4 B4 C5 D5 E5 F5.
- Capability: official GSA solicitation ingestion that pages SAM Opportunities v2, canonicalizes agency/office context, downloads attachments including malformed-link cases, extracts DOC/RTF/DOCX/PDF text and maintains solicitation/history state.
- Buyer/problem: CaptureBrief cannot be evidence-grade if it sees an opportunity record but misses the controlling solicitation packet or amendment history.
- Monetization / first paid wedge: packet-completeness adapter tested against 10 live solicitations before qualification/scoring.
- Why it wins: official operational implementation of the attachment/history edge cases generic SAM wrappers often omit.

### GSA/GSA-Acquisition-FAR
- Commit: `da52ccbbe114e1f031a7f4c59195c508dbfa485f`.
- Rights: official FAR/regulatory source is authoritative public-law/regulatory material; no blanket permissive software license for every repository packaging artifact was established, so code/packaging is not treated as MIT/Apache by default.
- Score: **29/30** — A5 B5 C5 D5 E5 F4.
- Capability: official Acquisition.gov machine-readable FAR DITA with clause/provision structure, fill-in metadata, FAC revision markers, FAR Case identifiers and change provenance.
- Buyer/problem: capture/proposal teams need exact current clause text, revision and required fill-ins rather than summarized or stale regulation text.
- Monetization / first paid wedge: authoritative clause-reconstruction and solicitation-completeness layer inside CaptureBrief.
- Why it wins: first-party structured regulatory source rather than another search wrapper.

### fedspendingtransparency/usaspending-api
- Commit: `1692d484b38c66361c54faa221548527cae29964`.
- Rights: CC0-1.0 for the official repository; source-system caveats separate.
- Capability: official USAspending server/ETL schemas and implementation for award, procurement, recipient and spending data with tests.
- Buyer/problem: GovCon products otherwise reverse-engineer historical award semantics and risk false incumbent/spend joins.
- Monetization / first paid wedge: authoritative award/incumbent/spend evidence beneath CaptureBrief.
- Why it wins: official upstream semantics and data lineage.

### fedspendingtransparency/data-act-broker-backend
- Commit: `76dcae4ccbf6951223608bc1d8fd0c5b03da5d68`.
- Rights: CC0-1.0; downstream/source-system caveats separate.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Capability: official DATA Act broker semantics including UEI/DUNS/legal/DBA/parent identities, addresses/business types and procurement/referenced-IDV identifiers.
- Buyer/problem: false entity/parent/PIID joins can invalidate CaptureBrief conclusions.
- Monetization / first paid wedge: evidence-grade identity/award lineage on current solicitation packets.
- Why it wins: government's own normalization semantics beat downstream fuzzy-name inference.

### cliwant/mcp-sam-gov
- Commit: `aaaaa70dcb6a08cf43cb40ece26b79d6d21c2463`.
- Rights: MIT; government-source currency/applicability remains contextual/human-reviewed.
- Capability: large read-only procurement/spending/regulatory toolset; inspected FAR path resolves exact clauses/prescriptions from versioned eCFR XML and rejects stale/blank/future/hollow sources.
- Buyer/problem: proposal teams need cited current regulatory evidence and deviation caveats.
- Monetization / first paid wedge: compliance/readiness layer in CaptureBrief.
- Why it wins: combines source-aware retrieval with fail-closed regulatory freshness checks.

### probavi/probavi
- Commit: `3f0dd3bd94259f91eb0a54ce6b5425afb70ad216`.
- Rights: Apache-2.0; database engines/images/backup tools remain separately licensed.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Capability: engine-agnostic continuous restore verification across database/search/time-series/vector systems using Docker/Kubernetes/SSH sandboxes, structural/freshness/custom SQL validation, RTO/PITR evidence and signed tamper-evident records verifiable offline.
- Buyer/problem: backup-success telemetry does not prove heterogeneous systems are recoverable or business-correct.
- Monetization / first paid wedge: fixed-price Recovery Readiness Audit on 1–3 critical systems, then recurring managed drills/evidence.
- Why it wins: combines broad real-restore execution with application-level checks and portable signed evidence; currently pre-alpha claims still require independent reproduction.

### cybertec-postgresql/pg_hardstorage
- Commit: `b47541b7e1cea69ce6ec63b26e154eb25fc4ca91`.
- Rights: Apache-2.0; PostgreSQL/storage/KMS/container dependencies separate.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Capability: PostgreSQL backup/PITR verifier restoring candidates into disposable sandboxes, booting PostgreSQL, running `pg_verifybackup` + `pg_amcheck --all` and recording signed verdict evidence.
- Buyer/problem: regulated SaaS/MSPs need evidence that a chosen recovery point actually boots and passes database-integrity checks.
- Monetization / first paid wedge: deep PostgreSQL oracle inside Recovery Readiness Audit.
- Why it wins: ties actual PITR execution to official integrity checks and signed evidence.

### google/cybernetic-agent-governance-engine
- Commit: `50b12e7d983db0e3d7faf206ac6aa600294f33ac`.
- Rights: Apache-2.0; downstream services/remediation actions separate.
- Score: **28/30** — A4 B5 C5 D4 E5 F5.
- Capability: deterministic authorization for consequential automated actions with allow/deny/approval/defer/narrow/pause outcomes, signed decision records and OSCAL Assessment Results export.
- Buyer/problem: compliance systems can detect failures but still need governed remediation and fresh re-proof.
- Monetization / first paid wedge: detect→approve/deny→remediate→re-test service around recovery/compliance findings.
- Why it wins: closes the operational action-governance loop rather than stopping at evidence collection.

### joschiservice/RosterSpec
- Commit: `f7e701c694bf1facdc4999e1681a3aa11493614d`.
- Rights: Apache-2.0.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Capability: deterministic workforce schedule verification/explanation/repair kernel using CP-SAT, stable rule codes, hard locks and minimum-disruption replanning with deep goldens/oracles/load tests.
- Buyer/problem: contact centers, field service and fulfillment teams need fast repairs without silently sacrificing coverage or rewriting published rosters.
- Monetization / first paid wedge: replay a week of callouts and compare manual/current repairs versus verified minimum-disruption repairs.
- Why it wins: treats the existing schedule, locks and repair validity as first-class evidence rather than optimizing from scratch.

### servicialo/mcp-server
- Commit: `5cc669d667f650f454bfaeb9236a88a540475219`.
- Rights: Apache-2.0.
- Score: **28/30** — A5 B5 C5 D5 E4 F5.
- Capability: service-order/delivery/evidence/accreditation/dispute/settlement protocol with OpenAPI/JSON Schema, persistence, webhooks/MCP and stress tests; separates verified delivery from billing/collection.
- Buyer/problem: service organizations lose revenue through completed-but-unbilled work, unsupported charges and unresolved settlement.
- Monetization / first paid wedge: Service Revenue Assurance diagnostic with 100-job leakage corpus.
- Why it wins: neutral proof-to-cash semantics are more valuable than another FSM CRUD system.

### proforcetech/phparm
- Commit: `a691ebfdea93a20f9de5f8a076430c859f299255`.
- Rights: MIT.
- Capability: recurring-service routes/stops/visits, QR-gated field execution, required visit-photo proof, contract-entitlement consumption, invoices/work orders, audit writes and centralized state transitions.
- Buyer/problem: janitorial/facility-service contractors lose margin when visits are missed/unprovable or out-of-scope work never becomes billable evidence.
- Monetization / first paid wedge: proof-of-service + contract-leakage audit on one route/site portfolio.
- Why it wins: ties recurring entitlement to field proof and billing state in a real line-of-business system.

### tonytonycoder11/stripe-connect-reckon
- Commit: `deb30aabfed84c7b0b2e5ae28c92cc9f85f79193`.
- Rights: MIT; Stripe/customer data access governed separately.
- Score: **29/30** — A5 B5 C4 D5 E5 F5.
- Capability: read-only Stripe Connect financial-controls engine reconciling balances, payouts, refunds, disputes, events and app state; flags failed payouts, refund mismatches, event gaps, negative balances/reserve/dispute exposure.
- Buyer/problem: marketplace finance teams can lose cash or days of labor when provider/app ledger state drifts.
- Monetization / first paid wedge: read-only Marketplace Money Safety Audit, then recurring monitoring.
- Why it wins: proves value without replacing payment execution or touching money movement.

### suoten/ProtoForge
- Commit: `7c61b10d9ae406224c86741d9c0a450b561b40ca`.
- Rights: MIT; protocol standards/vendor marks/patents/dependencies separate.
- Score: **29/30** — A5 B5 C5 D5 E5 F4.
- Capability: industrial multi-protocol simulation/testing with virtual-device templates, fault injection, record/replay, test plans/reports, metrics, RBAC and substantive IEC-104/Modbus implementation/testing.
- Buyer/problem: gateway/SCADA/OEM teams need repeatable pre-cutover validation without monopolizing physical hardware.
- Monetization / first paid wedge: fixed-price regression pack for 3–10 authorized device types.
- Why it wins: packages simulator breadth, fault/replay and evidence into a rights-clean acceptance-lab substrate.

### clicon/clixon-controller
- Commit: `36ecc0fd8787750978652495a39d0d01db2c7474`.
- Rights: Apache-2.0; vendor/customer YANG models separate.
- Score: **28/30** — A4 B5 C5 D4 E5 F5.
- Capability: active NETCONF/YANG multi-device controller with transaction validation/commit, locking, rollback/revert, services/templates and deep failure tests.
- Buyer/problem: telecom/network teams need to prove multi-device change semantics before NMS/controller migration.
- Monetization / first paid wedge: fixed-price controller migration preflight across synthetic/independent endpoints.
- Why it wins: difficult transaction/failure coordination is already implemented and testable.

### Benchling-Open-Source/allotropy
- Commit: `ecc574986b74f91eb84cd0ee14756cd8dc5e1b7e`.
- Rights: MIT for code; Allotrope specifications/vendor formats/fixtures and customer data remain separately governed.
- Score: **29/30** — A5 B5 C5 D4 E5 F5.
- Capability: broad vendor instrument-output parser estate normalizing chromatography/CDS, liquid-handler, plate-reader, cell-analysis, qPCR/dPCR, spectroscopy and related outputs into Allotrope Simple Model structures with dedicated readers/tests and active maintenance.
- Buyer/problem: pharma/biotech labs waste expert engineering time normalizing heterogeneous instrument exports before analytics/automation can begin.
- Monetization / first paid wedge: normalize 5–10 customer instruments into a canonical analytical-data layer with mapping/validation evidence.
- Why it wins: attacks the cross-vendor data-normalization bottleneck that device-control frameworks do not solve.

### labiium/pytestlab
- Commit: `8b7f873e29457f05dee7af0de698e27985c98a33`.
- Rights: Apache-2.0; vendor SCPI docs/firmware/SDKs/test data separate.
- Score: **29/30** — A5 B4 C5 D5 E5 F5.
- Capability: test-and-measurement automation with VISA, simulation, recording/replay/session backends, SCPI validation/profiles, bench orchestration, sweeps/results/uncertainty and strong safety/replay tests.
- Buyer/problem: electronics/RF/medical/semiconductor test teams cannot afford every regression to consume scarce physical benches.
- Monetization / first paid wedge: convert one brittle bench script into a recorded known-good session and CI replay with traceable regression evidence.
- Why it wins: combines control with hardware-independent regression evidence.

### novonordisk-research/OptiHPLCHandler
- Commit: `96399dcddc1457a5b942f61585b9e8fcf78b9a72`.
- Rights: BSD-3-Clause; Waters Empower/API/customer installation rights separate.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Capability: active Python SDK for Waters Empower Web API covering method/project/system/sample-set access, audit-trail messages and analytical-development workflows with tests/notebooks.
- Buyer/problem: pharma/biotech analytical-development teams spend expert time manually constructing method variants/sample sets inside existing CDS estates.
- Monetization / first paid wedge: automate one customer-authorized robustness/stability/assay workflow while preserving Empower as system of record.
- Why it wins: compresses a specialized high-budget vendor integration instead of trying to replace the validated CDS.

### sandialabs/DREAMS
- Commit: `3eb6c6089eadf09a4bf99961faac11a76ef30ca0`.
- Rights: MIT; OpenDSS/input datasets/customer models separate.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Capability: nodal hosting-capacity and quasi-static time-series distribution analysis with explicit voltage/thermal constraints, parallel evaluation and dedicated tests.
- Buyer/problem: utilities/DER developers need feeder-level constraint evidence rather than coarse hosting maps.
- Monetization / first paid wedge: fixed-price feeder hosting-capacity diagnostic on a rights-clean/customer-authorized model.
- Why it wins: closes the electrical-analysis middle layer between site/queue intelligence and engineering decisions.

### NLR-Distribution-Suite/erad
- Commit: `735f7a6baa9fe24878a986a3425bf6d55ad556c3`.
- Rights: BSD-3-Clause; hazard datasets/fragility parameters/literature/dependencies require separate provenance.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Capability: distribution-grid resilience engine with network models, asset-specific fragility, multi-hazard failure and restoration/resilience workflows across poles, lines, transformers, substations, switches and DER.
- Buyer/problem: utilities/consultants/insurers need hazard→asset failure→network consequence→restoration decisions, not another map.
- Monetization / first paid wedge: resilience/hardening study on a synthetic or customer-authorized feeder with planted failures.
- Why it wins: provides the hard operational middle layer from hazard to network consequence and restoration priority.

## Deliberate demotions from the elite set this run
The following remain validated and reusable in combinations/hunter catalogs but are no longer MASTER leaders because stronger or more specific assets now cover their job: `hupe1980/en16931` (retained as parser/serialization companion to FormaliS), `getomni-ai/zerox`, `microsoft/RulesEngine`, `dedupeio/dedupe`, `benseverndev-oss/goldenmatch`, `MindPetal/sam-search`, `Polycentric-Labs/evidentia`, `RamazanKara/restore-drill`, `sciencecorp/galago-tools`, `PyLabRobot/pylabrobot`, `ORNL/flowcept`, `agritheory/inventory_tools`, `gokhanozden/gabak`, `freeacs/freeacs`, and `OktopUSP/oktopus`. Demotion means **component/watch**, not rejection; their validated capabilities remain available to the active combinations.
