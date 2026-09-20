# KNOWLEDGE_GRAPH

Human-readable current graph connecting repository/data evidence to capabilities, opportunities and experiments. Detailed historical edges remain in Git history and hunter catalogs; `intelligence/edges.jsonl` remains the machine-readable mirror.

## Node / edge vocabulary
- Nodes: REPO, DATA, CAP, TECH, OPP, EXP, OUT.
- Core edges: IMPLEMENTS, STRENGTHENS, CHALLENGES, DEPENDS_ON, COMBINES_WITH, ENABLES, TESTED_BY, PRODUCED, INVALIDATES.
- No OUT node is created without a completed outcome record in `OUTCOMES.md`.

## Current high-value graph — 2026-09-20

### Freight Recovery
- opstrax -> IMPLEMENTS CAP-005.
- Trenova -> IMPLEMENTS CAP-003 and STRENGTHENS CAP-006.
- Kareya-Silo -> IMPLEMENTS CAP-004.
- RateCon extraction + Assay -> IMPLEMENTS CAP-001.
- trustmesh -> IMPLEMENTS CAP-007.
- Hunter03 persistent settlement store/corpus -> STRENGTHENS CAP-006/CAP-016 through exact integer-cents one-use allocation, append-only reversal, race-safe persistence and deterministic fuzz/regression evidence.
- CAP-001+003+004+005+006+007+016 -> ENABLES OPP Freight Recovery -> TESTED_BY EXP-001.
- External authorized buyer population -> DEPENDS_ON EXP-001; no OUT yet.

### AP Leakage Assurance
- formalis -> IMPLEMENTS CAP-008.
- Nomenklatura -> STRENGTHENS CAP-002 with durable negative/reversible identity judgements; Canon -> IMPLEMENTS CAP-002 production registry/replay.
- moneybin/dataset-loader -> IMPLEMENTS/STRENGTHENS CAP-019 source observation.
- Business Central exact receipt/invoice allocation + ERPNext partial-receipt semantics -> STRENGTHENS CAP-016.
- `odoo/odoo@c55c82dac6283a77ee747e1e672a29e85180980f` -> STRENGTHENS CAP-016 with line-scoped credit/cancellation/refunding-return semantics and CHALLENGES universal-return/universal-receipt rules.
- MiniGraf -> STRENGTHENS temporal replay.
- CAP-002+007+008+016+019 -> ENABLES OPP AP Leakage Assurance -> TESTED_BY EXP-002 reversible-authority corpus.

### Commission / Payout Assurance
- OpenPartner/Spree -> IMPLEMENT/STRENGTHEN CAP-018 provider-side claim/idempotency/unknown-result semantics.
- `Modern-Treasury/modern-treasury-python@406f354a...` -> STRENGTHENS CAP-018 with provider/payment-reference -> bank-derived Transaction -> Return/Reversal lineage; hosted bank service/reconciliation remains external.
- `szapata85/ACHInterbank@395a359...` -> CHALLENGES/VALIDATES CAP-018 Exact/Ambiguous/NotFound return correlation.
- `sebastienrousseau/bankstatementparser@b3309b78...` -> NEGATIVE_CONTROL for unsafe substring/fuzzy/first-match settlement identity.
- CAP-019 -> STRENGTHENS bank/payroll source coverage/freshness semantics.
- CAP-002+006+007+016+018+019 -> ENABLES OPP Partner/Commission Payout Assurance -> TESTED_BY EXP-003.

