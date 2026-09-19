# COMBINATIONS

Cross-repository product combinations. Keep only stacks that are materially more valuable than any component alone. A combination is commercial only when the joined capability solves a named buyer problem and has a falsifiable validation path. Unknown, contradictory or insufficient evidence stays REVIEW/UNKNOWN and never becomes a positive claim or dollar amount.

## Active combinations — 2026-09-19

### 1. Freight Recovery v10 — contract truth + physical evidence + deterministic rerating + blind incumbent bake-off + settlement proof
- Core components: permissioned `kodekinetics79/opstrax-enterprise-build@fec2ba1432d6f8b4ba4c48be3d58e7e096819045` + `DominicFinn/open_tms@93d8c2b8ff78373ff69bb7ea546743e4703628b1` + `sengtha/Kareya-Silo@a43eedea03add0728eadfc1f8ea35cc3ca6867cc` + `vidyesh95/qatoto-backend@4f5f270f6ba5ef3ed4b230716997ccea049ce408` + RateCon parser `A-Jatin/freight-ratecon-extraction@a3dbbfec7f6b042176880d06c5114f81f29e57eb` + XLS baseline `BestKylin2001/Freight-Rate-Sheet-Generator@78f3b86a2a4a25d9abf11d4addc2feea10667352` + calibrated acceptance `OmarFaig/Assay@821303935ef2855908a9a9bd1efd4c33f9cd39d2` + structured-invoice validation `mgilbir/formalis@2b3895a0c2c54e4f25ccb46e131d215ad4457eb2` with `hupe1980/en16931@894a3e0d36dea6d3dc086d066881d9a691b20882` as parser/serialization companion + benchmark `aiparallel0/freight-audit@e7869162cf9cb23f6d520a0cd71f87cf973d8c28` + proof/readiness `srthck/trustmesh@5a93d70b37aafecaf61a5bc0296eaf831e5504ac` + authorized transaction evidence `warpfreight/warp-agent-mcp@1850556032b465a0c24839e28564687462067323` + existing X12/settlement allocation primitives.
- Combined capability: customer-authorized contract/rate source + appointment/geofence/POD/BOL + invoice → source-grounded reviewed authority → provider/revision/effective-date control → deterministic rerating → proof-obligation gate → blind incumbent comparison → dispute packet → credit/refund/remittance attribution → realized recovery.
- New advantage: generic RateCon extraction is no longer the primary gap. A-Jatin supplies a tested evidence-gated RateCon path, while Opstrax supplies physical dwell/appointment truth for detention. The remaining hard problem is **accessorial/addendum authority that lives outside a clean RateCon plus real incumbent/settlement outcome evidence**.
- Buyer: CFO/controller, VP Transportation/Supply Chain, freight-payment/AP leaders, 3PL/broker finance and carrier revenue-assurance teams.
- First paid wedge: fixed-price Freight Audit Acceptance Test on a frozen customer population; optional success fee only on uniquely attributable cash/credits actually realized and not already identified by the incumbent.
- Rights: listed permissive code follows its licenses; Opstrax is usable only under the user's separately stated commercial permission; customer contracts/rates/shipments and provider data require authorization; do not reuse unlicensed carrier parsers or unclear sample documents.
- Validation: at least 20 challenge cases plus one representative customer-authorized production population. Gold truth is frozen before incumbent output is opened. Report extraction accuracy, auto-accept false accepts, finding precision, false-positive dollars, dollar-weighted recall, proof readiness, incumbent-missed dollars and realized incremental recovery.
- Hard invariant: unresolved extraction, controlling-rate/accessorial authority, entitlement, shipment identity, contradiction, evidence independence or settlement allocation = **$0 asserted recovery**.
- Implementation checkpoint (2026-09-19): **Freight Recovery v10 core v1.0 is now implemented with the permissioned Opstrax detention subsystem directly adapted into the runnable core.** The combined regression suite passes **55/55 tests**. New Opstrax-specific coverage includes consumed-event idempotency, bounce re-entry merge, superseded-exit protection, post-close duplicate absorption, customer-site gating, shortest-provable timeout intervals, customer-over-tenant rule precedence, later-of appointment/arrival clocks, round-down increments, notice-once behavior, late-arrival override gates, shipper-reference and claim-window gates, SHA-welded immutable evidence, exactly-once approval/billing, supplemental drafts and shipper-side detention validation. A 3-hour dwell with 2 free hours at $75/hour correctly supports $75 expected detention; a $150 billed line yields a **$75 validated variance** with evidence SHA. Artifact: `/Freight Recovery/Stack/freight-v10-core-v1.0-opstrax-integrated.zip` in ChatGPT Library. Buyer-facing Demo v5 now exposes both fail-closed and physical-proof paths: unsupported accessorial evidence remains $0 asserted recovery, while a permissioned Opstrax 180-minute dwell with 120 free minutes at $75/hour validates $75 expected detention against a $150 billed line, producing a $75 evidence-linked overcharge. Consolidated launch artifact: `/Freight Recovery/Stack/freight-audit-acceptance-lab-launch-bundle-v2.zip`.
- Status: **#1 commercial strategy.** Generic freight TMS/OCR/rating discovery is no longer the bottleneck; the decisive P0 is the first authorized customer population.

