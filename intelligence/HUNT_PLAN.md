# UNIFIED HUNT PLAN

Allocator generation: **ALLOCGEN:c080a1f0d909**
Portfolio policy: **PORTFOLIO:3f0ab6a3092f**

This is the current 14-slot work plan. Scores are scheduling priorities, not claims of repository or commercial value.

| Slot | Role | Score | Work | Capability | Experiment | Source |
|---|---|---:|---|---|---|---|
| SLOT-01 | experiment | 99.8 | EXP-002 — AP source-authority + reversible receipt-policy audit | CAP-002, CAP-007, CAP-008, CAP-016, CAP-019 | EXP-002 | EXP-002 |
| SLOT-02 | experiment | 97.5 | EXP-003 — Commission plan-to-bank acceptance test | CAP-002, CAP-006, CAP-007, CAP-016, CAP-018, CAP-019 | EXP-003 | EXP-003 |
| SLOT-03 | experiment | 97.2 | SEED:gap:cap-008 | CAP-008 | EXP-002 | SEED:gap:cap-008 |
| SLOT-04 | experiment | 97.2 | SEED:gap:cap-012 | CAP-012 | EXP-009 | SEED:gap:cap-012 |
| SLOT-05 | experiment | 96.9 | SEED:gap:cap-014 | CAP-014 | EXP-008 | SEED:gap:cap-014 |
| SLOT-06 | experiment | 94.5 | EXP-007 — Installed-base sequencing/lab handoff acceptance | CAP-013, CAP-017 | EXP-007 | EXP-007 |
| SLOT-07 | coverage | 88.2 | SEED:coverage:package-ecosystem-nuget:rule-version-transfer | — | — | SEED:coverage:package-ecosystem-nuget:rule-version-transfer |
| SLOT-08 | coverage | 77.4 | SEED:coverage:language-family-c-cpp:abstention-transfer | — | — | SEED:coverage:language-family-c-cpp:abstention-transfer |
| SLOT-09 | coverage | 76.9 | SEED:coverage:package-ecosystem-cargo:format-normalization-transfer | — | — | SEED:coverage:package-ecosystem-cargo:format-normalization-transfer |
| SLOT-10 | adjacency | 101.4 | ADJ:distinctive-symbol:sandialabs-dreams | — | — | ADJ:distinctive-symbol:sandialabs-dreams |
| SLOT-11 | adjacency | 101.4 | ADJ:distinctive-symbol:pedrocodesforcoffee-builder-api | — | — | ADJ:distinctive-symbol:pedrocodesforcoffee-builder-api |
| SLOT-12 | measurement | 63.7 | SEED:measure:cross-source-emergence-triangulation-abstention-transfer | — | — | SEED:measure:cross-source-emergence-triangulation-abstention-transfer |
| SLOT-13 | verification | 90.8 | Independent verification — EXP-007 | CAP-013, CAP-017 | EXP-007 | VERIFY:EXP-007 |
| SLOT-14 | wildcard | 75.0 | Rare / weird wildcard exploration | — | — | WILDCARD:rare-weird |

## Assignment packets

