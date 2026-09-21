# Immutable search-run intake

Each worker saves one completed search-run object in a new, uniquely named
`intelligence/search_run_spool/<run-id-with-safe-filename>.json` file. Use the
actual run ID inside the object. Keep source files unchanged after publication.
Workers do not append or rewrite the shared `search_runs.jsonl` ledger.

Run drafts prepared by `ti_prepare_run.py` contain an `_draft` marker and are
rejected by intake. Record the actual observations and complete review before
removing `_draft`, replacing the incomplete-draft note, and publishing the file.
Removing the marker alone does not turn a planned run into an observed result.

The integrator runs:

```sh
python tools/ti_sync.py
python tools/ti_ingest_runs.py --check
python tools/ti_ingest_runs.py --write
```

Continue the full intelligence build and validators before committing the ledger
and derived reports together. The legacy `intelligence/search_runs/*.json`
directory is also read; new workers should use `search_run_spool` consistently.

`--check` is read-only and returns a JSON report with existing, submitted,
replayed, pending, and error counts. Valid pending rows are not a check failure.
`--write` rejects the entire batch on any conflict or invalid submission; it
appends unique valid run IDs in deterministic order. Exact JSON-equivalent
replays are harmless. A reused run ID with changed values is an error, including
differences between a missing field and an explicit null. No value, timestamp,
measurement denominator, strategy, or provenance field is inferred or repaired.
Original ledger bytes and submission files are retained.

New rows are checked against the existing search-run schema and core registry,
count, disposition, and benchmark-set invariants. The dependency-free schema
evaluator supports only the keywords currently used in that schema and rejects
unknown keywords. It is not a general JSON Schema implementation. Existing exact
replays are not retroactively upgraded to a newer schema. Execution, dispatch,
coverage, and other cross-file validators remain required during the full build.

Only one integrator may write the canonical ledger. A local lock prevents
cooperating integrators from writing simultaneously; Git workflow concurrency
must serialize remote persistence as well. Direct ledger writers do not honor
this lock. The append operation checks for ledger changes and never rewrites old
bytes. A crashed integrator can leave a lock directory or an incomplete tail:
inspect the ledger and retained source records before removing a stale lock or
retrying an I/O failure.

Resolve conflicts by reviewing evidence and preserving both versions, never by
blindly overwriting the accepted row. An explicitly reviewed superseded source
may be moved byte-for-byte to `search_run_archive/` with original and canonical
hashes and a reason. That archive is outside automatic intake.
