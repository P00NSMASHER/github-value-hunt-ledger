# Hunter database as a training environment

The private hunter ledger is now compiled into a deterministic offline training environment rather than treated only as a catalog.

## Episode contract

Every eligible measured search run becomes one episode:

`state -> action -> observation -> reward`

State contains the lane/objective/seed/assignment context that existed before the hunt.

Action contains the strategy, query family, search surfaces, literal queries, recall-rescue choice and stopping decision.

Observation contains candidates, deep inspections, retained findings, capability effects, experiment links, time and tool usage.

Reward is multi-stage:

- **discovery** — measured retained yield, promotion, capability contribution, duplicate avoidance and efficiency;
- **technical** — downstream experiment results;
- **engineering** — observed implementation time saved when actually recorded;
- **commercial** — realized revenue/customer value when actually recorded.

Technical-only evidence is deliberately capped below commercially grounded evidence. A synthetic or partial technical result can teach the system which searches are promising, but it cannot masquerade as customer value.

## Long-horizon provenance credit

A downstream outcome may credit more than its immediate origin search, but only through explicit ledger links:

- direct `origin_search_ids`;
- shared `experiment_id`;
- contributed capability IDs;
- retained repositories that the outcome explicitly names.

Direct origin runs receive a reserved credit budget. Supporting runs share the remaining budget according to their explicit provenance paths. Per-outcome credit is normalized to exactly 1.0.

This is **training/accounting attribution, not a causal claim**.

## Leakage boundary

Prospective searches are deterministically split by the hash of `search_run_id` into train and confirm partitions.

- train outcomes can credit train runs only;
- confirm outcomes can credit confirm runs only;
- benchmark runs are `evaluation_only`;
- retrospective and non-search records are excluded;
- an outcome whose direct origins span train and confirm is excluded from learning.

This prevents the learning loop from improving itself using the evidence later used to judge that improvement.

## Generated artifacts

`tools/ti_training_environment.py` builds:

- `intelligence/TRAINING_ENVIRONMENT.json` — complete source snapshot, split policy, reward policy, episodes and provenance-credit edges;
- `intelligence/training_episodes.jsonl` — compact machine-learning episode stream.

`tools/ti_training_environment_validate.py` fails closed if episode hashes, split isolation or per-outcome credit conservation drift.

The generated environment is advisory/offline. It does not change live hunter assignments, global skills, MASTER promotion or benchmark policy by itself. Those remain behind the existing evidence and promotion gates.
