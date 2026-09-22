# UNIFIED HUNT PLAN

Allocator generation: **ALLOCGEN:51e2788d0136**
Portfolio policy: **PORTFOLIO:6c1a3e6e5624**

This is the current 14-slot work plan. Scores are scheduling priorities, not claims of repository or commercial value.

| Slot | Role | Score | Work | Capability | Experiment | Source |
|---|---|---:|---|---|---|---|
| SLOT-01 | experiment | 99.8 | EXP-002 — AP source-authority + reversible receipt-policy audit | CAP-002, CAP-007, CAP-008, CAP-016, CAP-019 | EXP-002 | EXP-002 |
| SLOT-02 | experiment | 97.5 | EXP-003 — Commission plan-to-bank acceptance test | CAP-002, CAP-006, CAP-007, CAP-016, CAP-018, CAP-019 | EXP-003 | EXP-003 |
| SLOT-03 | experiment | 94.5 | EXP-007 — Installed-base sequencing/lab handoff acceptance | CAP-013, CAP-017 | EXP-007 | EXP-007 |
| SLOT-04 | experiment | 94.2 | EXP-008 — Industrial virtual pre-FAT differential benchmark | CAP-014 | EXP-008 | EXP-008 |
| SLOT-05 | experiment | 93.2 | EXP-012 — Outcome-priced grid resilience calibration | CAP-015 | EXP-012 | EXP-012 |
| SLOT-06 | experiment | 88.2 | SEED:gap:cap-012 | CAP-012 | EXP-009 | SEED:gap:cap-012 |
| SLOT-07 | coverage | 77.2 | SEED:coverage:language-family-c-cpp:rule-version-transfer | — | — | SEED:coverage:language-family-c-cpp:rule-version-transfer |
| SLOT-08 | coverage | 70.3 | SEED:coverage:language-family-jvm:abstention-transfer | — | — | SEED:coverage:language-family-jvm:abstention-transfer |
| SLOT-09 | coverage | 73.2 | SEED:dna:gsa-gsa-acquisition-dfars | — | — | SEED:dna:gsa-gsa-acquisition-dfars |
| SLOT-10 | adjacency | 101.3 | ADJ:distinctive-symbol:sandialabs-dreams | — | — | ADJ:distinctive-symbol:sandialabs-dreams |
| SLOT-11 | measurement | 81.1 | SEED:learn:acceptance-path-transition-inspection-rule-version-transfer | — | — | SEED:learn:acceptance-path-transition-inspection-rule-version-transfer |
| SLOT-12 | measurement | 60.6 | SEED:learn:bidirectional-money-evidence-invariant-tracing-promotion-control-transfer | — | — | SEED:learn:bidirectional-money-evidence-invariant-tracing-promotion-control-transfer |
| SLOT-13 | verification | 90.8 | Independent verification — EXP-007 | CAP-013, CAP-017 | EXP-007 | VERIFY:EXP-007 |
| SLOT-14 | wildcard | 75.0 | Rare / weird wildcard exploration | — | — | WILDCARD:rare-weird |

## Assignment packets

