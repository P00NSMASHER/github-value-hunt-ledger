# MASTER

Elite cross-lane positive training set. This file is intentionally smaller than the hunter catalogs: only discoveries that materially compress a high-value product, provide rare evidence/data/protocol/decision infrastructure, or directly strengthen an active commercial stack belong here. Lane-local strong/watch candidates remain in `hunters/*.md`.

## Rules
- Promotion normally requires **24+/30** on A speed to first revenue, B plausible ACV/ceiling, C build-time/domain compression, D rarity/data/technical advantage, E evidence/completeness and F rights/reuse clarity.
- Preserve exact revision and public-facing rights. **Standing user assertion (2026-09-19): the user states they hold separate commercial permission/license for every public GitHub repository used in this hunt.** For portfolio scoring and product analysis, treat repository-owned code as commercially usable under that separate permission even when the public repo is no-license, GPL/AGPL, BSL, Commons-Clause, proprietary-looking or otherwise restrictive. Still record the actual public license/provenance and do not extend the assumption to separately owned datasets, model weights, standards/specifications, trademarks, patents, bundled media/assets, commercial APIs or third-party services without separate evidence.
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
- Implementation proof: the permissioned Opstrax semantics remain the physical-truth plane in Freight Recovery v12. The current v12.1 suite passes **108/108 tests**. Opstrax dwell facts are frozen into a physical-only SHA before the licensed Trenova/authority plane calculates money, so the runtime cannot prove itself. The original 3-hour/2-free-hour/$75 regression remains intact.

### emoss08/Trenova
- Commit: `95fcf816562025ad9af864ded4a5fce8a555bd65`.
- Rights: the public repository revision is FSL-1.1-ALv2, but on 2026-09-19 the user stated they hold a separate commercial license for this exact revision. Treat commercial integration for the user's project as authorized; do not infer redistribution, sublicensing, hosted-service or other rights beyond that separate agreement.
- Score: **29/30** — A5 B5 C5 D5 E4 F5.
- Capability: unusually complete trucking money/workflow plane spanning shipments/dispatch, rate agreements and rate confirmations, versioned RateCon parsing rules/fixtures, auto-rating, detention policy/evidence/notice/tiering/caps, billing queue rerating and rate-departure leakage, inbound EDI 210 carrier-invoice matching with variance tolerance/audit/reconciliation, disputes/adjustments/settlement, documents, reporting, RBAC and tenant controls.
- Buyer/problem: Freight Recovery needs one coherent transaction/evidence/settlement state machine around its independent audit math, not another disconnected parser or calculator.
- Monetization / first paid wedge: commercial operating substrate inside the Freight Audit Acceptance Test and managed recovery workflow; keep independent evidence/rerating oracles around it to prevent circular truth.
- Why it wins: it directly covers several hard policy/workflow dimensions that previously forced `REVIEW_ZERO_ASSERTION`, while also collapsing TMS, billing, carrier-settlement, document and reporting plumbing into one freight-native system.
- Implementation proof: Freight Recovery v12.1 core v1.1 commercially integrates the licensed detention-policy, rate-agreement/accessorial-version semantics and inbound carrier-invoice matching while preserving separate physical-truth, authority-lineage, calculation and settlement hashes. The new cross-document graph handles base agreement → amendment/addendum → incorporated tariff lineage, explicit rule supersession and fail-closed ambiguity. Partial credits/refunds/remittances now accumulate conservatively and feed a final recovery certificate. v12.1 additionally machine-enforces the blind bake-off sequence (population freeze → truth freeze → auditor output opened → scoring), rejects output opened before truth freeze or against a different population hash, and hash-chains the score record without claiming independent external timestamp proof. Regression suite passes **108/108 tests**. Artifact: `freight-v12-core-v1.1-blind-protocol.zip`.
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
- Rights: public repo is MIT. On 2026-09-19 the user also explicitly stated they hold a separate commercial license for `srthck/trustmesh`; domain policy/scheme content and third-party data remain separately governed.
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

## License-unlocked promotions — 2026-09-19

These repositories previously ranked below MASTER largely because of public-license/reuse restrictions. Under the user's standing assertion of separate commercial permission for every public repository, rights clarity is no longer treated as the limiting factor for repository-owned code. Scores below reflect technical/commercial value under that working assumption; actual public licenses remain recorded for provenance. Third-party datasets, standards content, models, trademarks, patents, APIs and external services remain separately governed.

### mizuharaa/olus
- Commit: `f1d1160de0c1cb8c2961d9a785d24b2e1ac48e68`.
- Rights: no root public LICENSE established at the inspected revision; **user asserts separate commercial permission** for public-repository code.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Capability: airline disruption/recovery operating stack with a substantial MILP optimizer, passenger/crew recovery, FAR-117 legality, uncertainty logic, cost decomposition, event simulation, cascade prediction, deterministic replay, shared schemas, scenarios and broad optimizer/crew/event/replay tests.
- Buyer/problem: airlines, logistics networks, field-service and manufacturing operations lose large amounts when disruptions force fast constrained recovery decisions.
- Monetization / first paid wedge: replay one historical disruption in shadow mode and quantify cost, legality and service tradeoffs across alternate recovery actions.
- Why it wins: compresses the rare **disruption → simulate → optimize → explain → replay** loop into one coherent system; potentially 6+ months of domain architecture.
- Combination role: BOCPD/kernel change detection can trigger recovery; TrustMesh can govern evidence obligations; production-planner/ChronosGuard/AnoShip can gate safe activation.

### Vzlentin/calibre
- Commit: `264b6fc27fd4293660983c2adf9f86cfa1b4d733`.
- Rights: no reusable public license established at inspection; **user asserts separate commercial permission** for public-repository code.
- Score: **27/30** — A3 B4 C5 D5 E5 F5.
- Capability: inventory-decision engine with forecasting, hierarchy reconciliation, conformal calibration, ordering, settlement, backtesting and persistent observation/state semantics. Its decision spine enforces `resolve → settle → predict → reconcile → calibrate → order`, blocks future reads and supports replay/restart correctness.
- Buyer/problem: distributors, retailers and inventory-planning vendors need live replenishment decisions that remain valid under delayed observations, restarts and hierarchy reconciliation rather than merely impressive backtests.
- Monetization / first paid wedge: replay one SKU/location panel continuously and with forced restarts; prove identical decisions and compare cost/service to the incumbent policy.
- Why it wins: temporal/provenance correctness is unusually deep and can prevent subtle leakage/state corruption that invalidates economic results.
- Combination role: inventory_tools economics + PyEPO/skwdro decision layers + deepbullwhip simulation + Calibre state discipline.

