# COMBINATIONS

Cross-repository product and capability combinations. Keep only combinations that are materially more valuable than their components alone; superseded versions are replaced rather than duplicated.

## Combination rules
- Preserve exact component revisions and rights boundaries.
- A combination is commercial only when the joined capability solves a named buyer problem and has a falsifiable validation step.
- Data/source rights are independent from repository-code rights.
- Unknown, contradictory or insufficient evidence must remain unknown/review; it must never be converted into a positive claim or dollar amount.

## Active combinations — 2026-09-19

### 1. Freight Recovery v9 — blind incumbent-auditor bake-off + rights-clean XLS tariff intake + proof-to-settlement
- Components: `DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1` + `sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc` + `vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408` + XLS intake `BestKylin2001/Freight-Rate-Sheet-Generator@78f3b86a2a4a25d9abf11d4addc2feea10667352` + structured invoices `hupe1980/en16931@894a3e0d36dea6d3dc086d066881d9a691b20882` + unstructured extraction `getomni-ai/zerox@91bbb20c50de86067670aa13833afa1b8a73c22e` + calibrated acceptance `OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2` + rules `microsoft/RulesEngine@5650f93f843865610240e0498b26b68b477a3920` + identity GoldenMatch/Dedupe + benchmark `aiparallel0/freight-audit@e7869162cf9cb23f6d520a0cd71f87cf973d8c28` + proof/readiness `srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac` + authorized live evidence `warpfreight/warp-agent-mcp@1850556032b465a0c24839e28564687462067323` + X12/settlement primitives already cataloged.
- Combined capability: customer-authorized rate workbook/PDF + shipment/POD/BOL + invoice → reviewed/versioned controlling tariff → deterministic rerating → evidence-gated finding → blind incumbent comparison → dispute packet → credit/refund/remittance attribution → realized recovery.
- New advantage this run: the messy-XLS rate-card gap is no longer purely hypothetical. BestKylin supplies a permissive baseline for header discovery, aliases, Excel dates/formula values and canonical ocean-rate output. No-license carrier-specific parsers remain clean-room requirements only for multi-origin/destination, add-on/base tables and included/excluded surcharge cases.
- Buyer: CFO/controller, VP Transportation/Supply Chain, freight-payment/AP leaders and 3PL finance teams with material freight spend.
- First paid wedge: fixed-price Freight Audit Acceptance Test on a frozen customer population; optional success fee only on uniquely attributable realized cash/credits the incumbent did not already identify.
- Rights: core listed code is permissive as cataloged. Customer contracts/rates and incumbent decisions require authorization. No-license carrier parser source/data is not reused. X12-derived metadata/fixtures require independent provenance.
- Required benchmark discipline: production population and challenge corpus are separately reported; gold truth is frozen before incumbent outputs are opened; clean invoices are included; unresolved extraction, controlling-rate authority, entitlement, shipment identity, contradiction or settlement allocation yields **$0 asserted recovery**.
- Validation: at least 20 challenge cases plus one representative customer-authorized production population. First decisive KPI = verified dollars incumbent missed minus false-positive dollars introduced; second = realized incremental recovery.
- Status: **#1 commercial strategy.** Remaining P0 is customer-authorized PDF/accessorial authority + an incumbent-comparison/settlement population, not generic TMS/OCR/XLS discovery.