### 2. ScopeSignal v3 — consensus revision evidence → quantity delta → portable issue context → entitlement
- Components: `MassingCloud/massing-pdf@36794b3c54fcfd62e3a0d2d5984cfc45cac83340` + independent comparator `joedanields/CaD-Track@5ae85e868e12f1814381174a3afdfff6e5edf629` + `Kentucky-ai/opentakeoff@6ff9cc355e60d6312c0c82e2ddac56cb212cc394` + `delongwangshu49-hub/bimchange-agent@cd7fd6e6522e060b7847f0daaed00979097da7dd` + MPL-2.0 `LTplus-AG/ifc-lite@802a30fba331feab9101ad4241335b97cfef023a` BCF layer + document/rule/evidence components.
- Combined capability: old/new drawing/model registration → independent correspondence check → reconciled changed regions/elements → measured quantity delta → BCF topic/viewpoint preserving exact model context → contract/spec/RFI/submittal/notice evidence → reviewer-approved compensability packet.
- Buyer / wedge: specialty contractors, GCs, BIM/VDC, estimators and claims teams; first paid wedge is one issued revision pair with analyst-time and false-positive measurement before dollars.
- Rights: customer drawings/models/contracts remain customer data; BCF interoperability or a visual/model change does not prove entitlement.
- Validation: 20 rights-clean revision pairs covering translation, scale/DPI, reorder, crop and moved-only annotations; measure each detector and disagreement. Round-trip one changed GlobalId through BCF. Then carry one authorized finding through quantity + controlling clause/notice + reviewer decision.
- Status: detector/takeoff search is solved enough. Remaining P0 is **entitlement, notice, change-event and cost/schedule evidence**.

### 3. CaptureBrief v4 — authoritative solicitation packet + identity/award lineage + exact regulation + fail-closed evidence
- Components: official packet ingestion `GSA/srt-fbo-scraper@fbdfa86a2bce4323a5afacda04f083698cab02e1` + official FAR DITA `GSA/GSA-Acquisition-FAR@da52ccbbe114e1f031a7f4c59195c508dbfa485f` + `fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964` + `fedspendingtransparency/data-act-broker-backend@76dcae4ccbf6951223608bc1d8fd0c5b03da5d68` + `blencorp/capture-mcp-server@e91ce243cd6a62e9c2a55609d34a187fca89703b` + `cliwant/mcp-sam-gov@aaaaa70dcb6a08cf43cb40ece26b79d6d21c2463` + SAM acquisition adapters + entity resolution + independently reauthored fail-closed evidence acceptance rules learned from no-license references.
- Combined capability: acquire current opportunity and actual attachment packet/history → normalize UEI/legal/parent/PIID/referenced-IDV lineage → reconstruct incumbent/award history → resolve exact clause/prescription/revision/fill-ins → emit evidence-backed bid/no-bid/compliance packet.
- New advantage: packet completeness and regulation truth now have first-party GSA sources. CaptureBrief should no longer accept “SAM record seen” as proof the controlling solicitation package was acquired.
- Buyer / wedge: federal capture/proposal teams and GovCon consultants; first paid wedge is 10 current solicitations with manual verification of packet completeness, identity/parent, incumbent, competition/set-aside and clause applicability.
- Rights: GSA scraper CC0; USAspending/DATA Act CC0; mcp-sam-gov MIT; FAR regulatory text is authoritative public source, but repository packaging/code without a blanket license is not assumed permissive.
- Validation: source artifact/hash or locatable support required for every high-risk conclusion; unresolved upstream source is not “not found”; identity conflict stays unresolved.
- Status: stop generic SAM wrappers. Hunt only authoritative missing packet/amendment/deviation/supplier-eligibility semantics that can change a bid/no-bid decision.

