# Skill evaluation result spool

Immutable evaluator submissions for candidates already present in the generated skill-evaluation queue.

## Contract

1. Start from `../SKILL_EVAL_RESULT_TEMPLATE.json`.
2. Copy the exact current `skill_eval_id`, `skill_eval_sha256`, `repair_candidate_id`, and `candidate_record_sha256`.
3. Freeze separate SHA-256 fingerprints for mutate-dev and promotion-test sets. They must differ.
4. The mutator must not see promotion-test data. Set `mutator_saw_promotion_test=false` only when that isolation actually held.
5. Record distinct mutator and evaluator identities; they must differ. The evaluator/controller must not be modified by the candidate, and the mutator must not open the sealed holdout.
6. Scores are normalized to [0,1] and must be backed by durable evaluation evidence.
7. Sensitive or benchmark-contaminated evaluation evidence is blocked.
8. Spool files are immutable. Correct mistakes with a new result ID.

Passing this intake produces only `STAGED_MUTATION`. It still cannot become global until the existing distinct-success, held-out, adversarial, adjacent-domain, curator and canary gates pass.
