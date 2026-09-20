# UNIFIED HUNT PLAN

Allocator generation: **ALLOCGEN:51522654b284**
Portfolio policy: **PORTFOLIO:d3b1e808cccc**

This is the current 14-slot work plan. Scores are scheduling priorities, not claims of repository or commercial value.

| Slot | Role | Score | Work | Capability | Experiment | Source |
|---|---|---:|---|---|---|---|
| SLOT-01 | experiment | 97.5 | SEED:gap:cap-002 | CAP-002 | EXP-002, EXP-003, EXP-006, EXP-009 | SEED:gap:cap-002 |
| SLOT-02 | experiment | 97.0 | SEED:gap:cap-014 | CAP-014 | EXP-008 | SEED:gap:cap-014 |
| SLOT-03 | experiment | 90.7 | SEED:gap:cap-009 | CAP-009 | — | SEED:gap:cap-009 |
| SLOT-04 | experiment | 88.9 | SEED:gap:cap-015 | CAP-015 | EXP-012 | SEED:gap:cap-015 |
| SLOT-05 | experiment | 87.7 | SEED:gap:cap-001 | CAP-001 | EXP-001, EXP-005, EXP-011 | SEED:gap:cap-001 |
| SLOT-06 | experiment | 80.9 | SEED:gap:cap-006 | CAP-006 | EXP-010 | SEED:gap:cap-006 |
| SLOT-07 | coverage | 93.5 | SEED:coverage:language-family-c-cpp:cap-002 | CAP-002 | EXP-002, EXP-003, EXP-006, EXP-009 | SEED:coverage:language-family-c-cpp:cap-002 |
| SLOT-08 | coverage | 92.7 | SEED:coverage:package-ecosystem-nuget:cap-009 | CAP-009 | — | SEED:coverage:package-ecosystem-nuget:cap-009 |
| SLOT-09 | coverage | 85.0 | SEED:coverage:language-family-dotnet:cap-014 | CAP-014 | EXP-008 | SEED:coverage:language-family-dotnet:cap-014 |
| SLOT-10 | adjacency | 101.5 | ADJ:distinctive-symbol:sandialabs-dreams | — | — | ADJ:distinctive-symbol:sandialabs-dreams |
| SLOT-11 | adjacency | 92.7 | ADJ:contributor-lineage:gsa-gsa-acquisition-dfars | — | — | ADJ:contributor-lineage:gsa-gsa-acquisition-dfars |
| SLOT-12 | measurement | 63.6 | SEED:measure:decision-claim-runtime-side-effect-trace-cap-008 | CAP-008 | — | SEED:measure:decision-claim-runtime-side-effect-trace-cap-008 |
| SLOT-13 | verification | 88.0 | Independent verification — SEED:coverage:package-ecosystem-nuget:cap-009 | — | — | VERIFY:SEED:coverage:package-ecosystem-nuget:cap-009 |
| SLOT-14 | wildcard | 75.0 | Rare / weird wildcard exploration | — | — | WILDCARD:rare-weird |

## Assignment packets

### SLOT-01 — SEED:gap:cap-002
- Assignment ID: ASSIGN:51522654b284:slot-01
- Work kind: **capability_gap**
- Score: **97.50** — {"base_priority": 88.0, "experiment_boost": 8, "strategy_allocation": 1.5}
- Strategy/objective: STRAT:capability-conjunction-search-claim-tracing / OBJ:independent-evaluation
- Capability/experiment: CAP-002, EXP-002, EXP-003, EXP-006, EXP-009
- Why now: CAP-002 is a current high-information gap (gap score 5, prior run attention 0). Saturation: INSUFFICIENT (+0 priority). Missing piece: datasets/customer identities separate.
- Queries:
  - evidence deterministic replay
  - evidence replay path:tests
  - evidence deterministic audit replay
- Search surfaces: GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.