### Money-State / Payment Integrity
- Summae -> IMPLEMENTS CAP-016 accounting/close truth.
- Wingcaster -> STRENGTHENS internal effective-contract→rating→invoice→allocation→reconciliation loop but DEPENDS_ON external contract and bank truth.
- `NotAbdelrahmanelsayed/paymob_integration@8999a6799c5673ad49471224ad0f8012a447495d` -> STRENGTHENS CAP-018/CAP-016 with Pending-on-ambiguity, provider inquiry recovery, durable refund-request intent, signed/independently fetched child refund evidence and compensating ledger entries.
- BlackPigIndustries/threvo-actions shadow evidence -> CHALLENGES/strengthens governed consequential-action architecture but DEPENDS_ON retained live-provider qualification; current inspected provider cases remain NOT_EXERCISED.
- CAP-006+016+018+019 -> ENABLES OPP Money-State Integrity -> TESTED_BY EXP-010.

### Recovery Proof
- probavi/Kronos/Mukuroji/pg-restore-drill/SiVa -> IMPLEMENT/STRENGTHEN CAP-010.
- `kirilurbonas/FireDrill@1e532b17e49e4424f988b29dd338ae6c48dc20f3` -> STRENGTHENS CAP-010 with multi-engine isolated restore, semantic checks, RTO/RPO, signed DSSE evidence and expected-subject coverage gate.
- `jorgedlcruz/open-backup-ui@d3956a4b83679a567669c241fdf09c97ab07368f` -> STRENGTHENS CAP-010 CENSUS plane through independent infrastructure-inventory minus protected-object reconciliation.
- `DanMrxs/danlab-vps-backup-control@6b071acda9912e40dab41ec98144d360a0d79567` -> STRENGTHENS CAP-010 with versioned inventory/manifests and explicit considered-vs-backed-up sets.
- `OmarRao/r3vp@404f7f7aaed5b9fbc39506622175d87e628b3054` -> NEGATIVE_CONTROL / INVALIDATES protected-set-as-census assumption.
- `NHSDigital/terraform-aws-backup@e0dbc8b2066834ed3383f60b4b4f603f7c757c42` -> CHALLENGES CAP-010 scope authority by showing protection-selector/compliance-scope semantic drift.
- `snapetech/DuneAwakeningSelfHost@8d3bac1df38f45fb13e2c1427216bf5dc384687b` -> STRENGTHENS CAP-010 dual-plane Postgres+RabbitMQ/Mnesia recovery.
- `WiseOpsTeam/mneme@e595986e6efb3988e1d64ad0bba7d9761f123786` -> NEGATIVE_CONTROL / INVALIDATES process-exit-as-semantic-proof assumption.
- nearai/pg-backup verifier mutation history -> STRENGTHENS verifier-self-test.
- CAP-010 now requires CENSUS + SCOPE to define the expected-subject denominator before PROOF can establish coverage.
- CAP-007+010 -> ENABLES OPP Recovery Proof -> TESTED_BY EXP-004 recovery-coverage-authority/scoped expected-subject/broken-verifier matrix.

### CaptureBrief / Government acquisition
- GSA FAR/DFARS + SAM/Data Services + USAspending + DATA Act + deviation sources -> IMPLEMENT CAP-011.
- contract-delta-au -> STRENGTHENS deterministic version/history architecture but does not establish U.S. authority.
- official GSA deletion controls (`excludeDeleted`, `deleteAll`) -> CHALLENGE latest-manifest-completeness assumption.
- `chrisfulcher/orrery@89ae2218c031c2c46720783acfb44cea22e48636` -> STRENGTHENS CAP-011 current attachment-manifest parsing/fail-closed shape drift but is LIMITED as historical completeness because deletion inclusion/history are not pinned/lossless.
- govly VCR / quirkyllama examples -> STRENGTHEN endpoint/protocol archaeology around deletion-inclusive reads.
- CAP-002+007+011+019 -> ENABLES OPP CaptureBrief -> TESTED_BY EXP-006.

### ScopeSignal / Construction
- massing-pdf + takeoff/model/change/deadline components -> IMPLEMENT evidence/change layers.
- DIGIT-Works -> STRENGTHENS contract-bounded quantity evidence but CHALLENGES the false claim that UI measurement awareness proves backend billing authority.
- Nirman + `mradul010/construction_management@ce345579...` -> STRENGTHEN measurement/work-order/quantity-to-bill challengers with distinct gaps.
- CAP-001+006+007 -> ENABLES OPP ScopeSignal -> TESTED_BY EXP-005.