### KesavamurthyT/Fair-Dispatch-Transparent-Fair-Route-Allocation
- Commit: `90f8768abe3b49e7bd577cd666096a93ff2da3cd`.
- Rights: no public license established at inspection; **user asserts separate commercial permission** for public-repository code.
- Score: **27/30** — A3 B4 C5 D5 E5 F5.
- Capability: CVRP dispatch stack with workload/fairness services, historical-effort models, explanations, appeals, manual overrides, decision logs, recovery logic, migrations, APIs and substantial solver/fairness/history/workflow tests.
- Buyer/problem: last-mile, field-service, regulated or unionized workforces need assignments that are efficient **and defensible**.
- Monetization / first paid wedge: shadow one operating day, compare incumbent routes with a distance/workload/fairness policy, and produce an explanation/override audit.
- Why it wins: combines route optimization with governance objects that most routing engines omit.
- Combination role: use TrustMesh/Firefly for evidence/policy, then exact/certified optimization or existing route engines underneath.

### angelvicen92/production-planner
- Commit: `e15c8a6a1194327713c7897e251a867ad4c22584`.
- Rights: no public license established at inspection; **user asserts separate commercial permission** for public-repository code.
- Score: **27/30** — A3 B4 C5 D5 E5 F5.
- Capability: deep production/event planning reasoner with hard-constraint validation, bounded search, dominance/transposition pruning, baseline preservation, repair lineage, opportunity-cost/recovery estimates, evidence gates and staged commit/fallback behavior.
- Buyer/problem: manufacturers, studios/events and field-service teams need optimizers that cannot silently replace a safe plan with an invalid “better” one.
- Monetization / first paid wedge: shadow-run an existing schedule and return a machine-readable candidate/validation/objective-delta report without changing production state.
- Why it wins: rare **baseline → candidate → hard validation → compare → commit/fallback** operating discipline that can wrap many optimizers safely.
- Combination role: safe activation layer around MIP++/optim-engine/Olus with TrustMesh evidence and ChronosGuard/AnoShip release control.

### Dimitres-Kisimov/revops-optimizer
- Commit: `4fd6d24c05807a1d3ec1d178f641fc97dbd35f74`.
- Rights: public repository states all-rights-reserved/internal-portfolio terms; **user asserts separate commercial permission** for public-repository code.
- Score: **26/30** — A4 B4 C4 D4 E5 F5.
- Capability: distributor RevOps stack spanning demand/churn/elasticity prediction, assortment MILP, newsvendor inventory, pricing/promotion optimization, service-level analysis, robustness/scenarios, simulation, prescriptions and report artifacts; inspected history reports a 91-test green state.
- Buyer/problem: distributors/wholesalers need ERP history converted into economically coherent assortment, replenishment, pricing and promotion actions.
- Monetization / first paid wedge: shadow-run one distributor export and quantify profit/service improvement versus incumbent policies.
- Why it wins: an unusually complete **predict → prescribe → stress-test → report** contract rather than isolated models.
- Combination role: benchmark/operating shell around inventory_tools, PyEPO, skwdro, deepbullwhip and Calibre.

### mann13072/financial-risk-fraud-engines
- Commit: `be2b2dc0f8bb30fe7a8e6c54dd8b47174ca7ca55`.
- Rights: no public license established at inspection; **user asserts separate commercial permission** for public-repository code.
- Score: **26/30** — A4 B5 C4 D3 E5 F5.
- Capability: credit/fraud decision systems combining calibrated models, explicit economic policy, rules, circuit breaker, explainability, audit logging, delayed labels and drift/latency monitoring with a large test surface.
- Buyer/problem: fintech/payment and marketplace risk teams need cost-sensitive accept/review/reject decisions that remain auditable and fail safely under drift.
- Monetization / first paid wedge: shadow-score historical transactions and compare incumbent decisions to a cost-sensitive review-band policy.
- Why it wins: the value is the operational decision/governance plumbing around the model, not another fraud classifier.
- Combination role: Firefly/Hashimori policy + ChronosGuard evidence + AnoShip rollout around the economic decision layer.

### carjam/credit-underwriting-engine
- Commit: `ddee40364106e8ab138de3c1b2209eb4ddf9493c`.
- Rights: no public license established at inspection; **user asserts separate commercial permission** for public-repository code. Bundled datasets remain separately governed.
- Score: **25/30** — A4 B5 C4 D3 E4 F5.
- Capability: tested probability-to-economic-decision layer with approve/review/decline thresholds, risk tiers, threshold sweeps, expected loss, break-even default rate, lifetime EL, unexpected loss, YAML policy and model-risk documentation.
- Buyer/problem: lenders need to translate model probability into explicit portfolio economics and policy, not stop at AUC.
- Monetization / first paid wedge: offline policy-shadowing diagnostic on a lender-authorized historical sample, quantifying approval/default/loss tradeoffs for human policy owners.
- Why it wins: tested bridge from model scores to economically accountable policy decisions.
- Combination role: upstream calibrated model + Firefly/Hashimori rules + ChronosGuard evidence/validation.

### nidhi-builds/ReconIQ
- Commit: `769fb2de92e39334703f0fd6a1e15b8a3fa4a8f4`.
- Rights: no public license established at inspection; **user asserts separate commercial permission** for public-repository code. Customer/data artifacts remain separately governed.
- Score: **25/30** — A4 B4 C4 D3 E5 F5.
- Capability: multi-source reconciliation engine with deterministic exact, fee-adjusted, refund and split-settlement matching, deduplication, exceptions, run persistence, evaluation, GST/TDS enrichment, API and dashboard.
- Buyer/problem: finance/AP/AR, payment processors and marketplaces lose money/time to unmatched or mis-settled transactions.
- Monetization / first paid wedge: reconcile two or three exported ledgers/settlement feeds and return quantified unmatched dollars plus exception evidence.
- Why it wins: unusually test-heavy, rules-first reconciliation that maps directly to recovery rather than generic analytics.
- Combination role: TrustMesh converts unmatched exceptions into proof obligations/next-evidence actions; freight/AP stacks can reuse the matching/evaluation layer.

