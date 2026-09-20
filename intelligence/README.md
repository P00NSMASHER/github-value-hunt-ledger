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
