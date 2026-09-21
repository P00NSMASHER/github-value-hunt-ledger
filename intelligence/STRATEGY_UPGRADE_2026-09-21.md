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

Prepared prompts preserve the frozen benchmark prefixes, original worker identities/catalog assignments and the three shadow overrides. Schedules, titles, enabled state and reserve tasks are unchanged. Stored prompt text falls from 244,282 to 44,098 characters across the 15 active tasks (81.9% shorter); common instructions are read from versioned repository files. This is not a measured token-cost or research-speed claim.

Original task configurations are preserved in `automation_backups/2026-09-21-before.json`. Desired instructions are in `automation_prompts.json`. The rollout receipt records actual update/readback status.

## Verification

- 44 regression tests passed, covering routing/gates, telemetry integrity, real-claim draft provenance and discovery-versus-execution measurement.
- All 48 steps of `python tools/ti_build.py` passed locally, including existing graph, allocator, execution, routing, dispatch, activation and attribution checks.
- `git diff --check` passed after regenerating reports.
- Canonical telemetry remained at 18 records; no historical counts or outcomes were invented.
- GitHub CI and task readback are recorded separately in the rollout receipt.

## Evidence limits and next operational priority

The existing frozen comparison is unfinished; the remaining experiment tasks need clean contexts without control answers. No benchmark tasks, gold, scoring rules or shadow restrictions were edited. There is no claim that the more elaborate architecture outperforms the baseline.

Next, collect genuine bounded worker runs through the repaired path, complete the existing experiments and record their outcomes. Reduce the load-bearing provenance debt when it affects a live decision. Keep automatic strategy/routing learning conservative until its evidence thresholds are satisfied. A larger ledger, an impressive score or a generated assignment does not establish revenue or an executed result.

This upgrade improves the current ChatGPT/GitHub operating system. It does not deploy the staged external production runtime, separate verifier identities, object storage or sandbox infrastructure described in `production/STATUS.md`.

## Reference

Search tooling instructions were checked against [GitHub REST search documentation](https://docs.github.com/en/rest/search/search) and [repository search qualifiers](https://docs.github.com/en/search-github/searching-on-github/searching-for-repositories). Connector-specific input contracts still govern connector queries.
