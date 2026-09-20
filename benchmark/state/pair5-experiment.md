# Pair 5 — EXPERIMENT persistent state

## Validated reusable lessons
- Task 30: README-level "verification" claims are not enough. High-signal implementation checks are: (a) executor output explicitly treated as a claim, (b) completion fail-closed unless a verifier/auditor confirms original requirements, (c) blocking constraints prevent `complete`, (d) verifier/auditor mutation is detected or restored, and (e) resume reconstructs planning context from durable recorded state. These discriminators separated a true verification loop from generic orchestration/checkpoint frameworks.

## Failed search patterns
- Broad repository searches centered only on phrases like `agent harness`, `manager verifier`, or `long horizon agent` produced high generic-framework noise and many systems with memory/checkpointing but no independent original-requirements audit boundary.
- Searching for "auditable" alone over-selected logging/trace/evidence-recording systems where the executing agent can still effectively self-certify completion.

## Useful terminology / signatures
- Role axis: `manager`, `executor`, `auditor`, `verifier`, `reviewer`.
- Persistence axis: `resume`, `checkpoint`, `task state`, `recorded rounds`, `latest state`, `durable run`.
- Proof axis: `original requirements`, `stable task contract`, `independent evidence`, `executor text is only a claim`, `blocking constraints`, `complete clean aligned`, `read-only auditor`, `workspace mutation`, `completion guard`.
- Source inspection signature: search for the code path that converts verifier output into an accepted completion state, not merely the prompt that asks a verifier to review.

## Candidate search skills awaiting second-task confirmation
### Role × persistence × proof conjunctive search
WHEN TO USE: Finding long-running or high-stakes agent/control architectures where the real value depends on reliable completion rather than generic agent capability.
PROCEDURE: Search using at least one term from each of role separation, durable state/resume, and evidence/original-requirements verification. Once a candidate is found, inspect the actual acceptance/completion guard, resume reconstruction path, failure persistence, and tests before reading broader benchmark claims.
WHY IT WORKED ON TASK 30: It surfaced AMAP-ML/LongHorizon-Harness and discriminated it from ramannanda9/agent-harness (strong checkpoint/orchestration but no equivalent independent original-contract auditor gate) and lordaeternus/agent-execution-harness (strong evidence/claim gates, but a lighter agent-instruction harness rather than the same manager/executor/auditor long-horizon runtime architecture).
STATUS: Awaiting confirmation on at least one additional distinct benchmark task; do not promote to SEARCH_SKILLS.md yet.
