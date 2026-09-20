MARKER: <!-- INTEGRATOR-R11-2026-09-20T0025-0400 -->

=== APPEND MASTER.md ===
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

=== APPEND COMBINATIONS.md ===
## Integrator overlay — 2026-09-20 current priority architecture

This overlay supersedes older version labels where they conflict. It intentionally separates **source truth, deterministic decision, evidence sufficiency and realized outcome** instead of letting one implementation validate itself.

### 1. Freight Recovery v14 — correction-aware authority -> blind acceptance -> realized settlement
- Core: existing v12/v13 licensed freight operating/evidence/rerating stack + `sandyliu3056/UPS-reconciliation@d1e11940b262debc3c3216aba6467f39722c3000` as a specialist parcel correction/rebill oracle; same-family `ups-reprice-web` is deduped as supporting implementation evidence rather than a second leader.
- New capability: preserve original charge, corrected shipment facts and rebill chronology; recompute contractual billable weight/zone/base/accessorial/fuel where authority exists; compare only source-grounded expected charges to corrected invoices; carry validated variance into blind incumbent scoring and later credit/refund/remittance attribution.
- Negative control: `Emmanuel-tech-hub/freight-invoice-auditor@1987a776...` demonstrated the exact fail-open defect to forbid: a missing contracted accessorial rate must **not** default to $0 expected and make the billed line look recoverable. Missing/ambiguous authority = REVIEW/$0; `needs_review` rows are excluded from asserted and realized money totals.
- Buyer / wedge: unchanged — fixed-price Freight Audit Acceptance Test on a frozen customer-authorized population; optional shared savings only on incremental cash/credits uniquely attributable and actually realized.
- Status: **#1 commercial strategy.** The bottleneck is still a real frozen customer population with controlling contract/addenda/accessorials, shipment evidence, incumbent outputs and later settlement evidence, not another TMS/OCR/rating repository.

### 2. AP Leakage Assurance v1 — PO + receipt + invoice + approval + settlement
- Components: `kingsleyonoh/invoice-reconciliation-engine@7545330806168102cd347d64a85a44481b37a6b3` + Formalis/Attestwire structured-invoice validation where applicable + Canon/Resolve identity controls + proof/readiness and settlement evidence patterns from the recovery stacks.
- Combined capability: buyer-authorized PO/contract price -> goods receipt/service proof -> invoice identity/line math -> duplicate/price/quantity/tax/no-receipt/no-PO exception -> human disposition -> vendor credit/refund/payment outcome.
- First paid wedge: read-only closed-period AP Leakage Diagnostic with a planted synthetic benchmark before customer data; report exposure separately from recovered dollars.
- Hard invariant: uncertain PO identity, receipt, commercial authority, tax rule or settlement allocation = review/unresolved, never automatic recovery.
- Strategic position: strongest new direct-money challenger after freight because the source→variance→outcome loop is clear and buyer ROI is measurable.

### 3. ScopeSignal v5 — design change -> field proof -> flow-down -> billing/payment outcome
- Components: existing PDF/IFC/quantity/deadline/CPM stack + `mattumali579/scope-creep@1defef1bf87b2838ba0b36750e56c150841ed51c` signed/photo T&M capture + `clay-good/vaulytica@ffb88ed27354f8a3b17269d327ec29bd1d1fae98` contract/flow-down playbooks + `pedrocodesforcoffee/builder-api@3a9d2f3af61b485763a9f0cc4209ed1a8b584683` owner/sub commercial state + `SharkooMaster/Marginal@e422a07f31588e7e04a714a7b7ad2b2bcac21a11` actual-cost→scope-exception→customer-approval→billable chain + LienGuard/payment/waiver evidence where authoritative law/currentness is separately proven.
- Combined capability: revised drawing/model -> measured quantity -> contemporaneous labor/material/equipment/photo/signature proof -> controlling contract and flow-down clause -> authoritative notice clock/receipt -> owner PCO/OCO and subcontract CCO -> actual cost -> customer approval -> invoice/pay app/retainage/waiver/payment/lien-status evidence.
- First paid wedge: one-project Change Leakage Audit for specialty contractors/GCs, following 20–50 changes from field evidence to recognized/paid value.
- Hard invariant: prototype notice timers are never authority; conditional waivers remain UNKNOWN without payment-clearing evidence; app state does not prove statutory entitlement.

### 4. Partner / Commission Payout Assurance v2
- Components: `getcoherence/openpartner@eeff532ee758dc6221b4d03af852e5705a2328fb` event-sourced payout/settlement control plane + existing Kleegr/OCA deterministic commission comparators + buyer-owned plan, CRM/order, refund/dispute and payroll/payment evidence.
- Combined capability: source attribution -> versioned plan/rule -> accrual -> review/reversal -> payable -> provider transfer intent -> ambiguous-result reconciliation -> refund/dispute recovery -> actual settlement.
- First paid wedge: one closed-month blind plan-to-payout acceptance test.
- Hard invariant: an ambiguous external payout result is not retried blindly and is not treated as paid until independently reconciled.

### 5. CaptureBrief v6 — official baseline + supplement/deviation + forecast/recompete evidence
- Components: official GSA FAR + `GSA/GSA-Acquisition-DFARS@7e609f791af9cc6d8e7d75a7b05c83b1f62c0cb8` + GSAM/other current verified supplements + FAR Overhaul deviation collector + SAM packet/amendment acquisition + USAspending/DATA Act identity/award lineage + `davidlarrimore/curatore-v2` acquisition-forecast version history + `PHiZou/recompete-radar` explainable historical signal + `JonGerhardson/federal-agent` bulk SAM provenance.
- Combined capability: planned-buy/forecast signal -> incumbent/award history -> actual SAM notice and complete amendment packet -> namespaced FAR/DFARS/agency-supplement clause resolution -> potentially controlling deviation/currentness -> source-backed analyst decision.
- First paid wedge: 10-solicitation rule-currency/packet-completeness review plus a frozen forecast→actual linkage benchmark.
- Hard invariant: forecast/recompete score is not an actual solicitation; repository commit date is not rule effective date; stale/archived supplement sources cannot drive live applicability.