### Permit Intelligence
- PermitBuild -> IMPLEMENTS CAP-012.
- CAP-019 -> STRENGTHENS absence/completeness semantics.
- CAP-002+012+019 -> ENABLES OPP Permit Intelligence -> TESTED_BY EXP-009.

### Lab / Sequencing Operations
- Allotropy -> IMPLEMENTS CAP-013.
- S4 Clarity + scilifelab EPPs + samplesheet-parser + Illumina InterOp -> IMPLEMENT/STRENGTHEN CAP-017.
- Flowcept/HELIOS -> STRENGTHEN provenance/governance.
- `AD-SDL/MADSci@6b1ab6a70ce8b15af7aa8968479c90d9138753d0` -> STRENGTHENS CAP-017 with same-action readback after a lost dispatch response and explicit `UNKNOWN` on unresolved result lookup, while CHALLENGING any system-wide exactly-once claim because generic workflow retry can create a fresh ActionRequest/ULID without mandatory physical reconciliation.
- `AD-SDL/ot2_module@39ffdfdb...` + `RoryMB/simlab@5ae0641...` -> TEST-HARNESS candidates for vendor-run identity and simulated actuation; `di-omics/plr-lab-robot@0b062298...` -> NEGATIVE_CONTROL for self-validating command-mutated local state.
- CAP-013+017 -> ENABLES OPP Installed-Base Lab Automation -> TESTED_BY EXP-007 actuated-but-response-lost/retry/restart acceptance case.

### Industrial pre-FAT
- Gaskony PLC emulator -> IMPLEMENTS CAP-014 controller/config binding.
- Dreamine.Gem + `bparzella/secsgem` -> STRENGTHEN CAP-014 independent SECS/GEM differential testing.
- Duplicate-ECID S2F15 source/test analysis -> CHALLENGES transaction/error/liveness semantics; duplicate-specific runtime remains NOT_RUN.
- CAP-014 -> ENABLES OPP Industrial Pre-FAT -> TESTED_BY EXP-008.

### Prediction / Grid resilience
- grid-crunch + queue_attrition -> IMPLEMENT/STRENGTHEN CAP-015 leakage-resistant historical/prospective prediction.
- DATA USECPO v2 -> TESTS CAP-015 as major-event-correlated outage outcome evidence.
- USECPO literal `event id` -> DEFINES whole-event grouping; STANDARD/8H/24H -> sensitivity variants, not independent validators; EAGLE-I+DOE-417 ancestry and imputation/geography quality -> LIMIT evaluator claims.
- CAP-015 + optimization/routing components -> ENABLES OPP Grid/Infrastructure Decision Assurance -> TESTED_BY EXP-012.

### Insurance Subrogation
- Recoupe deterministic workflow/quantum -> STRENGTHENS opportunity but DEPENDS_ON independently authoritative current rule/policy sources.
- CAP-001+006+007 -> ENABLES OPP Subrogation Recovery -> TESTED_BY EXP-011.

### Revenue Decision Assurance
- Talos + existing revenue/airline capacity optimizers -> STRENGTHEN constrained-capacity policy evaluation.
- Evaluation-Target Independence -> CHALLENGES synthetic/model-valued ROI as customer outcome.
- Revenue Decision Assurance remains outcome-blocked pending held-out/incumbent replay.

## Graph maintenance rule
Every central promotion/demotion must answer: which CAP changes, which OPP changes, which EXP changes, and whether any OUT exists. If none change, the finding usually belongs only in a hunter/component catalog.

## Machine graph mirror
`intelligence/edges.jsonl` is the canonical structured edge store. New machine edges should preserve source revision and evidence provenance; this Markdown file is the current human-readable synthesis.