### 4. Recovery Proof v5 — heterogeneous real restore + deep engine oracle + signed evidence + governed remediation
- Components: `probavi/probavi@3f0dd3bd94259f91eb0a54ce6b5425afb70ad216` + PostgreSQL deep verifier `cybertec-postgresql/pg_hardstorage@b47541b7e1cea69ce6ec63b26e154eb25fc4ca91` + application-invariant lessons/components from `backupdrill/cli@401954dd01d1141d81eda488ddf30c7d08b0f0e9` + byte-fidelity adapter `iacosta3994/restic-drill@0e11db6339fc86f87239b259827f6848a69886f7` + evidence/crosswalk plane from OpenWright/Evidentia + remediation governor `google/cybernetic-agent-governance-engine@50b12e7d983db0e3d7faf206ac6aa600294f33ac`.
- Combined capability: select backup/recovery point → restore into disposable Docker/Kubernetes/SSH target → run engine integrity + row/freshness + customer business invariants + object/content checks → record RTO/PITR → produce signed/offline-verifiable evidence → allow/deny/approve remediation → re-test and issue fresh proof.
- New advantage: Probavi materially closes the multi-engine execution and signed-evidence gap. The product no longer needs another generic backup manager or hash-chain library.
- Buyer / wedge: regulated SaaS, MSP/MSSP, SRE/platform teams and cyber-resilience consultants; fixed-price Recovery Readiness Audit on 1–3 systems.
- Rights: permissive components as cataloged; database engines/images/providers remain separate.
- Validation: reproduce one PostgreSQL and one non-SQL/object-storage path; inject green-backup-but-bad-restore, stale data, corrupt object/content and failed app-invariant cases. External anchoring/time-existence claims must be separately proven; a locally signed chain alone is not independent timestamp proof.
- Status: high-value challenger. Remaining gaps are independent reproduction, buyer-facing evidence format and external anchoring—not restore orchestration breadth.

### 5. Marketplace Settlement Reliability OS — independent read-only money-state assurance
- Components: `tonytonycoder11/stripe-connect-reckon@deb30aabfed84c7b0b2e5ae28c92cc9f85f79193` + rights-clean marketplace accounting/settlement semantics already cataloged + many-to-many reconciliation primitives.
- Combined capability: seller earning/reversal/payout state + read-only provider/app reconciliation → failed payouts, missing events, refund mismatches, negative balances, reserve/dispute exposure and forecasting.
- Buyer / wedge: marketplace CFO/controller/finance-ops/risk; fixed-price read-only Money Safety Audit followed by monitoring.
- Validation: planted failed payout, duplicate/missing event, cumulative refund rounding, negative-balance trajectory, reserve/dispute spike, seller reversal and cross-currency settlement; measure precision/recall, alert burden and unresolved dollars surfaced.
- Status: strongest low-friction direct-money challenger after freight, but no recovered-dollar claim until a real authorized pilot proves realized value.

