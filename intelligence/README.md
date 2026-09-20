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