### SLOT-02 — SEED:gap:cap-014
- Assignment ID: ASSIGN:51522654b284:slot-02
- Work kind: **capability_gap**
- Score: **96.99** — {"base_priority": 88.0, "experiment_boost": 8, "strategy_allocation": 0.99}
- Strategy/objective: STRAT:protocol-regression-archaeology-for-pre-fat-systems / OBJ:protocol-regression
- Capability/experiment: CAP-014, EXP-008
- Why now: CAP-014 is a current high-information gap (gap score 5, prior run attention 0). Saturation: INSUFFICIENT (+0 priority). Missing piece: standards/certification remain separate. Execute the frozen fixture with a neutral raw-HSMS harness that records every correlated message, maintains its own logical T3 clock and reads post-state independently; then run Dreamine and secsgem native clients only as a second requester-compatibility matrix. Seek a third engine only to adjudicate an observed endpoint disagreement..
- Queries:
  - independent adjudicate certification
  - independent certification path:tests
  - independent adjudicate audit replay
- Search surfaces: GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.

### SLOT-03 — SEED:gap:cap-009
- Assignment ID: ASSIGN:51522654b284:slot-03
- Work kind: **capability_gap**
- Score: **90.65** — {"base_priority": 90.0, "experiment_boost": 0, "strategy_allocation": 0.65}
- Strategy/objective: STRAT:rule-period-authority-version-audit / OBJ:current-rule-authority
- Capability/experiment: CAP-009
- Why now: CAP-009 is a current high-information gap (gap score 7, prior run attention 0). Saturation: INSUFFICIENT (+0 priority). Missing piece: labor/domain rules remain external.
- Queries:
  - deterministic "hard lock" against
  - deterministic against path:tests
  - deterministic "hard lock" audit replay
- Search surfaces: GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.

### SLOT-04 — SEED:gap:cap-015
- Assignment ID: ASSIGN:51522654b284:slot-04
- Work kind: **capability_gap**
- Score: **88.94** — {"base_priority": 79.0, "experiment_boost": 8, "strategy_allocation": 1.94}
- Strategy/objective: STRAT:acceptance-path-transition-inspection / OBJ:ambiguity-reconciliation
- Capability/experiment: CAP-015, EXP-012
- Why now: CAP-015 is a current high-information gap (gap score 4, prior run attention 2). Saturation: INSUFFICIENT (+0 priority). Missing piece: the Mendeley **outer package** hash is not the embedded USECPO source hash. Extract the public package manifest, read the exact USECPO source URL/release/size/SHA row, compare it with direct first-party OEDI bytes or a first-party published digest, and keep `UNKNOWN/MISMATCH` hard-fail semantics. Byte-level v2 headers/timezone/sentinels/thresholds/event-id namespace also remain to be confirmed from the official artifact..
- Queries:
  - immutable unknown semantic
  - immutable semantic path:tests
  - immutable unknown audit replay
- Search surfaces: GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.

### SLOT-05 — SEED:gap:cap-001
- Assignment ID: ASSIGN:51522654b284:slot-05
- Work kind: **capability_gap**
- Score: **87.65** — {"base_priority": 79.0, "experiment_boost": 8, "strategy_allocation": 0.65}
- Strategy/objective: STRAT:rule-period-authority-version-audit / OBJ:authority-lineage
- Capability/experiment: CAP-001, EXP-001, EXP-005, EXP-011
- Why now: CAP-001 is a current high-information gap (gap score 4, prior run attention 2). Saturation: INSUFFICIENT (+0 priority). Missing piece: domain calibration and contractual/legal authority remain external.
- Queries:
  - review ambiguity calibration
  - review calibration path:tests
  - review ambiguity audit replay
- Search surfaces: GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.

### SLOT-06 — SEED:gap:cap-006
- Assignment ID: ASSIGN:51522654b284:slot-06
- Work kind: **capability_gap**
- Score: **80.94** — {"base_priority": 71.0, "experiment_boost": 8, "strategy_allocation": 1.94}
- Strategy/objective: STRAT:acceptance-path-transition-inspection / OBJ:exactly-once-settlement
- Capability/experiment: CAP-006, EXP-010
- Why now: CAP-006 is a current high-information gap (gap score 2, prior run attention 1). Saturation: INSUFFICIENT (+0 priority). Missing piece: realized dollars require external outcome evidence.
- Queries:
  - reversal evidence one-use
  - reversal one-use path:tests
  - reversal evidence audit replay