### SLOT-01 — EXP-002 — AP source-authority + reversible receipt-policy audit
- Assignment ID: ASSIGN:51e2788d0136:slot-01
- Work kind/action: **experiment_execution / execute_fixture**
- Score: **99.75** — {"portfolio_priority_boost": 8, "queue_order_adjustment": -0.25, "readiness_base": 92}
- Strategy/objective: n/a / n/a
- Capability/experiment: CAP-002, CAP-007, CAP-008, CAP-016, CAP-019, EXP-002
- Why now: Experiment is READY and should be executed/falsified before searching for redundant components.
- Execution scope: READY — synthetic reference fixture PASSED; authorized endpoint-specific ERP/provider execution is next.
- Next action: in an authorized Dynamics 365 Finance sandbox, identify and freeze the exact vendor-credit create/post interface and original-invoice binding, force response loss or `PreProcessingError`, and prove whether financial posting began. Preserve exact operation/economic fingerprint and keep every unsupported case UNKNOWN.
- Acceptance target: all planted cases detected; unsupported recovery = 0; source outage cannot create money; capacity is conserved; crash/restart cannot create a second logical counter-event; bitemporal replay reproduces known-at/valid-at truth; unbound generic `PreProcessingError` remains UNKNOWN.
- Hypothesis: explicit source observation, reviewed identity, policy-specific receipt authority, reversible line-level authority consumption, crash-safe writeback and an exact endpoint-to-posting-boundary contract can distinguish recoverable AP leakage from unresolved exceptions without false missing-receipt/PO dollars or duplicate counter-events.
- Success: all planted cases detected; unsupported recovery = 0; source outage cannot create money; capacity is conserved; crash/restart cannot create a second logical counter-event; bitemporal replay reproduces known-at/valid-at truth; unbound generic `PreProcessingError` remains UNKNOWN.
- Failure: universal `has_receipt`, any-return-means-authority-restored, unavailable source becomes negative evidence, exception/timeout becomes NOT_APPLIED, provider-wide phase semantics are applied to an unverified economic endpoint, or UNKNOWN frees capacity/mints a new operation.
- Stop conditions: Execute the existing alias/non-match/merge/split corpus before seeking another identity engine.; Run the existing authority/admission matrix before further restore, OTA or attestation discovery.; Pin the official rule-pack version and authority before comparing existing validators; do not replace rule authority with another repository.; Run the existing crash/replay-expiry/finality matrix. Permit adapter search only for a separately named failed NOT_APPLIED proof gap.; Run synthetic transport/auth/partial-source failure cases before source-receipt discovery.; Do not broaden into generic discovery unless execution exposes a named technical gap.; READY scope authorizes the stated fixture/verification only; separately blocked commercial or customer proof remains external.

### SLOT-02 — EXP-003 — Commission plan-to-bank acceptance test
- Assignment ID: ASSIGN:51e2788d0136:slot-02
- Work kind/action: **experiment_execution / execute_fixture**
- Score: **97.50** — {"portfolio_priority_boost": 6, "queue_order_adjustment": -0.5, "readiness_base": 92}
- Strategy/objective: n/a / n/a
- Capability/experiment: CAP-002, CAP-006, CAP-007, CAP-016, CAP-018, CAP-019, EXP-003
- Why now: Experiment is READY and should be executed/falsified before searching for redundant components.
- Execution scope: READY — synthetic historical-authority/late-return fixture PASSED; external terminal observation is the next execution.
- Next action: run one real provider/bank or payroll adapter with the reversal webhook suppressed, require independent terminal readback to discover the late return, and reproduce the passing original-rate/exactly-once behavior.
- Acceptance target: unknown provider result stays pending; duplicate send impossible; later still-owed return exactly unwinds prior finality and reopens original authority without repricing; clawback-not-owed does not create a duplicate payable.
- Hypothesis: frozen entitlement plus provider state and independently observed bank/payroll state can detect payout errors without duplicate-send or false-finality risk, while ambiguous linkage and unavailable source windows remain non-final.
- Success: unknown provider result stays pending; duplicate send impossible; later still-owed return exactly unwinds prior finality and reopens original authority without repricing; clawback-not-owed does not create a duplicate payable.
- Failure: provider status establishes finality; trace/fuzzy/amount-only matching becomes exact; unavailable evidence mutates realized money; return leaves prior payout final; or repayment reads current policy.
- Stop conditions: Execute the existing alias/non-match/merge/split corpus before seeking another identity engine.; Await actual authorized settlement/return evidence; repository discovery cannot establish realized recovery.; Run the existing authority/admission matrix before further restore, OTA or attestation discovery.; Run the existing crash/replay-expiry/finality matrix. Permit adapter search only for a separately named failed NOT_APPLIED proof gap.; Execute the post-success lost-webhook fixture; do not resume generic commission or payout-wrapper discovery.; Run synthetic transport/auth/partial-source failure cases before source-receipt discovery.; Do not broaden into generic discovery unless execution exposes a named technical gap.; READY scope authorizes the stated fixture/verification only; separately blocked commercial or customer proof remains external.

