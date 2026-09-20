# Technology Intelligence Data Layer

This directory is the machine-readable learning layer for the GitHub Value Hunt.

The Markdown catalogs remain the human research record. These files add stable IDs, search attribution and outcome feedback so the system can measure which discovery methods actually create verified capabilities and realized value.

## Core files

- `capabilities.jsonl` — canonical capability nodes bootstrapped from `CAPABILITIES.md`.
- `edges.jsonl` — graph edges connecting repositories/sources, capabilities, targets, strategies, experiments and outcomes.
- `search_strategies.jsonl` — stable strategy nodes derived from `SEARCH_SKILLS.md`.
- `search_runs.jsonl` — one prospective event per hunting run. This is the denominator for empirical learning.
- `outcomes.jsonl` — machine-readable experiment/customer outcomes tied back to originating search runs and capabilities.
- `LEARNING_REPORT.md` — generated strategy performance report. Do not hand-edit.
- `schemas/` — JSON Schemas documenting the event contracts.

## Stable node IDs

- Capability: `CAP-001`
- Strategy: `STRAT:capability-conjunction-search-claim-tracing`
- Search run: `RUN:<UTC timestamp>:<hunter>:<short-id>`
- Repository: `REPO:owner/name@revision` when revision is known.
- Experiment: existing `EXP-###` IDs.
- Outcome: `OUT:<date>:<short-id>`
- Target/business surface: `TARGET:<slug>`

## Search-attribution contract

Every materially completed hunt cycle MUST append exactly one object to `search_runs.jsonl`.

A prospective run should record:
1. the strategy ID and query family used;
2. search surfaces and literal queries;
3. candidate count before deep inspection;
4. number deeply inspected;
5. retained/watch/rejected/MASTER dispositions for inspected candidates;
6. capabilities created or strengthened;
7. experiments changed;
8. no-find or false-positive information.

Never invent missing historical denominators. Retrospective backfills must use `measurement_quality: "retrospective"` and may leave counts null. The learning report excludes denominator-free runs from yield calculations.

## Outcome-credit contract

When an experiment or buyer validation finishes, append an object to `outcomes.jsonl` with:
- `origin_search_ids`;
- contributing capability IDs and repositories;
- PASSED / FAILED / PARTIAL / INVALID;
- realized revenue/customer value only when directly evidenced;
- observed engineering compression as a range when measurable;
- the search-policy consequence.

This creates the loop:

```
SEARCH STRATEGY
  -> SEARCH RUN
  -> REPOSITORY / DATA
  -> CAPABILITY
  -> COMBINATION / OPPORTUNITY
  -> EXPERIMENT
  -> OUTCOME
  -> STRATEGY METRICS
  -> SEARCH ALLOCATION
```

## Learning rules

The system does not promote or suppress a strategy from one anecdote.

`tools/ti_report.py` marks a strategy/query family as **insufficient evidence** until it has at least:
- 5 prospective/benchmark runs, AND
- 20 deep inspections.

Reported yield metrics include Wilson 95% intervals where a numerator/denominator exists.

Primary metrics:
- retained precision = retained / deeply inspected;
- MASTER promotion yield = promoted / deeply inspected;
- capability novelty yield = new capabilities / deeply inspected;
- experiment conversion = runs that changed an experiment / measured runs;
- outcome conversion = measured runs eventually linked to a valid outcome;
- realized revenue/customer value and observed engineering-days saved, attributed only through explicit `origin_search_ids`.

Realized outcomes outrank repository popularity, README quality and predicted commercial scores.

## Updating generated files

Run:

```bash
python tools/ti_validate.py
python tools/ti_report.py
```

CI validates the graph and checks that the learning report is current.


## V2 adaptive learning layer

The system now distinguishes **source-of-truth records** from **generated intelligence**.

Source-of-truth:
- hunter Markdown evidence under `hunters/`;
- `CAPABILITIES.md`;
- `SEARCH_SKILLS.md`;
- `intelligence/search_runs.jsonl`;
- `intelligence/outcomes.jsonl`;
- curated `intelligence/edges.jsonl`;
- strategy aliases and standardized reason codes.

Generated on every intelligence build:
- `capabilities.jsonl` and `search_strategies.jsonl` synchronized from Markdown plus observed strategy variants;
- `derived_edges.jsonl` from search-run and outcome attribution;
- `REGISTRY_REPORT.md` and `registry_metrics.json` from the full hunter corpus;
- `DATA_QUALITY_REPORT.md` and `quality_metrics.json`;
- `GRAPH_HEALTH.md`;
- `LEARNING_REPORT.md`;
- `SEARCH_POLICY.md` and `search_policy.json`.

