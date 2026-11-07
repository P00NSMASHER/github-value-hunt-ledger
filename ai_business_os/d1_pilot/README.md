# Local D1 intake measurements

These results are local workerd D1 counters for the actual freight and group Pages handler functions. The harness uses Miniflare 4.20260730.0 with its pinned workerd build, installs all five freight intake migrations into a fresh disposable database, and captures each D1 result's `meta.rows_read` and `meta.rows_written`. For handler calls to `first()`, it retrieves the first row from the same bound statement's `all()` result so that metadata remains observable. The fixture captures every Turnstile and mail request. It makes zero external sends. The numbers do not measure production billing.

Run from this directory with Node 24, Python 3 and a local npm installation.

```sh
npm ci --no-audit --no-fund
node measure.mjs --without-feed
node measure.mjs
```

Both commands initialize a new Miniflare instance. The first uses the source migrations only. The second adds the pilot's feed trigger. The measured values below are reads / writes on November 7, 2026. Each accepted single submission follows a rejected Turnstile request from the same fixture IP. The concurrent pair uses a fresh IP and one idempotency key. Exact concurrent statement interleaving can vary across runs.

| Operation | Existing intake | With feed |
|---|---|---|
| Invalid freight or group payload | 0 / 0 | 0 / 0 |
| First Turnstile rejection from an IP | 2 / 6 | 2 / 6 |
| Second Turnstile rejection from that IP | 4 / 2 | 4 / 2 |
| Accepted freight or group, after a rejection | 8 / 9 | 9 / 12 |
| Replay or conflicting key | 1 / 0 | 1 / 0 |
| Two concurrent freight submissions, one receipt | 12 / 15 | 14 / 18 |
| Attempt beyond the 5/hour cap | 2 / 0 | 2 / 0 |
| Catch-up query, three eligible rows, limit 25 | — | 6 / 0 |
| Catch-up query, cursor at end | — | 1 / 0 |

Pre-verification writes occur in both versions because the handlers reserve rate capacity before checking Turnstile. The sixth attempt had zero writes. `EXPLAIN QUERY PLAN` showed a primary key range seek on feed sequence, a covering index lookup for the QA register and a unique-index lookup on inquiry reference. A page returns a maximum of the requested number of source sequence entries. A QA exclusion occupies a page slot and the private cursor advances past it within the same transaction that stores eligible deliveries.

The harness checks HTTP status, duplicate receipt identity and local mail capture. It collects the catch-up SQL directly from the pilot source. The per-query workload excludes schema installation, query-plan inspection, private SQLite state writes and CRM API calls. [Baseline JSON](baseline.json) · [Feed JSON](metrics.json)
