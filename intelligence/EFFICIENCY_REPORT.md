# HUNTER EFFICIENCY REPORT

Observe-first efficiency metrics. The network gets no credit for shallow work merely because it was cheap; duplicate avoidance counts only when prior evidence made a deep inspection redundant.

- Discovery runs: **22**
- Preflight-instrumented runs: **0**
- Candidate preflight checks: **0**
- Known-candidate preflight hits: **0**
- Duplicate deep inspections avoided: **0**
- Deep inspections per retained candidate: **1.51**
- Registry duplicate observations: **79 (4.4%)**
- Registry unknown-revision records: **91**
- Tool-call denominators observed on **4/22** discovery runs
- Elapsed-time denominators observed on **8/22** discovery runs

## Interpretation

- This is the baseline before prospective preflight-efficiency telemetry began; historical skips were not invented.
- A preflight hit does not automatically mean skip: reopen for a new revision, new capability/evidence delta, contradiction, experiment need or provenance repair.
- Count an avoided deep inspection only when the current assignment would otherwise have repeated substantially the same evidence work.
- Falling deep-inspection cost is useful only if recall, verifier quality and downstream outcomes remain stable or improve.
- Tool-call and elapsed-time comparisons are valid only where those denominators were actually observed.
- Do not optimize for a high avoidance count; the goal is less redundant work, not less curiosity.
