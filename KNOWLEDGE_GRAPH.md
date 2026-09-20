# KNOWLEDGE_GRAPH

Human-readable graph connecting findings to capabilities, technologies, opportunities, experiments and outcomes.

## Node types
- REPO — repository/project/revision
- DATA — dataset/source pipeline
- CAP — reusable capability from CAPABILITIES.md
- TECH — emerging technology category from TECHNOLOGY_RADAR.md
- OPP — business opportunity from OPPORTUNITIES.md
- EXP — falsifiable experiment from EXPERIMENTS.md
- OUT — recorded result from OUTCOMES.md

## Core edge types
IMPLEMENTS, VALIDATES, CHALLENGES, DEPENDS_ON, COMBINES_WITH, ENABLES, TESTED_BY, PRODUCED, INVALIDATES, STRENGTHENS.

## Current high-value graph — 2026-09-20

### Freight Recovery
- kodekinetics79/opstrax-enterprise-build -> IMPLEMENTS CAP-005.
- emoss08/Trenova -> IMPLEMENTS CAP-003 and STRENGTHENS CAP-006.
- sengtha/Kareya-Silo -> IMPLEMENTS CAP-004.
- A-Jatin/freight-ratecon-extraction -> IMPLEMENTS CAP-001 and STRENGTHENS CAP-003.
- OmarFaig/Assay -> IMPLEMENTS CAP-001.
- srthck/trustmesh -> IMPLEMENTS CAP-007.
- CAP-001 + CAP-003 + CAP-004 + CAP-005 + CAP-006 + CAP-007 -> ENABLES Freight Audit Acceptance Test / Recovery -> TESTED_BY EXP-001.

### AP Assurance
- mgilbir/formalis -> IMPLEMENTS CAP-008.
- cmdrvl/canon -> IMPLEMENTS CAP-002.
- opensanctions/nomenklatura@844dba09fafc8512dc3ce241f44aa5415b367029 -> STRENGTHENS CAP-002 with durable POSITIVE/NEGATIVE/UNSURE judgements and reversible cluster correction; Canon remains the promoted-version production-registry/replay gate.
- CAP-001 + CAP-002 + CAP-007 + CAP-008 + CAP-016 -> ENABLES AP Leakage Assurance -> TESTED_BY EXP-002.

### Commission Assurance
- getcoherence/openpartner@eeff532ee758dc6221b4d03af852e5705a2328fb -> STRENGTHENS CAP-006 and CAP-018 through event-sourced payout/settlement state.
- spree/spree@2a419d42e86dea30a69a3c5b7764185cea132b3f -> IMPLEMENTS CAP-018 through claim-before-send, ambiguous-outcome hold and settled amount/currency proof.
- Bdkelp/getmydpc_enrollment@e753d8ebf5e087ae9a4add978d1559af86c173fb -> STRENGTHENS commission entitlement/reversal/carry-forward cases.
- Reifye/Reifye-OS@acbb8ca46c6c6de20c0a64ac7ea0f174f308e17a -> STRENGTHENS collected-cash/hold/clawback cases.
- D-Haku/Channel-Partner-Commission-Engine@176084bb4a5bc0a1ad17ba94a11c869dfd8a463e -> STRENGTHENS lending slab/sequence cases but DEPENDS_ON independently current statutory/tax authority.
- mike4forge/forgelocal-commission-engine@cb4ab9bcb85a5863079d1798836727065d2d243a -> CHALLENGES/STRENGTHENS hierarchy-at-time provenance; provider settlement remains unverified.
- CAP-002 + CAP-006 + CAP-007 + CAP-016 + CAP-018 -> ENABLES Partner / Commission Payout Assurance -> TESTED_BY EXP-003.

### Recovery Proof
- duke5am/pg-restore-drill -> IMPLEMENTS CAP-010.
- open-eid/SiVa -> STRENGTHENS CAP-010.
- srthck/trustmesh -> STRENGTHENS CAP-010.
- CAP-007 + CAP-010 -> ENABLES Recovery Proof SLA -> TESTED_BY EXP-004.

