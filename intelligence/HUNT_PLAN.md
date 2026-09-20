# UNIFIED HUNT PLAN

Allocator generation: **ALLOCGEN:be768c686587**
Portfolio policy: **PORTFOLIO:3f0ab6a3092f**

This is the current 14-slot work plan. Scores are scheduling priorities, not claims of repository or commercial value.

| Slot | Role | Score | Work | Capability | Experiment | Source |
|---|---|---:|---|---|---|---|
| SLOT-01 | experiment | 97.4 | SEED:gap:cap-002 | CAP-002 | EXP-002, EXP-003, EXP-006, EXP-009 | SEED:gap:cap-002 |
| SLOT-02 | experiment | 96.9 | SEED:gap:cap-014 | CAP-014 | EXP-008 | SEED:gap:cap-014 |
| SLOT-03 | experiment | 88.2 | SEED:gap:cap-001 | CAP-001 | EXP-001, EXP-005, EXP-011 | SEED:gap:cap-001 |
| SLOT-04 | experiment | 88.1 | SEED:gap:cap-015 | CAP-015 | EXP-012 | SEED:gap:cap-015 |
| SLOT-05 | experiment | 81.2 | SEED:dna:gsa-gsa-acquisition-dfars | — | — | SEED:dna:gsa-gsa-acquisition-dfars |
| SLOT-06 | experiment | 81.2 | SEED:gap:cap-008 | CAP-008 | — | SEED:gap:cap-008 |
| SLOT-07 | coverage | 101.4 | SEED:coverage:package-ecosystem-nuget:cap-002 | CAP-002 | EXP-002, EXP-003, EXP-006, EXP-009 | SEED:coverage:package-ecosystem-nuget:cap-002 |
| SLOT-08 | coverage | 92.9 | SEED:coverage:package-ecosystem-cargo:cap-014 | CAP-014 | EXP-008 | SEED:coverage:package-ecosystem-cargo:cap-014 |
| SLOT-09 | coverage | 80.4 | SEED:dna:gridappsd-cimhub | — | — | SEED:dna:gridappsd-cimhub |
| SLOT-10 | adjacency | 92.7 | ADJ:contributor-lineage:gsa-gsa-acquisition-dfars | — | — | ADJ:contributor-lineage:gsa-gsa-acquisition-dfars |
| SLOT-11 | adjacency | 91.7 | ADJ:contributor-lineage:kodekinetics79-opstrax-enterprise-build | — | — | ADJ:contributor-lineage:kodekinetics79-opstrax-enterprise-build |
| SLOT-12 | measurement | 63.7 | SEED:measure:cross-source-emergence-triangulation-cap-008 | CAP-008 | — | SEED:measure:cross-source-emergence-triangulation-cap-008 |
| SLOT-13 | verification | 88.0 | Independent verification — SEED:coverage:package-ecosystem-nuget:cap-002 | — | — | VERIFY:SEED:coverage:package-ecosystem-nuget:cap-002 |
| SLOT-14 | wildcard | 75.0 | Rare / weird wildcard exploration | — | — | WILDCARD:rare-weird |

## Assignment packets

### SLOT-01 — SEED:gap:cap-002
- Assignment ID: ASSIGN:be768c686587:slot-01
- Work kind: **capability_gap**
- Score: **97.39** — {"base_priority": 88.0, "experiment_boost": 8, "strategy_allocation": 1.39}
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
- Assignment ID: ASSIGN:be768c686587:slot-02
- Work kind: **capability_gap**
- Score: **96.94** — {"base_priority": 88.0, "experiment_boost": 8, "strategy_allocation": 0.94}
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

### SLOT-03 — SEED:gap:cap-001
- Assignment ID: ASSIGN:be768c686587:slot-03
- Work kind: **capability_gap**
- Score: **88.18** — {"base_priority": 79.0, "experiment_boost": 8, "strategy_allocation": 1.18}
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

### SLOT-04 — SEED:gap:cap-015
- Assignment ID: ASSIGN:be768c686587:slot-04
- Work kind: **capability_gap**
- Score: **88.06** — {"base_priority": 79.0, "experiment_boost": 8, "strategy_allocation": 1.06}
- Strategy/objective: STRAT:fail-open-boundary-archaeology / OBJ:completeness-proof
- Capability/experiment: CAP-015, EXP-012
- Why now: CAP-015 is a current high-information gap (gap score 4, prior run attention 2). Saturation: INSUFFICIENT (+0 priority). Missing piece: first-party OEDI ZIP digest/bytes remain unresolved in the current evidence chain. Verify the current first-party artifact against the external expected digest, byte-inspect source schema/time/null semantics, then freeze the composite-event + unique-spell evaluator manifest before running policy scores..
- Queries:
  - immutable evidence schema
  - immutable schema path:tests
  - immutable evidence audit replay
- Search surfaces: GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.

