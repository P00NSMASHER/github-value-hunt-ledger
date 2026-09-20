MARKER: <!-- INTEGRATOR-R12-2026-09-20T0946-0400 -->

=== APPEND MASTER.md ===
## Promotions — 2026-09-20 09:46 ET

### bsaffel/moneybin
- Revision: `fd34d99962c833de87bdb45351f0ace142db3f63`.
- Rights: AGPL-3.0 publicly; standing separate commercial permission applies to repository-owned code. Plaid/broker APIs, financial-account/customer data and external services remain separately governed.
- Score: **28/30** — A4 B5 C5 D5 E5 F4.
- Capability: durable source-observation receipts that distinguish a successful zero result from unavailable/failed source coverage. The inspected Plaid path writes a snapshot receipt for a completed zero-holdings source but deliberately writes no receipt for failed/no-window sources; replay/cursor handling is idempotent and source status is retained.
- Buyer/problem: AP/recovery, finance ingestion and public-data products can otherwise turn connector failure or partial coverage into a false `nothing exists` conclusion and then into unsupported money/decision output.
- Monetization / first paid wedge: Source Authority Retrofit on one high-value connector: require `PRESENT`, `VERIFIED_EMPTY` or `UNAVAILABLE` evidence per source/object/window before money-bearing rules execute.
- Why it wins: makes **absence itself evidence-bearing**. It is stronger positive-training DNA than generic ETL health because a zero-row assertion is only trusted when a successful source observation is durably attested.
- Strongest objection / next action: the Plaid CLI can still require consumers to inspect per-institution status for partial failure; port the receipt invariant into a synthetic ERP/AP connector and prove partial coverage cannot authorize a missing-PO/receipt conclusion.

### mnmn0/mukuroji
- Revision: `34ec66604443da9ba60e9cfbf4d2e6246445bf66`.
- Rights: no root public LICENSE found; root package is private; standing separate commercial permission applies to repository-owned code. AWS, KMS, customer data and organization policies remain separate.
- Score: **28/30** — A4 B5 C5 D5 E5 F4.
- Capability: isolated non-Postgres recovery proof across DynamoDB and exact-version S3 state using a common historical point, authenticated content/metadata/descriptor aggregates, cross-domain semantic claims, RPO/RTO gates, immutable evidence publication and approval-bound cleanup.
- Buyer/problem: AWS SaaS/MSPs can show PITR/backups exist but still cannot prove one coherent historical application state restores correctly without touching production.
- Monetization / first paid wedge: AWS Stateful Recovery Acceptance Test on a customer's isolated DynamoDB/S3 resource set and a small frozen set of business invariants; recurring Recovery Proof SLA after the first adversarial pass.
- Why it wins: combines exact historical source selection, wrong-content/relationship rejection, fail-closed work ceilings, immutable evidence and governed cleanup in a non-Postgres recovery architecture.
- Strongest objection / next action: deeply application-specific and not a drop-in DR platform; run a rights-clean synthetic second-application adapter with wrong relation/content, stale restore point, object-version mutation and cleanup-receipt substitution before claiming portability.

