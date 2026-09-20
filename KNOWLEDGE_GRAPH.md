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
- Freight pre-parser hostile-input finding -> CHALLENGES production-readiness boundary: eager CSV materialization and untyped `csv.Error` can violate deterministic fail-closed ingestion even below byte/line limits; external freight search remains frozen.
- CAP-001+003+004+005+006+007+016 -> ENABLES OPP Freight Recovery -> TESTED_BY EXP-001.
- External authorized buyer population + deployment-safe environment evidence -> DEPENDS_ON EXP-001; no commercial OUT yet.

### AP Leakage Assurance
- formalis -> IMPLEMENTS CAP-008.
- Nomenklatura -> STRENGTHENS CAP-002 with durable negative/reversible identity judgements; Canon -> IMPLEMENTS CAP-002 production registry/replay.
- moneybin/dataset-loader -> IMPLEMENTS/STRENGTHENS CAP-019 source observation.
- Business Central exact receipt/invoice allocation + ERPNext partial-receipt semantics -> STRENGTHENS CAP-016.
- `odoo/odoo@c55c82dac6283a77ee747e1e672a29e85180980f` -> STRENGTHENS CAP-016 with line-scoped credit/cancellation/refunding-return semantics and CHALLENGES universal-return/universal-receipt rules.
- MiniGraf -> STRENGTHENS temporal replay.
- `prathamesh-git9/effect-broker@eb273640a3a8a2d65fc15169ed1f6d335608b23e` -> STRENGTHENS CAP-016/EXP-002 crash-safe writeback with stable semantic operation identity, durable reservation, OUTCOME_UNKNOWN, lease recovery, fenced stale workers and target-specific authoritative readback; real ERP NOT_APPLIED authority remains external.
- CAP-002+007+008+016+019 -> ENABLES OPP AP Leakage Assurance -> TESTED_BY EXP-002 reversible-authority + crash-safe counter-event corpus.

### Commission / Payout Assurance
- OpenPartner/Spree -> IMPLEMENT/STRENGTHEN CAP-018 provider-side claim/idempotency/unknown-result semantics.
- `Modern-Treasury/modern-treasury-python@406f354a...` -> STRENGTHENS CAP-018 with provider/payment-reference -> bank-derived Transaction -> Return/Reversal lineage; hosted bank service/reconciliation remains external.
- `szapata85/ACHInterbank@395a359...` -> CHALLENGES/VALIDATES CAP-018 Exact/Ambiguous/NotFound return correlation.
- `nzebrian/eruofood-ai@9c191ece...` -> STRENGTHENS CAP-016/CAP-018 with immutable event-time payable authority, non-retryable UNKNOWN settlement and compensating reversal/re-open; CHALLENGES end-to-end late-return claims because automatic external post-success return observation is not proven.
- `Layr-Labs/d-inference@1451a4c...` -> STRENGTHENS automatic provider counter-event/cash-location semantics but lacks the same historical payable-authority chain.
- `sebastienrousseau/bankstatementparser@b3309b78...` -> NEGATIVE_CONTROL for unsafe substring/fuzzy/first-match settlement identity.
- CAP-019 -> STRENGTHENS bank/payroll source coverage/freshness semantics.
- CAP-002+006+007+016+018+019 -> ENABLES OPP Partner/Commission Payout Assurance -> TESTED_BY EXP-003.

