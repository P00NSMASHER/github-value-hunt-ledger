# Hunt 13 referral — bank-feed freshness/source-health boundary

Date: 2026-09-20
Lane: Node 13 Revenue Leverage — EXP-003 / CAP-018 / CAP-019

## Why this search resumed
EXP-003 says settlement can become final only when an independently observed bank/payroll record is `EXACT_UNIQUE` inside a **verified source window**. SEARCH_QUEUE explicitly stops generic commission/reconciliation discovery and permits search again only for a concrete provider/reference→bank or coverage gap. The remaining gap is source observation health: a successful local sync or cursor advance does not prove the upstream financial institution was recently contacted or that a no-return window is complete.

## Best new component — jantman/biweeklybudget
- URL: https://github.com/jantman/biweeklybudget
- Exact revision: `ac8870d49b27087b69dc47013adeedcf9271182b`
- Inspected: 2026-09-20
- Public provenance: source files state AGPL-3.0-or-later plus Section 7b attribution terms; Plaid service/data remain separately governed.
- Score: **24/30 — A3 B4 C4 D5 E5 F3.** Strong source-health component, not a complete settlement oracle.

### Implemented / tested
A September 2026 change added a persisted `PlaidItem.last_successful_update` that is explicitly distinct from local `last_updated`: the former is the timestamp Plaid says it last successfully updated Transactions from the institution; the latter is when this application last polled Plaid. `PlaidUpdater._do_item()` calls `/item/get`, persists both timestamps, and unit tests assert that a local run at one time can store an older provider-source update time. The extraction helper is tested for missing/None/nested-status cases and preserves timezone awareness.

### Why unusual
This is one of the few inspected implementations that makes **provider source freshness different from local pipeline success** a first-class stored fact. That is precisely the false-finality edge in EXP-003: a local bank-feed request can succeed while the source data are stale.

### Important limitations / red-team
The repo intentionally excludes `last_failed_update`, keeps only the current freshness value rather than immutable observation history, and does not use freshness as a hard money-bearing acceptance gate. Its updater still uses date-ranged `/transactions/get`, not `/transactions/sync`; therefore the source-freshness primitive should be combined with cursor/delta ingestion rather than copied as a complete bank-feed design. It also does not prove that absence of a matching settlement/return is complete for a requested economic window.

## Comparator — noelpena/plaid-actual-sync
- URL: https://github.com/noelpena/plaid-actual-sync
- Exact revision: `750992bb14c2abb85cdd8fe9558194ee12a7386d`
- Status: **WATCH / negative comparator, ~21/30.**

This implementation does the other half well: `/transactions/sync`, all-page accumulation, added/modified/removed handling, retry from the original cursor on `TRANSACTIONS_SYNC_MUTATION_DURING_PAGINATION`, and cursor persistence only after every mapped account import succeeds. It correctly notes that one Item cursor is shared across accounts and processes every mapping before advancing it. However, its health timestamps (`lastSyncedAt` / mapping `lastSyncAt`) are local execution times; it does not retrieve `status.transactions.last_successful_update` or `last_failed_update`. A successful sync can therefore be locally green while Plaid's bank contact is stale. This is not sufficient to authorize VERIFIED_EMPTY / no-return / final settlement.

## Official sample comparator — plaid/pattern
- URL: https://github.com/plaid/pattern
- Exact revision: `2ab540f260819a5c97008cfc0ac865891430374d`
- Status: component/reference only.

Plaid Pattern accumulates every `/transactions/sync` page before applying the diff, leaves the cursor unadvanced if a page/write fails, and advances the cursor after applying all added/modified/removed changes. Its own source explicitly warns that a production implementation should wrap the writes and cursor in a DB transaction. This is strong ingestion replay semantics but still not a source-currentness receipt; no `last_successful_update` usage was found in the current branch.