### 6. Recovery Proof v9 — full restore + negative control + PITR/app/trust separation
- Components: `automat-it/project-discovery-toolkit@8d46d765...` multi-relational full restore + `duke5am/pg-restore-drill@e914caddd14ab1604d85ccb7919d4da071a6766c` mandatory wrong-target/archive-gap negative controls + Kronos/Probavi/pg_hardstorage/BackupDrill/RestoreLab where engine-specific + application/object checks + SiVa/trusted evidence.
- Combined capability: restore to isolated target -> engine-native integrity -> object/row/checksum parity -> deliberate bad-target/bad-history/bad-checksum rejection -> separate PITR proof -> application invariants -> measured RTO/RPO -> signed/timestamped trust validation.
- First paid wedge: Recovery Readiness Audit on 1–3 systems followed by recurring proof freshness.
- Hard invariant: “backup succeeded,” “full restore succeeded,” “PITR succeeded,” “app works,” “RTO/RPO met” and “evidence is trustworthy” are six different claims.

### 7. Lab Automation v5 — installed-base SLIMS + vendor control + normalization + provenance
- Components: `genohm/slims-python-api@c3e3f5fb0ef0562550257aa3251caf5f5f9322b9` installed-base integration + SLimsGate callbacks/workflows + vendor-specific control/method surfaces such as VWorks and Thermo method/iAPI where buyer-authorized + Allotropy/Rainbow normalization + PyTestLab/Galago/PyLabRobot replay/control as appropriate + Flowcept/HELIOS provenance/governed campaign logic.
- First paid wedge: automate one existing SLIMS workflow/instrument-result handoff with dummy/authorized data, replayable evidence and human approval before broader campaign control.
- Hard invariant: normalized files, instrument command success, sample identity and scientific result validity remain separate evidence surfaces.

### 8. Industrial Virtual Commissioning / Pre-FAT
- Components: `Gaskony-Ignition/module-plc-emulator@518f56b55566d7e20f19ce64003cdae45a08edc8` plant-specific L5K→OPC-UA tag tree + ProtoForge fault/replay + PLC4X/protocol bridges + independent client/SCADA checks.
- Wedge: customer-authorized synthetic or exported controller namespace -> emulator -> Ignition browse/read/write/binding regression -> type/tag/namespace/fault report before hardware FAT/SAT.
- Promotion gate: reproduce one fully synthetic CompactLogix-style L5K→OPC-UA→Ignition binding corpus with expected failures. Vendor format/specification/trademark rights remain separate.

### 9. Broadband USP/CWMP Migration Readiness
- Components: `BroadbandForum/usp-test@5d53f5280b2a90ea0040887e62828c7b7369a240` TP-469 readiness corpus + `usp-data-models@a6c869d4c6e80a3d940c4dc4fbeb9b5c859d233d` structured model/version source + legacy CWMP model/tooling + existing Oktopus/Caretaker/OB-USP-Agent/independent clients.
- Wedge: 10–20 high-value firmware/certificate/reconnect/event cases plus customer model-diff before a CPE/ISP rollout.
- Integrity boundary: market as readiness/pre-certification unless formal BBF certification/test-suite/IPR rights are independently verified.

### 10. Permit-to-Development Intelligence
- Components: `adamleap02/PermitBuild@ff795137e0c66e62a87e62956fa351926886255d` multi-source canonical permit/version/field-QA plane + `mosswild/res_prop_mcp@ef64c7a928366a044bc51a8c528efad96916e833` parcel hazards/comps/distress/suitability + `Elliot-Sones/Hack_Canada@595508e46b3b881839a1ca9eb769712d74026573` deterministic zoning/variance/buildability/economics where jurisdictionally applicable.
- Wedge: source-backed developer/site-screen packet answering not merely “a permit exists” but “what this project/site means economically and what evidence supports that conclusion.”
- Promotion gate: held-out live addresses with source freshness, parcel identity, zoning-version/citation and pro-forma assumption survival through human review.

### 11. Emerging returnables/custody proof-to-cash family
- Industrial gas: `NiketanSP/CylinderManagementSystem@78a27f75ee849e1d33fa059122e913eb7dbe814c` supplies serialized shell purchase/status/fill/distribution/invoice/outstanding-payment semantics. Pair safety/inspection and delivery/empty-return proof; first wedge is cylinder-returnables + receivables reconciliation.
- Commercial linen: `JaroslawBolejko/HotelLinenManagerV2@381ef0a3081f7b01a695f11fdd13454b469aacd8` supplies hotel↔laundry service documents, weights/rates/tax/invoice authority. Pair deeper route/lot/custody evidence; first wedge is completed-but-uninvoiced and weight/rate discrepancy audit.
- Keep both below MASTER until one buyer-authorized custody→invoice→payment population proves measurable dollars.

=== APPEND REJECTED.md ===
## Integrator additions — 2026-09-20

### Emmanuel-tech-hub/freight-invoice-auditor — production-blocked fail-open recovery logic
- Revision: `1987a776` (full inspected SHA preserved in hunter 36).
- Reason: missing contracted accessorial authority can resolve to `$0 expected`, making a positive billed charge appear as an overcharge; rows marked `needs_review` can still flow into totals. In a recovery product this is a false-dollar failure, not a cosmetic defect.
- Disposition: retain only as a negative regression fixture. Do not use its output for asserted/recovered money.
- Revisit trigger: missing/ambiguous authority routes to REVIEW/$0, review rows are excluded from money totals, and tests prove the fail-closed behavior on planted missing-rate/accessorial cases.