### Money-State / Payment Integrity
- Summae -> IMPLEMENTS CAP-016 accounting/close truth.
- Wingcaster -> STRENGTHENS internal effective-contract→rating→invoice→allocation→reconciliation loop but DEPENDS_ON external contract and bank truth.
- `NotAbdelrahmanelsayed/paymob_integration@8999a6799c5673ad49471224ad0f8012a447495d` -> STRENGTHENS CAP-018/CAP-016 with Pending-on-ambiguity, provider inquiry recovery, durable refund-request intent, signed/independently fetched child refund evidence and compensating ledger entries.
- `az-said/Interlock@822ec54692b30e1fdce04b55dfab62d0b56a60b2` -> STRENGTHENS CAP-016 with exact-revision Stripe test-mode evidence for post-effect process death, new-process recovery, one durable correction identity and later one-time provider-accounting application to a paid invoice; CHALLENGES any claim that provider-native accounting application equals bank settlement or that the framework uniquely owns the money outcome, because the published handwritten baseline ties it.
- `prathamesh-git9/effect-broker@eb273640...` -> STRENGTHENS CAP-016 with a reusable external-effect state machine and production-style crash matrix; its authoritative probe is only as trustworthy as the concrete adapter.
- `auths-dev/auths-proof@34fa1f33...` -> TRANSFER_ORACLE for a second valid restart pattern: durable pre-dispatch business-effect reference + deterministic idempotency + provider-readable metadata + explicit OutcomeUnknown + read-only reconciliation after restart. This challenges any architecture rule that demands knowing a provider-native operation ID before dispatch.
- `karfalacisse900-alt/Flames-up.com@2ba5fa87...` -> STRENGTHENS provider terminality evidence with exact successful Stripe test-mode balance/payout/readback at a pinned revision but CHALLENGES full crash-safe settlement because no post-effect payout kill/restart seam was executed.
- BlackPigIndustries/threvo-actions shadow evidence -> CHALLENGES/strengthens governed consequential-action architecture but DEPENDS_ON retained live-provider qualification; current inspected provider cases remain NOT_EXERCISED.
- `seancrecord/scvd-general-store-repo@06baa4211849dcffaee901468e1909ecd582b790` shadow evidence -> CHALLENGES any assumption that a historical live-provider qualification automatically remains current after behavior-scope expansion. Exact qualified release provenance is not current-route eligibility unless a machine-readable behavior closure/equivalence rule still matches the deployed subject.
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
- `foundriesio/aktualizr-lite@1d089b006295cd924b3c87337679fef7295e4329` -> STRENGTHENS CAP-007 with independent C++ tamper/expiry/stale-authority tests; `uptane/aktualizr@e5118a74874c0561ebac57560c667c18b19d984b` -> STRENGTHENS role-separated authority plus anti-rollback/version semantics. These are cross-domain trust-model oracles, not recovery-policy correctness evidence.
- `carabiner-dev/ampel@5cf19bc2786cbd73a8423383a966fbf842222d23` -> STRENGTHENS CAP-007 with signer-bound evidence admission, policy expiry, explicit PASS/FAIL/SKIP and signed result-attestation output; it also CHALLENGES process-exit-as-proof because default CLI success can represent SKIP unless semantic result/`--fail-skip` is enforced.
- `in-toto/in-toto@e352b43ad7cb8915d84c36d791aa61346152a0a3` -> STRENGTHENS CAP-007 with authorized-functionary sets, distinct thresholds and artifact agreement; DEPENDS_ON external/currentness authority for rollback/revocation semantics.
- current `sigstore/cosign` + `sigstore/policy-controller` exact-predicate checks and their recurring historical signed-but-wrong-type false-positive class -> NEGATIVE_CONTROL / STRENGTHENS CAP-007 typed-evidence admission. Preserve only the defensive invariant and patched/current behavior, not exploit mechanics.
- in-toto SVR v0.2 -> COMBINES_WITH CAP-007 as an interoperable result envelope containing subject/verifier/policy descriptors; it is a concise result, not the complete reproducibility/proof bundle.
- CAP-010 now requires CENSUS + SCOPE to define the expected-subject denominator before PROOF can establish coverage; CAP-007 now requires a snapshot-consistent non-expired non-rollback authority bundle plus authorized signer/functionary threshold, exact evidence type and explicit semantic PASS before PROVEN.
- CAP-007+010 -> ENABLES OPP Recovery Proof -> TESTED_BY EXP-004 recovery-coverage/scoped-subject/broken-verifier/currentness/typed-admission matrix.

### CaptureBrief / Government acquisition
- GSA FAR/DFARS + SAM/Data Services + USAspending + DATA Act + deviation sources -> IMPLEMENT CAP-011.
- contract-delta-au -> STRENGTHENS deterministic version/history architecture but does not establish U.S. authority.
- official GSA deletion controls (`excludeDeleted`, `deleteAll`) -> CHALLENGE latest-manifest-completeness assumption.
- Live SAM family `W50S8B-26-Q-A016` -> VALIDATES CAP-011 historical-action-union requirement: two same-filename source objects had different `resourceId`s, and one deleted resource was recoverable from historical action manifests yet absent from the latest `excludeDeleted=false` manifest. Historical action responses also exposed later tombstone state, so action membership and observation-time source state are separate.
- `chrisfulcher/orrery@89ae2218c031c2c46720783acfb44cea22e48636` -> STRENGTHENS CAP-011 resourceId/current attachment parsing/fail-closed shape drift but REMAINS_LIMITED as historical authority because its current-row UPSERT does not preserve the complete append-only observation ledger.
- govly VCR / quirkyllama examples -> STRENGTHEN endpoint/protocol archaeology around deletion-inclusive reads.
- CAP-002+007+011+019 -> ENABLES OPP CaptureBrief -> TESTED_BY EXP-006.