=== APPEND COMPONENTS.md ===
## Integrator component delta — 2026-09-20 09:46 ET
- **`payops-labs/solana-payment-ops@7e4d9cc8d137e4d32cdb4b23aa5c0965f3379e94` — 28/30:** fail-closed exact settlement-allocation oracle. Finalized money events auto-allocate only under unique reference/asset/destination/amount/time evidence; ambiguous, partial, excess, duplicate and stale cases remain exceptions. Use the persistence/one-use allocation invariant, not Solana as freight authority.
- **`Noone9029/Accounting-App@90e0eaa4896a55c1c8cda1c4101f4ab1323a4a61` — 25/30:** explicit pairwise partial-allocation edges with residual balances and stateful reversible history. Useful after a unique gate or reviewed adjudication; caller-selected invoice identity is not itself authority.
- **`scolladon/dataset-loader@5039257cde249a428f6ff5d0a2ba67fe59ac972e` — 26/30:** finalize-before-watermark incremental ETL with partial/all-failed exit semantics and no watermark advance on failed groups. Pair with an explicit observation receipt because empty reads are skipped rather than durably attested.
- **`NationalGenomicsInfrastructure/scilifelab_epps@fbbe16f9a5ee50d4df610b20908cef501da32bbe` — 28/30:** production-shaped Clarity LIMS EPP estate binding workflow/run identity to Illumina run folders, RunParameters/RunInfo, official InterOp metrics and LIMS writeback, plus AVITI/ONT adjacency. Major caveat: no comprehensive repo-local behavioral regression suite found.
- **`chaitanyakasaraneni/samplesheet-parser@511b484f59de18ed3f444f064d46e9c930dba630` — 26/30:** independent V1/V2/AVITI sample-sheet parser/converter/diff/validator with index-distance and chemistry-aware color-balance tests; suitable as an independent pre-run acceptance gate, not vendor certification.
- **`nearai/pg-backup@6836158bdfd38937a55fd21d72e221192d2a9b59` — 28/30:** encrypted Postgres backup/restore proof with snapshot-consistent counts, manifest-last completeness, checksums, app invariants and an unusually valuable verifier-self-test history: mutation testing exposed a Bats false-green helper and the repository repaired/locked the failure path.
- **`senecaSparsh/nirman@0e40fbada98a7448c4d74b1cbd4252da76c9183e` — 26/30:** positive-but-flawed construction measurement-to-RA-bill reference: server-derived billed quantity from APPROVED unbilled measurement-book rows, authorized work-order rates and atomic measurement claiming. Still lacks proven work-order ownership, period inclusion and external cash finality.
- **`moov-io/ach@f36ebb7ef2e6d678ef95ca6278d2b1f2deae4299` — 26/30:** Nacha return/reversal truth layer preserving `OriginalTrace` lineage from later Return Entries back to the original forward entry. Does not itself prove feed completeness or provider-ID→ACH-trace mapping.
- **`Maxed-OSS/statement-normalizer@0963c962a5ab618761ab57b604bad10578d39a0f` — 21/30 watch:** CAMT/MT940/OFX/QFX/CSV/QIF normalization retaining amount/currency/date/account/reference for independent bank readback; input component, not a finality oracle.

=== APPEND DATASETS.md ===
## Dataset / public-authority delta — 2026-09-20 09:46 ET
- **DHS Acquisition Planning Forecast System (APFS), official live service — 29/30 evidence artifact.** Public forecast records expose stable forecast IDs plus source-native dated `Change Log` events showing old→new field changes, cancellations/`No Longer Required`, dates, NAICS, vehicle/program and incumbent/contract context. This strengthens CaptureBrief's pre-solicitation timeline, but forecasts remain planning evidence rather than commitments and may not map deterministically to one SAM notice.
- **PNNL Event-correlated Outage Dataset in America (USECPO) v2 — 27/30.** Current Data.gov/OEDI metadata records public access and CC BY 4.0; combines 2014–2023 EAGLE-I county outages, DOE-417 events and population into event-aligned outage outcomes. Strong grid validation benchmark, but it is not independent truth for an EAGLE-I-trained model and inherits DOE-417/event-threshold selection bias.
- **EAGLE-I 2025 outage observations — out-of-time holdout candidate.** Released 2026-02-19 and temporally later than common 2015–2024 development histories. Exact commercial reuse terms were not established in the inspected metadata; keep rights unresolved before embedding/commercializing.
- **California OES Power Outage Incidents — 24/30 live acceptance source.** Public-domain, refreshed roughly every 15 minutes from major California utility public outage maps; useful for current/live ingestion spot checks but not a retrospective archive.
- **SAM.gov Alerts — source-health evidence surface.** Official dated incidents can explicitly state that opportunity/award/report surfaces are incomplete or delayed. Query success during an affected interval is not proof of source completeness; absence of an alert also does not prove health.

=== APPEND CAPABILITIES.md ===
## Capability delta — 2026-09-20 09:46 ET