### wave03F/landed-cost-engine
- Commit: `db8e918ee73a02c83c15ec9b4e9d362cd6693fb0`.
- Rights: no public license established at inspection; **user asserts separate commercial permission** for public-repository code. Commodity-code/duty data and authoritative tariff content remain separately governed.
- Score: **25/30** — A4 B4 C4 D3 E5 F5.
- Capability: landed-cost application with order/cost-element/duty-source workflows, multi-company isolation, Excel/API/manual source paths, audit-integrity controls, migrations and broad service/security/load tests.
- Buyer/problem: importers/distributors/manufacturers need to know when freight/customs/accessorial mistakes distort landed cost and inventory valuation.
- Monetization / first paid wedge: shadow-recompute landed-cost allocations from PO/receipt/vendor-bill exports and flag material variances.
- Why it wins: gives Freight Recovery a bridge from carrier/customs errors into inventory-cost distortion.
- Caveat: core allocation equations were not source-validated in the prior inspection; promotion is for product/domain infrastructure, not a claim that its math is authoritative.
- Combination role: Freight Recovery + Acumatica/ERP lineage + TrustMesh dispute evidence.

### KPowellAi/regulated-ai-decision-engine
- Commit: `2388fd6f37a80522c1011435375e29d4d0d9f0e9`.
- Rights: no public license established at inspection; **user asserts separate commercial permission** for public-repository code.
- Score: **25/30** — A4 B5 C4 D3 E4 F5.
- Capability: deterministic credit/risk rules engine with Pydantic decision schemas, YAML rules, explicit REJECT-over-REFER precedence, per-rule reasons, SQLAlchemy audit state and integration tests; inspected project configuration enforced an 80% coverage floor.
- Buyer/problem: regulated approval teams need reproducible policy decisions and chronological audit evidence.
- Monetization / first paid wedge: shadow an existing manual policy and measure decision consistency/reason-code completeness.
- Why it wins: straightforward vertical bridge from business rules into auditable regulated decisions.
- Combination role: vertical policy layer beside Hashimori/Firefly; ChronosGuard can govern any upstream model evidence.

### kenithphilip/Anvil
- Commit: `08678ac13312e03f6b4408f8060bf68f12650342`.
- Rights: public repository license is proprietary/all-rights-reserved for internal Obara India use; **user asserts separate commercial permission** for public-repository code.
- Score: **24/30** — A3 B5 C4 D3 E4 F5.
- Capability: industrial/manufacturing quote-to-cash workflow spanning RFQ, quoting, approvals, orders and evidence of deeper inventory-risk/conformal safety-stock decisioning with regression/CI activity.
- Buyer/problem: industrial manufacturers/distributors need quoting/order workflows joined to inventory-risk decisions rather than separate CRM and planning tools.
- Monetization / first paid wedge: vertical quote-to-cash + safety-stock diagnostic/implementation for a niche manufacturer or distributor.
- Why it wins: combines high-ACV industrial workflow with decision infrastructure that can grow into a vertical ERP wedge.
- Combination role: vertical ERP cluster + inventory decision stack.

### pavan2184/LTA-Hack (RailPlan)
- Commit: `7ca4efffad9babcb819951a923f12852ac7d450c`.
- Rights: no public license established at inspection; **user asserts separate commercial permission** for public-repository code.
- Score: **24/30** — A3 B4 C4 D4 E4 F5.
- Capability: railway access/maintenance planning application using OR-Tools CP-SAT with scenario comparison, disruption review and exact CSV outputs.
- Buyer/problem: rail, utilities and infrastructure operators face costly access-window/outage scheduling decisions.
- Monetization / first paid wedge: shadow one maintenance/access plan and quantify disruption/capacity tradeoffs.
- Why it wins: domain-specific planning workflow is much closer to a buyer problem than a generic solver.
- Combination role: MIP++/optim-engine substrate + TrustMesh exception evidence + production-planner safe activation.

### Neeraj-Parekh/special-parakeet
- Commit: `b1b5d0c638615dcc59eb14b31d65ebaefda18eef`.
- Rights: no public license established at inspection; **user asserts separate commercial permission** for public-repository code.
- Score: **24/30** — A4 B4 C4 D3 E4 F5.
- Capability: commerce risk product with accept/review/reject scoring plus OTP/prepaid recovery and hold/ship flows; implementation evidence shows real risk-to-intervention branching rather than a passive score.
- Buyer/problem: COD-heavy/D2C/marketplace merchants need to minimize expected fraud/loss **without** unnecessarily killing conversion.
- Monetization / first paid wedge: shadow a historical order set and estimate recovered gross margin from intervention routing versus binary decline.
- Why it wins: operationalizes risk into economically chosen interventions and recoverable customer flows.
- Combination role: Firefly/Hashimori policy + TrustMesh reason/evidence + calibrated risk models.

### StatMixedML/Hyper-Trees
- Commit: `89b138ed65b99cd04334887669eb9e6fbf7b13b7`.
- Rights: public code is Apache-2.0 modified by Commons Clause v1.0; **user asserts separate commercial permission** overriding the prior hosted/resale restriction for their use. Third-party datasets/method IP remain separate.
- Score: **24/30** — A3 B4 C4 D5 E3 F5.
- Capability: tree-conditioned classical time-series models, including Hyper-Tree TSB for intermittent demand, plus AR/ARMA/VAR/ETS-family hybrids and rolling conformal forecast intervals; dedicated TSB tests and example calibration workflow were inspected.
- Buyer/problem: spare-parts/MRO/inventory planners need adaptive intermittent-demand forecasts that react to changing state rather than fixed smoothing parameters.
- Monetization / first paid wedge: benchmark adaptive TSB against Croston/Durbyn on a customer-authorized sparse-demand panel using stockout + holding cost rather than forecast error alone.
- Why it wins: unusual hybrid between interpretable classical demand structure and nonlinear state adaptation.
- Combination role: Calibre state discipline + PyEPO/skwdro decisioning + deepbullwhip simulation.

