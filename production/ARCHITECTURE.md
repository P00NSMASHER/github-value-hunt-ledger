# Production Architecture — Verifier-Gated Technology Intelligence

## Purpose
Turn the GitHub Value Hunt from scheduled research prompts into a measurable learning system while preserving the frozen 50-task A/B benchmark.

## Non-negotiable invariants
1. No hunter writes MASTER directly.
2. No hunter promotes its own skill to global scope.
3. No claim becomes VERIFIED without an exact revision and frozen evidence manifest.
4. The verifier cannot mutate the evidence/workspace it judges.
5. README/demo-only evidence cannot establish a load-bearing implementation claim.
6. Accidental credentials, private/personal data, confidential material, leaked trade secrets, nonpublic classified material and unauthorized-access artifacts never enter shared research memory.
7. Untrusted repository code never executes on a persistent hunter host.
8. A crashed/stale task can be reclaimed by lease generation without duplicating trusted-state transitions.
9. Current benchmark treatment remains frozen until scoring is complete.

## Responsibility boundaries
- Persistent hunter runtime: Prime Agent is the intended worker substrate after pinned-revision verification. It owns working context, lane memory, hypotheses, local lessons and specialist delegation.
- Authoritative research state: external structured state owns candidates, claims, evidence, verifications, skill versions, leases, promotions and outcomes.
- Evidence store: content-addressed immutable manifests freeze exact revisions and load-bearing evidence before verification.
- Verifier: separate read-only session/process evaluates the frozen packet against proof obligations.
- Skill verifier: separate from finding verifier; decides whether a proposed search method transfers on held-out/adversarial tasks.
- Integrator: only role allowed to promote MASTER and fleet-wide SEARCH_SKILLS.
- Governance plane: policy/budget/approval/kill-switch layer outside the hunter prompt.
- Sandbox broker: disposable execution only; returns artifacts/hashes, never host access.

## Candidate state machine
DISCOVERED -> INVESTIGATING -> EVIDENCE_FROZEN -> VERIFICATION_PENDING -> PASS -> deterministic commercial gate -> STRONG_COMPONENT | MASTER_CANDIDATE -> Integrator approval -> MASTER.

Fail closed on missing exact revision, missing frozen evidence hash, sensitive-source contamination, critical contradiction, verifier BLOCKED/CONTRADICTED, or a load-bearing claim supported only by README/demo prose.

## Skill state machine
Observed once -> LOCAL lesson.
Two distinct successes -> STAGED candidate.
STAGED -> >=5 held-out tasks + 100% pass + zero regressions + adversarial pass + adjacent-domain pass -> VERIFIED.
Curator/Integrator approval -> CANARY.
CANARY on >=3 hunters with zero regression -> GLOBAL.
Any regression -> QUARANTINED.

## Coordination
Tasks are claimed using task/owner/generation/expiry leases. A live lease blocks duplicate work. Expired leases are reclaimable. Renewal requires matching owner+generation. Stale work is evidence, not trusted progress. Referrals are typed handoffs containing candidate, exact question, evidence snapshot, destination role/lane and task/lease identity.

## Specialist roles
- CODE_INSPECTOR — implementation/source/tests/schemas/state transitions only.
- SCIENCE_VALIDATOR — paper status, method, experiment-vs-simulation, replication.
- PATENT_ANALYST — prior art/families/convergence; no infringement opinions.
- ECOSYSTEM_ANALYST — independent implementations, packages, standards, production adoption.
- COMMERCIAL_ANALYST — buyer/pain/wedge/economics using only verifier-supported technical claims.
- RED_TEAMER — receives no promotion score; attempts to falsify novelty, completeness, feasibility and buyer thesis.

## Promotion gate
Independent verifier PASS is necessary but not sufficient.
- 0-18: REJECT.
- 19-23: WATCH.
- 24-26: STRONG_COMPONENT; Integrator review if uniquely important.
- 27-30 with evidence_quality>=4 and rights_operability>=4: MASTER_CANDIDATE.
- MASTER always requires Integrator approval.

## Current experiment status
The frozen A/B benchmark remains authoritative. [`benchmark/SCOREBOARD.md`](../benchmark/SCOREBOARD.md) is the source for current completion counts, matched scores, recall failures, effort limitations and the integrator's conclusion; do not maintain a second checkpoint here. Architecture superiority is not established merely by adding contracts or search skills. Benchmark workers must remain blind to gold, sibling results and scored candidate identities until their condition is frozen; the scoreboard is an operator/integrator source, not a discovery input.

Operational workers use [`intelligence/WORKER_RUNBOOK.md`](../intelligence/WORKER_RUNBOOK.md) for current run and telemetry contracts. This architecture remains staged as described in [`STATUS.md`](STATUS.md); documentation and prototype tests do not establish deployed runtime enforcement. See the [2026-09-21 strategy upgrade](../intelligence/STRATEGY_UPGRADE_2026-09-21.md) for the current improvement scope.

## Production acceptance after frozen benchmark
Before fleet cutover:
- mean paired advantage target >= +1/25 on a harder sealed holdout;
- 95% bootstrap interval not materially negative;
- false-promotion rate <= control;
- zero sensitive-source promotions;
- zero verifier bypasses;
- >=3 verified skills improve unseen tasks;
- cost per validated strong/MASTER finding <=1.25x control unless quality gain >=+2/25;
- restart, lease recovery, evidence mutation, poisoning, kill-switch and sandbox tests pass.

## Repository roles
- Prime Agent: persistent worker runtime; local refine only; global refine intercepted.
- LongHorizon-Harness: adapt Manager/Executor/Auditor invariants, not a second core runtime.
- ASG-SI: adapt verifier-gated skill-promotion concept; do not depend on unclear source rights.
- Preloop: preferred initial policy/budget/approval/observability plane if deployed.
- Archestra: alternative enterprise control plane; evaluate separately because of AGPL/enterprise licensing.
- Symphony: downstream implementation queue after a research finding becomes an approved build task.
- Anton: memory/vault reference, not a second core runtime.
- AI-Scientist-v2: branching-hypothesis/search inspiration only.

## Rollout
1. Keep current benchmark untouched.
2. Run three live SHADOW hunters on separate state files with no MASTER writes.
3. Compare shadow yield/cost/overturn rate with ordinary live hunt.
4. After benchmark ends, freeze next-gen prompts/skills and create a harder sealed holdout.
5. Canary 3 -> 7 -> 15 persistent hunters only after acceptance gates.