### CAP-019 — Source-authority observation receipts
- Ability: prove whether a queried source/object/window is `PRESENT`, `VERIFIED_EMPTY` or `UNAVAILABLE`, and advance source cursors only after durable downstream commit so absence cannot be manufactured by connector failure.
- Maturity: **VALIDATED COMPONENT**.
- Evidence basis: `bsaffel/moneybin@fd34d999...` tests successful zero-result snapshot receipts while failed/no-window sources receive no receipt; `scolladon/dataset-loader@5039257...` tests finalize-before-watermark, abort/no-watermark on failures and partial/all-failed exit codes.
- Reusable targets: AP Leakage, CaptureBrief, freight/settlement imports, permit/public-data intelligence and any money-bearing source adapter.
- Limitation: neither component alone supplies a universal whole-run completeness protocol; moneybin consumers must still fail closed on per-source partial failure and dataset-loader does not durably attest an empty read.
- Missing piece / next test: one synthetic ERP PO/GR lifecycle with source receipts, cursor identity and bitemporal corrections; transport/auth failure must never produce `VERIFIED_EMPTY`, and cursor advancement must occur only after exact source query plus durable target state are proven.

### Cross-capability upgrades
- **CAP-006 Settlement-grounded recovery attribution:** add PayOps-style immutable claim/event identity, exact unique auto-allocation and one-use persistence; reviewed split/partial settlement becomes explicit pairwise allocation edges with residual capacity and reversible history. A deterministic subset-sum/tie-break is only a proposal, never settlement proof.
- **CAP-010 Recovery proof:** add Mukuroji's DynamoDB/S3 historical-state/semantic verification and nearai/pg-backup's verifier-self-test requirement. The verifier itself must be mutation/fault tested; a broken assertion helper that yields green is a failed recovery-proof system.
- **CAP-011 Government acquisition authority/lineage:** add DHS APFS source-native dated change history and SAM official operational-health intervals. Preserve source event time separately from collector observation time; a known degraded source interval taints negative/completeness conclusions.
- **CAP-014 Industrial pre-FAT:** the Dreamine↔secsgem shared tested intersection now supports a frozen 10-case differential corpus plus `EC-ATOMIC-PROBE` (valid first EC update + invalid second) predicted to expose all-or-nothing vs partial-mutation semantics. Repository collection is no longer the bottleneck; execution is.
- **CAP-017 Sequencing operations evidence bridge:** add `scilifelab_epps` as the concrete Clarity process→flowcell/run-directory→RunParameters/RunInfo→InterOp→Clarity-writeback implementation and `samplesheet-parser` as an independent pre-run compatibility/diff gate. Missing behavioral regression/evidence packaging remains explicit.
- **CAP-018 Provider-settlement ambiguity / payout proof:** add `moov-io/ach` post-success Return Entry/reversal lineage and statement-normalizer bank-readback input. Provider `paid` is now explicitly revocable until external network/bank evidence plus later-return window/source freshness are accounted for.

=== APPEND KNOWLEDGE_GRAPH.md ===
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

=== APPEND COMBINATIONS.md ===
## Combination delta — 2026-09-20 09:46 ET

### Freight realized-recovery allocation hardening
`controlling contract/addendum authority -> independent expected charge -> issued carrier credit/refund authority -> PayOps exact unique settlement gate -> reviewed explicit pairwise partial/split allocation edges -> reversal/counter-event -> derived realized recovery`.
- Only active persisted allocation edges tied to an issued adjustment and independent money movement can increase realized recovery.
- Ambiguous identity, partial/excess auto-match, alternate feasible allocations or stale caller decisions remain exception/REVIEW and **$0 realized**.

### Commission / payout bank-finality chain
`effective-at entitlement -> payout intent/idempotent provider operation -> provider settlement decomposition -> ACH forward trace -> independent bank/network observation -> later Return Entry/reversal by OriginalTrace -> final classification`.
- Provider `paid`, ERP ledger posting and bank amount are three different evidence planes.
- Missing/stale ACH-return or bank feeds remain UNKNOWN; no return observed is not equivalent to proven finality.

### ScopeSignal measurement-to-payment authority chain
`design/contract/notice authority -> field measurement -> APPROVED state -> correct work-order ownership + billed-period inclusion -> server-derived RA bill quantity/rate -> bill approval/AP -> independent cleared-payment evidence`.
- DIGIT purchase-bill behavior is a negative-control architecture where measurement-aware UI does not prove backend authority.
- Nirman is the positive-but-flawed comparator: APPROVED/unbilled MB rows derive RA-bill quantity, but work-order attribution, period gating and external cash finality remain unresolved.

