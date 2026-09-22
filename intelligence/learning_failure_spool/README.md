# Learning failure spool

Immutable submissions describing **reproducible defects in the hunter system itself**.

Use this only when a hunter/search skill/query family/tool/prompt/workflow/routing or memory mechanism demonstrably failed in a way that can be reproduced and regression-tested. Ordinary repository rejection, a disappointing candidate, or a generic no-find is not automatically a learning failure.

## Contract

1. Start from `../LEARNING_FAILURE_TEMPLATE.json`.
2. Use one unique `*.json` file per failure.
3. Include the canonical origin `RUN:...` ID, reproduction steps, evidence refs, and a concrete proposed regression test.
4. Never include credentials, private/personal data, confidential material, leaked trade secrets, or other sensitive payloads. If sensitive material was involved, submit only sanitized metadata and set `sensitive_material_involved=true`; the learning engine will block repair learning from it.
5. Benchmark-contaminated observations set `benchmark_contaminated=true` and are blocked from learning.
6. Spool files are immutable submissions. Correct errors with a new superseding packet rather than silently rewriting history.

`tools/ti_learning_state.py` assesses these packets and exposes only `QUEUED` or `BLOCKED` state. A queued failure is **not** an approved repair and does not change a live hunter. Repairs still require a regression test, reviewed diff, skill evaluation, and the existing held-out/canary promotion gates.