### SLOT-01 — EXP-002 — AP source-authority + reversible receipt-policy audit
- Assignment ID: ASSIGN:c080a1f0d909:slot-01
- Work kind/action: **experiment_execution / execute_fixture**
- Score: **99.75** — {"portfolio_priority_boost": 8, "queue_order_adjustment": -0.25, "readiness_base": 92}
- Strategy/objective: n/a / n/a
- Capability/experiment: CAP-002, CAP-007, CAP-008, CAP-016, CAP-019, EXP-002
- Why now: Experiment is READY and should be executed/falsified before searching for redundant components.
- Execution scope: READY.
- Next action: implement the ERP-neutral reversible-authority ledger plus effect-broker crash matrix. The remaining external gap is a real ERP-facing adapter that can prove NOT_APPLIED without treating eventual-consistency “not found yet” as permission to release or retry.
- Acceptance target: all planted cases detected; unsupported recovery = 0; explicit non-match blocks false merge; unavailable source cannot create missing-receipt/PO money; amount+quantity capacity is conserved through returns/credits/cancellation/re-receipt; crash/restart never creates a second logical counter-event; bitemporal replay reproduces what was known then and what became valid later.
- Hypothesis: explicit source observation, reviewed identity, policy-specific receipt authority, reversible line-level authority consumption and crash-safe external writeback can distinguish recoverable AP leakage from unresolved exceptions without false missing-receipt/PO dollars or duplicate counter-events.
- Success: all planted cases detected; unsupported recovery = 0; explicit non-match blocks false merge; unavailable source cannot create missing-receipt/PO money; amount+quantity capacity is conserved through returns/credits/cancellation/re-receipt; crash/restart never creates a second logical counter-event; bitemporal replay reproduces what was known then and what became valid later.
- Failure: universal `has_receipt`, any-return-means-authority-restored, source outage becomes negative evidence, ERP header/status copied as truth, same-product auto-assignment establishes ownership, implicit float/UoM rounding creates/destroys authority, exception dollars are labeled recovered, exception/timeout becomes NOT_APPLIED, or UNKNOWN frees reserved capacity / mints a fresh operation ID.
- Stop conditions: Execute the existing alias/non-match/merge/split corpus before seeking another identity engine.; Run the existing authority/admission matrix before further restore, OTA or attestation discovery.; Pin the official rule-pack version and authority before comparing existing validators; do not replace rule authority with another repository.; Run the existing crash/replay-expiry/finality matrix. Permit adapter search only for a separately named failed NOT_APPLIED proof gap.; Run synthetic transport/auth/partial-source failure cases before source-receipt discovery.; Do not broaden into generic discovery unless execution exposes a named technical gap.; READY scope authorizes the stated fixture/verification only; separately blocked commercial or customer proof remains external.

### SLOT-02 — EXP-003 — Commission plan-to-bank acceptance test
- Assignment ID: ASSIGN:c080a1f0d909:slot-02
- Work kind/action: **experiment_execution / execute_fixture**
- Score: **97.50** — {"portfolio_priority_boost": 6, "queue_order_adjustment": -0.5, "readiness_base": 92}
- Strategy/objective: n/a / n/a
- Capability/experiment: CAP-002, CAP-006, CAP-007, CAP-016, CAP-018, CAP-019, EXP-003
- Why now: Experiment is READY and should be executed/falsified before searching for redundant components.
- Execution scope: READY.
- Next action: execute the provider-neutral matrix. Resume search only if it exposes a concrete provider/reference->independent-bank/payroll or late-counter-event correlation gap.
- Acceptance target: unknown provider result stays pending and cannot retry; definite refusal alone releases; duplicate send impossible; provider success and final settlement distinct; only exact unique mapping inside verified coverage may establish settlement; later return/reversal exactly unwinds prior finality without deleting history or rerating original authority.
- Hypothesis: frozen entitlement plus provider state and independently observed bank/payroll state can detect payout errors without duplicate-send or false-finality risk, while ambiguous linkage and unavailable source windows remain non-final.
- Success: unknown provider result stays pending and cannot retry; definite refusal alone releases; duplicate send impossible; provider success and final settlement distinct; only exact unique mapping inside verified coverage may establish settlement; later return/reversal exactly unwinds prior finality without deleting history or rerating original authority.
- Failure: provider status establishes entitlement/finality; trace alone is finality; substring/fuzzy/amount-only/first-match becomes exact; cursor continuity is treated as completeness; ambiguous/unavailable bank evidence mutates realized money; return leaves prior payout economically final; or late re-payment reads current rate/commission instead of immutable event-time authority.
- Stop conditions: Execute the existing alias/non-match/merge/split corpus before seeking another identity engine.; Await actual authorized settlement/return evidence; repository discovery cannot establish realized recovery.; Run the existing authority/admission matrix before further restore, OTA or attestation discovery.; Run the existing crash/replay-expiry/finality matrix. Permit adapter search only for a separately named failed NOT_APPLIED proof gap.; Execute the post-success lost-webhook fixture; do not resume generic commission or payout-wrapper discovery.; Run synthetic transport/auth/partial-source failure cases before source-receipt discovery.; Do not broaden into generic discovery unless execution exposes a named technical gap.; READY scope authorizes the stated fixture/verification only; separately blocked commercial or customer proof remains external.