### CaptureBrief
- GSA/srt-fbo-scraper -> IMPLEMENTS CAP-011.
- GSA/GSA-Acquisition-FAR -> IMPLEMENTS CAP-011.
- fedspendingtransparency/usaspending-api -> IMPLEMENTS CAP-011.
- fedspendingtransparency/data-act-broker-backend -> IMPLEMENTS CAP-011.
- opensanctions/nomenklatura@844dba09fafc8512dc3ce241f44aa5415b367029 -> STRENGTHENS CAP-002 for durable reviewed negative identity knowledge; external source datasets remain separately governed.
- slicedearth/contract-delta-au@630d1903507e6f5e47adaf1c690c9d6d4363af54 -> STRENGTHENS CAP-011 with deterministic procurement version-history/diff/run-failure architecture; it is an Australian-procurement implementation pattern and does NOT establish U.S. SAM semantics or authority.
- CAP-002 + CAP-007 + CAP-011 -> ENABLES CaptureBrief FAR-Deviation Readiness -> TESTED_BY EXP-006.

### Permit Intelligence
- adamleap02/PermitBuild -> IMPLEMENTS CAP-012.
- slicedearth/contract-delta-au@630d1903507e6f5e47adaf1c690c9d6d4363af54 -> CHALLENGES/STRENGTHENS the general version-lineage pattern for public-data sources where latest-row truth is insufficient; permit semantics remain separately validated by PermitBuild.
- CAP-002 + CAP-012 -> ENABLES Permit-to-Development Opportunity Intelligence -> TESTED_BY EXP-009.

### Lab Automation / Sequencing Operations
- Benchling-Open-Source/allotropy -> IMPLEMENTS CAP-013.
- SemaphoreSolutions/s4-clarity-lib@ad577fff3a3c4c93f4bb898940a0b45268c7dbe7 -> IMPLEMENTS CAP-017.
- Illumina/interop@015a85ec100c7a770ed0e27ce7fadc6230a38208 -> IMPLEMENTS CAP-017.
- ORNL/Flowcept -> STRENGTHENS CAP-013 and CAP-017 through provenance/evidence lineage.
- labscript-suite/labscript-suite + labscript-devices -> CHALLENGES/STRENGTHENS deterministic scientific execution under the broader lab opportunity without displacing the installed-base integration leaders.
- NatLabRockies/ALchemist@02c7a6eaa5a8e75bb65d0292b9b8d9a5e08301cf -> CHALLENGES/STRENGTHENS experiment-governance provenance through suggested-vs-actually-executed conditions, but remains a shadow 26/30 component candidate pending an independent second implementation and physical/restart outcome evidence.
- CAP-013 + CAP-017 -> ENABLES Installed-Base Lab Automation / Sequencing Operations Evidence / Governed Campaign Shadow Audit -> TESTED_BY EXP-007.

### Insurance Subrogation Recovery
- sidnov6/recoupe@60e0e02bec789ab505752dacfecdd76438aacd48 -> IMPLEMENTS a deterministic subrogation workflow/quantum/evaluation substrate but DEPENDS_ON independently authoritative current rule/policy sources before hard-dollar use.
- CAP-001 + CAP-006 + CAP-007 + Recoupe deterministic quantum/workflow -> ENABLES Insurance Subrogation Recovery Diagnostic -> TESTED_BY EXP-011.
- Recoupe illustrative/default jurisdiction rule data -> CHALLENGES the opportunity's authority boundary; unknown/conflicting authority must remain REVIEW/$0 rather than silently default.

### Revenue Decision Assurance
- GiovanniGatti/talos@41fae94f941ea36fccddd395e86cd5662002e3cb -> STRENGTHENS constrained-capacity/booking-horizon policy evaluation.
- Dimitres-Kisimov/revops-optimizer + Talos -> ENABLES a broader shadow-mode Revenue Decision Assurance concept; no production-economic claim is accepted without held-out replay against simple/incumbent baselines.