### mccabetrow/capsight — permit/property connector surpassed on source truth
- Revision: `1f0afdaa90e8c7e5ef0c3310fdbc8ce6a5ecdb6`.
- Reason: inspected municipal source layer included placeholder/example dataset configuration and lacked the stronger retained controls for portal-count completeness, explicit source-health/refusal semantics and immutable permit-version history.
- Disposition: deprioritized; PermitBuild + Urban Signal + source-health/completeness components are stronger.
- Revisit trigger: real source coverage plus independently verified completeness, versioning/diff and `fresh/stale/not_covered/error` semantics.

### GSA/GSA-Acquisition-NMCARS — currentness not established
- Revision: `09d5b2d7040065fead99e15aacabb1d782b450d5`.
- Reason: repository maintenance recency did not establish that sampled substantive NMCARS content was current; inspected lineage pointed to older 2022-era content.
- Disposition: do not use for live rule applicability until independently reconciled with the current authoritative Navy/Marine Corps source.
- Revisit trigger: newer substantive publication or authoritative cross-check proves effective/current content.

### GSA/GSA-Acquisition-DAFFARS — historical/archived authority only
- Revision: `645e3050d4e40d600bdd68a8b7fd112a6bf3171b`.
- Reason: inspected repository is archived and directs users to a newer Department of the Air Force contracting publication location.
- Disposition: historical provenance only; never silently use the archived snapshot as current authority.
- Revisit trigger: none for current authority; follow the successor official source instead.

### Rejection lesson reinforced
Clear repository use permission does not cure **stale authority, fail-open money logic, weak source coverage or misleading completeness**. Technical/commercial scoring must continue to penalize those defects independently of license category.

=== APPEND DATASETS.md ===
## Additional elite data/evidence sources — 2026-09-20

### HopkinsICARUS/ICARUS-PJM-Dataset — large synthetic PJM-like grid testbed
- Repository/source: https://github.com/HopkinsICARUS/ICARUS-PJM-Dataset
- Exact revision: `0cb6a1af86e2bdfc1d160f44b6e4a7518ca3ffe3`.
- Category: Dataset / simulation testbed.
- Capability: 17,467-bus synthetic PJM-like network and associated planning/resilience/queue/large-load analysis surfaces suitable for reproducible regional stress and infrastructure studies without using a customer production grid model.
- Rights: repository software MIT and repository data CC BY 4.0 as recorded in hunter 23/related grid lane; upstream/source-derived assumptions and any external standards remain separately governed.
- Score: **29/30** at inspection.
- Product use: falsifiable large-load/DER/queue/resilience benchmark before customer feeder/system models; useful for testing whether algorithms preserve electrical constraints at meaningful scale.
- Next action: define planted congestion/voltage/contingency/large-load scenarios with expected engineering outcomes; do not market the synthetic network as a utility's actual grid.

### garretlking1-commits/jobwalk — synthetic construction evidence archive
- Repository/source: exact repository/revision recorded in hunter 04 (`fdcb507...`).
- Category: Synthetic benchmark / evidence archive.
- Capability: rights-clean synthetic construction evidence corpus spanning project/change/payment/waiver-style records useful for testing document linking and claim-state logic without customer/private records.
- Score: **27/30** at inspection.
- Product use: ScopeSignal acceptance tests around evidence continuity, payment/waiver ambiguity and change-state joins.
- Integrity rule: synthetic records are regression fixtures, not empirical construction-market evidence; conditional waiver effectiveness remains UNKNOWN without cleared payment/remittance proof.
- Next action: add deliberately contradictory and missing-evidence cases and require fail-closed output.

### xiazeyu/FireDataForge — historical wildfire event feature factory
- Repository/source: https://github.com/xiazeyu/FireDataForge
- Exact revision: `4328d4f6bdbec5a3ab30bf786718d759fc4fb84c`.
- Category: Dataset pipeline / benchmark infrastructure.
- Capability: harmonizes perimeter/fireline, VIIRS, terrain, fuels/canopy, weather, recent burn, building/land-cover, Sentinel-2 and WUI-style context onto consistent projected event grids with caching, batch work, skip/failure reasons and validation tooling.
- Rights: MIT repository code; every underlying public/hosted source retains its own terms/provenance.
- Score: **27/30**.
- Product use: historical backtest corpus for STORCITO and infrastructure/utility wildfire-risk systems.
- Next action: build a source-rights matrix and a 20-event benchmark with deliberate missing-layer degradation tests.

=== APPEND COMPONENTS.md ===
## Additional reusable components — 2026-09-20

### sandyliu3056/UPS-reconciliation — parcel correction/rebill specialist oracle
- Revision: `d1e11940b262debc3c3216aba6467f39722c3000`.
- Score: **28/30**.
- Capability: reconstructs UPS-style original/corrected billing chronology and contractual reprice logic including corrected weight/zone/returns/multipiece/LPS cases; useful for proving incremental base-charge shortages after corrections.
- Integration: Freight Recovery v14 specialist comparator, not a second TMS/rating plane. Same-family `ups-reprice-web` is deduped as supporting evidence.
- Rights: actual public provenance recorded in hunter 36; user's separate permission applies to repository-owned code. Carrier tariff/contracts/customer data remain separate.
- Next action: independently author correction/rebill fixtures and compare oracle output against the main freight calculation plane.

### clay-good/vaulytica — construction contract/flow-down rule component
- Revision: `ffb88ed27354f8a3b17269d327ec29bd1d1fae98`.
- Score: **28/30**.
- Capability: deterministic construction contract-analysis/playbook rules around prime/subcontract scope, incorporation/flow-down, payment/retainage, change orders, lien waivers, bonds, insurance/indemnity and related evidence.
- Integration: ScopeSignal v5 authority extraction/review before commercial-state calculations.
- Rights: MIT repository code; source legal forms/standards/current law remain independently governed and require authoritative current-source review.
- Next action: held-out contract set with exact source spans and deliberate conflicting/absent clauses; unresolved authority stays unresolved.

