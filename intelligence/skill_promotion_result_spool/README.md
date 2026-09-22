# Skill promotion result spool

Immutable evidence submissions for mutations already present in `SKILL_PROMOTION_QUEUE.md`.

## Contract

1. Start from `../SKILL_PROMOTION_RESULT_TEMPLATE.json`.
2. Bind to the exact current `skill_promotion_id`, `skill_promotion_sha256`, `skill_eval_result_id`, and `evaluation_result_sha256`.
3. Record at least two distinct observed success-task IDs before promotion can advance.
4. Held-out evidence must identify a frozen held-out set and frozen evidence bundle by SHA-256. Five held-out tasks at 100% pass and zero regressions are required before VERIFIED.
5. Adversarial and adjacent-domain passes require separately frozen SHA-256 evidence.
6. Curator approval requires an explicit curator identity plus frozen approval evidence.
7. Canary evidence is bound to distinct hunter IDs and a frozen SHA-256 bundle. Three canary hunters and zero regressions are required for `GLOBAL_ELIGIBLE`.
8. Any held-out or canary regression produces `QUARANTINED`.
9. Sensitive or benchmark-contaminated promotion evidence is blocked.
10. Spool files are immutable; correct errors with a new result ID.

`GLOBAL_ELIGIBLE` is **not GLOBAL**. The intake never writes a live skill and never promotes globally. A separate Integrator approval is still required.
