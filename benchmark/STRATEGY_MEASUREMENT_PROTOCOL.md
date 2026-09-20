# STRATEGY MEASUREMENT PROTOCOL

This protocol exists to measure **search methods**, not merely to repeat the repository benchmark.

## Purpose

Observational hunt telemetry is useful but confounded by domain, task difficulty, hunter context and search surface. A cleaner comparison requires matched frozen tasks where the search strategy is the main intended difference.

## Rules

1. Use only task text from `benchmark/BENCHMARK_TASKS.md`. Do **not** read `benchmark/BENCHMARK_GOLD.md` before completing and freezing the result.
2. For a comparison group, run the same task independently under each assigned strategy.
3. Use a clean/new agent context for each condition when possible. Do not reveal sibling-condition results until every condition in the comparison group is frozen.
4. Keep tool access and broad effort budget comparable. Record elapsed time/tool calls when available rather than silently allowing one condition unlimited work.
5. The strategy may change *how* the task is searched/verified, but must not change the task's acceptance target.
6. Record no-find and reject results. A strategy that safely rejects a planted false positive can outperform a strategy that returns a polished but wrong candidate.
7. Every benchmark search run must record:
   - `measurement_quality: "benchmark"`
   - `benchmark_task_ids`
   - `comparison_group_id`
   - `evaluation_set_id`
   - strategy/query/search-surface instrumentation
   - candidate/deep-inspection/retention counts
   - durable evidence location
8. Score only after all matched conditions are frozen. Use the existing benchmark dimensions where applicable; preserve false-promotion and no-find outcomes.
9. Repeating a task later is allowed only when the comparison has a different pre-registered question or materially changed strategy implementation.
10. Results feed the search-policy learner as benchmark evidence, but a benchmark win does not by itself prove commercial value.

## Experimental interpretation

- **Matched task difference** is stronger evidence about search strategy than ordinary cross-domain observational yield.
- It is still not perfect causal inference: model/context drift and stochastic search can matter.
- Real customer/engineering outcomes remain the highest-value evidence and should eventually dominate allocation.

## Campaign source

`intelligence/strategy_evaluation_sets.json` defines the curated strategy/task overlap. `tools/ti_measurement_campaign.py` turns current measurement debt into the next recommended matched comparisons.