### abdu2030/Resolve_api — deterministic resolver challenger for identity mastering
- Revision: `de593e6...` (full exact SHA preserved in hunter 18).
- Score: **28/30**.
- Capability: evidence-oriented record/identity resolution that complements Canon's reviewed/versioned registry boundary.
- Integration: candidate generation/normalization -> Resolve/other challenger -> Canon human review/promotion -> pinned production registry.
- Next action: synthetic vendor/customer corpus with ambiguous aliases, mergers/splits and negative matches; compare false-merge/false-split frontier.

### attestwire/en16931 — independent structured-invoice rule oracle
- Revision: `09d08...` (full exact SHA preserved in hunter 16).
- Score: **29/30**.
- Capability: strong independent EN16931 structured-invoice validation source/oracle.
- Integration: use as a peer challenge to Formalis rather than replacing it; disagreements in money/compliance fields route to rule-pack/source review.
- Rights: repository-owned material under public/standing permission; official schemas/Schematrons/code lists remain separately governed.
- Next action: parity corpus across identical UBL/CII fixtures and exact rule-pack versions.

### adamleap02/PermitBuild — canonical permit/version/source-QA plane
- Revision: `ff795137e0c66e62a87e62956fa351926886255d`.
- Score: **29/30**.
- Capability: Socrata/ArcGIS/CKAN/Accela-style connectors, canonical permit/property schema, idempotent upserts, immutable versions + field-level diffs and demonstrated semantic source-field QA such as fee-vs-valuation and professional-role/date mapping corrections.
- Integration: PermitPlate source-of-event/version layer before parcel/buildability/economic enrichment.
- Safety: reported `.playwright-signup-evidence/` browser-profile-like artifacts were not opened or used; see EXPOSURES_INDEX.
- Next action: three-jurisdiction held-out completeness/semantic-mapping benchmark.

### davidlarrimore/curatore-v2 — acquisition-forecast version/history plane
- Exact revision: recorded in hunter 42 (`d4e42ac...`).
- Score: **29/30**.
- Capability: multi-source planned-buy/acquisition-forecast normalization with rich fields, SHA-256 content/history, first-seen/last-updated/field diffs and source-run success/failed/partial states.
- Integration: CaptureBrief pre-solicitation signal; forecast must later be linked to actual SAM notice/award evidence rather than treated as procurement fact.
- Next action: frozen forecast→SAM outcome benchmark and source coverage/failure accounting.

### Gaskony-Ignition/module-plc-emulator — L5K-derived virtual PLC
- Revision: `518f56b55566d7e20f19ce64003cdae45a08edc8`.
- Score: **29/30**.
- Capability: imports customer-authorized Rockwell L5K exports and creates an OPC-UA simulated controller with real tag hierarchy/types/UDT/AOI/arrays/module I/O and configurable behaviors; intended NodeIds can challenge HMI/SCADA bindings before hardware FAT.
- Rights: Apache-2.0 repository code; Rockwell/Allen-Bradley/Studio 5000/Ignition trademarks, proprietary formats/specifications and third-party test assets remain separate.
- Next action: synthetic L5K→OPC-UA→Ignition browse/read/write/type-drift regression.

### BroadbandForum USP acceptance/model family
- `BroadbandForum/usp-test@5d53f5280b2a90ea0040887e62828c7b7369a240` — **29/30**, standards-body TP-469-style acceptance procedures/pass metrics for message/path/access-control/MTP and stateful firmware/certificate/event behavior.
- `BroadbandForum/usp-data-models@a6c869d4c6e80a3d940c4dc4fbeb9b5c859d233d` — **25/30**, structured model/version/object/parameter/command/event source.
- `BroadbandForum/cwmp-xml-tools@ea856e227734001695e61135f38071afd67be90d` — **23/30**, archived migration/mapping/conversion tooling.
- Integration: CWMP/USP model diff -> selected acceptance cases -> independent controller/agent matrix -> readiness evidence.
- Rights: repository permission does not imply BBF certification, trademark, patent/IPR or wholesale standards redistribution rights.
- Next action: automate 10–20 highest-value cases while keeping outputs framed as readiness unless official certification rights are verified.

### thermofisherlsms/meth-modifications — official vendor method schema/version component
- Exact revision: recorded in hunter 20 (`b30bbe1...`).
- Score: **28/30**.
- Capability: Thermo method XML/XSD/versioned modification surface useful for authoritative instrument-method interchange and regression.
- Integration: Lab Automation v5 vendor-control plane beside SLIMS and normalized outputs.
- Rights: MIT repository code; Thermo runtime/services/trademarks/vendor ecosystem remain separately governed.
- Next action: dummy/authorized method round-trip with version mismatch and unsupported-field negative cases.

=== APPEND OPPORTUNITIES.md ===
## Current opportunity ranking overlay — 2026-09-20

### 1. Freight Audit Acceptance Test / Recovery — **29/30, unchanged #1**
The strongest path remains a frozen customer-authorized blind population carried through controlling authority, independent expected charge, incumbent comparison, dispute and actual credit/refund/remittance. Freight v14 adds correction/rebill evidence without changing the bottleneck.

### 2. AP Leakage Assurance — **29/30 challenger**
- Sources: invoice-reconciliation-engine + structured-invoice validation + identity/proof/settlement components.
- Buyer: controllers, AP shared services, audit/recovery firms.
- Wedge: one closed-period read-only three-way audit with planted duplicate/partial-receipt/price/quantity/tax/no-PO/no-receipt cases first.
- Monetization: diagnostic -> recurring assurance -> outcome-based recovery only on actually resolved credits/refunds.
- Key risk: PO/receipt identity and contractual/tax authority must fail closed; “exception dollars” are not “recovered dollars.”

### 3. Partner / Commission Payout Assurance — **29/30 challenger**
- Sources: OpenPartner + Kleegr/OCA commission comparators + buyer plan/CRM/refund/payment evidence.
- Wedge: blind one-month plan-to-payout reconciliation including refunds, disputes, reversals and ambiguous provider outcomes.
- Monetization: fixed diagnostic + recurring monitoring; recovered/avoided dollars require settlement proof.