## Real failure evidence — OCA/bank-statement-import #883
Open issue #883 (created 2026-01-08; reporter reconfirmed 2026-07-26) documents transactions lost because the OCA Plaid adapter uses date-window `/transactions/get`; a transaction dated January 5 but not learned by Plaid until January 7 can be missed by a window that assumes event date ~= ingestion date. The reporter explicitly points to cursor-based `/transactions/sync` as the repair. This independently confirms that *window continuity is not change-stream completeness*.

## External authority checked
Current Plaid documentation says:
- `/transactions/sync` returns incremental added/modified/removed changes and exposes `transactions_update_status`; historical readiness is separate from a successful response.
- `SYNC_UPDATES_AVAILABLE` includes `initial_update_complete` / `historical_update_complete`; initial/historical preparation can be incomplete even when calls succeed.
- Plaid normally contacts institutions roughly one to four times per day; `/transactions/sync` and account balances can be cached.
- `/item/get` exposes Transactions `last_successful_update`; optional `/transactions/refresh` can force a refresh when appropriate.
- Therefore a cursor, HTTP success, empty delta, or local `lastSyncedAt` is not proof that the source was fresh enough for a settlement/return conclusion.

## Proposed EXP-003 source-observation receipt
Treat content and coverage as separate planes.

`CONTENT = PRESENT | VERIFIED_EMPTY`

`COVERAGE = VERIFIED_WINDOW | STALE | INITIALIZING | PARTIAL | UNAVAILABLE`

Minimum durable receipt fields:
- provider + stable Item/account IDs;
- query/product and exact observation purpose/window;
- local request started/finished times;
- provider `last_successful_update` and `last_failed_update` when available;
- initial/historical readiness flags/status;
- prior cursor, final cursor and all-pages-complete flag;
- added/modified/removed counts and durable-commit ID/hash;
- provider/item error state;
- freshness threshold/policy version;
- observed account set / expected source scope;
- optional refresh request ID/time and resulting provider update time;
- immutable observation ID so later good data cannot rewrite what was known earlier.

### Money-bearing rule
`VERIFIED_EMPTY` may be used to support **no settlement / no return** only when `COVERAGE=VERIFIED_WINDOW`. An empty delta with stale/initializing/partial/unavailable coverage stays UNKNOWN and must not mutate realized money.

### Mandatory new negatives for EXP-003
1. local sync succeeds but `last_successful_update` predates the payout/return window;
2. `last_failed_update` is newer than `last_successful_update`;
3. cursor drains to empty while `historical_update_complete=false`;
4. successful empty delta after an institution outage;
5. delayed/backdated transaction that arrives after its event-date poll window;
6. all pages fetched but durable commit fails before cursor advancement;
7. one shared Item cursor with a mapped sibling account failing import;
8. source scope/account set silently changes;
9. refresh requested but no newer provider update is observed;
10. later return appears after an earlier locally green empty observation.

## VALUE HANDOFF
**Capability delta:** CAP-019 gains a concrete, test-backed distinction between **local poll time** and **upstream institution update time**, plus a complementary crash-safe cursor implementation.

**Graph edge:** strengthens CAP-019 → CAP-018 → EXP-003 source-window authority. It does not itself establish finality.

**Radar signal:** supports RAD-006/money-state integrity: external outcome assurance needs *observation provenance and freshness*, not merely payment identity.

**Experiment impact:** EXP-003 should add an explicit coverage state separate from content state and plant the ten negatives above before any `NOT_FOUND` can be treated as economically meaningful.

**Commercial impact:** prevents a high-severity false-negative failure in Commission Payout Assurance: declaring a payout settled/no-return because the local bank-sync job was green while upstream bank data were stale.

**Negative knowledge:** local sync success, cursor continuity, empty deltas and lack of provider errors are individually insufficient to prove a bank/payroll observation window is current or complete.

## Cross-agent referral
Finance/payments and payroll lanes should look for provider-neutral implementations that turn source freshness/completeness into an immutable, machine-enforced gate rather than merely displaying `last_successful_update` in UI. Exact unanswered question: **what provider-specific evidence is sufficient to elevate `NOT_FOUND` to `VERIFIED_EMPTY` for a bounded settlement/return window without assuming cursor continuity equals source completeness?**