### DataZooDE/anofox-forecast
- Commit: `7e23980762ca713a565cf68fd6188aeee8f2ce4e`.
- Rights: public code is BSL 1.1 with hosted/embedded restrictions and later MPL-2.0 change license; **user asserts separate commercial permission** for their use.
- Score: **25/30** — A3 B4 C5 D4 E4 F5.
- Capability: C++/Rust-backed DuckDB forecasting extension exposing roughly 148 `ts_*` functions spanning forecasting, intermittent-demand Croston/ADIDA/IMAPA/TSB, backtesting/bootstrap metrics, EDA/data quality and detection utilities.
- Buyer/problem: embedded analytics/data-warehouse teams can eliminate a large amount of Python-service plumbing by forecasting where the data already lives.
- Monetization / first paid wedge: warehouse-local forecasting pilot over an existing DuckDB/embedded analytics dataset; compare throughput and decision quality against current pipeline.
- Why it wins: unusually broad SQL-native statistical surface and very high build-time compression for embedded forecasting.
- Combination role: Calibre for state correctness, ChronosGuard for leakage-safe evaluation, PyEPO/skwdro for action optimization.

## Deliberate demotions from the elite set this run
The following remain validated and reusable in combinations/hunter catalogs but are no longer MASTER leaders because stronger or more specific assets now cover their job: `hupe1980/en16931` (retained as parser/serialization companion to FormaliS), `getomni-ai/zerox`, `microsoft/RulesEngine`, `dedupeio/dedupe`, `benseverndev-oss/goldenmatch`, `MindPetal/sam-search`, `Polycentric-Labs/evidentia`, `RamazanKara/restore-drill`, `sciencecorp/galago-tools`, `PyLabRobot/pylabrobot`, `ORNL/flowcept`, `agritheory/inventory_tools`, `gokhanozden/gabak`, `freeacs/freeacs`, and `OktopUSP/oktopus`. Demotion means **component/watch**, not rejection; their validated capabilities remain available to the active combinations.

<!-- INTEGRATOR-R11-2026-09-19T2028-0400 -->
## Integrator promotions — 2026-09-19 20:28 ET

The entries below were re-scored under the standing commercial-permission posture: a public repository's missing/restrictive/copyleft public license is provenance metadata, not a value penalty for repository-owned code. Third-party standards, datasets, models, services, patents, trademarks and customer data remain separately governed.

### aldemirkonuk/RestaurantAIAutomation — X12 812 realized-credit proof
- Exact revision: `79dfea023658f014248f3c805ebe7d903c7f3974`.
- Score: **29/30** — A5 B5 C5 D5 E5 F4. F reflects separate ASC X12/specification-content diligence, not the repository's lack of a public license.
- Rights: no root public LICENSE identified; repository-owned code treated as commercially permitted under the user's standing assertion. Independently owned X12 specifications/code lists remain separate.
- Concrete capability: deterministic 812 Credit/Debit Adjustment parsing with invoice-reference linkage, credit-vs-debit direction, implied-decimal N2 money, currency semantics and fail-closed warnings; tests join 810 invoice + 856 shipped quantity + 812 settlement and refuse to count debit adjustments as recovered cash.
- Buyer/problem: shipper/3PL finance, freight-audit/payment and AP teams need proof that a finding actually became an issued credit rather than a claimed saving.
- Monetization / first paid wedge: read-only settlement adapter in the Freight Audit Acceptance Test; charge success fees only after invoice-linked credit/payment/refund evidence reconciles.
- Why it beats alternatives: it closes the last-mile `finding -> issued credit` semantic gap with tested direction/reference logic rather than another generic EDI parser.

### acqagent FAR Overhaul family — moving deviation authority
- Exact revisions: `acqagent/far-collector@40789a073134a484b2e4a5a2398629b067da0eea`; `acqagent/rfo-deviations@ccf31107508085cc311fb07488eb513ab97c6b7d`.
- Score: **30/30 family** — A5 B5 C5 D5 E5 F5 under the standing repository-code permission posture; official-source/derived-index distinctions remain mandatory.
- Rights: `far-collector` has no repository-wide public software license at the inspected revision but is covered by the user's separate permission assumption for repo-owned code. `rfo-deviations` documents U.S. Government source PDFs plus CC BY 4.0 packaging/manifest. Model dependencies and any non-government third-party material remain separate.
- Concrete capability: official acquisition.gov FAR Overhaul guide crawl, raw PDF/HTML preservation, source hashes, agency/FAR-Part/effective-date normalization, DuckDB/incremental refresh plus a dated corpus with source-link/missing-link accounting and Part 52 indexes.
- Buyer/problem: federal capture/proposal/compliance teams can miss agency class deviations that change the operational FAR rule surface during active solicitations.
- Monetization / first paid wedge: fixed-price solicitation rule-currency diagnostic: solicitation agency/date/clause set -> codified FAR baseline -> potentially controlling deviation -> exact source PDF/hash/effective/supersession evidence -> reviewer verdict.
- Why it beats alternatives: this is moving-rule evidence infrastructure, not another FAR search wrapper; it directly fills CaptureBrief's highest-value applicability gap.

### open-eid/SiVa — production timestamp/signature trust validation
- Exact revision: `0c9c5f2490b1a27798b47906bbaa6adb4d26daad`.
- Score: **25/30** — A3 B4 C5 D4 E5 F4. Promoted as a uniquely important trust component even though revenue is indirect.
- Rights: EUPL v1.1; repository-owned code also covered by the standing permission assertion. DigiDoc4J/DSS, EU trusted lists, certificates and trust-service infrastructure remain separately governed.
- Concrete capability: validates XAdES/CAdES/PAdES/ASiC/timestamp evidence with chain trust, timestamp imprint, OCSP/CRL status and revocation freshness rather than merely parsing an RFC 3161 token.
- Buyer/problem: recovery/compliance evidence products need to prove that a timestamp/signature was trusted and temporally valid, not just syntactically valid.
- Monetization / first paid wedge: evidence-integrity add-on to a Recovery Readiness Audit.
- Why it beats alternatives: it closes the specific PKIX/revocation/freshness gap left by generic timestamp clients and self-authored hash chains.