### 6. Field-service Proof-to-Cash v2
- Components: `proforcetech/phparm@a691ebfdea93a20f9de5f8a076430c859f299255` + `servicialo/mcp-server@5cc669d667f650f454bfaeb9236a88a540475219` + fail-closed work-order normalization + invoice-parity arithmetic + RosterSpec for capacity/repair + optional ERPNext adapter.
- Combined capability: contract/service allowance → scheduled visit/job → field proof/acceptance → billable-extra authority → invoice → dispute/credit/collection/settlement.
- Buyer / wedge: recurring service contractors; 100-job leakage diagnostic for completed-but-unbilled work, unsupported billed work and SLA/service-credit exceptions.
- Validation: every asserted dollar traces to agreement/warranty authority + delivery evidence + invoice/settlement state; missing authority/proof/settlement = **$0 asserted recovery**.
- Status: strong direct-money adjacent vertical; hunt only vertical entitlement/settlement semantics, not more FSM CRUD.

### 7. Commission Payout Assurance — blind plan-to-payroll acceptance test
- Components: rights-clear `OCA/commission@288b2a8a62920657b40b845983fcc31860463af6` execution substrate + independently authored stress cases learned from proprietary/no-license ICM references + reconciliation/provenance layer. Insurance carrier-statement→policy→producer→payroll semantics from no-license `BreezDev/trackyoursheets@618a1fbd211b6a4c0c8d4348484cbef7ed68f9d0` remain clean-room requirements only.
- Combined capability: effective plan + transactions/credits/splits/refunds/clawbacks → independent expected payout → incumbent/approved/payroll comparison → explainable disagreement and settlement lineage.
- Buyer / wedge: compensation, finance, payroll, insurance agencies/brokerages; closed-period Commission Payout Acceptance Test.
- Validation: freeze plan/credit truth before incumbent output; benchmark 30–50 fixed/section/tier/split/overlay/retro/clawback/draw/carry-forward/cent-allocation cases and one authorized closed period.
- Status: credible freight-like audit business, but below MASTER-business priority until a real corrected payout/avoided-overpayment outcome exists.

### 8. Industrial Interoperability Acceptance Lab
- Components: `suoten/ProtoForge@7c61b10d9ae406224c86741d9c0a450b561b40ca` + Apache PLC4X + independent Modbus peer/simulator `pymodbus-dev/pymodbus` as cataloged + additional independent IEC-104/OPC-UA implementations where rights/standards boundaries are satisfied.
- Combined capability: model customer-authorized endpoints → normal/fault/disconnect/timeout/write/replay scenarios → independent-client/server comparison → reproducible compatibility matrix before cutover.
- Buyer / wedge: industrial gateway/SCADA/OEM/integrator QA; fixed-price 3–10-device regression pack.
- Validation: Modbus TCP first, then IEC-104 and OPC UA; advertise only protocol families that pass cross-implementation tests. Implementation disagreement is a regression case, not automatic standards truth.
- Status: strong difficult-integration service. Stop broad protocol library hunting.

### 9. Network Management-Plane Migration Acceptance
- Components: `clicon/clixon-controller@36ecc0fd8787750978652495a39d0d01db2c7474` + `notconf/notconf@cc2499d2a859aa76a3ec3a265ec7c36f2d5ea07e` + `CESNET/netopeer2@5be28a93e783b41d1c284c1275c9b24237d0454d` + `openconfig/gnmic@ce0d4173630ae73fe9cfe124ce8d564fa3b69c5e`.
- Combined capability: model YANG/OpenConfig estate → validate/lock/commit/rollback/disconnect/timeout plus Get/Set/Subscribe across synthetic and independent endpoints → migration compatibility report.
- Buyer / wedge: telecom operators, MSPs, NMS/OSS vendors; fixed-price controller migration preflight.
- Validation: identical service/config fixture across 10–100 endpoints; disagreements remain human-reviewed regression cases.

