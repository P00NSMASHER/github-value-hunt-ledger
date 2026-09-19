# COMBINATIONS

Cross-repository product and capability combinations. Keep only combinations that are materially more valuable than their components alone; superseded versions are replaced rather than duplicated.

## Combination rules
- Preserve exact component revisions and rights boundaries.
- A combination is commercial only when the joined capability solves a named buyer problem and has a falsifiable validation step.
- Data/source rights are independent from repository-code rights.
- Unknown, contradictory or insufficient evidence must remain unknown/review; it must never be converted into a positive claim or dollar amount.

## Active combinations — 2026-09-19

### 1. Freight Recovery v10 — physical-truth detention/accessorial proof + blind incumbent bake-off + proof-to-settlement
- Components: permissioned physical-truth/recovery subsystem `kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045` + `DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1` + `sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc` + `vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408` + XLS intake `BestKylin2001/Freight-Rate-Sheet-Generator@78f3b86a2a4a25d9abf11d4addc2feea10667352` + structured invoices `hupe1980/en16931@894a3e0d36dea6d3dc086d066881d9a691b20882` + unstructured extraction `getomni-ai/zerox@91bbb20c50de86067670aa13833afa1b8a73c22e` + calibrated acceptance `OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2` + rules `microsoft/RulesEngine@5650f93f843865610240e0498b26b68b477a3920` + identity GoldenMatch/Dedupe + benchmark `aiparallel0/freight-audit@e7869162cf9cb23f6d520a0cd71f87cf973d8c28` + proof/readiness `srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac` + authorized live evidence `warpfreight/warp-agent-mcp@1850556032b465a0c24839e28564687462067323` + X12/settlement primitives already cataloged.
- Combined capability: customer-authorized rate workbook/PDF + shipment/POD/BOL + invoice + geofence/appointment/arrival/departure evidence → reviewed/versioned controlling tariff → physical-truth validation of detention/time-based accessorials → deterministic rerating → evidence-gated finding → blind incumbent comparison → approval-ready dispute packet → credit/refund/remittance attribution → realized recovery.
- New advantage this version: Opstrax closes the hardest evidence gap in freight recovery: converting physical movement and appointment truth into defensible money. Its consumed-event ledger, later-of(appointment, arrival) clock, pre-expiry notices, customer/tenant rule cards, fail-closed pricing, immutable evidence hashes, approval controls and exactly-once charge creation can now be directly reused/adapted under the user's separate commercial modification/deployment permission rather than reimplemented clean-room.
- Why stronger than v9: v9 could prove document/rate mismatches but still depended on external evidence for whether detention/accessorial events actually happened. v10 can connect operational telemetry to entitlement and then carry the same evidence chain through blind auditor comparison and settlement attribution.
- Buyer: CFO/controller, VP Transportation/Supply Chain, freight-payment/AP leaders, 3PL finance teams, brokers and carriers with material freight spend or detention/accessorial exposure.
- First paid wedge: fixed-price Freight Audit Acceptance Test on a frozen customer population, with Opstrax-powered detention/accessorial evidence review. Optional success fee only on uniquely attributable realized cash/credits the incumbent did not already identify.
- Rights: core listed code is permissive as cataloged except Opstrax, which has no public license but is covered by the user's separately stated permission for **commercial modification and deployment**. Treat that as permissioned direct reuse for the user's projects only; preserve the permission record and do not assume redistribution/sublicensing or third-party rights. Customer contracts/rates, telemetry and incumbent decisions require authorization. No-license carrier-parser source/data remains excluded. X12-derived metadata/fixtures require independent provenance.
- Required benchmark discipline: production population and challenge corpus are separately reported; gold truth is frozen before incumbent outputs are opened; clean invoices are included; unresolved extraction, controlling-rate authority, entitlement, shipment identity, physical-event contradiction, notice/free-time evidence or settlement allocation yields **$0 asserted recovery**.
- Required Opstrax regression cases: geofence bounce/re-entry dedupe; missing entry/exit pair; appointment before/after arrival; free-time boundary; pre-expiry notice present/missing; customer-specific vs tenant-default rule card; cap/rounding; event already consumed; duplicate approval; missing evidence reference; validated override; share-token/evidence integrity; invoice detention with no supporting dwell; carrier-side unbilled detention where entitlement is provable.
- Validation: at least 20 challenge cases plus one representative customer-authorized production population. First decisive KPI = verified dollars incumbent missed minus false-positive dollars introduced; second = realized incremental recovery. Detention findings must reconstruct the exact event pair, appointment, free-time rule, rate-card version, notice state, calculation, approval and settlement.
- Status: **#1 commercial strategy and #1 overall repository-driven opportunity.** Remaining P0 is the first customer-authorized population containing controlling rate/accessorial truth + invoice/shipment evidence + incumbent decisions; generic TMS/OCR/rating discovery is no longer the bottleneck.

