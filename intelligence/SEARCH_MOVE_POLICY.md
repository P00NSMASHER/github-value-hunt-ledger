# SEARCH MOVE CURRICULUM

Mode: **observe_only_insufficient_evidence**

This is a cautious retrieval-method curriculum, not an autonomous command. It balances learning which search moves work with preserving unusual/underused discovery paths.

- Sufficient move types: **0**
- Exploration floor: **100%**
- Active recommendation: **no**

| Move type | Recommended share | Uses | Productive hit | Retrieval-limited | Evidence |
|---|---:|---:|---:|---:|---|
| direct_domain_search | 9.1% | 0 | — | — | insufficient |
| code_signature_search | 9.1% | 0 | — | — | insufficient |
| official_source_trace | 9.1% | 0 | — | — | insufficient |
| organization_graph | 9.1% | 0 | — | — | insufficient |
| contributor_or_commit_lineage | 9.1% | 0 | — | — | insufficient |
| paper_to_code_lineage | 9.1% | 0 | — | — | insufficient |
| package_or_dependency_graph | 9.1% | 0 | — | — | insufficient |
| adjacent_domain_invariant | 9.1% | 0 | — | — | insufficient |
| independent_comparator | 9.1% | 0 | — | — | insufficient |
| history_archaeology | 9.1% | 0 | — | — | insufficient |
| other | 9.1% | 0 | — | — | insufficient |

## Use

- While inactive, interpret shares only as an exploration curriculum: diversify methods and collect telemetry.
- Once active, use high-evidence moves as priors, not mandatory recipes; assignment-specific anchors still control.
- Keep at least one materially different exploration path available on true discovery tasks when budget permits.
- Revalidate stale move priors after material ecosystem/tool changes.
- Never convert a retrieval-limited move into evidence that a capability is absent.