### SLOT-05 — SEED:dna:gsa-gsa-acquisition-dfars
- Assignment ID: ASSIGN:be768c686587:slot-05
- Work kind: **positive_dna_transfer**
- Score: **81.18** — {"base_priority": 80.0, "experiment_boost": 0, "strategy_allocation": 1.18}
- Strategy/objective: STRAT:rule-period-authority-version-audit / OBJ:authority-lineage
- Capability/experiment: cross-domain
- Why now: Transfer the load-bearing implementation DNA of MASTER leader GSA/GSA-Acquisition-DFARS into unrelated verticals. Why it wins: first-party structured supplement authority that directly closes a high-value CaptureBrief gap.
- Queries:
  - authority first-party artifacts
  - authority artifacts path:tests
  - authority first-party audit replay
- Search surfaces: GitHub code search, low-star/zero-star repository search, archived repository archaeology, author/org adjacency, dependency/consumer adjacency
- Verification gate: A transfer candidate must implement the invariant in executable code and tests; domain naming similarity is irrelevant. Prefer a different vertical or protocol family from the source repo.
- Stop conditions: Do not search the originating vertical merely because its MASTER leader scored highly.; Reject forks/clones that add no independent implementation evidence.

### SLOT-06 — SEED:gap:cap-008
- Assignment ID: ASSIGN:be768c686587:slot-06
- Work kind: **capability_gap**
- Score: **81.18** — {"base_priority": 80.0, "experiment_boost": 0, "strategy_allocation": 1.18}
- Strategy/objective: STRAT:rule-period-authority-version-audit / OBJ:current-rule-authority
- Capability/experiment: CAP-008
- Why now: CAP-008 is a current high-information gap (gap score 5, prior run attention 0). Saturation: INSUFFICIENT (+0 priority). Missing piece: official rule-pack/version authority must be pinned.
- Queries:
  - review semantic authority
  - review authority path:tests
  - review semantic audit replay
- Search surfaces: GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.

### SLOT-07 — SEED:coverage:package-ecosystem-nuget:cap-002
- Assignment ID: ASSIGN:be768c686587:slot-07
- Work kind: **coverage_gap**
- Score: **101.39** — {"base_priority": 92.0, "experiment_boost": 8, "strategy_allocation": 1.39}
- Strategy/objective: STRAT:capability-conjunction-search-claim-tracing / OBJ:independent-evaluation
- Capability/experiment: CAP-002, EXP-002, EXP-003, EXP-006, EXP-009
- Why now: Intersect exploration blind spot COV:package-ecosystem:nuget (.NET / NuGet: 0/3) with CAP-002, an active high-value capability gap. This is coverage correction tied to a valuable technical hypothesis, not diversity for its own sake.
- Queries:
  - evidence deterministic replay language:C#
  - evidence replay path:tests language:C#
- Search surfaces: GitHub repository search, GitHub code search, GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough. Coverage membership alone never raises evidence quality.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.; If the coverage qualifier produces only shallow variants, record the no-find and do not lower the evidence bar.

### SLOT-08 — SEED:coverage:package-ecosystem-cargo:cap-014
- Assignment ID: ASSIGN:be768c686587:slot-08
- Work kind: **coverage_gap**
- Score: **92.94** — {"base_priority": 84.0, "experiment_boost": 8, "strategy_allocation": 0.94}
- Strategy/objective: STRAT:protocol-regression-archaeology-for-pre-fat-systems / OBJ:protocol-regression
- Capability/experiment: CAP-014, EXP-008
- Why now: Intersect exploration blind spot COV:package-ecosystem:cargo (Rust / Cargo: 1/3) with CAP-014, an active high-value capability gap. This is coverage correction tied to a valuable technical hypothesis, not diversity for its own sake.
- Queries:
  - independent adjudicate certification language:Rust
  - independent certification path:tests language:Rust
- Search surfaces: GitHub repository search, GitHub code search, GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Retain only when at least two required signatures meet in a connected executable path and source/tests establish the claimed state transition or invariant. README-only co-location is not enough. Coverage membership alone never raises evidence quality.
- Stop conditions: Reject generic CRUD/wrapper/dashboard matches with no load-bearing invariant.; Stop after repeated capability duplicates unless a new independent implementation, stronger evidence state, or materially different failure mode appears.; If the coverage qualifier produces only shallow variants, record the no-find and do not lower the evidence bar.

### SLOT-09 — SEED:dna:gridappsd-cimhub
- Assignment ID: ASSIGN:be768c686587:slot-09
- Work kind: **positive_dna_transfer**
- Score: **80.39** — {"base_priority": 79.0, "experiment_boost": 0, "strategy_allocation": 1.39}
- Strategy/objective: STRAT:capability-conjunction-search-claim-tracing / OBJ:ingestion-durability
- Capability/experiment: cross-domain
- Why now: Transfer the load-bearing implementation DNA of MASTER leader GRIDAPPSD/CIMHub into unrelated verticals. Why it wins: independent model-intake/round-trip proof before engineering analytics.
- Queries:
  - independent against analytics
  - independent analytics path:tests
  - independent against audit replay
