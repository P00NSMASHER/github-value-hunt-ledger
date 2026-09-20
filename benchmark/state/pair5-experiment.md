# Pair 5 — EXPERIMENT persistent state

## Validated reusable lessons
- Task 30: README-level "verification" claims are not enough. High-signal implementation checks are: (a) executor output explicitly treated as a claim, (b) completion fail-closed unless a verifier/auditor confirms original requirements, (c) blocking constraints prevent `complete`, (d) verifier/auditor mutation is detected or restored, and (e) resume reconstructs planning context from durable recorded state. These discriminators separated a true verification loop from generic orchestration/checkpoint frameworks.
- Task 31: For ticket-driven autonomous software orchestration, inspect four implementation transitions rather than generic "agent orchestration" claims: tracker state -> dispatch/reconciliation; worker exit/stall -> retry/backoff; issue identity -> collision-safe isolated workspace/path boundary; validation evidence -> review/merge state. OpenAI Symphony implemented and tested all four strongly enough to survive red-team review, while also exposing important caveats: retry/block state is process-local, workspace separation is not equivalent to a hardened sandbox, and some quality gates are WORKFLOW policy rather than an independent verifier.
- Cross-task reinforcement from Tasks 30 and 31: the useful transferable habit is to locate the actual state transition that accepts work as complete/reviewable, then inspect recovery and evidence around that transition. This is stronger than searching for reviewer/auditor terminology alone. The exact Task-30 role×persistence×proof search recipe is not yet considered independently confirmed because Task 31 did not require a manager/executor/auditor role split.

## Failed search patterns
- Broad repository searches centered only on phrases like `agent harness`, `manager verifier`, or `long horizon agent` produced high generic-framework noise and many systems with memory/checkpointing but no independent original-requirements audit boundary.
- Searching for "auditable" alone over-selected logging/trace/evidence-recording systems where the executing agent can still effectively self-certify completion.
- Task 31: Broad searches for `coding agent orchestrator` or `kanban coding agent` returned many thin wrappers that spawn a CLI in a worktree but lack reconciliation, retry semantics or an evidence-to-review gate. Require at least two of: tracker-state reconciliation, retry/backoff, path/workspace safety, CI/review proof, or explicit rework semantics before deep inspection.
- Task 31: README claims of "isolated workspace" are insufficient evidence of security isolation. Distinguish deterministic per-issue workspace/path-safety from container/OS sandboxing and do not upgrade one into the other.

## Useful terminology / signatures
- Role axis: `manager`, `executor`, `auditor`, `verifier`, `reviewer`.
- Persistence axis: `resume`, `checkpoint`, `task state`, `recorded rounds`, `latest state`, `durable run`.
- Proof axis: `original requirements`, `stable task contract`, `independent evidence`, `executor text is only a claim`, `blocking constraints`, `complete clean aligned`, `read-only auditor`, `workspace mutation`, `completion guard`.
- Source inspection signature: search for the code path that converts verifier output into an accepted completion state, not merely the prompt that asks a verifier to review.
- Task-31 orchestration signatures: `reconcile_running_issues`, `retry_attempts`, worker `DOWN`, stall timeout, exponential/backoff retry, stale retry token, active/terminal tracker states, `workspace_key`, symlink/path escape, persistent workpad, ticket-provided `Validation`/`Test Plan`, PR feedback sweep, Human Review, Rework, Merging.
- Ecosystem-lineage signal: multiple independent projects explicitly advertising compatibility with the same named orchestration specification can reveal a canonical reference implementation worth deeper inspection.

## Candidate search skills awaiting second-task confirmation
### Role × persistence × proof conjunctive search
WHEN TO USE: Finding long-running or high-stakes agent/control architectures where the real value depends on reliable completion rather than generic agent capability.
PROCEDURE: Search using at least one term from each of role separation, durable state/resume, and evidence/original-requirements verification. Once a candidate is found, inspect the actual acceptance/completion guard, resume reconstruction path, failure persistence, and tests before reading broader benchmark claims.
WHY IT WORKED ON TASK 30: It surfaced AMAP-ML/LongHorizon-Harness and discriminated it from ramannanda9/agent-harness (strong checkpoint/orchestration but no equivalent independent original-contract auditor gate) and lordaeternus/agent-execution-harness (strong evidence/claim gates, but a lighter agent-instruction harness rather than the same manager/executor/auditor long-horizon runtime architecture).
STATUS: Awaiting confirmation on at least one additional distinct benchmark task; Task 31 reinforced the acceptance-path inspection principle but did not independently confirm the exact three-axis role search. Do not promote yet.

### Descendant cluster -> canonical spec -> transition verification
WHEN TO USE: Several low-attention repositories advertise compatibility with or implementation of the same named agent/orchestration specification.
PROCEDURE: (1) use descendants as discovery beacons rather than assuming they are the best artifact; (2) pivot to the named canonical spec/reference; (3) pin exact revision; (4) inspect the concrete control transitions required by the target task; (5) search tests for those transitions and their failure modes; (6) compare descendant-added features separately rather than attributing them to the canonical system.
WHY IT WORKED ON TASK 31: Harmonica, Stokowski and other issue-driven orchestrators repeatedly pointed to the Symphony specification. Pivoting to openai/symphony exposed the canonical Elixir reference, its retry/reconciliation state machine, collision-safe workspace lifecycle, extensive tests and proof-to-review WORKFLOW policy.
FAILURE MODES: descendant marketing can overstate what the canonical spec requires; a spec may exist without a maintained reference implementation; independent projects may all copy the same weak claim; popular canonical projects can distract from a technically superior descendant.
STATUS: One-task evidence only. Await a second distinct benchmark success before promotion to SEARCH_SKILLS.md.