### SLOT-03 — SEED:gap:cap-008
- Assignment ID: ASSIGN:c080a1f0d909:slot-03
- Work kind/action: **capability_gap / verify_artifact**
- Score: **97.18** — {"base_priority": 88.0, "experiment_boost": 8, "strategy_allocation": 1.18}
- Strategy/objective: STRAT:rule-period-authority-version-audit / OBJ:current-rule-authority
- Capability/experiment: CAP-008, EXP-002
- Why now: CAP-008 is a current high-information gap (gap score 5, prior run attention 0). Saturation: INSUFFICIENT (+0 priority). Missing piece: official rule-pack/version authority must be pinned.
- Next action: run identical UBL/CII fixtures across independent validators and route disagreement to source review.
- Acceptance target: run identical UBL/CII fixtures across independent validators and route disagreement to source review.
- Verification gate: Record the exact fixture/artifact subject, independent expected result, observed result and blocker. Completion of research is not completion of the acceptance test.
- Stop conditions: Pin the official rule-pack version and authority before comparing existing validators; do not replace rule authority with another repository.; Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.

### SLOT-04 — SEED:gap:cap-012
- Assignment ID: ASSIGN:c080a1f0d909:slot-04
- Work kind/action: **capability_gap / execute_fixture**
- Score: **97.18** — {"base_priority": 88.0, "experiment_boost": 8, "strategy_allocation": 1.18}
- Strategy/objective: STRAT:rule-period-authority-version-audit / OBJ:completeness-proof
- Capability/experiment: CAP-012, EXP-009
- Why now: CAP-012 is a current high-information gap (gap score 5, prior run attention 0). Saturation: INSUFFICIENT (+0 priority). Missing piece: jurisdiction completeness/semantics vary.
- Next action: run three-jurisdiction source-field truth and source-outage benchmark.
- Acceptance target: run three-jurisdiction source-field truth and source-outage benchmark.
- Verification gate: Record the exact fixture/artifact subject, independent expected result, observed result and blocker. Completion of research is not completion of the acceptance test.
- Stop conditions: Freeze three-jurisdiction source-field truth and source-outage cases before more permit repository discovery.; Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.

### SLOT-05 — SEED:gap:cap-014
- Assignment ID: ASSIGN:c080a1f0d909:slot-05
- Work kind/action: **capability_gap / execute_fixture**
- Score: **96.94** — {"base_priority": 88.0, "experiment_boost": 8, "strategy_allocation": 0.94}
- Strategy/objective: STRAT:protocol-regression-archaeology-for-pre-fat-systems / OBJ:protocol-regression
- Capability/experiment: CAP-014, EXP-008
- Why now: CAP-014 is a current high-information gap (gap score 5, prior run attention 0). Saturation: INSUFFICIENT (+0 priority). Missing piece: standards/certification remain separate. Execute the frozen fixture with a neutral raw-HSMS harness that records every correlated message, maintains its own logical T3 clock and reads post-state independently; then run Dreamine and secsgem native clients only as a second requester-compatibility matrix. Seek a third engine only to adjudicate an observed endpoint disagreement..
- Next action: standards/certification remain separate. Execute the frozen fixture with a neutral raw-HSMS harness that records every correlated message, maintains its own logical T3 clock and reads post-state independently; then run Dreamine and secsgem native clients only as a second requester-compatibility matrix. Seek a third engine only to adjudicate an observed endpoint disagreement.
- Acceptance target: standards/certification remain separate. Execute the frozen fixture with a neutral raw-HSMS harness that records every correlated message, maintains its own logical T3 clock and reads post-state independently; then run Dreamine and secsgem native clients only as a second requester-compatibility matrix. Seek a third engine only to adjudicate an observed endpoint disagreement.
- Verification gate: Record the exact fixture/artifact subject, independent expected result, observed result and blocker. Completion of research is not completion of the acceptance test.
- Stop conditions: CAP-014 STOP: no third SECS/GEM engine until an actually executed endpoint disagreement needs adjudication. Run the neutral raw-HSMS fixture against both pinned endpoints first.; Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.