The registry is intentionally generated from the source catalogs rather than kept as one giant checked-in JSONL. This prevents connector truncation or partial-write failures from silently deleting history.

### Before deep inspection

Run locally when available:

```bash
python tools/ti_lookup.py owner/repo
```

or perform the equivalent ledger lookup through GitHub. Reinspect a known repo only when there is a new revision, new capability hypothesis, unresolved evidence gap, new experiment edge, or contradictory evidence.

### Search-run v2 instrumentation

New prospective runs should use `schema_version: 2` and record:
- strategy and reusable query family;
- search surfaces plus literal queries;
- candidate/deep-inspection/retention/promotion denominators;
- standardized candidate dispositions and reason codes;
- capability and experiment deltas;
- recall-rescue usage and stop reason;
- optional elapsed minutes and tool-call counts for future research-efficiency measurement.

Missing recommended instrumentation lowers data-quality confidence but does not erase the underlying research.

### Adaptive allocation

`tools/ti_policy.py` uses a cautious exploration/exploitation mixture. While outcomes are sparse, the exploration budget remains high. A strategy is never declared superior from a lucky run: exploitation claims require at least 5 measured runs and 20 deep inspections.

The policy is advisory. A named blocker in a P0 experiment can override the generic allocation for a bounded search.

### CI behavior

Pull requests recompute and validate all intelligence products without requiring hand-maintained generated files.

After a qualifying push to `main`, the workflow refreshes generated intelligence and commits it with a skip-CI marker. This prevents the dashboard drift that occurred when search runs advanced but the learning report remained stale.


## V3 empirical-learning layer

V3 adds measurement structures that prevent several common research-system errors:

- **Canonical query families** — `query_families.jsonl` gives reusable query hypotheses stable `QF:...` IDs while preserving literal queries in each run.
- **Fractional outcome attribution** — `ATTRIBUTION_REPORT.md` splits realized value across multiple origin runs instead of crediting the same dollars in full to every strategy. This is accounting attribution, not causal proof.
- **Measurement debt** — `MEASUREMENT_PLAN.md` tracks how many additional measured runs/deep inspections are needed before each strategy can be compared credibly.
- **Candidate negative training** — `NEGATIVE_TRAINING_REPORT.md` separates controlled rejection/watch reasons from detailed free-form evidence.
- **Search-surface analytics** — `SURFACE_REPORT.md` measures which discovery surfaces participate in useful runs without pretending multi-surface runs are isolated experiments.
- **MASTER registry integrity** — the registry now treats `MASTER.md` as authoritative and CI fails if elite promotion counts drift to zero or disagree with the file.
- **Graph provenance** — query-family, search-surface, candidate and outcome provenance are added to the derived graph.

### V3 prospective run contract

New runs should use `schema_version: 3` and record:

1. `strategy_id`;
2. `query_family` plus canonical `query_family_id`;
3. literal `queries` and `search_surfaces`;
4. candidate/deep-inspection/retention/promotion denominators;
5. candidate dispositions using a controlled `reason_code_standard` plus detailed `reason_detail`;
6. capability/experiment deltas;
7. durable evidence path.

Do not fabricate missing history to make the dashboard look complete. Measurement debt is preferable to invented denominators.


## V4 normalized measurement and matched strategy evaluation

V4 separates four levels that were previously easy to conflate:

1. **Literal query** — the exact strings used in one run.
2. **Query family (`QF:...`)** — a reusable implementation-level hypothesis.
3. **Search objective (`OBJ:...`)** — a broader cross-domain research question such as completeness proof, authority lineage or ambiguity reconciliation.
4. **Strategy (`STRAT:...`)** — the search/verification procedure used to pursue that objective.

This prevents one-off query wording from fragmenting the learner while preserving exact provenance.

### Normalized search surfaces

Exact labels such as “GitHub code/signature search” and “GitHub code search” remain stored, but `surface_aliases.json` maps them into stable `SURFACE_FAMILY:...` categories. Family-level metrics reduce wording fragmentation; exact labels remain available for diagnosis.

### Candidate reason normalization

New V4 candidate dispositions use:
- `reason_code_standard` — controlled machine-learning category;
- `reason_detail` — precise technical evidence.

