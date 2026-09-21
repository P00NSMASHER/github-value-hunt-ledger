# Hunter strategy upgrade — 2026-09-21

## Assessment

The bottleneck was operational correctness and evidence follow-through, not a shortage of search algorithms. The existing system already had capability graphs, 14 logical worker slots, search attribution, coverage exploration, saturation controls, dispatch/presence machinery and multiple conservative learners.

Inspected baseline: GitHub tree `d4bc6e33330f0ea46c16bdeffbd7ca87e0df4489`, plus the 15 enabled automation prompts. Baseline reports contained 1,705 unique repositories, 18 structured runs, one structured outcome, 90 unknown-revision observations and two MASTER/catalog provenance gaps. All 12 active search strategies remained below their comparison evidence thresholds. These are snapshot observations, not permanent operating counters; current reports are authoritative.

## Implemented changes

| Finding | Repair | Practical effect |
|---|---|---|
| `**READY**.` was parsed as `READY.` and excluded from ready-work selection | Normalize status separately from its explanatory scope | Existing ready experiments can outrank redundant discovery |
| `CAP-002, 007, 008` kept only the first capability | Parse compact capability references in both compiler and allocator | Concentration limits and experiment links use the full list |
| Specific artifact/fixture gaps became generic queries such as “independent adjudicate certification” | Reviewed domain-anchor recipes and explicit work actions | Workers search, verify or execute according to the actual missing evidence |
| Coverage/measurement could reopen a task that required execution first | Inherit action/STOP contracts; require an evidence-bound reviewed reopening record | Exploration no longer silently defeats current task gates |
| Verification could repeat the discoverer's queries before any result existed | Separate experiment falsification from pre-discovery hypothesis challenge | A verifier must identify a frozen target and independent evidence before claiming verification |
| Structured submissions lacked one reconciliation path | Immutable per-run intake, exact-replay deduplication, conflict rejection, single canonical writer | Concurrent workers no longer need to replace a shared run log |
| Telemetry template contained fictional provenance placeholders | Draft helper copies actual stored claims or explicitly produces unallocated drafts | Unknown counts stay null and fabricated packet IDs stay out of learning |
| Execution tasks could contaminate discovery statistics | Explicit work-action filtering for discovery learning | Fixture/artifact work remains valuable without masquerading as search yield |
| The pipeline was duplicated in CI | One shared build order; source sync before/after intake; MASTER and regression-test triggers | Local and CI validation follow the same dependencies |
| Prompts and docs prescribed older schemas/paths | Shared worker runbook and mission, current template references, shorter task prompts | Hunters have one current operating entry point |

The first complete regenerated plan assigned three explicit experiment-execution items instead of zero. Its work-action mix was six fixture actions, one artifact-verification action and seven search actions. This is an allocation correction, not evidence that those tasks executed successfully. Protected coverage, adjacency, measurement, verification and wildcard roles remain intact.

## Telemetry reconciliation

No lost runs were recovered. The HUNTER-13 submission was already an exact canonical replay. The older HUNTER-11 submission conflicted with a previously repaired retrospective canonical record. Its original bytes were archived with hashes and a reconciliation manifest; the existing corrected canonical record and its unknown denominators were preserved. Intake now reports 18 existing records, one exact replay, zero pending rows and zero errors for this snapshot.

## Scheduled-worker rollout

All 15 active prompts were updated and read back successfully. They preserve the frozen benchmark prefixes, original worker identities/catalog assignments and the three shadow overrides. Schedules, titles, enabled state and reserve tasks are unchanged. Stored prompt text falls from 244,282 to 44,098 characters across the 15 active tasks (81.9% shorter); common instructions are read from versioned repository files. This is not a measured token-cost or research-speed claim.

Original task configurations are preserved in `automation_backups/2026-09-21-before.json`. Desired instructions are in `automation_prompts.json`. The [rollout receipt](automation_rollout_2026-09-21.json) records all 15 successful updates and readback comparisons, including unchanged schedules, enabled state, titles and reserve tasks.

## Verification

- 44 regression tests passed, covering routing/gates, telemetry integrity, real-claim draft provenance and discovery-versus-execution measurement.
- All 48 steps of `python tools/ti_build.py` passed locally, including existing graph, allocator, execution, routing, dispatch, activation and attribution checks.
- `git diff --check` passed after regenerating reports.
- Canonical telemetry remained at 18 records; no historical counts or outcomes were invented.
- Both GitHub workflows passed for source commit `991f8acb0a103491d24344563a30486261e889fb`: Technology Intelligence System and Freight Commercial Contracts. The former also persisted regenerated intelligence.
- All 15 automation prompts matched readback; frozen benchmark prefixes and three shadow overrides were preserved. See the rollout receipt.

## Evidence limits and next operational priority

The existing frozen comparison is unfinished; the remaining experiment tasks need clean contexts without control answers. No benchmark tasks, gold, scoring rules or shadow restrictions were edited. There is no claim that the more elaborate architecture outperforms the baseline.

Next, collect genuine bounded worker runs through the repaired path, complete the existing experiments and record their outcomes. Reduce the load-bearing provenance debt when it affects a live decision. Keep automatic strategy/routing learning conservative until its evidence thresholds are satisfied. A larger ledger, an impressive score or a generated assignment does not establish revenue or an executed result.

This upgrade improves the current ChatGPT/GitHub operating system. It does not deploy the staged external production runtime, separate verifier identities, object storage or sandbox infrastructure described in `production/STATUS.md`.