### SLOT-06 — EXP-007 — Installed-base sequencing/lab handoff acceptance
- Assignment ID: ASSIGN:c080a1f0d909:slot-06
- Work kind/action: **experiment_execution / execute_fixture**
- Score: **94.50** — {"portfolio_priority_boost": 4, "queue_order_adjustment": -1.5, "readiness_base": 92}
- Strategy/objective: n/a / n/a
- Capability/experiment: CAP-013, CAP-017, EXP-007
- Why now: Experiment is READY and should be executed/falsified before searching for redundant components.
- Execution scope: READY for rights-clean synthetic tests.
- Next action: execute two bounded subtests before more broad lab discovery: (1) run `MSV000094032/raw/Lee_CB_03.raw` through the pinned production Thermo decoder and `OpenTFRaw@63380...` with field-level disagreement ledger before normalization, retaining Entab as third challenger, and (2) run the SiLA/Opentrons real-provider ambiguity matrix with a controlled kill in the provider-accepted/before-local-receipt window and authoritative read-only recovery of the same effect after restart. Do not call the four-vendor branch PASSED until the Thermo row actually runs.
- Acceptance target: deterministic workflow/run linkage, independent sample-sheet validation, faithful multi-vendor measurement/provenance preservation, rejection of bad identities/transitions, explicit unknowns and replayable provenance; restart preserves the same effect identity/decision; pre-confirmation ambiguity cannot mint a fresh physical operation; APPLIED causes no reissue; unresolved remains blocked; replacement only follows authoritative NOT_APPLIED.
- Hypothesis: Clarity -> sample-sheet/run identity -> InterOp -> provenance can improve workflow evidence without sequence-content/PHI dependence; cross-vendor analytical files can be normalized with retained source/parser provenance; consequential physical actions must remain single-identity, fail-closed and non-redispatchable under ambiguous outcomes.
- Success: deterministic workflow/run linkage, independent sample-sheet validation, faithful multi-vendor measurement/provenance preservation, rejection of bad identities/transitions, explicit unknowns and replayable provenance; restart preserves the same effect identity/decision; pre-confirmation ambiguity cannot mint a fresh physical operation; APPLIED causes no reissue; unresolved remains blocked; replacement only follows authoritative NOT_APPLIED.
- Failure: normalized output silently drops required values/provenance or is marketed as vendor-certified without evidence; wrong run joined; missing evidence turns green; PHI becomes required; command-mutated local state is accepted as physical proof; process restart loses original identity; client intent is incorrectly assumed equal to server execution UUID; generic retry creates a new physical action while the old effect remains unresolved; receipt absence is treated as safe redispatch authority; or a memory-only dry-run provider is credited as authoritative physical reconciliation.
- Stop conditions: Execute the pinned Thermo RAW row before shared normalization; no converter discovery until it runs.; Execute the existing durable-provider ambiguity matrix before broad lab-orchestrator discovery.; Do not broaden into generic discovery unless execution exposes a named technical gap.; READY scope authorizes the stated fixture/verification only; separately blocked commercial or customer proof remains external.