### Money-State / Payment Integrity
- amrit-kumar/fintechcore@b27a22890e8b5173d2a97be512a198a4564ed425 -> CHALLENGES/STRENGTHENS CAP-016 with append-only ledger, idempotency, settlement and independent reconciliation semantics.
- The Fintechcore test-deferred ADR -> LIMITS its maturity; it remains a reference/challenger until automated invariant/race/refund/reversal/outbox tests exist.
- Etherlabs-dev/revenue_leakage_system@64c1af79ac0a22915cfb49f1a2dd6d870059b78a -> CHALLENGES/STRENGTHENS authority-aware expected-vs-actual billing assurance with effective-dated pricing, fail-closed source freshness and idempotent evidence, but remains shadow-only pending independent authority-ingestion and realized settlement evidence.
- dylanpulver/recon@e6b787213bb023568c99c432ea4733e1f2456a5e -> STRENGTHENS matching truth with deterministic receipts/conservation while NOT establishing contractual expected-state truth.
- CAP-006 + CAP-016 -> ENABLES Money-State Integrity / Close Assurance -> TESTED_BY EXP-010.

### Industrial Pre-FAT
- Gaskony-Ignition/module-plc-emulator -> IMPLEMENTS CAP-014.
- CodeMaru-Dreamine/Dreamine.Gem@82604d6f03c1e95e0558de5c757989b27cd4a3d6 -> STRENGTHENS CAP-014 with a second stateful industrial protocol family: host/equipment E30/GEM behavior over HSMS/TCP, frozen-profile state, alarms/events/remote commands/spooling/error behavior. It DEPENDS_ON separately governed SEMI standards/current equipment profiles and is not itself conformance proof.
- CAP-014 -> ENABLES Industrial Pre-FAT / Virtual Commissioning -> TESTED_BY EXP-008.

### Prediction Credibility / Infrastructure Outcomes
- owgreen-dev/grid-crunch -> IMPLEMENTS CAP-015.
- savabs/queue_attrition -> STRENGTHENS CAP-015.
- DATA Saki et al. harmonized EAGLE-I + NWS VTEC v2 (`10.5281/zenodo.22651795`) -> CHALLENGES/VALIDATES infrastructure weather/outage/recovery predictions with a fresh 2015–2024 observational outcome benchmark plus missingness/recovery sensitivity; harmonized-v2 reuse rights remain unresolved and must be confirmed before commercial redistribution/use beyond permitted analysis.
- CAP-015 -> ENABLES Queue Materialization Intelligence.
- The outage/warning dataset enables a separate historical falsification loop for storm/outage risk and recovery models but is not itself causal evidence or a new commercial opportunity until rights and held-out reproduction are resolved.

### Verifier-gated research production
- ThousandBirdsInc/chidori@223bb8779f63822c3e63a9a4347dda7483a02158 -> CHALLENGES/STRENGTHENS the staged verifier-gated production architecture with mediated side-effect journaling, no-live replay, divergence detection and crash/pause resume. No reusable CAP node is promoted yet because the shadow evaluation was non-authoritative, tests were inspected rather than independently rerun and filesystem/S3 lease semantics are advisory.
- Next evidence gate: recorded-run no-live replay plus crash/resume, approval-fail-closed and duplicate-driver cases on a storage backend with strong single-writer lease semantics.

## Graph maintenance rule
Every MASTER promotion must answer:
1. Which CAP node does it implement, strengthen or challenge?
2. Which TECH radar category does it support or contradict?
3. Which OPP becomes stronger or weaker?
4. Which EXP should change because of it?

If the answer is none, the finding is not yet integrated into the value system.

<!-- INTEGRATOR-R11-2026-09-20T0856-0400 -->
## Integration edges — 2026-09-20 08:56 ET
- REPO `project-minigraf/minigraf@ccdc85e...` -> STRENGTHENS AP trusted-fact replay -> TESTED_BY `EXP-002` correction/partial-receipt replay.
- REPO `mujeeb-k/AP-Three-Way-Matching-Agent@c15a4cc...` -> CHALLENGES AP source-health semantics because adapter failure can collapse into empty/missing-reference state -> TESTED_BY `EXP-002` tri-state source-authority cases.
- REPO `lailarallc/edi-reconciliation-tool@11740303...` -> STRENGTHENS `CAP-006` settlement acceptance -> TESTED_BY `EXP-001` planted freight 210/812/820 corpus.
- REPO `egovernments/DIGIT-Works@7c44e963...` -> STRENGTHENS `CAP-007` contract-bounded quantity proof -> TESTED_BY `EXP-005` draft/rejected/approved/over-measure-to-bill cases.
- REPO `GSA/open-gsa-redesign@494b131...` opportunity history semantics -> STRENGTHENS `CAP-011` -> TESTED_BY `EXP-006` latest-vs-history packet completeness.
- REPO `GSA/open-gsa-redesign@494b131...` subaward API -> STRENGTHENS CaptureBrief award/entity/team lineage; Deleted is a distinct source state, not absence.
- REPO `bparzella/secsgem@59a5242...` -> VALIDATES/CHALLENGES `CAP-014` through an unrelated implementation -> TESTED_BY `EXP-008` Dreamine↔secsgem differential corpus.
- REPO `chase-sets/chase-sets@32aa260...` -> STRENGTHENS `CAP-018` provider-settlement ownership and receivable clawback -> TESTED_BY `EXP-003`; bank-finality remains a missing downstream edge.
- DATA `PNNL OWL-I USA v1` -> ENABLES held-out high-resolution outage outcome validation; DEPENDS_ON separate rights and circularity checks because it is calibrated against EAGLE-I.

