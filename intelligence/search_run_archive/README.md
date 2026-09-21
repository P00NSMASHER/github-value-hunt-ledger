# Reviewed search-run submissions

This directory preserves superseded submissions outside automatic intake. The
integrator does not silently choose a winner when the same run ID has different
contents. `reconciliations.json` records each explicit decision, original path,
archive path, hash of the preserved bytes, and hash of the accepted canonical
record at review time.

On 2026-09-21, the old HUNTER-11 C/C++ proof-authority submission was moved here
without changing its bytes. Its run ID already existed in `search_runs.jsonl` as
a retrospective evidence-repair record with unknown denominators left null. The
legacy submission claims different prospective counts and includes incompatible
query-family and coverage metadata. The accepted retrospective record remains
unchanged; the conflicting values were not adopted.

No new run was recovered by this reconciliation. The HUNTER-13 rule-authority
submission remains in the active spool as an exact replay of its existing
canonical row. The canonical ledger still contains 18 runs at reconciliation.