### SLOT-07 — SEED:coverage:package-ecosystem-nuget:rule-version-transfer
- Assignment ID: ASSIGN:c080a1f0d909:slot-07
- Work kind/action: **coverage_gap / search**
- Score: **88.18** — {"base_priority": 87.0, "experiment_boost": 0, "strategy_allocation": 1.18}
- Strategy/objective: STRAT:rule-period-authority-version-audit / OBJ:current-rule-authority
- Capability/experiment: cross-domain
- Why now: Intersect exploration blind spot COV:package-ecosystem:nuget (.NET / NuGet: 0/3) with rule-version-transfer, an authorized anchored search hypothesis. This is coverage correction tied to a valuable technical hypothesis, not diversity for its own sake.
- Next action: Run the bounded anchored transfer queries and inspect one connected implementation path.
- Acceptance target: One independent target-domain implementation with source/test evidence for: effective rule version, historical evaluation, authority provenance
- Queries:
  - OpenFisca reforms parameter language:C#
  - "tax" "effective_date" path:tests language:C#
- Search surfaces: GitHub repository search, GitHub code search, GitHub code search, low-star/zero-star repository search, archived repository archaeology, author/org adjacency, dependency/consumer adjacency
- Verification gate: A transfer candidate must implement the invariant in executable code and tests; domain naming similarity is irrelevant. Prefer a different vertical or protocol family from the source repo. Coverage membership alone never raises evidence quality.
- Stop conditions: Use this named target-domain transfer hypothesis only; do not reopen a source-domain STOP gate.; Retain only a connected implementation plus source/tests for the transferred invariant; popularity and README claims are insufficient.; Do not search the originating vertical merely because its MASTER leader scored highly.; Reject forks/clones that add no independent implementation evidence.; If the coverage qualifier produces only shallow variants, record the no-find and do not lower the evidence bar.

### SLOT-08 — SEED:coverage:language-family-c-cpp:abstention-transfer
- Assignment ID: ASSIGN:c080a1f0d909:slot-08
- Work kind/action: **coverage_gap / search**
- Score: **77.39** — {"base_priority": 76.0, "experiment_boost": 0, "strategy_allocation": 1.39}
- Strategy/objective: STRAT:capability-conjunction-search-claim-tracing / OBJ:independent-evaluation
- Capability/experiment: cross-domain
- Why now: Intersect exploration blind spot COV:language-family:c-cpp (C / C++: 1/3) with abstention-transfer, an authorized anchored search hypothesis. This is coverage correction tied to a valuable technical hypothesis, not diversity for its own sake.
- Next action: Run the bounded anchored transfer queries and inspect one connected implementation path.
- Acceptance target: One independent target-domain implementation with source/test evidence for: source span, selective prediction, review threshold
- Queries:
  - "mortgage" "extraction" "abstain" language:C
  - "insurance" "source_span" "review" language:C
  - "mortgage" "extraction" "abstain" language:C++
  - "insurance" "source_span" "review" language:C++
- Search surfaces: GitHub repository search, GitHub code search, GitHub code search, low-star/zero-star repository search, archived repository archaeology, author/org adjacency, dependency/consumer adjacency
- Verification gate: A transfer candidate must implement the invariant in executable code and tests; domain naming similarity is irrelevant. Prefer a different vertical or protocol family from the source repo. Coverage membership alone never raises evidence quality.
- Stop conditions: Use this named target-domain transfer hypothesis only; do not reopen a source-domain STOP gate.; Retain only a connected implementation plus source/tests for the transferred invariant; popularity and README claims are insufficient.; Do not search the originating vertical merely because its MASTER leader scored highly.; Reject forks/clones that add no independent implementation evidence.; If the coverage qualifier produces only shallow variants, record the no-find and do not lower the evidence bar.

### SLOT-09 — SEED:coverage:package-ecosystem-cargo:format-normalization-transfer
- Assignment ID: ASSIGN:c080a1f0d909:slot-09
- Work kind/action: **coverage_gap / search**
- Score: **76.94** — {"base_priority": 76.0, "experiment_boost": 0, "strategy_allocation": 0.94}
- Strategy/objective: STRAT:protocol-regression-archaeology-for-pre-fat-systems / OBJ:protocol-regression
- Capability/experiment: cross-domain
- Why now: Intersect exploration blind spot COV:package-ecosystem:cargo (Rust / Cargo: 1/3) with format-normalization-transfer, an authorized anchored search hypothesis. This is coverage correction tied to a valuable technical hypothesis, not diversity for its own sake.
- Next action: Run the bounded anchored transfer queries and inspect one connected implementation path.
- Acceptance target: One independent target-domain implementation with source/test evidence for: raw-source identity, metadata preservation, numeric fixture
- Queries:
  - DICOM "roundtrip" language:Rust
  - "ECG" "parser" "fixtures" language:Rust