Reviewed `reason_aliases.json` maps older free-form reason codes into the controlled taxonomy without rewriting source history.

### Matched strategy measurement

Ordinary hunt telemetry is observational and confounded. V4 adds a matched benchmark layer:
- `strategy_evaluation_sets.json` — curated strategy/task overlap;
- `benchmark/STRATEGY_MEASUREMENT_PROTOCOL.md` — clean-condition protocol;
- `MEASUREMENT_CAMPAIGN.md` — next recommended comparisons.

Benchmark runs use `measurement_quality: "benchmark"` and record `benchmark_task_ids`, `evaluation_set_id` and `comparison_group_id`. Do not read `BENCHMARK_GOLD.md` until matched results are frozen.

### Revision debt

`REVISION_DEBT_REPORT.md` tracks findings whose exact inspected revision is missing plus MASTER entries lacking matching catalog evidence. Never invent a historical SHA; reinspect and create a new pinned observation when the original cannot be recovered.

### V4 run contract

Every new prospective hunt should use `schema_version: 4` and persist:
- `strategy_id`
- `query_family` and canonical `query_family_id`
- controlled `search_objective_id`
- literal queries and search surfaces
- candidate/deep-inspection/retention/MASTER denominators
- controlled candidate reason code + evidence detail
- capability and experiment deltas
- durable evidence location

Matched benchmark runs additionally require task/set/comparison metadata.


## V5 search-seed compiler

V5 closes the loop between what the system has learned and what hunters search next.

Generated products:
- `search_seeds.jsonl` — stable ranked search hypotheses.
- `SEARCH_SEEDS.md` — human-readable seed packets with query templates, verification gates and stop conditions.
- `SEED_PERFORMANCE.md` — empirical seed-level yield once V5 runs accumulate.
- `seed_metrics.json` — seed inventory/performance metadata.

`tools/ti_seed_compiler.py` creates three seed types:
1. **capability_gap** — converts the adaptive policy's highest-information capability gaps into concrete searches;
2. **positive_dna_transfer** — extracts load-bearing implementation signatures from MASTER leaders and searches for those invariants in unrelated verticals;
3. **strategy_measurement** — pairs under-measured strategies with real capability gaps so exploration also reduces measurement debt.

New prospective runs should use `schema_version: 5` and record:
- `seed_mode: generated` plus one or more `seed_ids` when using generated hypotheses;
- `seed_mode: manual_hypothesis` for a hunter-authored bounded hypothesis;
- `seed_mode: free_exploration` with an empty `seed_ids` list for deliberate wildcard exploration.

Seed priority is advisory. It cannot override domain-specific search gates, safety rules, source authority or experiment stop conditions. Seed performance is not used to penalize a hypothesis until it has at least 3 measured runs and 10 deep inspections.


## V6 adjacency expansion

V6 makes second-order discovery measurable. A high-value repository can now generate bounded adjacency hypotheses across:

- organization siblings;
- contributor/maintainer lineage;
- forks and production descendants;
- unusual upstream dependencies;
- downstream consumers;
- distinctive source/test symbols;
- commit, rename and regression lineage.

Generated products:
- `adjacency_queue.jsonl` — stable `ADJ:...` hypotheses rooted in MASTER leaders and recent strong findings;
- `ADJACENCY_QUEUE.md` — ranked human-readable expansion packets;
- `ADJACENCY_PERFORMANCE.md` — yield by adjacency type and exact hypothesis;
- `adjacency_metrics.json` — machine-readable summary.

New prospective runs use `schema_version: 6` and record:
- `adjacency_mode: generated` with one or more generated adjacency IDs;
- `adjacency_mode: manual` for a bounded hunter-authored neighbor search;
- `adjacency_mode: none` when no adjacency expansion was used;
- standardized `adjacency_types` and `adjacency_root_nodes`.

Adjacency is never evidence by itself. A neighbor is retained only when it adds a new capability, materially stronger evidence, an independent implementation, a production descendant, a useful negative control, or a new experiment edge.

Minimum evidence before adjacency performance can influence priority:
- exact adjacency hypothesis: 3 measured runs and 10 deep inspections;
- adjacency type: 5 measured runs and 20 deep inspections.

Domain STOP gates still win. Adjacency cannot be used to silently reopen broad freight or another explicitly closed search lane.


## V7 search saturation and diminishing-return detection

V7 measures whether a research neighborhood is still producing new technical value or is approaching diminishing returns.