### 2. ScopeSignal v3 — consensus revision evidence → quantity delta → BCF issue envelope → entitlement
- Components: primary 2D revision core `MassingCloud/massing-pdf@36794b3c54fcfd62e3a0d2d5984cfc45cac83340` + independent vector/raster comparator `joedanields/CaD-Track@5ae85e868e12f1814381174a3afdfff6e5edf629` + quantity engine `Kentucky-ai/opentakeoff@6ff9cc355e60d6312c0c82e2ddac56cb212cc394` + IFC revision evidence `delongwangshu49-hub/bimchange-agent@cd7fd6e6522e060b7847f0daaed00979097da7dd` + portable BCF 2.1/3.0 issue/viewpoint layer `LTplus-AG/ifc-lite@802a30fba331feab9101ad4241335b97cfef023a` (`@ifc-lite/bcf`) + Zerox/Docling for contract/spec intake + RulesEngine/evidence gates.
- Combined capability: old/new drawing/model registration → independent structural correspondence check for added/removed/moved/modified entities → reconciled changed regions/model elements → measured quantity delta → portable BCF topic/viewpoint retaining exact IFC GlobalId/context → controlling contract/spec/RFI/submittal evidence → reviewer-approved compensability and commercial-impact packet.
- New advantage this run: CaD-Track provides a second rights-clean detector with explicit vector-entity matching and a reliability warning for weak extraction, so ScopeSignal can measure detector disagreement rather than trust one visual pipeline. IFC-lite's tested BCF 2.1/3.0 path preserves exact model-object/viewpoint context when a validated finding leaves the detector and enters human review.
- Buyer: specialty contractors, GCs, BIM/VDC, quantity surveyors, estimators and change/claims teams.
- First paid wedge: one issued revision pair → Massing/CaD-Track comparison → reconciled change set + migrated markups → quantity delta + BCF review packet. Measure registration/correspondence disagreement and analyst time before attaching dollars.
- Rights: Massing/BIMChange are MIT; OpenTakeoff and CaD-Track Apache-2.0; IFC-lite MPL-2.0 with file-level copyleft obligations. Customer drawings/models/contracts remain customer data. BCF interoperability does not itself prove entitlement.
- Validation: 20 rights-clean held-out vector/raster revision pairs spanning translation, rescale/DPI, reorder, crop, moved-only annotations and extraction-density imbalance; measure each detector separately and consensus/disagreement. For IFC, round-trip one known changed GlobalId through BCF 3.0 and at least one independent viewer. Then carry one customer-authorized finding through exact quantity + clause/evidence + reviewer decision.
- Status: Stronger and more falsifiable. **Stop generic BCF and 2D-diff discovery.** Remaining P0 is downstream entitlement/notice/change-event/cost evidence; detector disagreement routes to review, never dollars.