- Search surfaces: GitHub code search, low-star/zero-star repository search, archived repository archaeology, author/org adjacency, dependency/consumer adjacency
- Verification gate: A transfer candidate must implement the invariant in executable code and tests; domain naming similarity is irrelevant. Prefer a different vertical or protocol family from the source repo.
- Stop conditions: Do not search the originating vertical merely because its MASTER leader scored highly.; Reject forks/clones that add no independent implementation evidence.

### SLOT-10 — ADJ:contributor-lineage:gsa-gsa-acquisition-dfars
- Assignment ID: ASSIGN:be768c686587:slot-10
- Work kind: **adjacency**
- Score: **92.66** — {"base_priority": 92.0, "strategy_allocation": 0.66}
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

### SLOT-11 — ADJ:contributor-lineage:kodekinetics79-opstrax-enterprise-build
- Assignment ID: ASSIGN:be768c686587:slot-11
- Work kind: **adjacency**
- Score: **91.66** — {"base_priority": 91.0, "strategy_allocation": 0.66}
- Strategy/objective: STRAT:paper-research-artifact-production-descendant / OBJ:research-lineage
- Capability/experiment: cross-domain
- Why now: kodekinetics79/opstrax-enterprise-build is a high-value root. Expand nearby while preserving the load-bearing invariant rather than cloning the product category.
- Queries:
  - maintainer repositories for kodekinetics79/opstrax-enterprise-build
  - fail-closed user:<maintainer>
  - fail-closed org:<maintainer-org>
- Search recipe:
  - Identify maintainers responsible for load-bearing files or architecture commits.
  - Search their other repositories and later organizations for generalized or productionized descendants.
  - Require source-level invariant continuity before calling a project a descendant.
- Verification gate: Retain a neighbor only if it adds a new capability, stronger evidence, an independent implementation, a production descendant, a useful negative control, or a new experiment edge. Mere proximity is not value.
- Stop conditions: Stop after three consecutive deep inspections produce only duplicates or clones with no evidence or capability delta.; Do not inspect accidental secrets or private data; quarantine metadata only.; Do not reopen a domain-specific STOP gate through adjacency.

### SLOT-12 — SEED:measure:cross-source-emergence-triangulation-cap-008
- Assignment ID: ASSIGN:be768c686587:slot-12
- Work kind: **strategy_measurement**
- Score: **63.66** — {"base_priority": 63.0, "experiment_boost": 0, "strategy_allocation": 0.66}
- Strategy/objective: STRAT:cross-source-emergence-triangulation / OBJ:current-rule-authority
- Capability/experiment: CAP-008
- Why now: STRAT:cross-source-emergence-triangulation has no measured runs but receives exploration allocation. Pair it with CAP-008 so the hunt searches a real gap and reduces strategy measurement debt.
- Queries:
  - review semantic authority
  - review authority path:tests
  - review semantic audit replay
- Search surfaces: GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Use the named strategy consistently enough to make the run comparable, while preserving the same evidence bar as ordinary discovery.
- Stop conditions: Do not turn a measurement run into an unrestricted domain sweep.; A no-find result is valid data; do one recall-rescue pass, then stop.

### SLOT-13 — Independent verification — SEED:coverage:package-ecosystem-nuget:cap-002
- Assignment ID: ASSIGN:be768c686587:slot-13
- Work kind: **independent_verification**
- Score: **88.00** — {"fallback_target": "top_active_search_hypothesis", "verification_base": 88}
- Strategy/objective: STRAT:evaluation-target-independence / OBJ:independent-evaluation
- Capability/experiment: cross-domain
- Why now: No READY/RUNNING experiment currently needs a dedicated verifier, so use reserved verification capacity to independently challenge the highest-ranked active search hypothesis before it becomes accepted positive training.
- Queries:
  - evidence deterministic replay language:C#
  - evidence replay path:tests language:C#
- Search surfaces: GitHub repository search, GitHub code search, GitHub code search, GitHub repository search, source/tests/schema/history, author/org adjacency
- Verification gate: Use an independent implementation, first-party authority, hand-authored fixture, negative control or contradictory source. Do not count the target repository's own claims as independent proof.
- Stop conditions: Do not duplicate the discovery agent's inspection path.; Preserve disagreement and uncertainty rather than forcing a PASS.

### SLOT-14 — Rare / weird wildcard exploration
- Assignment ID: ASSIGN:be768c686587:slot-14
- Work kind: **wildcard**
- Score: **75.00** — {"protected_exploration_budget": 75}
- Strategy/objective: n/a / n/a
- Capability/experiment: cross-domain
- Why now: Preserve high-recall discovery for technologies the current capability graph cannot predict.
- Search surfaces: zero-star and low-star repositories, archived repositories, obscure university/lab/government organizations, unusual protocol and hardware integrations
- Verification gate: Weirdness is only a discovery prior; retain only concrete technical evidence.
- Stop conditions: Do not chase credentials, private/confidential material or accidental secrets.; No padding: a no-find run is valid.