### 4. Recovery Proof SLA v9 — **28–29/30 portfolio priority**
- Wedge: 1–3 critical systems, real isolated restore, mandatory bad-target/history/checksum negative controls, app invariants, RTO/RPO and evidence trust.
- Differentiator: prove the verifier can reject a deliberately wrong recovery, not merely produce a green report.

### 5. ScopeSignal v5 / Construction Change Leakage Recovery — **28/30 challenger**
- Wedge: one project, 20–50 changes, tracing design delta/field T&M through flow-down/notice, owner/sub commercial state, actual cost, customer approval and pay/payment/waiver evidence.
- Differentiator: measures whether field-incurred extra work actually became approved/billable/paid value.

### 6. CaptureBrief v6 — DoD rule currency + pre-solicitation evidence — **28/30**
- Wedge: 10 live DoD/GSA solicitations with exact FAR/DFARS/supplement/deviation resolution plus packet/amendment completeness; separately backtest forecast/recompete signals against actual notices.
- Differentiator: first-party structured regulatory source + source packet + award/identity lineage + explicit forecast-vs-actual separation.

### 7. Installed-Base Lab Automation v5 — **27/30 commercial priority**
- Wedge: automate one existing SLIMS workflow/instrument handoff using dummy or authorized records, normalized output and replayable provenance.
- Ceiling: high-value integration/governance work; sales cycle heavier than direct-money audits.

### 8. Industrial Pre-FAT / Virtual Commissioning — **27/30 challenger**
- Wedge: customer-authorized L5K namespace to virtual OPC-UA PLC, then HMI/SCADA binding/type/fault acceptance before hardware is available.
- Promotion gate: synthetic end-to-end bind benchmark with planted missing/type-drift/fault cases.

### 9. Permit-to-Development Opportunity Intelligence — **27/30 challenger**
- Wedge: trusted permit event/version -> parcel/hazard/economic context -> zoning/buildability/variance packet with source dates/citations.
- Differentiator: ranks what a permit/site means economically rather than selling raw lead rows.

### Emerging vertical audits — validate before promotion
- **Industrial Gas Returnables Proof-to-Cash:** serialized cylinder -> fill -> distribution/customer custody -> return -> invoice -> receivable/payment.
- **Commercial Linen Custody-to-Cash:** scheduled pickup/count/weight -> processing/return -> accepted service -> rate/tax -> invoice/payment.
- **Facilities Warranty Leakage:** work order/repair spend -> warranty/service-contract coverage -> receipt/document/claim state -> vendor/manufacturer recovery outcome. `sassanix/Warracker` is useful evidence plumbing but remains below MASTER at 23/30.

=== APPEND EXPOSURES_INDEX.md ===
## Additional redacted exposure observations — 2026-09-20

### sandyliu3056/UPS-reconciliation
- Repository: `sandyliu3056/UPS-reconciliation`.
- Canonical URL: https://github.com/sandyliu3056/UPS-reconciliation
- Exact revision used for safe technical evidence: `d1e11940b262debc3c3216aba6467f39722c3000`.
- High-level exposure type: repository documentation/history indicated older public versions contained password/authentication material.
- Apparent status: **unknown; no historical value was retrieved, copied, tested or validated**.
- Non-sensitive context: current safe source was evaluated only for parcel correction/rebill semantics.
- Remediation note: repository owner should ensure any historical credential is revoked/rotated; hunt should use only sanitized revisions and never reopen secret-bearing history.

### BritneyMcCullough/PayrollReconciliation
- Repository: `BritneyMcCullough/PayrollReconciliation`.
- Exact revision: `64cd190...` (full exact SHA preserved in hunter 21).
- High-level exposure type: tree contains payroll-like `data/uploads/` and `data/runs/` artifacts that could hold personal/private operational data.
- Apparent status: **not inspected**; no artifact contents or personal values were opened or retained.
- Non-sensitive context: safe source/code evidence was sufficient to assess its normalization/matching architecture.
- Remediation note: continue code-only inspection; use synthetic fixtures for benchmarking unless customer data is explicitly authorized.

### adamleap02/PermitBuild
- Repository: `adamleap02/PermitBuild`.
- Exact revision: `ff795137e0c66e62a87e62956fa351926886255d`.
- High-level exposure type: repository documentation reports `backend/.playwright-signup-evidence/` may contain browser-profile/cookie/autofill/payment-adjacent state.
- Apparent status: **not opened, copied, tested or used for authentication**.
- Non-sensitive context: permit connector/version/semantic-QA code was assessed independently of that directory.
- Remediation note: owner should review/remove any sensitive browser state and revoke unintended accounts; hunt must continue to avoid the directory.

### kasun-m-rathnayaka/gas-distributer-backend
- Repository: `kasun-m-rathnayaka/gas-distributer-backend`.
- Exact revision: `f0a1f8013759f11be625f383a9449826f0751f37`.
- File/path: committed `backend/.env.development.local`; file was not opened.
- High-level exposure type: environment/configuration artifact potentially containing secrets/auth material.
- Apparent status: **unknown; not tested or validated**.
- Remediation note: quarantine this revision; revisit only a sanitized revision/fork.

### dev-k99/ScrapFlow
- Repository: `dev-k99/ScrapFlow`.
- Exact revision: `170a655118347be55fcefd8f94f51747df8a9a35`.
- High-level exposure type: public documentation exposed authentication material.
- Apparent status: **unknown; no value retained, tested or used**.
- Remediation note: revisit only sanitized later revision; rotate/remove any exposed authentication material.

### openmymed/open-fleetr
- Repository: `openmymed/open-fleetr`.
- Exact revision: `8a4bfdd8ff644784b3706d4821ca49fb98e5c188`.
- High-level exposure type: public SQL artifact contains credential-like authentication material and personal-data-like seed values.
- Apparent status: **not inspected beyond safe metadata; no value/person record retained or tested**.
- Remediation note: sanitize the dump and rotate potentially live credentials before any revisit.