### 3. Compliance/resilience v4 — collect → restore/PITR → tamper-evident proof → govern remediation → re-prove
- Components: Attestful collectors + `Polycentric-Labs/evidentia@0e0bc8bac7d8e4b71f729ac488fd3b47273f5531` + `RamazanKara/restore-drill@dea374da3b340f53b798112eee82bd7ed1224572` + PostgreSQL proof engine `cybertec-postgresql/pg_hardstorage@b47541b7e1cea69ce6ec63b26e154eb25fc4ca91` + signed/Merkle evidence layer `allthingsN/openwright@83d0035bbe89e0fd0c86e94d90c065db94080a8b` + remediation governor `google/cybernetic-agent-governance-engine@50b12e7d983db0e3d7faf206ac6aa600294f33ac`. `forevidence/provenance-seal@082e786cd85612314bedf0ff0707a931ecbc808f` is an independent negative-test comparator; the Apache portions of `coverbasedev/trustmcp@61d52efefbc5326f8910f0c116edfbc59ab89cf3` are optional for customer-facing signed evidence exchange.
- Combined capability: collect normalized control evidence → execute a real isolated restore/PITR → run database/content/application checks → record canonical events with Merkle inclusion proof/signed checkpoint and explicit gap/insufficient-evidence semantics → normalize control state → allow/deny/require-approval remediation → fresh re-test and new independently verifiable evidence.
- New advantage this run: OpenWright pins the control crosswalk hash, includes underlying event inclusion proofs in the signed report and preserves `insufficient_evidence` rather than silently mapping gaps to pass. Provenance Seal independently reinforces the critical boundary that an unanchored local chain proves self-consistency, not immutable independent existence. This closes a chain-of-custody weakness left by ordinary signed summary reports.
- Buyer: regulated SaaS, MSP/MSSP, platform/SRE teams, cyber-insurance/compliance consultants and vendors repeatedly answering customer assurance requests.
- First paid wedge: fixed-price Recovery Readiness Audit on one backup/recovery point, delivering artifact identity, recovery target/duration, structural/logical/application checks, signed inclusion evidence, limitations and a human-readable pass/review/fail. Recurring drills can later publish scoped deltas through a rights-cleared TrustMCP subset if buyers need continuous evidence exchange.
- Rights: Evidentia/restore-drill/pg_hardstorage/OpenWright/CAGE are permissive as cataloged. OpenWright is Apache-2.0; framework/crosswalk content still needs provenance review. Provenance Seal code is Apache-2.0 and its spec is CC-BY-4.0. TrustMCP has Apache-designated spec/SDK/MCP/conformance surfaces but FSL-restricted reference applications; do not repackage restricted apps as a competing hosted service.
- Validation: vendor-neutral evidence schema plus adversarial chain tests: mutate an event, delete/reorder an event, change crosswalk hash, forge a `satisfied` result, use a stale checkpoint, truncate the tail and present an unanchored rewritten chain. Missing/dropped evidence must remain review/insufficient, never compliant. Reproduce on PostgreSQL plus one non-Postgres/object-storage path.
- Status: High-value challenger. Generic evidence-ledger/signing discovery is now sufficiently covered; remaining risk is real recovery/application invariants, external anchoring and buyer acceptance—not cryptographic plumbing.

### 4. Marketplace Settlement Reliability OS — execute correctly + independently detect money-state drift
- Components: rights-clean execution/accounting semantics from `spree/spree@65839390ae2048a491de948364c93edf310ef478` plus previously cataloged MIT marketplace split-payment/double-entry substrate + independent read-only assurance `tonytonycoder11/stripe-connect-reckon@deb30aabfed84c7b0b2e5ae28c92cc9f85f79193`.
- Combined capability: seller earning/reversal/payout state + concurrency/ambiguous-provider handling + independent read-only Stripe/app-state reconciliation for failed payouts, event gaps, refund mismatches, negative balances, reserve/dispute exposure and forecasting.
- Why stronger: the assurance plane can be sold without replacing the customer's payment execution path, dramatically lowering pilot friction while still targeting direct financial exposure.
- Buyer: marketplace CFO/controller/finance-ops/risk and engineering teams using Stripe Connect.
- First paid wedge: Marketplace Money Safety Audit using read-only authorized data; report unresolved exposure and reconciliation exceptions, then convert to recurring monitoring.
- Rights: Spree BSD-3-Clause; stripe-connect-reckon MIT; provider terms/customer authorization separate.
- Validation: synthetic fault corpus with known failed payouts, refund-state mismatches, missing events, negative-balance trajectories, reserve exposure and dispute spikes; score precision/recall, time-to-detection and false-alert burden.
- Status: **New high-priority challenger.** Strong first-revenue shape, but not yet evidence-backed enough to displace freight.

### 5. Industrial interoperability acceptance lab
- Components: simulator/fault/replay plane `suoten/ProtoForge@7c61b10d9ae406224c86741d9c0a450b561b40ca` + multi-vendor client/gateway comparator Apache PLC4X + Logix/EtherNet/IP digital-twin candidate `joyautomation/nautilus@ee970ebc12edd894fdab4f83d557cef100cbf986` + independent device/client implementations such as OpENer/EIPScanner where standards-rights boundaries are satisfied.
- Combined capability: model customer-authorized industrial endpoints → normal/fault/disconnect/timeout/write/replay scenarios → independent-client comparison → reproducible compatibility/evidence matrix before plant cutover.
- Buyer: industrial gateway/SCADA vendors, machine builders, system integrators, OEM QA and plant OT teams.
- First paid wedge: fixed-price gateway regression pack for 3–10 device types and three verified protocol families.
- Rights: ProtoForge MIT and PLC4X Apache-2.0; protocol standards, vendor marks/patents and third-party libraries remain separate. OpENer itself warns of separate ODVA technology/mark obligations.
- Validation: start with Modbus TCP, IEC-104 and OPC UA using external clients; only market protocol coverage that passes reproducible cross-implementation tests.
- Status: New strong B2B cluster. Stop broad protocol-library hunting; validate protocol-by-protocol commercial reliability.