### redrillhq/redrill — recurring Backup Proof SLA
- Exact revision: `2016f658b366d5d5ce2e6ffab5162f7b97062597`.
- Score: **29/30** — A5 B5 C5 D4 E5 F5.
- Rights: AGPL-3.0 publicly; repository-owned code treated as commercially permitted under the standing user assertion. Borg/restic/PostgreSQL/container/provider rights remain separate.
- Concrete capability: recurring L1 integrity/freshness, L2 sampled file restore and L3 isolated PostgreSQL restore + typed SQL invariants, with semantically distinct `fail`, `error` and `stale`, `max_proof_age`, history, reports and alerts.
- Buyer/problem: SaaS/MSP/self-hosted operators often know that backup jobs ran but cannot prove when the protected dataset was last restored and shown usable.
- Monetization / first paid wedge: managed Backup Proof SLA with setup plus recurring per-dataset/workload fee.
- Why it beats alternatives: the valuable primitive is stale-proof semantics and recurring proof freshness, not one-off restore orchestration.

### AccelerationConsortium/HELIOS — governed closed-loop campaign authority
- Exact revision: `1e5765ec694d5ba5c26f5a8605c7e37b238a19e0`.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Rights: MIT; external scientific data/equipment APIs/services remain separately governed.
- Concrete capability: typed decision authority above optimizers/automation backends deciding optimize/validate/recover/acquire-context/escalate/stop, with hard safety gates, deterministic decision cards, append-only trajectories, replay/offline policy evaluation and shadow/canary/promotion gates.
- Buyer/problem: pharma/biotech/materials/self-driving-lab teams need expensive sequential experiments governed by evidence and recoverable policy rather than an optimizer that can propose invalid actions.
- Monetization / first paid wedge: shadow one existing campaign and deliver a replayable ledger of decisions and avoided invalid actions without controlling hardware.
- Why it beats alternatives: it is a governed campaign authority and learning/promotion control plane, not another Bayesian-optimization wrapper.

### GRIDAPPSD/CIMHub — utility-model conversion acceptance oracle
- Exact revision: `5ba4c63fa525108928942d564fddc022c3fb031f`.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Rights: Battelle permissive grant; external CIM/IEC standards, customer utility models, Blazegraph/GridLAB-D/OpenDSS and example datasets retain separate rights.
- Concrete capability: CIM XML ingestion/model handling, measurement support, OpenDSS/GridLAB-D/CSV export and conversion validation by running incoming/converted simulations against explicit tolerances.
- Buyer/problem: utilities, ADMS/GridAPPS-D integrators and DER/resilience consultants cannot rely on a hosting-capacity study if model translation silently changes electrical meaning.
- Monetization / first paid wedge: customer-authorized model conversion + topology/electrical-parity acceptance report before DREAMS/DISCO/ERAD studies.
- Why it beats alternatives: it supplies independent model-intake/round-trip proof rather than another power-flow engine.

### chrisallen12789/ProofLink — hydrovac/liquid-waste proof-to-cash vertical OS
- Exact revision: `0ca71e3cddd1d0fb6a9c65b406ef3559a759c9f0`.
- Score: **29/30** — A5 B5 C5 D5 E4 F5. E is 4 because source depth is strong but automated-test depth has not yet been independently established.
- Rights: no root public LICENSE found; repository-owned code treated as commercially permitted under the standing user assertion. Stripe/Supabase and other third-party services remain separately governed.
- Concrete capability: multi-tenant CRM/jobs/scheduling/quotes/orders/invoices/payments plus a deep hydrovac/liquid-waste module covering trucks/crews, time segments, service contracts, disposal facilities, manifests, permits, qualifications, locate tickets, assets and hydrovac invoice generation. Confirmed billable uninvoiced manifests, mobilization, time, disposal, water and materials feed billing state.
- Buyer/problem: hydrovac/excavation/liquid-waste operators can complete and document work yet miss disposal/time/material charges or carry jobs/manifests that never reach billing.
- Monetization / first paid wedge: fixed-price 100–1,000 job-to-invoice leakage audit, followed by recurring proof-to-cash monitoring.
- Why it beats alternatives: it is a complete vertical operating chain that directly joins compliance/disposal evidence to billable money rather than generic FSM CRUD.

<!-- INTEGRATOR-R11-LATE-2026-09-19T2032-0400 -->
## Late-run promotions — recovery and commission assurance

### mehdi-arfaoui/Stronghold — recoverability-as-code evidence contracts
- Exact revision: `776fe21f159bcab9e4333c716c8ac11cd6329a91`.
- Score: **29/30** — A5 B5 C5 D5 E4 F5.
- Rights: AGPL-3.0 publicly; repository-owned code treated as commercially permitted under the user's standing assertion. AWS/service data and dependencies remain separate.
- Concrete capability: declarative per-service recovery contracts, read-only infrastructure discovery, dependency/recovery chains, append-only measured test evidence and deterministic RTO/RPO/evidence-level/chain-coverage/SPOF verdicts with explicit MET/VIOLATED/UNKNOWN semantics. CI can fail enforced violations while preserving UNKNOWN when evidence is insufficient.
- Buyer/problem: SaaS/platform/MSP/regulated teams need to know whether measured recovery evidence actually proves service-level RTO/RPO promises rather than whether a backup job exists.
- Monetization / first paid wedge: recoverability diagnostic that maps critical services to explicit contracts, ingests real drill evidence and produces machine-checkable proof gaps; recurring managed proof follows.
- Why it beats alternatives: it is the policy/evidence decision layer above restore engines and refuses to invent RTO/RPO when measured evidence is missing.