### Recovery Proof multi-engine adversarial stack
`Postgres PITR/restore engine + DynamoDB/S3 exact-version isolated restore + application/business invariants + trust/evidence envelope + verifier mutation/self-test`.
- A valid proof system must reject wrong-but-restorable content and must also fail if its own assertion/test harness is intentionally broken.

### CaptureBrief pre-solicitation-to-award timeline
`DHS APFS source-native forecast changes/cancellations -> normalized history events -> SAM opportunity/version/attachment packet + SAM health intervals -> FAR/supplement/deviation authority -> entity/award/incumbent lineage -> USAspending outcome`.
- Collector polling remains useful but source-native history wins on event time; known platform degradation taints completeness.

### Sequencing installed-base acceptance stack
`Clarity workflow/process state -> scilifelab EPP run identity/handoff -> independent sample-sheet semantic diff/compatibility gate -> vendor-native run artifacts + Illumina InterOp metrics -> LIMS writeback -> provenance/evidence layer`.
- Sell as an acceptance/modernization service, not as replacement LIMS or regulator/vendor certification.

=== APPEND OPPORTUNITIES.md ===
## Portfolio movement — 2026-09-20 09:46 ET
- **#1 Freight Recovery remains unchanged.** PayOps-style exact one-use settlement allocation materially improves defensibility but does not remove the external blocker: one customer-authorized frozen population must reach an attributable credit/refund/remittance.
- **AP Leakage Assurance strengthens technically, rank unchanged.** CAP-019 gives the synthetic benchmark a durable distinction between legitimate absence and source failure; no new matcher should be collected until this source-authority gate is executed.
- **Recovery Proof SLA strengthens.** Mukuroji adds a rare DynamoDB/S3 semantic recovery plane and nearai adds verifier-self-test evidence. This makes the immediate fixed-price Recovery Readiness/Stateful Recovery Acceptance service technically stronger without constituting buyer validation.
- **Commission Payout Assurance broadens its paid wedge:** provider-paid-but-returned deposits, duplicate reissue risk and unrecovered returned payouts become explicit finance exceptions once ACH trace and independent bank evidence can be joined. Bank/network freshness/completeness remains the gating seam.
- **CaptureBrief gains a higher-leverage pre-solicitation wedge:** forecast-change radar based on source-native DHS APFS history, followed forward into SAM/award evidence. Planning records are not commitments and linkage precision must be measured before selling predictive claims.
- **Installed-Base Lab Automation becomes more concrete:** a Clarity Sequencing Handoff Acceptance / upgrade-regression engagement can now start from a production-shaped EPP/run-metric estate plus an independent sample-sheet validator rather than inventing the handoff semantics from scratch.
- **Grid resilience gains an outcome-priced validation path:** USECPO event outcomes plus separately governed interruption-cost economics can test avoided interruption dollars/crew-hour. Keep below top direct-money opportunities until circularity, rights and held-out reproduction are resolved.
- No opportunity is commercially validated by this run; `OUTCOMES.md` still has no completed customer/value result that would justify a ranking change based on realized revenue.