### 2. ScopeSignal v2 — registered 2D/IFC revision → quantity delta → entitlement evidence
- Components: 2D revision core `MassingCloud/massing-pdf@36794b3c54fcfd62e3a0d2d5984cfc45cac83340` + quantity engine `Kentucky-ai/opentakeoff@6ff9cc355e60d6312c0c82e2ddac56cb212cc394` + IFC revision evidence `delongwangshu49-hub/bimchange-agent@cd7fd6e6522e060b7847f0daaed00979097da7dd` + Zerox/Docling for contract/spec intake + RulesEngine + evidence/proof gates.
- Combined capability: old/new sheet registration with translation/scale correction and markup migration → structured changed regions/model elements → measured quantity delta → controlling contract/spec clause → reviewer-approved compensability and commercial-impact packet.
- Why stronger: Massing-pdf closes the missing 2D registration problem that raw pixel/OCR diff could not. A drawing difference still does **not** become compensable until entitlement evidence is present.
- Buyer: specialty contractors, GCs, BIM/VDC, quantity surveyors, estimators and change/claims teams.
- First paid wedge: one issued revision pair with aligned redlines + migrated-markup review queue + quantity delta; measure review time/false positives before attaching dollars.
- Rights: Massing-pdf/BIMChange are MIT; OpenTakeoff Apache-2.0. Customer drawings/contracts remain customer data.
- Validation: 20 rights-clean synthetic/public revision pairs spanning translation, scale, reorder, crop and moved-only annotations; then one customer-authorized pair through exact clause/quantity evidence.
- Status: Strong. Next gap is entitlement-to-dollar proof, not generic PDF diff.

### 3. Compliance/resilience v3 — collect → restore/PITR → govern remediation → re-prove
- Components: Attestful collectors + `Polycentric-Labs/evidentia@0e0bc8bac7d8e4b71f729ac488fd3b47273f5531` + `RamazanKara/restore-drill@dea374da3b340f53b798112eee82bd7ed1224572` + PostgreSQL proof engine `cybertec-postgresql/pg_hardstorage@b47541b7e1cea69ce6ec63b26e154eb25fc4ca91` + optional `backupdrill/cli@401954dd01d1141d81eda488ddf30c7d08b0f0e9`/`iacosta3994/restic-drill@0e11db6339fc86f87239b259827f6848a69886f7` adapters + remediation governor `google/cybernetic-agent-governance-engine@50b12e7d983db0e3d7faf206ac6aa600294f33ac`.
- Combined capability: evidence collection → normalized control state → real isolated restore/PITR → database/content/application checks → signed verdict → allow/deny/require-approval remediation decision → fresh re-test/evidence.
- Why stronger: pg_hardstorage supplies unusually hard proof: actual recovery plus `pg_verifybackup`/`pg_amcheck` and signed verdict. This moves the product beyond “backup job succeeded.”
- Buyer: regulated SaaS, MSP/MSSP, platform/SRE teams, cyber-insurance/compliance consultants.
- First paid wedge: fixed-price Recovery Readiness Audit on one backup/recovery point, then recurring independent drills.
- Rights: permissive as cataloged; backup/customer data and cloud/provider terms separate.
- Validation: vendor-neutral evidence schema containing artifact identity, target, duration, structural/logical checks, app invariants, content hashes, limitations and signer; reproduce on PostgreSQL plus one non-Postgres/object-storage path.
- Status: High-value challenger; now validation/packaging constrained, not tool-discovery constrained.

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

### 9. Field-service proof-to-cash assurance
- Components: `proforcetech/phparm@a691ebfdea93a20f9de5f8a076430c859f299255` + `TheGringo-ai/cmms-normalize@dd0c752f6e0da0506ffb95ea6832c66dae81eb92` + scheduling/repair `RosterSpec` + evidence/rules layer.
- Combined capability: normalize heterogeneous work-order history → prove scheduled/entitled field visit → capture QR/photo/work evidence → detect missed SLA/out-of-scope/unbilled work → route repair/exception without fabricating fields.
- Buyer: janitorial/facilities contractors and multi-site maintenance operators.
- First paid wedge: normalize one export and quantify missed/unprovable/out-of-entitlement work plus baseline SLA/backlog metrics.
- Rights: phparm/cmms-normalize MIT; customer work-order data requires authorization.
- Validation: three synthetic/customer-authorized CMMS export shapes must preserve labor/status/date semantics and fail closed on non-work-order files.
- Status: Strong niche wedge; regulated PTW/LOTO/MOC semantics remain clean-room/authoritative-source work.

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