### kleegr/sales-commission-manager — commission attribution-to-settlement control plane
- Exact revision: `5fe802dba9b3a1c322995d4ccc73cb40922ab34d`.
- Score: **29/30** — A5 B5 C5 D5 E5 F4. F reflects separately governed provider APIs/customer records, not the absence of a public license.
- Rights: no public LICENSE found; repository-owned code treated as commercially permitted under the standing user assertion. GoHighLevel/provider APIs and customer records remain separate.
- Concrete capability: deterministic plan snapshots, dated assignments, product/rule attribution, receipts/refunds, payout batches/entries/events, integer-money calculations, hold/release, reversals, partial settlement/carry-forward, audit/integration events and tests for attribution/refund/cancel/exact awards.
- Buyer/problem: RevOps/finance/payroll teams face underpayment, overpayment and disputes from stale plan versions, split attribution, reversals and payout-state drift.
- Monetization / first paid wedge: blind Commission Payout Acceptance Test on one closed month with customer-owned CRM/plan/payment/refund/payroll truth frozen before incumbent output.
- Why it beats alternatives: it spans entitlement through settlement and payout reconciliation rather than stopping at commission calculation.

<!-- INTEGRATOR-R11-WARRANTY-2026-09-19T2034-0400 -->
## Late-run promotion — aftermarket entitlement assurance

### OCA/rma — deterministic warranty/return entitlement authority
- Exact revision: `9416b2a5f5e1d604eff27610635eb3573227337c` on branch `18.0`.
- Score: **28/30** — A5 B4 C5 D4 E5 F5.
- Rights: AGPL-3.0 family; repository-owned code additionally treated as commercially permitted under the user's standing assertion. Odoo/customer data and third-party integrations remain separately governed.
- Concrete capability: tested product-warranty and RMA entitlement path binding return eligibility to partner/product/sale state/date, completed delivery moves, operation-specific return windows and remaining returnable quantity; deterministically splits eligible returns across multiple deliveries and blocks over-return. Tests cover expired windows, exact/partial quantities, consumed entitlement, multiple deliveries and forced over-return rejection.
- Buyer/problem: manufacturers, distributors, ecommerce and aftermarket/service finance teams lose margin to duplicate, expired, over-quantity or weakly sourced warranty/return approvals and waste analyst time reconstructing source sales/deliveries.
- Monetization / first paid wedge: blind Warranty/RMA Entitlement Leakage Audit on customer-owned sales/delivery/serial/warranty/RMA/credit facts, measuring unsupported credits/refunds, duplicate/over-return claims, valid incorrectly rejected claims and review labor.
- Why it beats alternatives: it supplies executable tested entitlement semantics from fulfilled sale/delivery history to remaining returnable quantity rather than generic warranty dates or RMA CRUD.

<!-- INTEGRATOR-R12-2026-09-19T2231-0400 -->
## Integrator promotions — 2026-09-19 22:31 ET

### pialmmh/billing-dotnetcore — telecom mediation/rating and revenue-assurance kernel
- Exact revision: `ec9e0abacce7e80b3a34d2d89b929ee5db946209`.
- Score: **29/30** — A5 B5 C5 D5 E5 F4.
- Rights: no controlling root public `LICENSE` established at the inspected revision; repository-owned public code/content is treated as commercially authorized under the user's standing assertion. Third-party dependencies, telecom standards/data and any customer-origin corpus remain separately governed.
- Concrete capability: production-shaped telecom CDR mediation/rating with rate-plan resolution/provenance, prefix/A-to-Z rating, charge/finalization, reseller/interconnect service families, Kafka/DLQ paths, idempotency/atomic batch semantics and extensive billed-duration, rounding, prefix, duplicate and service-family tests.
- Buyer/problem: MVNOs, carriers, wholesale/interconnect finance, BSS vendors and revenue-assurance teams lose margin in rate-plan, duration, rounding, prefix, reseller and settlement edge cases.
- Monetization / first paid wedge: fixed-price read-only rerating diagnostic on one closed authorized billing period, followed by recurring revenue-assurance monitoring; settlement recovery is claimed only after actual partner/payment evidence.
- Why it wins: it is a deep deterministic money engine with accumulated telecom billing invariants, not another BSS shell or anomaly model. Pairing it with D-NBS adds bilateral reconciliation and reproducible statement evidence.

### aurelianware/cloudhealthoffice — healthcare claims adjudication and payment-integrity operating plane
- Exact revision: `85c8e18146d168ad2f4e30fbcfe6e90af0bfdb58`.
- Score: **28/30** — A4 B5 C5 D5 E5 F4.
- Rights: BSL-1.1 publicly at the inspected revision; repository-owned code/content treated as commercially authorized under the user's standing assertion. CMS/NCCI/code sets, payer policies, FHIR/X12 materials, customer claims and third-party services remain separately governed.
- Concrete capability: payer-core adjudication spanning professional/institutional/dental claims, declarative plans/accumulators, fee schedules, NCCI/MUE-style edits, scrubbing, COB, provider/network state, prior authorization, FHIR R4, X12 and operator workflows, with benchmark semantics that preserve pended/unsupported states rather than forcing payment conclusions.
- Buyer/problem: health plans, TPAs, RCM/payment-integrity vendors and provider revenue-cycle teams need independent replay of complex claims state to distinguish true financial errors from contractual adjustments, patient responsibility or correctly pended claims.
- Monetization / first paid wedge: synthetic/redacted or customer-authorized Healthcare Revenue Integrity Diagnostic, paired with 837↔835 reconciliation and human review; no autonomous coverage/payment decisions.
- Why it wins: unusually deep end-to-end adjudication domain compression makes a deterministic claims-replay product plausible, while its explicit unsupported/pended states fit the portfolio's fail-closed evidence standard.

### ersinkoc/Kronos — heterogeneous recovery-verification engine
- Exact revision: `541d06069459a313f91940191a2ec3812f724a71`.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Rights: Apache-2.0 for repository-owned code; database engines, containers, storage providers and customer data remain separately governed.
- Concrete capability: backup/recovery orchestration with signed manifests and driver-based PostgreSQL, MySQL/MariaDB, MongoDB and Redis support; inspected evidence includes real MongoDB destructive-restore conformance, document count/checksum/index verification, large CI corpus and oplog/PITR-style rehearsal logic.
- Buyer/problem: regulated SaaS/MSPs/platform teams need proof across mixed database estates, not a PostgreSQL-only green restore signal.
- Monetization / first paid wedge: Mixed-Database Recovery Readiness Audit on 2–4 critical systems, then recurring proof-SLA monitoring layered with Redrill/Stronghold/SiVa.
- Why it wins: materially expands Recovery Proof's real-restore surface into MongoDB/mixed-engine estates while preserving verifiable post-restore state instead of treating process exit as proof.

