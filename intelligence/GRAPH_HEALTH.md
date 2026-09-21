# GRAPH HEALTH REPORT

- Curated edges: **132**
- Derived attribution edges: **615**
- Capability nodes: **19**
- Query-family nodes: **41**
- Search-objective nodes touched: **10**
- Exact search-surface nodes touched: **112**
- Normalized surface-family nodes touched: **9**
- Capabilities touched by measured search runs: **16**

## Highest-priority capability gaps

| Capability | Evidence | Components | Graph support | Run attention | Experiments | Gap score | Missing piece |
|---|---|---:|---:|---:|---:|---:|---|
| CAP-001 — Evidence-gated document facts | source_or_test_validated | 3 | 4 | 2 | 1 | 4 | domain calibration and contractual/legal authority remain external |
| CAP-002 — Reviewed, versioned identity mastering | source_or_test_validated | 2 | 4 | 1 | 1 | 4 | datasets/customer identities separate |
| CAP-003 — Freight contract/rate authority reconstruction | benchmarked | 3 | 3 | 0 | 0 | 4 | buyer/carrier authority is population-specific |
| CAP-004 — Deterministic freight rerating and exception math | benchmarked | 2 | 3 | 0 | 0 | 4 | correct math cannot cure wrong authority |
| CAP-008 — Structured invoice compliance/validation | source_or_test_validated | 3 | 7 | 3 | 0 | 4 | pin official rule-pack/table bytes, source identity, effective interval, parser/map digest, imported-row-set digest and validator/runtime revision in one authority receipt |
| CAP-012 — Permit event versioning and semantic source QA | source_or_test_validated | 2 | 1 | 1 | 1 | 4 | jurisdiction completeness/semantics vary |
| CAP-014 — Virtual industrial endpoint / pre-FAT acceptance | source_or_test_validated | 3 | 5 | 2 | 1 | 4 | secsgem's correction is source and local-test verified, not yet a real raw-HSMS/T3 capture, and Dreamine was not runtime-executed in the correcting run. Use a neutral raw-HSMS harness for EC-ATOMIC-SHARED and EC-DUPLICATE-POLICY, record every correlated message, maintain an independent logical T3 clock and independently read post-state. Seek a third engine only after an observed endpoint disagreement. |
| CAP-015 — Prospective, leakage-resistant prediction and evaluator-grain evidence | source_or_test_validated | 10 | 4 | 3 | 1 | 4 | first-party OEDI ZIP digest/bytes remain unresolved in the current evidence chain. Verify the current first-party artifact against the external expected digest, byte-inspect source schema/time/null semantics, then freeze the composite-event + unique-spell evaluator manifest before running policy scores. |
| CAP-019 — Source-authority observation receipts | source_or_test_validated | 4 | 4 | 10 | 3 | 4 | whole-run completeness and negative authority remain source-specific. Execute the authorized ERP credit-endpoint test plus first-party cross-status SAM receipts and day-boundary rule fixtures; transport/auth/partial/unrepresentable states may never authorize VERIFIED_EMPTY, NOT_APPLIED or CURRENT_VERIFIED. |
| CAP-005 — Physical-event-to-entitlement evidence | runtime_or_stack_proven | 2 | 1 | 0 | 0 | 3 | physical truth and commercial authority remain separate |
| CAP-016 — Money-state integrity / deterministic close truth | watch | 6 | 3 | 8 | 4 | 3 | — |
| CAP-006 — Settlement-grounded recovery attribution | runtime_or_stack_proven | 6 | 3 | 1 | 1 | 2 | realized dollars require external outcome evidence |

## Graph policy

- Query families belong to broader objectives; exact surfaces belong to normalized surface families.
- These provenance edges explain how knowledge was found; they are not causal proof that a strategy/surface produced the outcome.
- Prefer searches that close a named missing edge in an active experiment over another similar implementation.
- A capability with many repositories but no experiment/outcome edge remains a research cluster.
- Independent challengers and negative controls can be more valuable than a second implementation of the same mechanism.