### ScopeSignal / Construction
- massing-pdf + takeoff/model/change/deadline components -> IMPLEMENT evidence/change layers.
- DIGIT-Works -> STRENGTHENS contract-bounded quantity evidence but CHALLENGES the false claim that UI measurement awareness proves backend billing authority.
- `raahul2701/nirman@9b860bf59b4b8beca14aeafdbb7a33e2ae550a20` -> STRENGTHENS the DB-side measurement→bill authority pattern with exact-row locking, approval provenance, BOQ/project lock, quantity ceiling, BOQ-derived rate and audit lineage, while CHALLENGING any claim that row locking alone proves one-use consumption because sequential replay/direct-table bypass/contractor-period authority and migration-replay gaps remain.
- `sudosahil/pmis@03d5c47c2a235e12f3c53ed518201476f566fc72` -> STRENGTHENS exact package/agreement-BOQ line identity, authoritative agreed-rate reload, cumulative quantity ceiling and certification/deduction semantics; CHALLENGES complete field-to-cash authority because measurement-book identity is free text, quantities remain caller-originated and internal PAID is not independent settlement.
- `Rakesh-7989/Site-Tracker-Pro@4cbb874...` -> NEGATIVE_CONTROL showing broad green CI/RLS can coexist with project-wide post-approval MB auto-linking, mutable billed measurements and weak exact-line/period authority.
- `jbhp9fysxx-droid/construction-billing-verification-engine@3fb551a85fe6ae606b99acff0ce0abac94d4c7e6` -> COMPARATOR / NEGATIVE_CONTROL for independent BOQ/rate/arithmetic/cumulative checks; synthetic falsification shows negative and NaN quantities can pass without explicit finite/domain guards.
- `abhirails/InfraLedgerEliteA2C` -> NEGATIVE_CONTROL for a correct service path coexisting with generic CRUD mutation bypass.
- `mradul010/construction_management@ce345579...` -> STRENGTHENS server-reloaded work-order/PO quantity/rate bounds with separate finality gaps.
- CAP-001+006+007+016 -> ENABLES OPP ScopeSignal -> TESTED_BY EXP-005 authority-transition replay, one-use evidence and independent-cash matrix.

### Permit Intelligence
- PermitBuild -> IMPLEMENTS CAP-012.
- CAP-019 -> STRENGTHENS absence/completeness semantics.
- CAP-002+012+019 -> ENABLES OPP Permit Intelligence -> TESTED_BY EXP-009.

### Lab / Sequencing Operations
- Allotropy -> IMPLEMENTS CAP-013.
- `ethanbass/chromConverter@ddf959bb71a595357a3f4028be48afd006a78714` -> STRENGTHENS CAP-013 with registry-driven Agilent/Shimadzu/Waters/Thermo/Varian/open-format normalization, canonical source-hash/parser provenance, fixture-backed numerical/metadata comparisons and CI archaeology that exposed prior silent skips; reverse-engineered vendor formats remain non-certified until customer/vendor corpus acceptance.
- S4 Clarity + scilifelab EPPs + samplesheet-parser + Illumina InterOp -> IMPLEMENT/STRENGTHEN CAP-017.
- Flowcept/HELIOS -> STRENGTHEN provenance/governance.
- `AD-SDL/MADSci@6b1ab6a70ce8b15af7aa8968479c90d9138753d0` -> STRENGTHENS CAP-017 with same-action readback after a lost dispatch response and explicit `UNKNOWN` on unresolved result lookup, while CHALLENGING system-wide exactly-once behavior because generic workflow retry can create a fresh ActionRequest/ULID. Its current SiLA adapter adds a stronger receipt-boundary challenge: orchestration action ID and server-assigned CommandExecutionUUID are not the same identity, and the mapping is held in memory only after the SDK call returns.
- SiLA pre-confirmation ambiguity -> CHALLENGES safe redispatch: the server may have accepted/started a non-idempotent action before the caller receives the server execution UUID. No receipt means UNKNOWN, not NOT_APPLIED.
- `trieu04/lab-in-the-loop@80eb9524a4a36178b35810a7999cd95e8394d4fc` -> ARCHITECTURE_ORACLE / NEGATIVE_CONTROL: durable submit intent, explicit ambiguity states and reconcile-before-resubmit are implemented, but the only installed lab provider is a memory-only dry run and real mode fails closed. It therefore strengthens the control contract while invalidating any claim of completed physical Level-3 reconciliation.
- `MolBioFreak/BioModStack@9b36a0b106cd538d772de39092c1d532ad361083` -> CONCEPTUAL_COMPLEMENT with provider-queryable stable request-key/command/receipt shape; the crash-persistent join with lab-in-the-loop remains unproven.
- `auths-dev/auths-proof@34fa1f33...` -> COMBINES_WITH CAP-017 only as an adjacent-domain transfer oracle for stable business-effect references searchable after restart; scientific transfer requires equivalent device/server history semantics.
- `Opentrons/opentrons@03b991fb263b97b6bb767ce311ca56e103d635e4` -> STRENGTHENS CAP-017 with external vendor `run_id` plus restart-persistent run/action/command state; CHALLENGES naive SAFE_TO_REISSUE because play/resume can begin before the run-control action row is persisted.
- `AD-SDL/ot2_module@39ffdfdb...` + `RoryMB/simlab@5ae0641...` -> TEST-HARNESS candidates for vendor-run identity and simulated actuation; `di-omics/plr-lab-robot@0b062298...` -> NEGATIVE_CONTROL for self-validating command-mutated local state.
- CAP-013+017 -> ENABLES OPP Installed-Base Lab Automation -> TESTED_BY EXP-007 normalization + response-loss/pre-confirmation/retry/restart/provider-binding acceptance cases.