### SLOT-03 — EXP-007 — Installed-base sequencing/lab handoff acceptance
- Assignment ID: ASSIGN:51e2788d0136:slot-03
- Work kind/action: **experiment_execution / execute_fixture**
- Score: **94.50** — {"portfolio_priority_boost": 4, "queue_order_adjustment": -1.5, "readiness_base": 92}
- Strategy/objective: n/a / n/a
- Capability/experiment: CAP-013, CAP-017, EXP-007
- Why now: Experiment is READY and should be executed/falsified before searching for redundant components.
- Execution scope: READY — execute the Thermo metadata repair/replay and the pending physical-action branch.
- Next action: (1) patch/rebuild OpenTFRaw event lookup to use `entry.scan_event`, replay the exact fixture and add oracle-backed metadata/CV regressions; use Entab only to adjudicate remaining disagreement. (2) run the SiLA/Opentrons real-provider kill/restart matrix. Do not call the four-vendor normalization branch PASSED while Thermo metadata disagrees.
- Acceptance target: (1) patch/rebuild OpenTFRaw event lookup to use `entry.scan_event`, replay the exact fixture and add oracle-backed metadata/CV regressions; use Entab only to adjudicate remaining disagreement. (2) run the SiLA/Opentrons real-provider kill/restart matrix. Do not call the four-vendor normalization branch PASSED while Thermo metadata disagrees.
- Hypothesis: cross-vendor analytical files can be normalized only when independently decoded measurement and acquisition semantics agree before common normalization; consequential physical actions must retain one external effect identity across ambiguity and restart.
- Stop conditions: Execute the pinned Thermo RAW row before shared normalization; no converter discovery until it runs.; Execute the existing durable-provider ambiguity matrix before broad lab-orchestrator discovery.; Do not broaden into generic discovery unless execution exposes a named technical gap.; READY scope authorizes the stated fixture/verification only; separately blocked commercial or customer proof remains external.

### SLOT-04 — EXP-008 — Industrial virtual pre-FAT differential benchmark
- Assignment ID: ASSIGN:51e2788d0136:slot-04
- Work kind/action: **experiment_execution / execute_fixture**
- Score: **94.25** — {"portfolio_priority_boost": 4, "queue_order_adjustment": -1.75, "readiness_base": 92}
- Strategy/objective: n/a / n/a
- Capability/experiment: CAP-014, EXP-008
- Why now: Experiment is READY and should be executed/falsified before searching for redundant components.
- Execution scope: READY — secsgem atomicity source/test claim verified; real-HSMS differential is the next execution.
- Next action: execute both frozen hypotheses against the pinned endpoints through the neutral harness. Seek a third engine only after an observed endpoint disagreement.
- Acceptance target: execute both frozen hypotheses against the pinned endpoints through the neutral harness. Seek a third engine only after an observed endpoint disagreement.
- Hypothesis: customer/profile-derived virtual endpoints can catch binding/type/state/error/liveness defects before hardware when endpoint behavior is measured independently from requester-library policy.
- Stop conditions: CAP-014 STOP: no third SECS/GEM engine until an actually executed endpoint disagreement needs adjudication. Run the neutral raw-HSMS fixture against both pinned endpoints first.; Do not broaden into generic discovery unless execution exposes a named technical gap.; READY scope authorizes the stated fixture/verification only; separately blocked commercial or customer proof remains external.