### 6. Network management-plane migration acceptance
- Components: `clicon/clixon-controller@36ecc0fd8787750978652495a39d0d01db2c7474` + dense synthetic device plane `notconf/notconf@cc2499d2a859aa76a3ec3a265ec7c36f2d5ea07e` + independent reference server `CESNET/netopeer2@5be28a93e783b41d1c284c1275c9b24237d0454d` + current gNMI probe/control plane `openconfig/gnmic@ce0d4173630ae73fe9cfe124ce8d564fa3b69c5e`.
- Combined capability: model YANG/OpenConfig estate → replay validate/lock/commit/rollback/disconnect/timeout plus Get/Set/Subscribe workflows across synthetic and independent endpoints → machine-readable migration compatibility report.
- Buyer: telecom operators, MSPs, NMS/OSS/controller vendors and network automation integrators.
- First paid wedge: fixed-price controller/NMS migration preflight on one representative service/config workflow before production cutover.
- Rights: Clixon/gnmic Apache-2.0; notconf/Netopeer2 BSD-3-Clause. Vendor YANG models/content remain separately licensed.
- Validation: identical OpenConfig fixture across 10–100 notconf endpoints and Netopeer2; retain semantic disagreements as regression cases rather than treating any single implementation as the standards oracle.
- Status: Strong new difficult-integration service wedge.

### 7. Lab/instrument automation + analytical-development evidence fabric
- Components: `labiium/pytestlab@8b7f873e29457f05dee7af0de698e27985c98a33` + `sciencecorp/galago-tools@7ddf68c7bb7eda0243f6466cfbd6b97fdcfcf782` + `PyLabRobot/pylabrobot@c3c59eebf45c4f6bb2fc78dbfd30f6e458653494` + `ORNL/flowcept@c000b10ea49659af6c5821b61918f3893bd46a92` + high-value vendor lane `novonordisk-research/OptiHPLCHandler@96399dcddc1457a5b942f61585b9e8fcf78b9a72`; optional NIST `rmellipse@79daadef817c892e0366cd748279665c6f1f8dd3` for correlated metrology uncertainty.
- Combined capability: vendor/device control + hardware-independent replay/simulation + assay/sample-set/method generation inside an existing CDS + workflow provenance and optional recalculable uncertainty chain.
- Why stronger: OptiHPLC adds a specific, high-budget analytical-development workflow rather than another generic lab framework; Flowcept preserves run lineage and PyTestLab makes regression evidence reproducible.
- Buyer: pharma/biotech analytical-development/QC labs, CROs, instrument integrators and research cores.
- First paid wedge: automate one existing Empower robustness/stability/assay workflow while preserving Empower as system of record; measure expert touches removed and reproducibility.
- Rights: listed code permissive as cataloged; vendor runtime/API/instrument licenses and customer methods/data remain separate.
- Validation: mock/synthetic Empower flow first, then customer-authorized hardware/CDS validation. Do not imply vendor certification.
- Status: Strong service-first vertical; buyer access is the main friction.

### 8. CaptureBrief verified procurement intelligence
- Components: `MindPetal/sam-search@019b31dca0f980e79117a7c559777cb357a2a385` + `blencorp/capture-mcp-server@e91ce243cd6a62e9c2a55609d34a187fca89703b` + `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964` + `fedspendingtransparency/data-act-broker-backend@76dcae4ccbf6951223608bc1d8fd0c5b03da5d68` + `cliwant/mcp-sam-gov@aaaaa70dcb6a08cf43cb40ece26b79d6d21c2463` + identity/rules/evidence layers.
- Combined capability: current opportunity → authoritative recipient/parent/award identity → incumbent/competition history → exact clause/prescription/deviation evidence → explainable bid/no-bid/readiness packet.
- Buyer: federal primes/subs and capture/proposal consultants.
- First paid wedge: manually verified 10-opportunity evidence packet benchmark.
- Rights: MIT/CC0 as cataloged; applicability/currentness remains contextual and human-reviewed.
- Validation: no stored source/hash or locatable support means no accepted high-risk claim; unresolved upstream source remains unresolved, not “not found.”
- Status: High-priority architecture; generic SAM/fuzzy-wrapper discovery is exhausted.