### anjalaeepriyadarshaniyapa/Medical-Waste-Management-System
- Repository: `anjalaeepriyadarshaniyapa/Medical-Waste-Management-System`.
- Exact revision: `f1ea2792db9b3a8684a68677c2f4391a6107c83b`.
- High-level exposure type: README contains login credential-like authentication material.
- Apparent status: **unknown; no value retained, tested or used**.
- Remediation note: remove public authentication material and rotate if potentially live; inspect only a sanitized later revision.

=== APPEND hunters/04.md ===
## 2026-09-20 — merged staged construction recovery findings

### mattumali579/scope-creep — STRONG — 27/30
- URL: https://github.com/mattumali579/scope-creep
- Exact revision: `1defef1bf87b2838ba0b36750e56c150841ed51c`.
- Capability: mobile/offline extra-work/T&M capture converting labor, overtime, material, equipment, photos and on-screen signature into a priced PDF ticket with history and tested phone/PDF behavior.
- Buyer/wedge: specialty subcontractor signed-T&M recovery/capture audit; compare performed extra work to contemporaneous tickets and downstream PCO pricing.
- Rights: package metadata private/UNLICENSED and no root LICENSE found; user's standing separate commercial permission applies to repository-owned code. AIA/contract/legal sources remain separate.
- Evidence caveat: built-in/default notice clock is prototype logic and must never override controlling-contract/calendar authority.
- Combination: ScopeSignal revision/quantity -> scope-creep field proof -> authoritative deadline engine -> commercial state/payment outcome.

### SharkooMaster/Marginal — STRONG / MASTER referral — 28/30
- URL: https://github.com/SharkooMaster/Marginal
- Exact revision: `e422a07f31588e7e04a714a7b7ad2b2bcac21a11`.
- Capability: Django/mobile construction margin flow where field CheckIn/MaterialUsage becomes actual cost; out-of-scope labor/material creates linked ÄTA; state proceeds detected -> review -> internal approval -> sent -> customer approval, and only customer approval creates billable scope. Invoice-basis math includes customer-approved changes only.
- Buyer/wedge: project change-leakage/margin audit — find actual field cost that never reached customer-approved/billable state.
- Rights: no root LICENSE found; repository-owned code treated under standing separate permission. Swedish/legal/tax rules remain separate.
- Caveat: prototype seven-day notification timing is not authoritative; use contract-derived timing.
- Combination: field proof + actual-cost exception + owner/sub commercial flow + pay/payment evidence.

### Staged watch/reject disposition
- `rene-kropf/scopeguard@6789ad36dde903881b403948243cceadb59e3ad1` remains **watch 21/30** as low-friction local approval UX; do not treat QR/link approval as independent immutable receipt/authority without server/audit identity evidence.
- `python-construction-automation/python-construction-automation@fc525cb7c908993a84f5d5f019d08e6898fb23d6` remains **rejected/deprioritized 17/30** because the inspected repository is primarily a documentation/reference site, not a transactional entitlement engine.
- `Latif080790/PM-NATA@e9a7c5e8092f226c0bf2ae115d1321170d36cf1e` remains **rejected 16/30**; generic PM/budget surface, README approximately 25% complete, no material evidence-to-recovery improvement.

=== APPEND hunters/06.md ===
## 2026-09-20 — merged staged downstream property/development findings

### mosswild/res_prop_mcp — STRONG — 25/30
- URL: https://github.com/mosswild/res_prop_mcp
- Exact revision: `ef64c7a928366a044bc51a8c528efad96916e833`.
- Capability: installable property-intelligence server with tested FEMA flood, USGS elevation/seismic, USDA soil/septic, EPA hazard, wildfire, assessor/ranking, listing, parcel, pre-foreclosure, FSBO, historical-comps and source-health tools.
- Buyer/wedge: paid enrichment packet attached to a trusted permit/project lead; answer site risk/suitability/comps/distress context rather than adding generic lead rows.
- Rights: no root LICENSE verified; standing separate permission applies to repository code. Redfin/FSBO/county portals and government/commercial data sources remain separate.
- Score: A4 B4 C4 D4 E4 F5 = **25/30**.
- Next action: held-out active permit addresses with source/retrieval/coverage state on every enriched field and measurable change in lead ranking.

### Elliot-Sones/Hack_Canada (CoCivil) — STRONG / MASTER referral — 28/30
- URL: https://github.com/Elliot-Sones/Hack_Canada
- Exact revision: `595508e46b3b881839a1ca9eb769712d74026573`.
- Capability: Ontario/Toronto land-development due-diligence platform with parcel/PIN, zoning/overlay/setback/height/coverage, deterministic compliance matrices and by-law citations, precedent/approval research, massing/infrastructure and financial feasibility/pro-forma; substantial schema/test evidence.
- Buyer/wedge: fixed-price parcel feasibility packet for developers/architects/land-use teams: trusted project/parcel identity -> zoning compliance/variances -> approval risk -> preliminary economics with cited sources.
- Rights: no root LICENSE verified; standing separate permission applies to repository code. Toronto Open Data, Ontario planning/building law, OLT/CanLII and other sources/services remain separately governed/currentness-sensitive.
- Score: A4 B5 C5 D5 E4 F5 = **28/30**.
- Integrity: AI/planning prose is not authority; controlling zoning version and citations must survive human review.

=== APPEND hunters/33.md ===
## 2026-09-20 — merged staged warranty-recovery finding