### SLOT-05 — EXP-012 — Outcome-priced grid resilience calibration
- Assignment ID: ASSIGN:51e2788d0136:slot-05
- Work kind/action: **experiment_execution / verify_artifact**
- Score: **93.25** — {"portfolio_priority_boost": 4, "queue_order_adjustment": -2.75, "readiness_base": 92}
- Strategy/objective: n/a / n/a
- Capability/experiment: CAP-015, EXP-012
- Why now: Experiment is READY and should be executed/falsified before searching for redundant components.
- Execution scope: READY with artifact-byte gate.
- Next action: fetch the already-public Mendeley ZIP in a binary-capable runtime, verify the outer SHA, extract only the source/download manifest, inspect the exact USECPO row and compare it with first-party OEDI bytes/digest. Then freeze event-level 2019–2023 splits and simple-vs-optimized comparisons.
- Acceptance target: source-byte/digest identity is pinned or explicitly UNKNOWN/MISMATCH; model/policy beats simple baselines on frozen same-event outcomes without leakage; evaluator lineage/construct and imputation flags are explicit; variants are sensitivity views only; modeled interruption dollars remain separate from observed outage outcome.
- Hypothesis: a resilience policy can demonstrate same-input advantage only when evaluator ancestry, construct, grouping and independence are explicit and predictions are frozen before prospective challenge.
- Success: source-byte/digest identity is pinned or explicitly UNKNOWN/MISMATCH; model/policy beats simple baselines on frozen same-event outcomes without leakage; evaluator lineage/construct and imputation flags are explicit; variants are sensitivity views only; modeled interruption dollars remain separate from observed outage outcome.
- Failure: Mendeley outer-package hash is misreported as USECPO source hash, duplicate aliases are counted as independent witnesses, row-level/random split leaks one physical event across train/test, lag variants are counted as independent votes, state-generalized geography becomes county-precise truth, imputed restoration becomes observed outcome, or event correlation becomes feeder/component causality.
- Stop conditions: CAP-015 STOP: obtain and verify the current first-party OEDI artifact bytes against an independently expected digest, inspect schema/time/null semantics, and freeze the event/spell manifest before policy scoring. Missing bytes or digest is blocked evidence, not authority to find more outage datasets.; Do not broaden into generic discovery unless execution exposes a named technical gap.; READY scope authorizes the stated fixture/verification only; separately blocked commercial or customer proof remains external.

### SLOT-06 — SEED:gap:cap-012
- Assignment ID: ASSIGN:51e2788d0136:slot-06
- Work kind/action: **capability_gap / execute_fixture**
- Score: **88.21** — {"base_priority": 79.0, "experiment_boost": 8, "strategy_allocation": 1.21}
- Strategy/objective: STRAT:rule-period-authority-version-audit / OBJ:completeness-proof
- Capability/experiment: CAP-012, EXP-009
- Why now: CAP-012 is a current high-information gap (gap score 4, prior run attention 2). Saturation: INSUFFICIENT (+0 priority). Missing piece: jurisdiction completeness/semantics vary.
- Next action: run three-jurisdiction source-field truth and source-outage benchmark.
- Acceptance target: run three-jurisdiction source-field truth and source-outage benchmark.
- Verification gate: Record the exact fixture/artifact subject, independent expected result, observed result and blocker. Completion of research is not completion of the acceptance test.
- Stop conditions: Freeze three-jurisdiction source-field truth and source-outage cases before more permit repository discovery.; Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.

### SLOT-07 — SEED:coverage:language-family-c-cpp:rule-version-transfer
- Assignment ID: ASSIGN:51e2788d0136:slot-07
- Work kind/action: **coverage_gap / search**
- Score: **77.21** — {"base_priority": 76.0, "experiment_boost": 0, "strategy_allocation": 1.21}
- Strategy/objective: STRAT:rule-period-authority-version-audit / OBJ:current-rule-authority
- Capability/experiment: cross-domain
- Why now: Intersect exploration blind spot COV:language-family:c-cpp (C / C++: 1/3) with rule-version-transfer, an authorized anchored search hypothesis. This is coverage correction tied to a valuable technical hypothesis, not diversity for its own sake.
- Next action: Run the bounded anchored transfer queries and inspect one connected implementation path.
- Acceptance target: One independent target-domain implementation with source/test evidence for: effective rule version, historical evaluation, authority provenance
- Queries:
  - OpenFisca reforms parameter language:C
  - "tax" "effective_date" path:tests language:C
  - OpenFisca reforms parameter language:C++
  - "tax" "effective_date" path:tests language:C++
- Search surfaces: GitHub repository search, GitHub code search, GitHub code search, low-star/zero-star repository search, archived repository archaeology, author/org adjacency, dependency/consumer adjacency
- Verification gate: A transfer candidate must implement the invariant in executable code and tests; domain naming similarity is irrelevant. Prefer a different vertical or protocol family from the source repo. Coverage membership alone never raises evidence quality.
- Stop conditions: Use this named target-domain transfer hypothesis only; do not reopen a source-domain STOP gate.; Retain only a connected implementation plus source/tests for the transferred invariant; popularity and README claims are insufficient.; Do not search the originating vertical merely because its MASTER leader scored highly.; Reject forks/clones that add no independent implementation evidence.; If the coverage qualifier produces only shallow variants, record the no-find and do not lower the evidence bar.