### 10. Lab Data + Automation Evidence Fabric v2
- Components: vendor-file normalization `Benchling-Open-Source/allotropy@ecc574986b74f91eb84cd0ee14756cd8dc5e1b7e` + replay/bench validation `labiium/pytestlab@8b7f873e29457f05dee7af0de698e27985c98a33` + device gateways from Galago/PyLabRobot + workflow provenance Flowcept + high-value Waters lane `novonordisk-research/OptiHPLCHandler@96399dcddc1457a5b942f61585b9e8fcf78b9a72`; optional Hamilton installed-base bridge `dgretton/pyhamilton@65938d05...` and `VerisFlow/TraceLogicLocal@85c89...` only after exact rights/runtime validation.
- Combined capability: vendor instrument output → canonical analytical-data model → device/workflow control → record/replay regression → CDS method/sample-set automation → run provenance.
- New advantage: Allotropy closes the normalization layer that control frameworks lacked, so value can be sold even before full hardware automation.
- Buyer / wedge: pharma/biotech analytical-development/QC, CROs, test labs; first wedge can be either “normalize 5–10 instruments” or “automate one Empower assay/workflow,” whichever has lower buyer friction.
- Rights: repository code as cataloged; vendor SDK/runtime/spec/file-format rights and customer data remain separate.
- Validation: vendor-file parser goldens + mock/synthetic control path first, then authorized instrument/CDS runtime; preserve exact source/run lineage and do not imply vendor certification.

### 11. Grid Hosting + Resilience Engineering
- Components: `sandialabs/DREAMS@3eb6c6089eadf09a4bf99961faac11a76ef30ca0` + synthetic feeder/grid sources such as SHIFT where rights permit + `NLR-Distribution-Suite/erad@735f7a6baa9fe24878a986a3425bf6d55ad556c3` + rights-cleared hazard/fragility inputs.
- Combined capability: feeder model → voltage/thermal/QSTS hosting constraints → hazard-to-asset failure → network consequence → restoration/hardening priorities.
- Buyer / wedge: utilities, DER/storage developers, resilience consultants and insurers; fixed-price feeder or resilience study.
- Validation: 25–50 synthetic feeders with planted voltage/thermal/DER boundaries, hazard failures and restoration order; do not extrapolate synthetic topology performance to real utility assets.

### 12. Warehouse Decision Stack
- Components: `agritheory/inventory_tools@dd1e07d98eb81b2388acb922ce9ae3397a5af7ac` + `gokhanozden/gabak@711856814856e1730bd3be1cc7e4468ceca4fd5d` + optional decision-focused forecasting `khalil-research/PyEPO@6a9fa25ce3b1c25ac5295b44707adf66a016929e` and robust inventory `iutzeler/skwdro@0c7d52557fa4c90bd9b0f3ecff619403c347c400` after benchmark.
- Combined capability: ERP movement facts → slotting/layout/path model → current-vs-proposed travel/capacity evidence; optional decision-focused inventory layer optimizes economic regret rather than forecast error alone.
- Buyer / wedge: warehouses/distributors; fixed-price re-slotting diagnostic or inventory decision benchmark.
- Validation: actual travel-distance/labor delta and disruption cost must beat current layout; PyEPO/skwdro enter only if downstream dollars/service improve over simpler baselines.

### 13. Contact-Center Assurance
- Components: `snehalsurti12/audrique` pre-release journey regression + `Kazaam-sudo/CallQuanta@6454507a7e3dec23c469c8e9b7fcae1ce8433c08` AI↔human QA calibration + existing permissive QA execution + `joschiservice/RosterSpec`/pyworkforce for WFM effects + platform adapters such as MIT Five9 and MIT-0 Amazon Connect flow comparison.
- Combined capability: release/config change → synthetic call/IVR/CRM journey proof → post-call QA calibration → production coverage → staffing/repair impact.
- Buyer / wedge: BPO/contact-center QA/release teams; fixed-price release acceptance or 50–200-call QA calibration benchmark.
- Validation: score journey correctness, critical-issue recall, false escalation, AI-human score delta, reviewer minutes and staffing effect before automating decisions.
- Status: P2 until buyer/value evidence is stronger than direct-money opportunities.