### sassanix/Warracker — WATCH — 23/30
- URL: https://github.com/sassanix/Warracker
- Exact revision: `07d12c2cc163b9ce7d2d49c004f4898ceb05d616`.
- Capability: mature self-hosted warranty manager with purchase dates/durations, serials/vendors, receipts/invoices/manuals, expiry alerts, multi-user/RBAC, import/export, audit trail and warranty-claim status/date/resolution lifecycle.
- Buyer/problem: facilities/property operators may pay repair spend that was recoverable under warranty or miss claim windows because proof and claim state are fragmented.
- Wedge: portfolio warranty-leakage audit linking maintenance spend to active coverage and missing/incomplete claim lifecycle.
- Rights: AGPL-3.0 public provenance plus standing separate commercial permission for repository-owned code. Warranty terms, receipts/documents and asset records remain separately governed/private.
- Score: A3 B3 C4 D3 E5 F5 = **23/30**.
- Disposition: useful evidence layer below MASTER. Promote only if it materially improves recovered-dollar tracking versus the current CAFM/service-contract stack.

=== REPLACE SEARCH_QUEUE.md ===
# SEARCH_QUEUE

Integrator-owned search and validation direction. Updated 2026-09-20 after the latest cross-lane sweep. The portfolio is now mature enough that **validation and missing-evidence searches outrank broad repository collection**. Search by repository family, old product name, protocol/standard, file/class signature, dependency graph, fork/commit/PR lineage and obscure/low-attention projects when a concrete gap remains.

## Operating rules for all 14 workstreams
- Deduplicate by **repository + exact revision + capability**, not name alone.
- Use the user's standing separate commercial-permission assertion for repository-owned public code/content when prioritizing. Still record the actual public license/provenance and keep third-party standards, data, models, trademarks, patents, assets, APIs/services and customer records separate.
- Verify beyond README with source, tests, schemas/migrations, fixtures, deploy/config structure and history when safe.
- Never inspect, retain, test or use credentials/authentication material, private/personal/confidential data, vulnerabilities or accidentally exposed secrets. Record sanitized metadata only.
- No padding: a run with no new validated find is acceptable.
- Prefer the MASTER DNA: vertical operating systems; deterministic audit/recovery; authoritative public-data/evidence infrastructure; standards/protocol acceptance; difficult installed-base integration; optimization/decision engines; service-first B2B wedges with measurable outcomes.

## 1. Freight Recovery v14 — P0: validate money, not more plumbing
Hunt/validate only: external accessorial/addendum/tariff authority, carrier correction/rebill chronology, incumbent/FAP reason-code exports and credit/refund/812/820/remittance settlement lineage. Build the first authorized blind population where contract/addenda, shipment/POD/BOL/appointment evidence, invoices, incumbent decisions and later settlement all exist for the same frozen shipments. Add independently authored UPS-style corrected-weight/zone/multipiece/return cases to the benchmark.

**Stop/deprioritize:** generic TMS, OCR, EDI/X12 libraries, rate parsers, entity matching, invoice anomaly models, parcel repricers or freight CRUD unless they introduce a rare authority/settlement invariant that materially beats the current stack. Missing authority must route to REVIEW/$0.

## 2. AP Leakage Assurance — P0: three-way exception -> credit/refund outcome
Use `invoice-reconciliation-engine` as the current decision core. Build a rights-clean synthetic corpus with duplicate invoice, partial/missing receipt, PO identity ambiguity, quantity/price drift, tax mismatch, credit memo, partial settlement and fuzzy-PO false-match cases. Then target one authorized closed AP period with PO/contract, receipt/service proof, invoice, approvals and later payment/credit evidence.

**Search gaps:** ERP export adapters that preserve immutable source IDs/version/effective commercial terms; credit/debit/remittance allocation; difficult service-receipt/blanket-PO cases. Route lane findings into `hunters/07.md`, which remains under-covered.

**Stop:** generic AP OCR/RPA/invoice dashboards.

## 3. ScopeSignal v5 — P0: change evidence -> flow-down -> recognized/paid value
Run one held-out construction change end to end: drawing/model delta -> quantity -> signed/photo T&M -> controlling contract/flow-down source -> authoritative notice trigger/receipt -> owner PCO/OCO + subcontract CCO -> actual cost -> customer approval -> budget/commitment -> pay app/retainage/waiver -> payment/collection. Search only missing authoritative receipt/delivery, payment-clearing, owner/sub flow-down and cost/causation evidence.

**Stop:** generic PDF/CAD diff, takeoff, CPM, notice calculators, CO CRUD, field-photo apps or legal-text summarizers. Prototype notice timers are never authority; conditional waiver effectiveness remains UNKNOWN without cleared payment evidence.

## 4. Partner / Commission Payout Assurance — P0/P1
Build a closed-period benchmark covering plan version, source attribution, splits/overlays, tier boundaries, refund/dispute/clawback, partial payout, provider timeout/unknown result, idempotency and residual receivable. Compare OpenPartner and existing Kleegr/OCA semantics against the same gold truth, then seek one authorized month from CRM/order through payroll/payment settlement.

**Search gaps:** authoritative plan/version sources and provider settlement/reconciliation adapters only.

**Stop:** affiliate dashboards, generic commission calculators and payout wrappers without reversal/settlement truth.

## 5. CaptureBrief v6 — P0/P1: namespaced rule currentness + packet + forecast-to-actual
Extend the live benchmark with DoD/GSA solicitations: FAR baseline -> DFARS/agency supplement namespace -> prescription/revision -> class deviation/effective/supersession -> solicitation packet/amendment evidence. Separately freeze Curatore/recompete forecasts and later link to actual SAM notices/awards without rewriting history. Validate SAM bulk provenance states (`complete`, `restricted`, `partial`, `source_error`, `not_found`).

**Search gaps:** current official acquisition supplements/deviation successor sources and hard source-currentness/version metadata; not another wrapper.

**Stop:** generic SAM search wrappers, FAR scrapers, RAG over regulations, award dashboards or speculative recompete products without backtests. NMCARS/archived DAFFARS examples are negative currentness controls.

## 6. Recovery Proof v9 — P0: prove the verifier rejects bad recovery
Create a matrix across PostgreSQL/MySQL/SQL Server/Mongo/Redis/application/object state with deliberate wrong target, missing WAL/binlog/history, bad checksum, stale proof, broken app invariant and untrusted/revoked timestamp evidence. Full restore and PITR remain separate. Compare `project-discovery-toolkit`, pg negative-control fixtures, Kronos and engine-specific leaders on identical cases.