### SLOT-08 — SEED:coverage:language-family-jvm:abstention-transfer
- Assignment ID: ASSIGN:51e2788d0136:slot-08
- Work kind/action: **coverage_gap / search**
- Score: **70.29** — {"base_priority": 69.0, "experiment_boost": 0, "strategy_allocation": 1.29}
- Strategy/objective: STRAT:capability-conjunction-search-claim-tracing / OBJ:independent-evaluation
- Capability/experiment: cross-domain
- Why now: Intersect exploration blind spot COV:language-family:jvm (Java / Kotlin: 1/3) with abstention-transfer, an authorized anchored search hypothesis. This is coverage correction tied to a valuable technical hypothesis, not diversity for its own sake.
- Next action: Run the bounded anchored transfer queries and inspect one connected implementation path.
- Acceptance target: One independent target-domain implementation with source/test evidence for: source span, selective prediction, review threshold
- Queries:
  - "mortgage" "extraction" "abstain" language:Java
  - "insurance" "source_span" "review" language:Java
  - "mortgage" "extraction" "abstain" language:Kotlin
  - "insurance" "source_span" "review" language:Kotlin
- Search surfaces: GitHub repository search, GitHub code search, GitHub code search, low-star/zero-star repository search, archived repository archaeology, author/org adjacency, dependency/consumer adjacency
- Verification gate: A transfer candidate must implement the invariant in executable code and tests; domain naming similarity is irrelevant. Prefer a different vertical or protocol family from the source repo. Coverage membership alone never raises evidence quality.
- Stop conditions: Use this named target-domain transfer hypothesis only; do not reopen a source-domain STOP gate.; Retain only a connected implementation plus source/tests for the transferred invariant; popularity and README claims are insufficient.; Do not search the originating vertical merely because its MASTER leader scored highly.; Reject forks/clones that add no independent implementation evidence.; If the coverage qualifier produces only shallow variants, record the no-find and do not lower the evidence bar.

### SLOT-09 — SEED:dna:gsa-gsa-acquisition-dfars
- Assignment ID: ASSIGN:51e2788d0136:slot-09
- Work kind/action: **positive_dna_transfer / search**
- Score: **73.21** — {"base_priority": 72.0, "experiment_boost": 0, "strategy_allocation": 1.21}
- Strategy/objective: STRAT:rule-period-authority-version-audit / OBJ:current-rule-authority
- Capability/experiment: cross-domain
- Why now: Transfer the load-bearing implementation DNA of MASTER leader GSA/GSA-Acquisition-DFARS into unrelated verticals. Why it wins: first-party structured supplement authority that directly closes a high-value CaptureBrief gap.
- Next action: Run the bounded anchored transfer queries and inspect one connected implementation path.
- Acceptance target: One independent target-domain implementation with source/test evidence for: effective rule version, historical evaluation, authority provenance
- Queries:
  - OpenFisca reforms parameter
  - "tax" "effective_date" path:tests
  - "benefits" "rule_version"
- Search surfaces: GitHub code search, low-star/zero-star repository search, archived repository archaeology, author/org adjacency, dependency/consumer adjacency
- Verification gate: A transfer candidate must implement the invariant in executable code and tests; domain naming similarity is irrelevant. Prefer a different vertical or protocol family from the source repo.
- Stop conditions: Use this named target-domain transfer hypothesis only; do not reopen a source-domain STOP gate.; Retain only a connected implementation plus source/tests for the transferred invariant; popularity and README claims are insufficient.; Do not search the originating vertical merely because its MASTER leader scored highly.; Reject forks/clones that add no independent implementation evidence.

