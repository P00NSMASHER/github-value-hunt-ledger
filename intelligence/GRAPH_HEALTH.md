# GRAPH HEALTH REPORT

- Curated edges: **132**
- Derived attribution edges: **47**
- Capability nodes: **19**
- Capabilities touched by measured search runs: **8**

## Highest-priority capability gaps

| Capability | Evidence | Components | Run attention | Experiments | Gap score | Missing piece |
|---|---|---:|---:|---:|---:|---|
| CAP-002 — Reviewed, versioned identity mastering | source_or_test_validated | 1 | 0 | 0 | 7 | datasets/customer identities separate |
| CAP-007 — Proof obligations and next-best-evidence routing | source_or_test_validated | 1 | 0 | 0 | 7 | domain policy provenance is external |
| CAP-008 — Structured invoice compliance/validation | source_or_test_validated | 1 | 0 | 0 | 7 | official rule-pack/version authority must be pinned |
| CAP-009 — Schedule verification and conservative repair | source_or_test_validated | 1 | 0 | 0 | 7 | labor/domain rules remain external |
| CAP-012 — Permit event versioning and semantic source QA | source_or_test_validated | 1 | 0 | 0 | 7 | jurisdiction completeness/semantics vary |
| CAP-013 — Cross-vendor scientific data normalization | source_or_test_validated | 1 | 0 | 0 | 7 | vendor formats/specs and buyer fixtures separately governed |
| CAP-004 — Deterministic freight rerating and exception math | benchmarked | 1 | 0 | 0 | 6 | correct math cannot cure wrong authority |
| CAP-019 — Source-authority observation receipts | source_or_test_validated | 1 | 1 | 1 | 6 | whole-run completeness remains source-specific; a cursor is not completeness proof. Run synthetic ERP/bank source cases where transport/auth/partial failure may never authorize VERIFIED_EMPTY or “no return.” |
| CAP-001 — Evidence-gated document facts | source_or_test_validated | 3 | 0 | 0 | 5 | domain calibration and contractual/legal authority remain external |
| CAP-005 — Physical-event-to-entitlement evidence | runtime_or_stack_proven | 1 | 0 | 0 | 5 | physical truth and commercial authority remain separate |
| CAP-014 — Virtual industrial endpoint / pre-FAT acceptance | source_or_test_validated | 3 | 0 | 0 | 5 | standards/certification separate |
| CAP-003 — Freight contract/rate authority reconstruction | benchmarked | 3 | 0 | 0 | 4 | buyer/carrier authority is population-specific |

## Graph policy

- High gap score means **information value**, not commercial priority.
- Prefer searches that close a named missing edge in an active experiment over searches that add another similar implementation.
- A capability with many repositories but no experiment or outcome edge is a research cluster, not yet a validated asset.
- Independent challengers and negative controls can be more valuable than a second implementation of the same mechanism.