## Reference

Search tooling instructions were checked against [GitHub REST search documentation](https://docs.github.com/en/rest/search/search) and [repository search qualifiers](https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories). Connector-specific input contracts still govern connector queries.


## Follow-on fleet coordination patch

After the live automation audit found Hunt 02 paused while the other 14 hunter tasks were enabled, Hunt 02 was restored without altering its frozen benchmark prompt or schedule. The live-only shared operating documents were then tightened around the benchmark's current empirical weakness: experimental verification depth has not yet improved aggregate discovery yield, and two experiment results were no-find/recall failures.

The live path now adds three conservative protections:
1. a recall floor before NO_FIND so one polished near-match cannot consume the whole discovery budget;
2. a durable stop/miss taxonomy so retrieval failure, duplicate/no-delta, evidence blocks and genuine no-qualifying-candidate outcomes are not conflated;
3. an explicit cross-hunter handoff checkpoint for capability deltas, contradictions, verifier failures, negative knowledge and typed referrals.

These changes do not modify benchmark tasks, gold, scoring, experiment state/results, or SEARCH_SKILLS while Pair 1 remains unfinished. They are intended to improve coordination and learning after each worker exits its frozen benchmark phase.

## Immutable coordination and recall-rescue instrumentation

A second follow-on patch added a race-safe cross-hunter learning channel without changing the unfinished frozen benchmark.

### Coordination channel
- `intelligence/COORDINATION_PROTOCOL.md` defines one immutable coordination packet per materially useful live run when a finding can change another worker's next action.
- `intelligence/coordination_spool/` prevents concurrent workers from replacing one shared mutable blackboard.
- Hunt 15 owns the compact `COORDINATION_BOARD.md` and routes durable capability deltas, negative knowledge, referrals, contradictions, local lessons and next tests into the existing authoritative ledgers.
- Search-run telemetry now records both emitted `coordination_signal_ids` and materially `consumed_coordination_signal_ids`.
- `tools/ti_coordination_report.py` measures transfer/consumption downstream but is **observe-first**; coordination does not yet change automatic routing.
- Baseline at introduction: 39 measured runs, 0 historical emitted signals, 0 consumed signals. No history was retroactively relabeled.

### Recall-rescue learning
The completed benchmark exposed two different false-negative patterns: deep falsification of a polished near-match while missing another qualifying target, and overly literal domain taxonomy that rejected an adjacent-domain implementation even though it exercised the exact required invariant on domain-specific cases.

The live post-benchmark path now:
- preserves the existing recall floor;
- treats retrieval/rate-limit failures as retrieval debt rather than absence evidence;
- permits an **invariant-first adjacent-domain rescue** when domain-labelled candidates miss the defining mechanism;
- keeps the original acceptance target unchanged, so adjacency cannot lower the verification bar;
- records `recall_rescue_type` and whether the rescue surfaced a qualifying candidate;
- records a controlled `stop_reason_standard` so no-find, duplicate, retrieval-limited, evidence-blocked, safety/rights, external-prerequisite and budget-exhausted states can be distinguished.

These fields are diagnostic only. At introduction, 10 prior discovery runs had explicitly observed recall-rescue usage and 2 reported using one, but the new rescue-type/success fields did not exist historically; those two therefore remain `unspecified` and are not backfilled with invented success labels.

No change here is evidence that the architecture is superior. The unfinished Pair 1 benchmark remains frozen, and automatic allocation should only use these new signals after enough prospective examples show improved useful outcomes without worsening recall.

## Per-move learning, compact priors and measured efficiency

A third live-path upgrade moves learning below whole-run/query-family granularity.

### Why
The current query-family report showed **39 measured families and 39 one-run measured families**. That is too fragmented for fast empirical learning: a useful code-signature search or lineage jump can work repeatedly even when the full query-family wording is unique.

### Added
- `search_moves` telemetry records materially different retrieval moves and their observed result, surface, candidate/deep/retained counts and references.
- `tools/ti_search_move_learning.py` aggregates move-level evidence globally and by search objective with conservative minimum-sample gates.
- Move telemetry preserves first/last-seen recency and recent-use counts so an old successful method does not become permanent dogma.
- `tools/ti_search_move_policy.py` creates a cautious search curriculum. It remains observe-only until at least three move types satisfy evidence gates, and always preserves an exploration floor.
- Baseline curriculum is correctly **100% exploration / inactive** because no historical runs were retroactively assigned search-move results.
- `candidate_preflight_checks`, `known_candidate_preflight_hits` and `duplicate_deep_inspections_avoided` measure useful work the network avoids through prior memory.
- `tools/ti_efficiency_report.py` tracks those savings alongside deep-inspection, tool-call and elapsed-time denominators without rewarding shallow work.
- Baseline registry pressure is 1,706 unique repositories, 79 duplicate observations (4.4%) and 91 unknown-revision records. Historical duplicate avoidance was not invented.
- `tools/ti_network_priors.py` generates `NETWORK_PRIORS.md`, a compact navigation layer so live hunters can start from current high-information constraints instead of rereading the full corpus. It is explicitly non-authoritative.

### Compounding loop
Future live hunts now produce:
`search move -> candidate/evidence result -> run telemetry -> coordination handoff -> outcome -> move/strategy/efficiency reports -> compact network priors -> next hunt`.

The new move policy is deliberately a recommendation, not an autonomous command. It should activate only after prospective evidence accumulates, and assignment-specific acceptance targets, domain gates and verifier evidence always outrank generic priors.