Neighborhoods are derived from existing telemetry rather than manually declared:
- capability neighborhoods;
- canonical query families;
- search objectives;
- adjacency types and roots;
- generated search seeds.

Generated products:
- `research_neighborhoods.jsonl` — measured neighborhood health;
- `SATURATION_REPORT.md` — human-readable status and evidence;
- `redirect_queue.jsonl` / `REDIRECT_QUEUE.md` — recommended effort shifts;
- `saturation_metrics.json` — machine-readable summary.

Statuses:
- `INSUFFICIENT` — not enough evidence to judge;
- `PRODUCTIVE` — still producing meaningful novelty or MASTER/capability delta;
- `BALANCED` — neither obviously productive nor exhausted;
- `SATURATING` — diminishing returns are emerging;
- `SATURATED` — repeated measured search is producing little novelty and enough duplicate/low-yield evidence exists.

A neighborhood cannot be marked SATURATING or SATURATED until it has at least 5 measured runs and 20 deep inspections. Duplicate and first-seen signals are ignored until their own observation thresholds are met.

Saturation is a soft redirect, not a ban. Seed priority adjusts conservatively:
- PRODUCTIVE: +5;
- BALANCED / INSUFFICIENT: 0;
- SATURATING: -12;
- SATURATED: -25.

A concrete experiment blocker or independently justified cross-domain transfer can still override the generic redirect. Domain STOP gates remain authoritative.


## V8 blind-spot exploration coverage

V8 measures where the hunt has barely explored at all, using explicit coverage quotas rather than pretending to know the true distribution of valuable technology on GitHub.

Observable dimensions are derived from repository profiles:
- primary language family;
- star/attention band;
- repository age;
- archived/fork lifecycle;
- owner account type.

Reviewed/manual dimensions are supported but do not create automatic blind-spot seeds until classification coverage is high enough:
- institution/source type (government, national lab, university, standards body, company, nonprofit, community, individual);
- package/application ecosystem;
- protocol family;
- operational geography.

Generated products:
- `repository_profiles.jsonl` — merged bootstrap + V8 run profiles;
- `coverage_targets.jsonl` — every quota target and its state;
- `exploration_gap_queue.jsonl` — searchable undercovered targets;
- `COVERAGE_REPORT.md` — coverage and metadata debt;
- `EXPLORATION_GAPS.md` — ranked searchable blind spots;
- `coverage_metrics.json` — machine-readable summary.

V8 adds `coverage_gap` search seeds. They intersect a searchable blind spot (for example zero-star, archived, Rust/C++, or older repositories) with an active high-value capability gap. Coverage membership never substitutes for technical evidence.

New prospective runs use `schema_version: 8` and record:
- `coverage_mode: generated | manual | none`;
- `coverage_gap_ids`;
- a `repository_profile` for every structured candidate disposition. Unknown manual tags stay `unknown`/empty rather than being guessed.

The default taxonomy is an exploration policy, not a claim about GitHub prevalence. It is editable as evidence accumulates.


## V9 unified hunt allocator

V9 turns the separate intelligence products into one ranked 14-slot work plan.

Inputs include:
- adaptive strategy allocation;
- READY/RUNNING experiments and their current next actions;
- capability-gap seeds;
- V7 saturation redirects;
- V8 blind-spot coverage seeds;
- V6 adjacency opportunities;
- strategy measurement debt;
- explicit verification and wildcard reserves.

Generated products:
- `hunt_candidates.jsonl` — all eligible work items with transparent score components;
- `hunt_allocations.jsonl` — one assignment per configured slot;
- `HUNT_PLAN.md` — the executable 14-slot plan;
- `ALLOCATOR_REPORT.md` — portfolio mix and concentration controls;
- `allocator_metrics.json` — machine-readable allocator state.

Default 14-slot portfolio:
- 6 experiment/high-value capability slots;
- 3 blind-spot exploration slots;
- 2 adjacency slots;
- 1 strategy-measurement slot;
- 1 independent falsification slot;
- 1 protected wildcard slot.

Hard concentration controls prevent more than:
- 2 assignments on one capability;
- 2 assignments on one experiment;
- 3 assignments using one strategy;
- 1 adjacency assignment from the same root repository.

READY/RUNNING experiments can outrank additional repository search. BLOCKED_EXTERNAL experiments are not assigned as autonomous work.