- Search surfaces: GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.

### SLOT-07 — SEED:coverage:language-family-c-cpp:cap-002
- Assignment ID: ASSIGN:51522654b284:slot-07
- Work kind: **coverage_gap**
- Score: **93.50** — {"base_priority": 84.0, "experiment_boost": 8, "strategy_allocation": 1.5}
- Strategy/objective: STRAT:capability-conjunction-search-claim-tracing / OBJ:independent-evaluation
- Capability/experiment: CAP-002, EXP-002, EXP-003, EXP-006, EXP-009
- Why now: Intersect exploration blind spot COV:language-family:c-cpp (C / C++: 1/3) with CAP-002, an active high-value capability gap. This is coverage correction tied to a valuable technical hypothesis, not diversity for its own sake.
- Queries:
  - evidence deterministic replay language:C
  - evidence replay path:tests language:C
  - evidence deterministic replay language:C++
  - evidence replay path:tests language:C++
- Search surfaces: GitHub repository search, GitHub code search, GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough. Coverage membership alone never raises evidence quality.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.; If the coverage qualifier produces only shallow variants, record the no-find and do not lower the evidence bar.

### SLOT-08 — SEED:coverage:package-ecosystem-nuget:cap-009
- Assignment ID: ASSIGN:51522654b284:slot-08
- Work kind: **coverage_gap**
- Score: **92.65** — {"base_priority": 92.0, "experiment_boost": 0, "strategy_allocation": 0.65}
- Strategy/objective: STRAT:rule-period-authority-version-audit / OBJ:current-rule-authority
- Capability/experiment: CAP-009
- Why now: Intersect exploration blind spot COV:package-ecosystem:nuget (.NET / NuGet: 0/3) with CAP-009, an active high-value capability gap. This is coverage correction tied to a valuable technical hypothesis, not diversity for its own sake.
- Queries:
  - deterministic "hard lock" against language:C#
  - deterministic against path:tests language:C#
- Search surfaces: GitHub repository search, GitHub code search, GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough. Coverage membership alone never raises evidence quality.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.; If the coverage qualifier produces only shallow variants, record the no-find and do not lower the evidence bar.