- Search surfaces: GitHub repository search, GitHub code search, GitHub code search, low-star/zero-star repository search, archived repository archaeology, author/org adjacency, dependency/consumer adjacency
- Verification gate: A transfer candidate must implement the invariant in executable code and tests; domain naming similarity is irrelevant. Prefer a different vertical or protocol family from the source repo. Coverage membership alone never raises evidence quality.
- Stop conditions: Use this named target-domain transfer hypothesis only; do not reopen a source-domain STOP gate.; Retain only a connected implementation plus source/tests for the transferred invariant; popularity and README claims are insufficient.; Do not search the originating vertical merely because its MASTER leader scored highly.; Reject forks/clones that add no independent implementation evidence.; If the coverage qualifier produces only shallow variants, record the no-find and do not lower the evidence bar.

### SLOT-10 — ADJ:distinctive-symbol:sandialabs-dreams
- Assignment ID: ASSIGN:c080a1f0d909:slot-10
- Work kind/action: **adjacency / search**
- Score: **101.39** — {"base_priority": 100.0, "strategy_allocation": 1.39}
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

### SLOT-11 — ADJ:distinctive-symbol:pedrocodesforcoffee-builder-api
- Assignment ID: ASSIGN:c080a1f0d909:slot-11
- Work kind/action: **adjacency / search**
- Score: **101.39** — {"base_priority": 100.0, "strategy_allocation": 1.39}
- Strategy/objective: STRAT:capability-conjunction-search-claim-tracing / OBJ:emergence-triangulation
- Capability/experiment: cross-domain
- Why now: pedrocodesforcoffee/builder-api is a high-value root. Expand nearby while preserving the load-bearing invariant rather than cloning the product category.
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

### SLOT-12 — SEED:measure:cross-source-emergence-triangulation-abstention-transfer
- Assignment ID: ASSIGN:c080a1f0d909:slot-12
- Work kind/action: **strategy_measurement / search**
- Score: **63.66** — {"base_priority": 63.0, "experiment_boost": 0, "strategy_allocation": 0.66}
- Strategy/objective: STRAT:cross-source-emergence-triangulation / OBJ:independent-evaluation
- Capability/experiment: cross-domain
- Why now: STRAT:cross-source-emergence-triangulation has no measured runs but receives exploration allocation. Pair it with abstention-transfer so the hunt searches a real gap and reduces strategy measurement debt.
- Next action: Run the bounded anchored transfer queries and inspect one connected implementation path.
- Acceptance target: One independent target-domain implementation with source/test evidence for: source span, selective prediction, review threshold
- Queries:
  - "mortgage" "extraction" "abstain"
  - "insurance" "source_span" "review"
  - "mortgage" "confidence" path:tests
- Search surfaces: GitHub code search, low-star/zero-star repository search, archived repository archaeology, author/org adjacency, dependency/consumer adjacency
- Verification gate: A transfer candidate must implement the invariant in executable code and tests; domain naming similarity is irrelevant. Prefer a different vertical or protocol family from the source repo. Use the named strategy consistently enough to make the run comparable.
- Stop conditions: Use this named target-domain transfer hypothesis only; do not reopen a source-domain STOP gate.; Retain only a connected implementation plus source/tests for the transferred invariant; popularity and README claims are insufficient.; Do not search the originating vertical merely because its MASTER leader scored highly.; Reject forks/clones that add no independent implementation evidence.; Do not turn a measurement run into an unrestricted domain sweep.; A no-find result is valid data; do one recall-rescue pass, then stop.