=== APPEND EXPERIMENTS.md ===
## Stage-gate delta — 2026-09-20 09:46 ET
- **EXP-001 Freight:** add immutable issued claim + exact unique auto-allocation + explicit reviewed pairwise partial/split allocation + reversal. Plant duplicate event, alternate feasible allocation, partial, excess, wrong payee/currency/time, stale decision and reversal. Only non-reversed independently sourced allocated settlement counts as realized; external buyer population remains the blocker.
- **EXP-002 AP:** implement CAP-019 receipts for PO/GR/invoice sources. Require one receipt per `{source, object/query-window, run}` with health, count/hash/cursor. Failed/auth/unreachable source -> `UNAVAILABLE`; completed zero -> `VERIFIED_EMPTY`; cursor advances only after durable load. Replay through the bitemporal correction and Nomenklatura→Canon identity lifecycle.
- **EXP-003 Commission:** add provider-success followed by ACH Return Entry joined by `OriginalTrace`, duplicate reissue while return state unresolved, unmatched trace, amount/currency mismatch, missing/stale return feed and independent CAMT/MT940 readback. Finality requires traceable external observation; source-degraded remains UNKNOWN.
- **EXP-004 Recovery Proof:** add Mukuroji-style non-Postgres cases: correct counts but wrong relationship/value, stale restore point, wrong S3 object version, metadata mismatch and substituted cleanup receipt. Add a nearai-style verifier mutation: deliberately break one assertion/helper and require CI/e2e to fail before any green recovery proof is trusted.
- **EXP-005 ScopeSignal:** use DIGIT purchase bill as negative control and Nirman RA bill as positive-but-flawed control. Plant DRAFT/VERIFIED/REJECTED/APPROVED measurements, DRAFT vs ACTIVE work order, wrong eligible work-order ownership, before/inside/after bill period, concurrent double claim, superseded baseline and internal `PAID` without external clearing.
- **EXP-006 CaptureBrief:** add 25 DHS APFS records with multiple source-native Change Log events and compare against polling/archive output; normalize leading `*` as change marker rather than identity. Add SAM alert-overlap cases where otherwise successful queries must be `source_degraded`, plus the existing 10-solicitation latest-vs-history/attachment benchmark.
- **EXP-007 Sequencing:** use a synthetic/mock Clarity process + synthetic run directory and require distinct failures for no run match, ambiguous run match, missing RunParameters/RunInfo, InterOp parse/metric failure, sample-sheet collision, unknown-platform chemistry and LIMS writeback failure. Preserve each as separate evidence state.
- **EXP-008 Industrial:** freeze and execute the existing 10-case Dreamine↔secsgem intersection plus `EC-ATOMIC-PROBE`. Do not search another generic engine until a concrete disagreement requires a third oracle.

### EXP-012 — Outcome-priced grid resilience calibration
- Opportunity: Grid / Infrastructure Risk & Inspection.
- Status: **READY** for USECPO historical benchmark; later EAGLE-I 2025 use remains rights-dependent.
- Hypothesis: a frozen risk/inspection/restoration policy can beat highest-risk-first, nearest-route and scheduled baselines on the same event population when scored on outage outcomes and expected interruption consequence per crew-hour.
- Inputs: USECPO v2 event-correlated outcomes; frozen model/policy inputs; separately governed interruption-cost model/service; optional 2025 holdout only after rights are established; independent regulator/live spot checks for circularity.
- Success: materially better held-out outcome/calibration and consequence-per-crew-hour with uncertainty reported; false negatives and missing-data sensitivity explicit.
- Failure: advantage disappears against simple baselines, depends on overlapping EAGLE-I truth, or economic score is presented as observed avoided dollars without independent outcome evidence.
- Decision unlocked: whether grid risk/inspection intelligence deserves a buyer pilot rather than more repository/data hunting.

=== APPEND REJECTED.md ===
## Negative-memory delta — 2026-09-20 09:46 ET
- **DIGIT-Works purchase-bill APPROVED-measurement gate claim — FALSIFIED at `7c44e963c7aced16d648971ae66eb938cbe8fdc4`.** Keep DIGIT as a strong contract-bounded measurement component, but do not claim purchase-bill creation is server-gated by APPROVED measurement: the inspected backend accepts caller-provided bill details, does not load/validate measurement status/quantity on that path, and the UI's `not DRAFTED/not REJECTED` check is only a client warning boundary. Revisit only if a later backend revision introduces an authoritative measurement reference and direct negative tests.
- **`jhilly20/GovCon@0f40280af54649f047a467270631fda6acf31d2c` — REJECT for evidence-grade APFS ingestion.** Request/JSON failure can become an empty list and later a successful `0 results` state. Revisit only when source failure is typed/propagated and cannot authorize an empty conclusion.
- **Generic deterministic settlement matchers remain candidate generators, not realized-money authority.** Subset-sum/ILP/tie-breaking can choose one feasible allocation without proving economic identity or uniqueness. Revisit only if alternate-feasible sets are explicitly detected and ambiguity blocks posting.
- **Process `Completed`, provider `paid`, UI warning and internal `PAID` are not authority/finality.** Require source receipt, backend gate, external provider/bank/network evidence and later reversal/return handling appropriate to the claim.