**Stop:** generic backup tools, status dashboards, hash/signing libraries or restore scripts without independently falsifiable recovery-state tests.

## 7. Lab Automation v5 — P1: installed-base integration and provenance
Validate a dummy/authorized SLIMS workflow through `slims-python-api`/SLimsGate, one vendor method/control surface (VWorks/Thermo or buyer-installed equivalent), normalized output (Allotropy/Rainbow) and provenance/replay. Search only buyer-relevant installed-base adapters, vendor file/method version bridges and missing instrument command/result identity links.

**Stop:** generic LIMS, lab orchestration frameworks, plate-reader demos or another optimization loop unless it closes a specific installed-base integration gap.

## 8. Industrial Virtual Commissioning / Pre-FAT — P1
Build one synthetic L5K controller namespace -> OPC-UA emulator -> Ignition browse/read/write/binding test with planted missing tags, type drift, UDT/array edge cases and fault/scenario response. Combine with ProtoForge/PLC4X only where independent protocol/fault evidence adds value.

**Search gaps:** real namespace/type migration or protocol-fault acceptance cases; vendor-export parsers with safe synthetic fixtures.

**Stop:** generic PLC/Modbus/OPC simulators and protocol libraries.

## 9. Broadband USP/CWMP Migration Readiness — P1
Automate 10–20 high-value TP-469-style cases: certificate add/reconnect, firmware download/activate/checksum/cancel, ScheduleTimer/Notify/event lifecycle and model/path support. Diff legacy CWMP-supported model against current USP GetSupportedDM/data-model versions and run independent controller/agent implementations.

**Stop:** collecting more ACS/controllers/agents. Treat BBF certification marks/IPR/test-suite rights separately; output is readiness/pre-certification unless independently authorized.

## 10. Permit-to-Development Intelligence — P1
Use PermitBuild as the permit source/version/semantic-QA plane. On held-out active addresses, attach parcel identity/hazard/comps/suitability, then deterministic zoning/buildability/variance/economic evidence where the jurisdiction is supported. Every enrichment must carry source, retrieval date and coverage/error state; every legal/planning conclusion needs current authoritative citation/human review.

**Stop:** generic permit maps/leads, property aggregators with placeholder datasets, or enrichment that does not materially change opportunity ranking.

## 11. Grid / infrastructure risk and large-load decisions — P1
Use ICARUS-PJM as a synthetic scale testbed; preserve grid-crunch/queue_attrition historical/prospective discipline and CIMHub/DREAMS/ERAD feeder engineering. Where wildfire is buyer-relevant, test STORCITO live/current risk against FireDataForge historical event features before linking to asset failure/restoration. Require planted constraints and out-of-time outcomes.

**Stop:** generic power-flow wrappers, hazard maps or queue dashboards without engineering parity/calibration/outcome evidence.

## 12. Identity / provenance / structured evidence — P1
Benchmark Resolve/candidate engines -> Canon reviewed promotion -> pinned runtime -> controlled writeback on synthetic mergers/splits/aliases/negative matches. Challenge Formalis with Attestwire on identical structured-invoice fixtures and pinned rule packs. Search only provenance/lineage gaps that block a money/evidence product.

**Stop:** generic fuzzy matching, RAG, lineage dashboards, hash chains or signing layers that do not improve a top commercial decision.

## 13. Field / returnables proof-to-cash — P2
Validate one synthetic custody-to-money chain in each promising niche before expanding: industrial gas cylinder serial -> safety/fill -> route/customer -> empty return -> invoice/AR/payment; commercial linen pickup/count/weight -> processing -> accepted return -> rate/tax -> invoice/payment; facilities warranty work -> coverage -> document/claim -> credit/recovery. Prefer old product names, serialized-asset ledgers, deposits/rentals, route acceptance and settlement classes.

**Stop:** generic FSM, CMMS, laundry POS, delivery apps, ERP CRUD or warranty reminders without custody/entitlement/invoice/payment outcome.

## 14. Sparse-lane repair + wildcard analog search — P2
The shared system has broad coverage, but `hunters/08.md`, `hunters/29.md`, `hunters/30.md` and `hunters/31.md` remain especially under-filled; `hunters/07.md` also needs the strong AP findings referred into its thematic catalog. Direct these workstreams to deeply inspect at least one candidate in each sparse domain:
- insurance/claims: deterministic entitlement/reserve/subrogation/recovery or claim settlement evidence, not quote forms;
- pricing/yield: constrained inventory/capacity/revenue optimization with counterfactual ROI, not dynamic-pricing demos;
- payments/billing: hard reconciliation/settlement/reversal/unknown-result semantics, not payment SDK wrappers;
- tax/accounting: current authoritative rules plus deterministic money/reconciliation outcome, not stale calculators;
- wildcard: adjacent industries that reproduce the MASTER pattern `source authority -> deterministic expected state -> actual state -> evidence -> realized outcome`.

## Global stop list / search discipline
Do not spend hunter capacity on generic OCR, dashboards, CRUD, RAG, basic fuzzy matching, commodity auth/RBAC, basic job queues, generic protocol clients, generic optimization demos, backup-status tools, generic TMS/CMMS/FSM/LIMS/AP OCR, or speculative AI agents unless the candidate contributes a **rare domain invariant, authoritative source, difficult installed-base integration, independently falsifiable algorithm, or realized-money/evidence loop** that beats a current leader.

## Current validation order
1. Freight blind population through actual settlement.
2. AP synthetic three-way corpus -> one authorized closed period.
3. Partner/commission closed-period benchmark -> settlement.
4. ScopeSignal one-change evidence-to-paid benchmark.
5. Recovery Proof positive + negative adversarial matrix.
6. CaptureBrief DoD rule-currentness and forecast-to-actual benchmark.
7. Lab/industrial/broadband/permit challengers only after their focused held-out tests.