<!-- INTEGRATOR-R11-SHADOW-COM-2026-09-20T0914-0400 -->
## Revenue-to-receivable edges — 2026-09-20
- REPO `cyber-entrepreneur/wingcaster@0d97a4ab...` -> IMPLEMENTS effective-contract selection + append-only rating + invoice-close + payment-allocation + reconciliation.
- REPO `michaelayoade/dotmac_sub@fdc85559...` -> STRENGTHENS commercial-contract version/cut-over provenance.
- REPO `Etherlabs-dev/revenue_leakage_system@64c1af79...` -> STRENGTHENS fail-closed expected-vs-actual leakage decision.
- These components -> COMBINE_WITH external signed-contract/order-system authority and PSP/bank readback -> ENABLE Revenue-to-Receivable Trace Audit.
- The composed stack -> TESTED_BY a new external-authority/readback experiment; internal all-green reconciliation alone does not PRODUCE a realized-money outcome.

<!-- INTEGRATOR-R12-2026-09-20T0946-0400 -->
## Graph delta — 2026-09-20 09:46 ET
- `bsaffel/moneybin@fd34d999...` -> **CAP-019 Source-authority observation receipts** -> strengthens **EXP-002 AP**, **EXP-006 CaptureBrief**, public-data and settlement ingestion.
- `scolladon/dataset-loader@5039257...` -> finalize-before-watermark / partial-failure semantics -> complements CAP-019; does not independently prove durable empty.
- `payops-labs/solana-payment-ops@7e4d9cc8...` + `Noone9029/Accounting-App@90e0eaa...` -> **CAP-006** exact auto-allocation + reviewed partial/reversal edge ledger -> **EXP-001 Freight** realized-settlement proof.
- `mnmn0/mukuroji@34ec666...` + `nearai/pg-backup@6836158...` -> **CAP-010 Recovery Proof** non-Postgres semantic recovery + verifier-self-test -> **EXP-004**.
- DHS APFS native history + SAM operational alerts -> **CAP-011** temporal/source-health authority -> **EXP-006 CaptureBrief**.
- DIGIT purchase-bill path -> **negative control** for EXP-005 (UI awareness != backend authority); `senecaSparsh/nirman@0e40fba...` -> positive-but-flawed approved-measurement→RA-bill reference -> **EXP-005 ScopeSignal**.
- `Dreamine.Gem@82604d6...` + `bparzella/secsgem@59a5242...` -> frozen semantic intersection + EC atomicity probe -> **CAP-014** -> **EXP-008** execution stage.
- `scilifelab_epps@fbbe16f...` + `samplesheet-parser@511b484...` + Illumina InterOp -> **CAP-017** -> **EXP-007 sequencing handoff acceptance**.
- `moov-io/ach@f36ebb7...` + independent bank statement readback -> **CAP-018** external post-success invalidation -> **EXP-003 Commission Payout**.
- USECPO v2 -> observed event outcomes; ICE 2.2 (external service/terms) -> economic consequence -> grid risk/inspection/restoration policy benchmark. Preserve outcome/model independence and EAGLE-I circularity caveat.
- `AccelerationConsortium/bo-mcp@56d590b...` -> shadow evidence for stable experiment identity/idempotency/audit and proposed→actual provenance -> Installed-Base Lab / self-driving-science integrity challenger; external executor acknowledgement remains missing.