### cmdrvl/canon — reviewed identity compiler and deterministic production registry
- Exact revision: `45e9702ba7f3874c073134c1a6fb74500232b6a1`.
- Score: **29/30** — A4 B5 C5 D5 E5 F5.
- Rights: MIT for repository-owned code; external provider/reference data and customer identities remain separately governed.
- Concrete capability: messy identity evidence → candidate/review decisions → promoted versioned registry → pinned deterministic runtime replay, with rule/confidence/unresolved provenance, provider materialization separated from runtime, and calibration/evaluation separated from registry mutation.
- Buyer/problem: MDM/data-governance, procurement/AP, CRM and public-data products need reviewed canonical identities that remain reproducible after source systems change rather than opaque one-off fuzzy matches.
- Monetization / first paid wedge: fixed-price multi-source vendor/customer/company canonicalization delivering a reviewed versioned registry, followed by recurring compilation/review/mapping service.
- Why it wins: the moat is the identity **governance and replay lifecycle**, not pair scoring. It provides a clean production boundary for probabilistic discovery and is immediately useful to CaptureBrief, freight carrier mastering and AP/vendor identity.

### owgreen-dev/grid-crunch — leakage-safe interconnection-queue materialization intelligence
- Exact revision: `5f0c9a074d928b79caa792a84e8e92de1b2df3f2`.
- Score: **29/30** — A5 B5 C5 D5 E5 F4.
- Rights: MIT for repository software. LBNL Queued Up, EIA-860M, HIFLD, gridstatus/ISO queue feeds and other upstream datasets retain independent rights/redistribution conditions.
- Concrete capability: reproducible competing-risks/survival analysis over public interconnection-queue history with fixed-horizon labels, strict entry-time leakage controls, out-of-cohort/within-ISO validation, calibration/lift and EIA-860M corroboration; it also preserves negative/null feature results and explicitly declines to claim post-Order-2023 validation that is not yet observable.
- Buyer/problem: renewable/BESS developers, infrastructure investors/lenders, equipment vendors and data-center/site teams need evidence-backed completion ranking rather than queue counts or hindsight-contaminated scores.
- Monetization / first paid wedge: fixed-price queue-portfolio underwriting/competition screen followed by recurring materialization monitoring/API.
- Why it wins: it provides both a monetizable signal and a rare epistemic moat—leakage discipline plus documented negative results that prevent false precision and wasted feature engineering.

## Deliberate portfolio tightening — 2026-09-19 22:31 ET
- `DominicFinn/open_tms` is demoted from MASTER leader to **component/reference**. Its broad logistics plumbing remains useful as an independent comparator, but Trenova now owns the primary commercial workflow plane and Freight-Audit-Console/Kareya/Qatoto provide stronger independent audit/rating oracles. No capability is rejected; it simply no longer belongs in the elite positive set.
- `ChelseaKR/constituent-reconciler` remains a **29/30 component/watch** rather than a second MASTER identity leader because Canon better represents the reusable reviewed-registry/replay DNA. Constituent Reconciler is indexed in `COMPONENTS.md` for consent-aware writeback.
- `oscal-compass/compliance-to-policy-go` (**27/30**) and `duke5am/pg-restore-drill` (**28/30**) are intentionally indexed as uniquely important components rather than standalone MASTER leaders; they strengthen the compliance/recovery stacks without creating separate buyer wedges.
- `justicebajaj161/Freight-Audit-Console` (**27/30**) remains an independent freight oracle in COMBINATIONS, not another freight MASTER leader; its revised-fuel/split-bill/residual-weight cases should be ported into the frozen benchmark.

<!-- INTEGRATOR-R11-2026-09-20T0025-0400 -->
## Promotions — 2026-09-20 integrator pass

The following entries cleared the normal 24/30 bar **and materially improve an active high-value stack**. Higher-scoring discoveries that are better treated as components, datasets, comparators or still-unvalidated adjacent businesses remain outside MASTER by design.

### GSA/GSA-Acquisition-DFARS
- Commit: `7e609f791af9cc6d8e7d75a7b05c83b1f62c0cb8`.
- Rights: GitHub metadata reported no blanket root public license at inspection. The user's standing separate commercial permission applies to repository-owned public content for portfolio analysis. DFARS/regulatory source status, linked material, standards/IPR and current deviation authority remain separately governed and must be cited from the controlling source.
- Score: **30/30 — A5 B5 C5 D5 E5 F5** under the standing separate-permission posture.
- Capability: official Acquisition.gov/GSA machine-readable DFARS publication with clause/section DITA, paragraph hierarchy, prescription cross-references, revision markers and case-source artifacts, plus rendered publication formats.
- Buyer/problem: DoD capture/proposal/compliance teams need exact current clause text, prescription and revision context without relying on scraped prose or stale summaries.
- Monetization / first paid wedge: CaptureBrief DoD rule-currency diagnostic on 10 live solicitations: cited clause -> structured DFARS source -> prescription/revision -> potentially controlling class deviation -> explicit current/conflict/unresolved state.
- Why it beats alternatives: this is first-party structured acquisition-rule evidence, not another secondary FAR search/index layer. It directly strengthens the authoritative rule chain already built around machine-readable FAR and deviation collection.
- Integrity boundary: repository recency alone is not proof of current applicability. Solicitation date/agency, supplement namespace, deviation/supersession and authoritative source evidence must resolve before a definitive conclusion.