=== APPEND SEARCH_QUEUE.md ===
## Integrator override — 2026-09-20 09:46 ET
1. **Freight / EXP-001:** stop reconciliation-engine hunting. Implement the PayOps exact gate + explicit reviewed partial-edge ledger on the planted 210/812/820 corpus; continue only authority/correction/final settlement searches needed by the real external population.
2. **AP / EXP-002:** stop matcher hunting. Port the moneybin observation-receipt invariant + dataset-loader finalize-before-watermark discipline into PO/GR/invoice adapters and execute `PRESENT / VERIFIED_EMPTY / UNAVAILABLE` plus bitemporal/identity correction cases.
3. **Commission / EXP-003:** search only the final join `provider payout ID -> forward ACH trace -> independent bank/payroll statement observation -> later Return/Reversal`, with source freshness/completeness. `moov-io/ach` closes return semantics; another payout wrapper is low yield.
4. **ScopeSignal / EXP-005:** stop generic measurement/pay-app discovery. Execute DIGIT negative-control versus Nirman positive-but-flawed corpus. Search again only for the unresolved hard joins: measurement→correct work-order ownership, billed-period inclusion, superseded baseline and independent cleared cash.
5. **Recovery Proof / EXP-004:** stop broad restore-tool search. Run PostgreSQL + Mukuroji DynamoDB/S3 wrong-content/relationship controls and mutate the verifier itself using the nearai lesson. A green verifier that cannot fail when its assertion harness is broken is disqualified.
6. **CaptureBrief / EXP-006:** prioritize DHS APFS source-native history, SAM packet/version history and SAM operational alert intervals. Benchmark archive/polling diffs against source-native events and repair `*`-marker identity before using cross-agency forecast churn as customer evidence.
7. **Installed-Base Lab / EXP-007:** stop broad LIMS hunting. Build the Clarity EPP synthetic handoff around `scilifelab_epps` and independently validate generated sample sheets before run launch; keep BO-MCP as a shadow experiment-integrity challenger until external executor acknowledgement and buyer value are tested.
8. **Industrial / EXP-008:** execute the frozen 10-case Dreamine↔secsgem corpus and `EC-ATOMIC-PROBE`; search a third engine only to adjudicate an observed disagreement.
9. **Grid / EXP-012:** use USECPO as the current rights-clear event benchmark, separately resolve 2025 EAGLE-I reuse terms, and score simple vs optimized policies on same-event consequence/crew-hour. Stop broad outage-dataset collection.
10. **Global:** absence claims now require source-observation authority; `success/complete/paid` labels must be traced to the external fact they purport to prove. Preserve the benchmark recall-rescue pass before NO_FIND.

=== APPEND TECHNOLOGY_RADAR.md ===
## Radar evidence delta — 2026-09-20 09:46 ET
- **Authority-aware money assurance:** strengthened, no numeric score change. Independent findings now cover source-observation receipts, immutable/one-use settlement allocation, provider ambiguity and later ACH return/reversal. The emerging primitive is `authority -> explicit unknown -> one-use state transition -> external readback -> counter-event` rather than a terminal success bit.
- **Proof-carrying recovery software:** strengthened, no numeric score change. Mukuroji extends the pattern to DynamoDB/S3 semantic state and approval-bound cleanup; nearai adds verifier-self-test evidence, making "prove the proof system fails when it should" a material maturity signal.
- **Installed-base scientific operations adapters:** strengthened, no numeric score change. `scilifelab_epps` independently demonstrates preserve-the-LIMS + bridge-the-instrument/run-metrics architecture; BO-MCP adds experiment-identity/idempotency evidence in a separate self-driving-lab lineage.
- **Temporal machine-readable public authority:** strengthened, no numeric score change. DHS APFS source-native history and SAM operational incident intervals show that event time, observation time and source-health time all matter for defensible public-data conclusions.
- **Outcome-priced grid decision intelligence:** strengthened, no numeric score change. USECPO adds an event-aligned outage outcome benchmark and interruption-cost tooling supplies a separately governed consequence layer, but EAGLE-I circularity and buyer-grade asset truth remain unresolved.