### 9. Field-service proof-to-cash assurance v2 — entitlement → proof → invoice parity → settlement
- Components: contract/service-route layer `proforcetech/phparm@a691ebfdea93a20f9de5f8a076430c859f299255` + fail-closed normalization `TheGringo-ai/cmms-normalize@dd0c752f6e0da0506ffb95ea6832c66dae81eb92` + neutral service/evidence/dispute/settlement protocol `servicialo/mcp-server@5cc669d667f650f454bfaeb9236a88a540475219` + invoice-parity component `theluckystrike/mcp-work-order@5ea2600d0adf50e7f79b4af12b2be76fc51924d2` + schedule repair `joschiservice/RosterSpec@f7e701c694bf1facdc4999e1681a3aa11493614d`; optional ERPNext adapter `Beveren-Software-Inc/Field_Service_Management@ab6d56d1069882326475f256d09cc63236eddec1`.
- Combined capability: normalize completed work → bind to controlling agreement/warranty/entitlement → prove delivery from required evidence → derive invoice lines from the same captured labor/material source → detect completed-but-unbilled work, unsupported charges, rounding/markup drift and SLA exceptions → preserve dispute/collection state.
- Why stronger this run: Servicialo separates delivery, evidence, acceptance and financial settlement, while mcp-work-order adds a concrete regression for minor-unit/unit-markup invoice parity. The product can now test proof-to-cash continuity rather than merely finding missing visits.
- Buyer: janitorial/facilities, equipment-service, inspection/calibration and other recurring field-service operators where completed work and contract entitlement frequently diverge from billing.
- First paid wedge: replay 100 completed customer-authorized work orders against contract/warranty state and invoices; quantify provable completed-but-unbilled value, unsupported billed value, completion→invoice lag and arithmetic drift.
- Rights: phparm/cmms-normalize/mcp-work-order MIT; Servicialo/RosterSpec Apache-2.0; Beveren is AGPL-3.0 and optional. Customer contracts/work orders/photos/GPS/invoices require authorization and appropriate privacy handling.
- Validation discipline: include entitled/warranty/no-charge jobs, missing proof, partial delivery, amended scope, duplicated lines, unit-markup rounding and already-settled cases. Missing entitlement, insufficient proof or ambiguous settlement = **$0 asserted recovery**.
- Status: Materially stronger direct-money niche. Stop generic FSM/CMMS/work-order CRUD discovery; hunt only vertical entitlement and settlement evidence that can change dollars.

### 10. Workforce schedule assurance
- Components: `joschiservice/RosterSpec@f7e701c694bf1facdc4999e1681a3aa11493614d` + existing workforce/dispatch datasets/adapters where lawful.
- Combined capability: verify published roster → explain infeasibility → generate and re-solve minimum-disruption repair around locked work.
- Buyer: contact centers, fulfillment, healthcare ops and field service.
- First paid wedge: replay historical callouts and compare coverage, paid hours/overtime and assignment churn against manual repairs.
- Rights: Apache-2.0 core.
- Validation: historical/synthetic ground truth with independent oracle checks.
- Status: Strong algorithmic assurance wedge; no need for more generic schedulers.

### 11. Grid hosting + resilience decision stack
- Components: SHIFT-style feeder generation + `sandialabs/DREAMS@3eb6c6089eadf09a4bf99961faac11a76ef30ca0` + `NLR-Distribution-Suite/erad@735f7a6baa9fe24878a986a3425bf6d55ad556c3`.
- Combined capability: synthetic/customer feeder → hosting/QSTS constraints → hazard-induced asset failure → network consequence → restoration/hardening priority.
- Buyer: utilities, DER/storage developers, engineering consultants and insurers.
- First paid wedge: one rights-clean feeder with planted hosting and damage cases; produce constraint thresholds and restoration priorities.
- Rights: code permissive as cataloged; feeder/hazard/fragility data have separate provenance.
- Validation: independent OpenDSS/engineering truth checks before any interconnection or resilience claim.
- Status: Technically compelling, slower enterprise sale than freight.