### Industrial pre-FAT
- Gaskony PLC emulator -> IMPLEMENTS CAP-014 controller/config binding.
- Dreamine.Gem + `bparzella/secsgem` -> STRENGTHEN CAP-014 independent SECS/GEM differential testing.
- Duplicate-ECID S2F15 source/test analysis -> CHALLENGES endpoint semantics; duplicate-specific runtime remains NOT_RUN.
- Requester-correlation analysis -> CHALLENGES any endpoint-level T3 claim: Dreamine requires expected-secondary/Function0 completion while secsgem can release a waiter on same-System-Bytes S9F7. Neutral raw-HSMS harness -> DEPENDS_ON EXP-008 measurement integrity.
- CAP-014 -> ENABLES OPP Industrial Pre-FAT -> TESTED_BY EXP-008.

### Prediction / Grid resilience
- grid-crunch + queue_attrition -> IMPLEMENT/STRENGTHEN CAP-015 leakage-resistant historical/prospective prediction.
- DATA USECPO v2 -> TESTS CAP-015 as major-event-correlated outage outcome evidence.
- USECPO literal `event id` -> DEFINES whole-event grouping; STANDARD/8H/24H -> sensitivity variants, not independent validators; EAGLE-I+DOE-417 ancestry and imputation/geography quality -> LIMIT evaluator claims.
- Mendeley DOI `10.17632/r4csg2h2ps.1` exact outer package -> STRENGTHENS CAP-015 provenance chain but CHALLENGES any claim that the outer package SHA is the USECPO source SHA; two byte-identical aliases count as one witness.
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

<!-- INTEGRATOR-R13-2026-09-20T1900-0400 -->
## Integrator graph delta — 2026-09-20 19:00 ET
- `PayrollEngine temporal regulation selection` -> **STRENGTHENS CAP-009** -> `source-backed effective/known-at rule bundle` -> `RosterSpec hard-lock verify/repair` -> **EXP-008 workforce-rule acceptance**.
- `Jaskeeratr/grid-reliability-analytics@24e59a7...` -> **CHALLENGES prior bare event_id grouping assumption** -> strengthens **CAP-015** -> sharpens **EXP-012** with composite event identity + unique county-spell grain.
- `stripe-connect-reckon@deb30aab...` -> independent terminal provider observation -> strengthens **CAP-018** -> **EXP-010** lost-post-success-webhook fixture; reason-aware historical payable reopen remains a separate edge.
- `QuickBooks-V3-Java-SDK@c4d5df...` -> provider mutation identity exists but SDK resets it -> strengthens **CAP-016 / EXP-002** provider-adapter acceptance; durable request identity must be restored explicitly after restart.
- `cmbautomiser@fea18e1...` -> exact evidence reference + mutable-history failure -> **NEGATIVE_CONTROL EXP-005**; one-time selection is not historical immutability.
- `caretaker@08b309d...` + `ac-client@132c20a...` + `BroadbandForum/obuspa@59028be...` -> three-way USP Set semantic matrix -> **CAP-014 / EXP-008**; neutral runtime fixture required before conformance claims.
- SAM first-party historical resource observation for `N6600126Q6264` -> **CAP-011** separates action membership, semantic artifact identity and byte availability; verified membership may coexist with inferred filename and unavailable bytes.
- Freight Pilot Charter trust review -> **CHALLENGES EXP-001 launch gate** and **CAP-007 admission semantics**: strict JSON types + authority-bound launch-decision receipt are prerequisites to treating `KICKOFF_AUTHORIZED` as trusted.