New prospective runs use `schema_version: 9` and record:
- `allocation_mode: generated | manual_override | unallocated`;
- `allocator_generation_id`;
- `assignment_id`;
- `assignment_work_item_id`.

Manual overrides are allowed but must be explicit. The allocator is a scheduler, not evidence: all existing verification, rights, safety, saturation and domain-authorization gates remain in force.


## V10 allocator learning

V10 measures whether the V9 portfolio itself is allocating research capacity well.

It learns from executed allocator-attributed runs, not from generated plans. An assignment receives no learning credit until a search run records the assignment provenance and any downstream outcome links back to that run.

Generated products:
- `allocator_role_metrics.jsonl` — performance by slot role;
- `allocator_work_kind_metrics.jsonl` — diagnostic performance by work kind;
- `allocator_attribution_debt.jsonl` — V9 runs that cannot yet be mapped cleanly to role/kind;
- `allocator_policy_effective.json` — generated effective portfolio policy;
- `ALLOCATOR_LEARNING_REPORT.md` — evidence and adaptation decision;
- `ALLOCATOR_WORK_KIND_REPORT.md` — diagnostic work-kind metrics;
- `allocator_learning_metrics.json` — machine-readable summary.

Automatic adaptation is deliberately conservative:
- only `experiment`, `coverage`, and `adjacency` slot counts can move;
- `measurement`, `verification`, and `wildcard` remain protected;
- a role needs at least 5 attributed generated runs plus sufficient inspection/experiment/outcome evidence;
- the scheduling-signal gap must be at least 0.15;
- at most one slot can move per generation;
- hard floors remain: experiment >=4, coverage >=2, adjacency >=1;
- hard ceilings remain: experiment <=8, coverage <=4, adjacency <=3.

The allocation signal is a scheduling heuristic, not a causal estimate of commercial value. Realized outcomes remain the strongest downstream evidence.

Manual overrides are recorded separately and do not influence automatic portfolio adaptation.

New prospective runs use `schema_version: 10` and additionally record:
- `portfolio_policy_generation_id`;
- `assignment_slot_role`;
- `assignment_work_kind`;
- `assignment_source_id`;
- `assignment_score`.

The V10 learner runs before V9 allocation in CI. When evidence is insufficient, `allocator_policy_effective.json` is identical in slot composition to the human-authored baseline policy.


## V11 hunt execution control plane

V11 turns the V9/V10 plan into claimable work with explicit execution state.

Source-of-truth execution events live under `intelligence/execution_events/`, one append-only JSONL log per slot. Current state is derived; old events are never rewritten.

Supported transitions:
- `CLAIM` — acquire the exact assignment snapshot and lease;
- `HEARTBEAT` — extend a live lease;
- `START` — mark execution active;
- `COMPLETE` — close with a schema-v11 search run;
- `FAIL` — close retryable or terminal;
- `RELEASE` — voluntarily return the slot.

Concurrency model:
- slot event files are independent, reducing cross-hunter conflicts;
- connector-based claims use GitHub blob-SHA optimistic concurrency;
- one active claim per slot;
- one active claim per worker by default;
- overlapping claims for the same assignment are rejected;
- heartbeats cannot revive expired leases.

Generated products:
- `execution_state.jsonl` — current derived state for all 14 slots;
- `execution_claim_history.jsonl` — immutable derived claim history;
- `EXECUTION_BOARD.md` — current human-readable execution board;
- `EXECUTION_DEBT.md` — expiry/retry/supersession/telemetry debt;
- `execution_metrics.json` — machine-readable execution summary.

Completion is inseparable from telemetry. A COMPLETE event is invalid unless its search run is schema >=11 and exactly matches the claim's worker, slot, assignment, allocator generation, portfolio policy, work item, role, work kind, source ID and score.

New allocated V11 runs additionally record:
- `execution_claim_id`;
- `execution_slot_id`;
- `execution_worker_id`.

Local helper:
`python tools/ti_execution_event.py claim|heartbeat|start|complete|fail|release ...`

For connector-driven claims, follow `intelligence/execution_events/README.md` and use the exact GitHub file SHA for atomic updates.


## V12 worker routing and automatic slot selection

V12 gives the execution control plane durable worker identities and a measurable worker-to-assignment routing layer.

Source-of-truth:
- `worker_registry.json` — durable `HUNTER-01`…`HUNTER-14` identities and active/paused state;
- `worker_aliases.json` — reviewed historical label mappings;
- `routing_policy.json` — routing weights, evidence shrinkage and guardrails.