### kingsleyonoh/invoice-reconciliation-engine
- Commit: `7545330806168102cd347d64a85a44481b37a6b3`.
- Rights: AGPL-3.0 public provenance; user's standing separate commercial permission applies to repository-owned code. Customer invoice/PO/receipt/approval/payment data and ERP integrations remain separately authorized.
- Score: **29/30 — A5 B5 C5 D4 E5 F5**.
- Capability: deterministic invoice -> PO -> goods-receipt three-way reconciliation with exact/normalized/fuzzy/fallback PO resolution, receipt verification, integer-cent discrepancy math, duplicate prevention, approvals, tenant isolation, audit logs and substantial matching/integration tests. Exception families include quantity, price, amount, overcharge, no-receipt, no-PO, duplicate and tax mismatches.
- Buyer/problem: AP audit/recovery firms, controllers and shared-services teams lose money to duplicate invoices, unsupported receipts, price/quantity drift and weak exception controls.
- Monetization / first paid wedge: fixed-price **AP Leakage Diagnostic** over one customer-authorized closed period, returning only source-linked evidenced exceptions and quantified exposure; recurring monitoring/recovery follows only after false-positive and outcome validation.
- Why it beats alternatives: it supplies tested money-bearing three-way control semantics rather than OCR, anomaly scoring or generic AP workflow.
- Integrity boundary: an exception is not a recovered dollar. Recovery requires source authority, reviewer disposition and later credit/refund/payment evidence.

### getcoherence/openpartner
- Commit: `eeff532ee758dc6221b4d03af852e5705a2328fb`.
- Rights: MIT public provenance plus the user's standing separate commercial permission. Stripe/payment-provider services, customer attribution events and plan/source records remain independently governed.
- Score: **29/30 — A5 B5 C5 D5 E4 F5**.
- Capability: event-sourced partner/affiliate attribution and payout control plane with accrual/review/reversal/fraud states, payout funding, durable batch/allocation reservations, transfer intents created before provider calls, immutable idempotency, unknown-result reconciliation, refunds/disputes recovery and residual receivable handling; inspected evidence included a large automated test/race-test surface.
- Buyer/problem: marketplaces/SaaS/channel businesses need proof that partner commissions were attributed, reversed and settled correctly, especially when payment-provider outcomes are ambiguous.
- Monetization / first paid wedge: one closed-period **Partner Payout Acceptance Test** comparing plan + source attribution + reversals/refunds + expected payable against actual payout/settlement.
- Why it beats alternatives: it models the dangerous settlement/idempotency/unknown-result edge, not merely a commission calculator or affiliate dashboard.
- Integrity boundary: no blind replay after an ambiguous provider result; hard-dollar claims require later settlement evidence.

### pedrocodesforcoffee/builder-api
- Commit: `3a9d2f3af61b485763a9f0cc4209ed1a8b584683`.
- Rights: repository-owned public code treated under the user's standing separate commercial permission; customer contracts, project records, AIA/other forms and legal authority remain separately governed.
- Score: **29/30 — A5 B5 C5 D4 E5 F5**.
- Capability: construction commercial-control backend that keeps owner PCO/OCO state distinct from subcontract/commitment CCO state, links cost codes/budget state, enforces approval-gated conversion and atomically carries approved commitment changes into commitment and budget committed cost.
- Buyer/problem: GCs and specialty contractors lose margin when one change is recognized on the owner side but fails to flow down/up correctly through subcontract commitments, budget and billing state.
- Monetization / first paid wedge: **Commercial Flow-Down Audit** on one project: trace a frozen set of changes through owner revenue, subcontract liability, budget mutation, pay-app/retainage and eventual payment evidence.
- Why it beats alternatives: it exposes the two-sided commercial state that generic change-order CRUD often flattens, making owner-vs-sub leakage measurable.
- Integrity boundary: contract entitlement, notice, waiver and payment-right conclusions remain external authoritative evidence; application state alone is not legal entitlement.

### automat-it/project-discovery-toolkit
- Commit: `8d46d765` (exact inspected revision recorded in hunter 15; preserve the full SHA from that catalog when referenced in downstream artifacts).
- Rights: repository public provenance recorded in hunter 15; user's standing separate commercial permission applies to repository-owned code. Database engines, storage, hosted infrastructure and customer production data remain separate.
- Score: **29/30 — A5 B5 C5 D5 E5 F4**.
- Capability: multi-engine full-restore verification across PostgreSQL, MySQL, SQL Server and related estates with strict source != target, measured RTO, queryability, object/row parity, engine-native integrity checks and per-table/checksum evidence. The repository explicitly does **not** prove PITR merely because a full restore succeeds.
- Buyer/problem: regulated SaaS/MSPs/self-hosters can show backup jobs succeeded but often cannot prove that a separate target was restored to a usable, internally consistent state.
- Monetization / first paid wedge: fixed-price Recovery Readiness Audit on 1–3 critical systems, then recurring proof-SLA monitoring.
- Why it beats alternatives: it exercises real restores and engine integrity instead of backup status; paired with negative controls it can test the verifier itself.
- Integrity boundary: full-restore proof, PITR proof, application invariants, RTO/RPO and cryptographic trust remain separate claims.

### genohm/slims-python-api
- Commit: `c3e3f5fb0ef0562550257aa3251caf5f5f9322b9`.
- Rights: Apache-2.0 public repository provenance plus the user's standing separate commercial permission. Agilent/SLIMS deployments, customer lab data, vendor services and instrument/vendor assets remain separately governed.
- Score: **29/30 — A4 B5 C5 D5 E5 F5**.
- Capability: production-shaped Python integration surface for Genohm/Agilent SLIMS, including entity/data access and SLimsGate workflow/callback/OAuth integration patterns that bridge an installed laboratory information estate to external automation.
- Buyer/problem: labs with an existing SLIMS estate need automation, data exchange and governed workflow extensions without replacing the system of record.
- Monetization / first paid wedge: automate one customer-authorized SLIMS workflow or instrument-result handoff with provenance, replay and human approval, then expand into recurring lab integration/governance.
- Why it beats alternatives: difficult installed-base integration is a stronger commercial substrate than another standalone LIMS or generic lab framework.
- Integrity boundary: begin with synthetic/dummy or explicitly authorized customer records; do not infer rights to vendor/customer data from repository permission.

### Promotion restraint this pass
High-scoring `PermitBuild`, `curatore-v2`, `BroadbandForum/usp-test`, `module-plc-emulator`, `Attestwire/en16931`, `Resolve_api`, `ICARUS-PJM-Dataset`, `LienGuard`, `pyfao56`, STORCITO and other 27–29/30 discoveries remain in COMPONENTS/DATASETS/COMBINATIONS/OPPORTUNITIES until they prove incremental buyer value or are better classified as source/comparator infrastructure. No existing MASTER leader was demoted on the evidence reviewed in this run.