### SLOT-10 — ADJ:distinctive-symbol:sandialabs-dreams
- Assignment ID: ASSIGN:51e2788d0136:slot-10
- Work kind/action: **adjacency / search**
- Score: **101.29** — {"base_priority": 100.0, "strategy_allocation": 1.29}
- Strategy/objective: STRAT:capability-conjunction-search-claim-tracing / OBJ:emergence-triangulation
- Capability/experiment: cross-domain
- Why now: sandialabs/DREAMS is a high-value root. Expand nearby while preserving the load-bearing invariant rather than cloning the product category.
- Acceptance target: Retain a neighbor only if it adds a new capability, stronger evidence, an independent implementation, a production descendant, a useful negative control, or a new experiment edge. Mere proximity is not value.
- Queries:
  - <distinctive_symbol>
  - <symbol_a> <symbol_b>
  - <schema_key> path:tests
- Search recipe:
  - Extract two to four distinctive class, function, config or schema symbols from load-bearing source and tests.
  - Search those symbols globally, including zero-star and archived repositories.
  - Separate exact copies from independent implementations; independent reimplementation is higher-value evidence.
- Verification gate: Retain a neighbor only if it adds a new capability, stronger evidence, an independent implementation, a production descendant, a useful negative control, or a new experiment edge. Mere proximity is not value.
- Stop conditions: Stop after three consecutive deep inspections produce only duplicates or clones with no evidence or capability delta.; Do not inspect accidental secrets or private data; quarantine metadata only.; Do not reopen a domain-specific STOP gate through adjacency.

### SLOT-11 — SEED:learn:acceptance-path-transition-inspection-rule-version-transfer
- Assignment ID: ASSIGN:51e2788d0136:slot-11
- Work kind/action: **learning_measurement / search**
- Score: **81.06** — {"base_priority": 79.5, "experiment_boost": 0, "strategy_allocation": 1.56}
- Strategy/objective: STRAT:acceptance-path-transition-inspection / OBJ:current-rule-authority
- Capability/experiment: cross-domain
- Why now: STRAT:acceptance-path-transition-inspection is a curriculum-ranked adaptive-learning measurement target (train_measurement). Train evidence: 4 runs / 10 deep; confirm evidence: 0 runs / 0 deep. Pair it with rule-version-transfer so the run measures a real bounded search task. The worker must not know or infer whether this run will later be train or confirm.
- Next action: Run the bounded anchored transfer queries and inspect one connected implementation path.
- Acceptance target: One independent target-domain implementation with source/test evidence for: effective rule version, historical evaluation, authority provenance
- Queries:
  - OpenFisca reforms parameter
  - "tax" "effective_date" path:tests
  - "benefits" "rule_version"
- Search surfaces: GitHub code search, low-star/zero-star repository search, archived repository archaeology, author/org adjacency, dependency/consumer adjacency
- Verification gate: A transfer candidate must implement the invariant in executable code and tests; domain naming similarity is irrelevant. Prefer a different vertical or protocol family from the source repo. Use the named strategy consistently enough to make the run comparable; record no-find as valid evidence.
- Stop conditions: Use this named target-domain transfer hypothesis only; do not reopen a source-domain STOP gate.; Retain only a connected implementation plus source/tests for the transferred invariant; popularity and README claims are insufficient.; Do not search the originating vertical merely because its MASTER leader scored highly.; Reject forks/clones that add no independent implementation evidence.; Do not turn a learning-measurement run into an unrestricted domain sweep.; A no-find result is valid data; do one materially different recall-rescue pass, then stop.; Never compute, request, infer, retry, release, or alter the work based on train/confirm partition membership.

### SLOT-12 — SEED:learn:bidirectional-money-evidence-invariant-tracing-promotion-control-transfer
- Assignment ID: ASSIGN:51e2788d0136:slot-12
- Work kind/action: **learning_measurement / search**
- Score: **60.57** — {"base_priority": 60.0, "experiment_boost": 0, "strategy_allocation": 0.57}
- Strategy/objective: STRAT:bidirectional-money-evidence-invariant-tracing / OBJ:runtime-side-effect
- Capability/experiment: cross-domain
- Why now: STRAT:bidirectional-money-evidence-invariant-tracing is a curriculum-ranked adaptive-learning measurement target (train_measurement). Train evidence: 0 runs / 0 deep; confirm evidence: 0 runs / 0 deep. Pair it with promotion-control-transfer so the run measures a real bounded search task. The worker must not know or infer whether this run will later be train or confirm.
- Next action: Run the bounded anchored transfer queries and inspect one connected implementation path.
- Acceptance target: One independent target-domain implementation with source/test evidence for: promotion authority, versioned candidate, rollback test
- Queries:
  - MLflow "alias" "rollback"
  - "model registry" "approval"
  - MLflow "champion" path:tests