### SLOT-09 — SEED:coverage:language-family-dotnet:cap-014
- Assignment ID: ASSIGN:51522654b284:slot-09
- Work kind: **coverage_gap**
- Score: **84.99** — {"base_priority": 76.0, "experiment_boost": 8, "strategy_allocation": 0.99}
- Strategy/objective: STRAT:protocol-regression-archaeology-for-pre-fat-systems / OBJ:protocol-regression
- Capability/experiment: CAP-014, EXP-008
- Why now: Intersect exploration blind spot COV:language-family:dotnet (C# / .NET: 1/3) with CAP-014, an active high-value capability gap. This is coverage correction tied to a valuable technical hypothesis, not diversity for its own sake.
- Queries:
  - independent adjudicate certification language:C#
  - independent certification path:tests language:C#
- Search surfaces: GitHub repository search, GitHub code search, GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough. Coverage membership alone never raises evidence quality.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.; If the coverage qualifier produces only shallow variants, record the no-find and do not lower the evidence bar.

### SLOT-10 — ADJ:distinctive-symbol:sandialabs-dreams
- Assignment ID: ASSIGN:51522654b284:slot-10
- Work kind: **adjacency**
- Score: **101.50** — {"base_priority": 100.0, "strategy_allocation": 1.5}
- Strategy/objective: STRAT:capability-conjunction-search-claim-tracing / OBJ:emergence-triangulation
- Capability/experiment: cross-domain
- Why now: sandialabs/DREAMS is a high-value root. Expand nearby while preserving the load-bearing invariant rather than cloning the product category.
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

### SLOT-11 — ADJ:contributor-lineage:gsa-gsa-acquisition-dfars
- Assignment ID: ASSIGN:51522654b284:slot-11
- Work kind: **adjacency**
- Score: **92.65** — {"base_priority": 92.0, "strategy_allocation": 0.65}
- Strategy/objective: STRAT:paper-research-artifact-production-descendant / OBJ:research-lineage
- Capability/experiment: cross-domain
- Why now: GSA/GSA-Acquisition-DFARS is a high-value root. Expand nearby while preserving the load-bearing invariant rather than cloning the product category.
- Queries:
  - maintainer repositories for GSA/GSA-Acquisition-DFARS
  - authority user:<maintainer>
  - authority org:<maintainer-org>
- Search recipe:
  - Identify maintainers responsible for load-bearing files or architecture commits.
  - Search their other repositories and later organizations for generalized or productionized descendants.
  - Require source-level invariant continuity before calling a project a descendant.
- Verification gate: Retain a neighbor only if it adds a new capability, stronger evidence, an independent implementation, a production descendant, a useful negative control, or a new experiment edge. Mere proximity is not value.
- Stop conditions: Stop after three consecutive deep inspections produce only duplicates or clones with no evidence or capability delta.; Do not inspect accidental secrets or private data; quarantine metadata only.; Do not reopen a domain-specific STOP gate through adjacency.

### SLOT-12 — SEED:measure:decision-claim-runtime-side-effect-trace-cap-008
- Assignment ID: ASSIGN:51522654b284:slot-12
- Work kind: **strategy_measurement**
- Score: **63.65** — {"base_priority": 63.0, "experiment_boost": 0, "strategy_allocation": 0.65}
- Strategy/objective: STRAT:decision-claim-runtime-side-effect-trace / OBJ:current-rule-authority
- Capability/experiment: CAP-008
- Why now: STRAT:decision-claim-runtime-side-effect-trace has no measured runs but receives exploration allocation. Pair it with CAP-008 so the hunt searches a real gap and reduces strategy measurement debt.
- Queries:
  - review semantic authority
  - review authority path:tests
  - review semantic audit replay
- Search surfaces: GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Use the named strategy consistently enough to make the run comparable, while preserving the same evidence bar as ordinary discovery.
- Stop conditions: Do not turn a measurement run into an unrestricted domain sweep.; A no-find result is valid data; do one recall-rescue pass, then stop.

### SLOT-13 — Independent verification — SEED:coverage:package-ecosystem-nuget:cap-009
- Assignment ID: ASSIGN:51522654b284:slot-13
- Work kind: **independent_verification**
- Score: **88.00** — {"fallback_target": "top_active_search_hypothesis", "verification_base": 88}
- Strategy/objective: STRAT:evaluation-target-independence / OBJ:independent-evaluation
- Capability/experiment: cross-domain
- Why now: No READY/RUNNING experiment currently needs a dedicated verifier, so use reserved verification capacity to independently challenge the highest-ranked active search hypothesis before it becomes accepted positive training.
- Queries:
  - deterministic "hard lock" against language:C#
  - deterministic against path:tests language:C#
- Search surfaces: GitHub repository search, GitHub code search, GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Use an independent implementation, first-party authority, hand-authored fixture, negative control or contradictory source. Do not count the target repository's own claims as independent proof.
- Stop conditions: Do not duplicate the discovery agent's inspection path.; Preserve disagreement and uncertainty rather than forcing a PASS.

### SLOT-14 — Rare / weird wildcard exploration
- Assignment ID: ASSIGN:51522654b284:slot-14
- Work kind: **wildcard**
- Score: **75.00** — {"protected_exploration_budget": 75}
- Strategy/objective: n/a / n/a
- Capability/experiment: cross-domain
- Why now: Preserve high-recall discovery for technologies the current capability graph cannot predict.
- Search surfaces: zero-star and low-star repositories, archived repositories, obscure university/lab/government organizations, unusual protocol and hardware integrations
- Verification gate: Weirdness is only a discovery prior; retain only concrete technical evidence.
- Stop conditions: Do not chase credentials, private/confidential material or accidental secrets.; No padding: a no-find run is valid.