### 12. Warehouse movement-to-slotting ROI
- Components: `agritheory/inventory_tools@dd1e07d98eb81b2388acb922ce9ae3397a5af7ac` + `gokhanozden/gabak@711856814856e1730bd3be1cc7e4468ceca4fd5d`.
- Combined capability: ERP movement heat + dimensional/capacity fit → slotting recommendation → layout/path simulation → travel/labor ROI evidence.
- Buyer: warehouses/DCs, especially ERPNext operators.
- First paid wedge: fixed-price re-slotting diagnostic.
- Rights: MIT; ERP/customer movement data separate.
- Validation: neutral CSV geometry + pick-list benchmark exposing capacity violations, travel savings and labor assumptions.
- Status: Discovery largely resolved; prove ROI/willingness-to-pay.

### 13. TR-069 → TR-369 migration/conformance lab
- Components: `freeacs/freeacs@f4c5d056ac6c247e0757de20acacd6046fd0ef0d` + rights-clean current CPE simulator `softov/cwmp-sim@5fa8fd830bba178310febb9e62d87df17ce9a306` + `OktopUSP/oktopus@e1f07d71a93c4169421f2e94ce6605746ece37ad` + BSD OB-USP-Agent + Apache agent simulation assets already cataloged.
- Combined capability: deterministic legacy CWMP fleet/session fixture → equivalent USP controller/agent fixture → behavioral migration gap report.
- Buyer: regional ISPs/WISPs, ACS/controller vendors and CPE OEMs.
- First paid wedge: provisioning-change/migration preflight across BOOT/periodic/Get/Set/download/diagnostic plus equivalent USP operations.
- Rights: FreeACS MIT, cwmp-sim BSD-3-Clause, Oktopus Apache-2.0; BBF/vendor data-model/spec assets remain separate.
- Validation: 50–100 simulated CPE identities and differential lifecycle cases.
- Status: Rights-clean legacy endpoint gap is now closed enough for a pilot; stop generic USP/CWMP discovery.

### 14. GST input-tax reconciliation assurance
- Components: `Tamil-Venthan/Rekvia@158d199e4f08041e587a70926f2ed22d17511431` + deterministic evidence/rule/versioning layers.
- Combined capability: Purchase Register↔GSTR-2B duplicate-safe matching → discrepancy/risk classification → reviewed exception evidence.
- Buyer: Indian SMEs/accounting firms.
- First paid wedge: fixed-price reconciliation diagnostic; recurring exception service only after current IMS/GSTR rules are independently validated.
- Rights: MIT code; taxpayer/government-rule data separate.
- Validation: accountant-reviewed monetary outcomes on current rule set; never infer recovered ITC from a mismatch alone.
- Status: Credible but below freight until current-rule and realized-value validation is complete.

### 15. Commission payout assurance — blind plan-to-payroll acceptance test
- Components: rights-clear executable settlement substrate `OCA/commission@288b2a8a62920657b40b845983fcc31860463af6` (AGPL-3.0) + independently authored plan-version/credit/split/clawback test cases derived only from technology-neutral behavior documented in no-license/proprietary references such as `The-Thought-Magician/commission-dispute-ledger@d848a728205c0d3f557767fa4d7765ae2a04acd6` and `hvs-finmarkai/CommissionEngine-AI@1c2ddb5e1cd13ddfe49d78d793cf2056e98d86b3` + evidence/provenance gates from the shared assurance stack.
- Combined capability: freeze customer-owned plan/version/rep/territory/transaction facts → independently calculate supported fixed/section/margin settlement cases → extend with clean-room quota/split/accelerator/clawback fixtures → compare expected vs incumbent-calculated vs approved vs payroll-paid amounts with a replayable discrepancy trace.
- Buyer: enterprise RevOps, sales-comp, finance/controller and payroll teams with large variable-compensation spend and costly payout disputes.
- First paid wedge: fixed-price Commission Payout Acceptance Test over one closed compensation period; gold truth is frozen before incumbent output is opened, then disagreement dollars and reviewer/dispute labor are measured.
- Rights: OCA execution code is AGPL-3.0 and requires compliance if deployed/modified as a networked service. The no-license/proprietary references are **inspect/learn/clean-room only**; their source/tests are not copied. Customer comp plans, CRM transactions and payroll data require authorization and strict handling.
- Validation: 30–50 synthetic cases spanning fixed rates, section boundaries, gross vs margin, multiple agents, currencies, settlement periods, effective-date boundaries, cumulative vs marginal tiers, split/overlay credit, retro rerating, clawback/draw/carry-forward and cent-exact allocation; then one customer-authorized closed period.
- Status: **High-value direct-money challenger, not yet a MASTER leader.** It resembles freight's audit-the-auditor economics, but buyer-data integration and realized payout-correction evidence remain unproven.