- Search surfaces: GitHub code search, low-star/zero-star repository search, archived repository archaeology, author/org adjacency, dependency/consumer adjacency
- Verification gate: A transfer candidate must implement the invariant in executable code and tests; domain naming similarity is irrelevant. Prefer a different vertical or protocol family from the source repo. Use the named strategy consistently enough to make the run comparable; record no-find as valid evidence.
- Stop conditions: Use this named target-domain transfer hypothesis only; do not reopen a source-domain STOP gate.; Retain only a connected implementation plus source/tests for the transferred invariant; popularity and README claims are insufficient.; Do not search the originating vertical merely because its MASTER leader scored highly.; Reject forks/clones that add no independent implementation evidence.; Do not turn a learning-measurement run into an unrestricted domain sweep.; A no-find result is valid data; do one materially different recall-rescue pass, then stop.; Never compute, request, infer, retry, release, or alter the work based on train/confirm partition membership.

### SLOT-13 — Independent verification — EXP-007
- Assignment ID: ASSIGN:51e2788d0136:slot-13
- Work kind/action: **independent_verification / execute_fixture**
- Score: **90.80** — {"portfolio_priority_boost": 4, "status_boost": 0, "verification_base": 88}
- Strategy/objective: STRAT:evaluation-target-independence / OBJ:independent-evaluation
- Capability/experiment: CAP-013, CAP-017, EXP-007
- Why now: Attempt to falsify the experiment using an independent oracle/fixture/implementation and negative controls.
- Execution scope: READY — execute the Thermo metadata repair/replay and the pending physical-action branch.
- Next action: (1) patch/rebuild OpenTFRaw event lookup to use `entry.scan_event`, replay the exact fixture and add oracle-backed metadata/CV regressions; use Entab only to adjudicate remaining disagreement. (2) run the SiLA/Opentrons real-provider kill/restart matrix. Do not call the four-vendor normalization branch PASSED while Thermo metadata disagrees.
- Acceptance target: (1) patch/rebuild OpenTFRaw event lookup to use `entry.scan_event`, replay the exact fixture and add oracle-backed metadata/CV regressions; use Entab only to adjudicate remaining disagreement. (2) run the SiLA/Opentrons real-provider kill/restart matrix. Do not call the four-vendor normalization branch PASSED while Thermo metadata disagrees.
- Verification mode: experiment_falsification
- Independence requirements: Freeze the exact claim, fixture and inspected revision before comparison.; Use an independently sourced expected result or different implementation lineage.; Preserve PASS/DISAGREE/UNSUPPORTED/ORACLE_UNAVAILABLE separately; repeated discovery does not establish independent VERIFIED.
- Hypothesis: cross-vendor analytical files can be normalized only when independently decoded measurement and acquisition semantics agree before common normalization; consequential physical actions must retain one external effect identity across ambiguity and restart.
- Stop conditions: Execute the pinned Thermo RAW row before shared normalization; no converter discovery until it runs.; Execute the existing durable-provider ambiguity matrix before broad lab-orchestrator discovery.; Do not reuse the target system's own outputs as the sole oracle.; Preserve disagreements instead of forcing consensus.

### SLOT-14 — Rare / weird wildcard exploration
- Assignment ID: ASSIGN:51e2788d0136:slot-14
- Work kind/action: **wildcard / search**
- Score: **75.00** — {"protected_exploration_budget": 75}
- Strategy/objective: n/a / n/a
- Capability/experiment: cross-domain
- Why now: Preserve high-recall discovery for technologies the current capability graph cannot predict.
- Acceptance target: A concrete source/test finding outside the current ontology, or an honest no-find disposition.
- Search surfaces: zero-star and low-star repositories, archived repositories, obscure university/lab/government organizations, unusual protocol and hardware integrations
- Verification gate: Weirdness is only a discovery prior; retain only concrete technical evidence.
- Stop conditions: Do not chase credentials, private/confidential material or accidental secrets.; No padding: a no-find run is valid.