Generated products:
- `worker_profiles.jsonl` — worker history, strategy/objective/experiment/capability/domain counts and V11 claim experience;
- `worker_strategy_domain_metrics.jsonl` — observational worker × strategy × domain performance;
- `WORKER_PROFILE_REPORT.md` — human-readable profile evidence;
- `routing_candidates.jsonl` — every eligible worker↔slot edge and score decomposition;
- `worker_routing.jsonl` — one route decision per registered worker;
- `worker_claim_packets.jsonl` — exact assignment snapshots for routed workers;
- `WORKER_ROUTING.md` — current routing plan;
- `routing_metrics.json` — routing summary.

Routing behavior:
- active V11 claims are locked and cannot be rerouted;
- idle workers and claimable slots are matched with an exact maximum-total-fit assignment rather than greedy first-pick routing;
- assignment priority is always part of the score;
- historical strategy, objective, experiment, capability, domain and completed-role evidence can only increase fit;
- sparse/missing history never creates a negative penalty;
- unmeasured workers receive a small exploration bonus so the router learns them;
- one worker gets at most one slot and one slot gets at most one worker.

Historical labels are normalized conservatively. Clear numeric identities such as `NODE 04`, `Hunt 05`, `H06`, and `hunter11` map to their corresponding durable worker. Ambiguous labels remain unmapped and are reported as profile debt.

V12 run provenance adds:
- `routing_mode`;
- `routing_generation_id`;
- `worker_profile_generation_id`;
- `routing_score`.

Generated V12 routing is observational optimization, not a causal ranking of worker quality.

Local routed claim helper:
`python tools/ti_worker_claim.py --worker HUNTER-05`

Remote/connector claims still use V11 optimistic file-SHA concurrency. The claim packet tells the worker exactly which slot file and assignment snapshot to claim.


## V13 routing outcome learning

V13 measures whether V12 worker-routing choices actually produce useful results and only then feeds bounded evidence back into future routing.

Training eligibility is strict:
- schema_version >= 12;
- routing_mode = generated;
- measurement_quality = prospective or benchmark;
- V11 claim status COMPLETE;
- telemetry_status MATCHED.

Manual overrides, unrouted work, retrospective repairs, active claims and INVALID outcomes do not train automatic routing.

Generated products:
- `routing_learning_runs.jsonl` — one auditable realized-utility row per eligible completed generated route;
- `routing_adjustments.jsonl` — worker × context residuals and bounded adjustments;
- `routing_calibration.jsonl` — descriptive routing-score vs realized-utility calibration;
- `routing_learning_metrics.json`;
- `ROUTING_LEARNING_REPORT.md`;
- `ROUTING_CALIBRATION_REPORT.md`.

Automatic influence requires at least 12 completed generated routes globally. A worker-context additionally requires repeated worker runs, a multi-worker baseline, and either sufficient deep inspection or downstream outcome evidence.

Matched contexts are role, work kind, strategy, objective and experiment. Worker residuals are shrunk toward zero and bounded to +3 / -2 routing-score points.

The system intentionally reports **no causal worker ranking**. Assignment difficulty is confounded. V13 uses matched task-context residuals as routing evidence, not as a performance-review score.

Until thresholds are met, mode is `observe_only_insufficient_evidence` and every V13 routing adjustment is exactly zero.


## V14 routing decision audit

V14 preserves the alternatives that V12/V13 rejected at routing time without changing any worker assignment.

For every routed worker-slot pair it independently re-solves the full matching problem with that exact pair forbidden.

Generated products:
- `routing_decision_audit.jsonl` — one decision-evidence row per chosen pair;
- `routing_generation_audit.json` — generation-level optimum and summary metrics;
- `ROUTING_DECISION_AUDIT.md` — human-readable criticality and local-alternative table.

Each decision record preserves:
- chosen routing score;
- independently recomputed global optimum;
- best feasible full matching when the chosen pair is forbidden;
- global pair criticality = optimum score loss after forbidding that pair;
- worker-local next-best slot and score delta;
- slot-local next-best worker and score delta;
- full counterfactual pair set when feasible.

A zero-criticality pair can be removed without reducing the globally optimized routing score. Those pairs are useful candidates for later controlled routing exploration.

A negative local delta is not an error: the globally optimal matching can choose a locally lower-scoring edge to improve the total portfolio.

V14 is evidence-only. It does not reroute workers, alter claims, or make causal regret claims.