### SLOT-13 — Independent verification — EXP-007
- Assignment ID: ASSIGN:c080a1f0d909:slot-13
- Work kind/action: **independent_verification / execute_fixture**
- Score: **90.80** — {"portfolio_priority_boost": 4, "status_boost": 0, "verification_base": 88}
- Strategy/objective: STRAT:evaluation-target-independence / OBJ:independent-evaluation
- Capability/experiment: CAP-013, CAP-017, EXP-007
- Why now: Attempt to falsify the experiment using an independent oracle/fixture/implementation and negative controls.
- Execution scope: READY for rights-clean synthetic tests.
- Next action: execute two bounded subtests before more broad lab discovery: (1) run `MSV000094032/raw/Lee_CB_03.raw` through the pinned production Thermo decoder and `OpenTFRaw@63380...` with field-level disagreement ledger before normalization, retaining Entab as third challenger, and (2) run the SiLA/Opentrons real-provider ambiguity matrix with a controlled kill in the provider-accepted/before-local-receipt window and authoritative read-only recovery of the same effect after restart. Do not call the four-vendor branch PASSED until the Thermo row actually runs.
- Acceptance target: deterministic workflow/run linkage, independent sample-sheet validation, faithful multi-vendor measurement/provenance preservation, rejection of bad identities/transitions, explicit unknowns and replayable provenance; restart preserves the same effect identity/decision; pre-confirmation ambiguity cannot mint a fresh physical operation; APPLIED causes no reissue; unresolved remains blocked; replacement only follows authoritative NOT_APPLIED.
- Verification mode: experiment_falsification
- Independence requirements: Freeze the exact claim, fixture and inspected revision before comparison.; Use an independently sourced expected result or different implementation lineage.; Preserve PASS/DISAGREE/UNSUPPORTED/ORACLE_UNAVAILABLE separately; repeated discovery does not establish independent VERIFIED.
- Hypothesis: Clarity -> sample-sheet/run identity -> InterOp -> provenance can improve workflow evidence without sequence-content/PHI dependence; cross-vendor analytical files can be normalized with retained source/parser provenance; consequential physical actions must remain single-identity, fail-closed and non-redispatchable under ambiguous outcomes.
- Success: deterministic workflow/run linkage, independent sample-sheet validation, faithful multi-vendor measurement/provenance preservation, rejection of bad identities/transitions, explicit unknowns and replayable provenance; restart preserves the same effect identity/decision; pre-confirmation ambiguity cannot mint a fresh physical operation; APPLIED causes no reissue; unresolved remains blocked; replacement only follows authoritative NOT_APPLIED.
- Failure: normalized output silently drops required values/provenance or is marketed as vendor-certified without evidence; wrong run joined; missing evidence turns green; PHI becomes required; command-mutated local state is accepted as physical proof; process restart loses original identity; client intent is incorrectly assumed equal to server execution UUID; generic retry creates a new physical action while the old effect remains unresolved; receipt absence is treated as safe redispatch authority; or a memory-only dry-run provider is credited as authoritative physical reconciliation.
- Stop conditions: Execute the pinned Thermo RAW row before shared normalization; no converter discovery until it runs.; Execute the existing durable-provider ambiguity matrix before broad lab-orchestrator discovery.; Do not reuse the target system's own outputs as the sole oracle.; Preserve disagreements instead of forcing consensus.

### SLOT-14 — Rare / weird wildcard exploration
- Assignment ID: ASSIGN:c080a1f0d909:slot-14
- Work kind/action: **wildcard / search**
- Score: **75.00** — {"protected_exploration_budget": 75}
- Strategy/objective: n/a / n/a
- Capability/experiment: cross-domain
- Why now: Preserve high-recall discovery for technologies the current capability graph cannot predict.
- Acceptance target: A concrete source/test finding outside the current ontology, or an honest no-find disposition.
- Search surfaces: zero-star and low-star repositories, archived repositories, obscure university/lab/government organizations, unusual protocol and hardware integrations
- Verification gate: Weirdness is only a discovery prior; retain only concrete technical evidence.
- Stop conditions: Do not chase credentials, private/confidential material or accidental secrets.; No padding: a no-find run is valid.
