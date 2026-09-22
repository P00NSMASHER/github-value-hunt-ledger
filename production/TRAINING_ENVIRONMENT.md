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
- **commercial** — realized revenue/customer value when actually recorded, using a bounded log-scale magnitude signal so $1K, $100K and $1M are not treated as equivalent while extreme outliers cannot dominate training.

Technical-only evidence is deliberately capped below commercially grounded evidence. A synthetic or partial technical result can teach the system which searches are promising, but it cannot masquerade as customer value.

## Long-horizon provenance credit

A downstream outcome may credit more than its immediate origin search, but only through explicit ledger links:

- direct `origin_search_ids`;
- contributed capability IDs;
- retained repositories that the outcome explicitly names;
- shared `experiment_id` only as contextual corroboration, never as sufficient indirect-credit evidence by itself.

Direct origin runs receive a reserved credit budget. Supporting runs share the remaining budget according to their explicit provenance paths. Per-outcome credit is normalized to exactly 1.0. Indirect support must also precede the outcome in time; when an outcome has only day-level precision, same-day indirect support is excluded rather than guessing event order.

This is **training/accounting attribution, not a causal claim**.

## Leakage boundary

Prospective generated searches use a **post-run blind partition receipt**. The worker receives a validated schema-v14+ `execution_claim_id` before the hunt, but the train/confirm label is assigned only after canonical run intake by HMAC-SHA256 using the repository Actions secret `TI_TRAINING_SPLIT_KEY`. The key is never committed or exposed to workers. Legacy/manual/unallocated runs are train-only and can never manufacture confirm evidence.

- a generated run without a persisted blind receipt is `pending_partition` and contributes to neither train nor confirm learning;
- train outcomes can credit train runs only;
- confirm outcomes can credit confirm runs only;
- live value priors train only on the train partition and must separately pass a confirm-support gate before they can steer hunters;
- benchmark runs are `evaluation_only`;
- retrospective and non-search records are excluded;
- an outcome whose direct origins span train and confirm is excluded from learning;
- an excluded non-search origin may anchor downstream support credit only when it carries the same validated generated-claim provenance; untrusted/manual origins cannot create a confirm anchor.

This prevents the learning loop from improving itself using the evidence later used to judge that improvement, and prevents a worker from changing behavior because it knows it is in the held-out confirmation arm.

## Generated artifacts

`tools/ti_training_environment.py` builds:

- `intelligence/TRAINING_ENVIRONMENT.json` — complete source snapshot, split policy, reward policy, episodes and provenance-credit edges;
- `intelligence/training_episodes.jsonl` — compact machine-learning episode stream.

`tools/ti_training_environment_validate.py` fails closed if episode hashes, split isolation or per-outcome credit conservation drift.

The generated environment is advisory/offline. It does not change live hunter assignments, global skills, MASTER promotion or benchmark policy by itself. Those remain behind the existing evidence and promotion gates.
