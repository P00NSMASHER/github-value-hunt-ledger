# RecoveryOS Phase 3 — Step 2 Large-Scale Reliability & Performance

Status: **COMPLETE AS AN ENGINEERING BENCHMARK; NOT A PRODUCTION SLA**  
Completed: 2026-10-07

This step answers a less glamorous but more useful question than "does it scale?":

> Exactly which parts have actually been exercised at scale, what did they do,
> and which claims would still be fiction?

## 1. CPU rating path: one million records actually executed

A dedicated GitHub Actions benchmark exercised the real RecoveryOS path:

canonical record construction -> record hash -> authority resolution ->
six-mode deterministic rerating -> rating hash.

Modes were evenly cycled across:

- Parcel;
- LTL;
- TL;
- Intermodal;
- Air;
- Ocean.

Environment:

- GitHub-hosted Ubuntu 24.04 runner;
- Python 3.11.17;
- one Python process;
- no PostgreSQL/network/document-parser/carrier API in the timed path.

Source run:

- canonical conservative workflow run: **37572874306**;
- canonical job: **112635211557**;
- a second successful same-commit run was materially faster, which is retained as evidence of hosted-runner variability rather than cherry-picked as the baseline;
- source commit: `a68b060550e3f44891bc7603296c141d4d8523e4`;
- report hash:
  `ff7b4e0fe67573b0ba144f79ea308105f1b81dbb1094f8a1e1fb0d1f2cfa147e`.

### Measured results

| Tier | Trials | Median records/s | Slowest | Fastest | Median sampled p99 | Max RSS |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10,000 | 5 | 4,069.04 | 4,028.95 | 4,075.35 | 0.3131 ms | 21.76 MB |
| 100,000 | 3 | 4,128.73 | 4,077.97 | 4,136.76 | 0.3104 ms | 21.89 MB |
| 1,000,000 | 1 | 4,152.92 | 4,152.92 | 4,152.92 | 0.3038 ms | 21.89 MB |

The one-million-record primary pass completed in **240.79 seconds**. A complete
one-million-record replay completed in **240.93 seconds** at **4,150.65 records/s**.

A separate successful same-commit hosted-runner execution produced roughly
**8,628 records/s** at one million records. That nearly 2× spread is the most
important performance warning in this section: hosted GitHub runners are not a
capacity contract. Step 2 therefore anchors regression thresholds to the slower
successful run rather than publishing the faster run as if hardware did not matter.

Every measured scale trial had:

- zero unexpected review-routed records;
- deterministic replay;
- identical aggregate billed/expected/variance dollars on replay;
- identical ordered result digest on replay.

That is meaningful evidence of the deterministic compute core. It is not evidence
that the web application can accept 8,600 HTTP invoice submissions per second.

## 2. Failure injection

A 10,000-record run deliberately removed controlling authority every 97 records.

Expected review-routed records: **104**.  
Actual review-routed records: **104**.  
Automatically rated records: **9,896**.  
Replay digest equal: **yes**.

This matters more than another happy-path speed number. Missing commercial
authority remained review-required under load instead of quietly turning into a
zero/default rate.

## 3. Interruption / retry correctness

The benchmark then simulated a worker processing 10,000 records in 1,000-record
chunks and failing after four committed chunks.

Recovery deliberately replayed the last uncertain chunk, mimicking
at-least-once execution after response loss.

Results:

- uncertain chunks replayed: **1**;
- baseline digest == resumed digest: **yes**;
- baseline variance == resumed variance: **yes**;
- duplicate aggregate dollars after replay: **no**;
- aggregate variance in both paths: **24,424,145 cents**.

This is a deterministic chunk/replay test, not a live kill/restart of a
distributed worker fleet. The distinction is irritating but important.

## 4. Memory behavior

Timing and memory instrumentation were separated because Python
`tracemalloc` itself materially distorts an allocation-heavy benchmark.

The separate 10,000-record memory probe measured:

- Python peak tracked allocations: **0.91 MB**;
- process maximum RSS: **22.89 MB**.

The timed 10K/100K/1M runs remained near **21.9 MB RSS**, consistent with the
streaming benchmark not retaining the population.

That does not prove the deployed API/database pipeline has the same memory
profile.

## 5. Production data-plane stress evidence

Synthetic database fixtures were executed against the RecoveryOS Floot-managed
PostgreSQL data plane inside explicit transactions and then rolled back.

The write path inserted synthetic ingress receipts while executing the real
per-tenant append-only audit trigger for every row.

A performance issue was immediately visible: the audit trigger repeatedly needs
the current tenant chain head. The data plane did not have an index explicitly
matching that lookup. Step 2 added:

`recovery_audit_chain_head_idx
(tenant_id, occurred_at DESC, id DESC)`

After warm-up, three repeated 10,000-row trials measured:

| Trial | Insert time | Rows/s | Full chain verify |
| ---: | ---: | ---: | ---: |
| 1 | 1,283.994 ms | 7,788.20 | 27.580 ms |
| 2 | 1,321.074 ms | 7,569.60 | 30.525 ms |
| 3 | 1,299.048 ms | 7,697.94 | 27.810 ms |

Median 10K bulk-write throughput: **7,697.94 rows/s**.

A larger **100,000-row** transaction then executed the same audited write path in
**14,170.792 ms**, or **7,056.77 rows/s**. Full audit-chain verification took
**333.871 ms** and returned **0 invalid hashes / 0 broken links**. The transaction
was rolled back after verification.

All measured post-index write trials produced **0 invalid audit hashes and 0 broken links**.

Critical qualification: this is one bulk SQL statement, one tenant, and no HTTP
round trip per row. Calling it "7,700 API requests per second" would be nonsense.

## 6. The load test found real application problems

The exercise exposed more than benchmarks. It found scalable correctness and
query-shape problems in the deployed app.

### Dashboard totals were wrong at scale

Before this step, the dashboard fetched only the top 100 findings and then used
that limited array to calculate:

- total findings;
- challenger-only findings;
- candidate difference dollars.

Once a tenant had more than 100 findings, the KPI cards could therefore be
materially wrong.

That was repaired. Totals now aggregate across the complete tenant population in
PostgreSQL while the human review queue remains capped separately.

### Several endpoints loaded entire histories

Before Step 2:

- dashboard loaded all review dispositions into JavaScript;
- confirmed-findings loaded all findings + dispositions before filtering;
- payment list fetched all tenant payment events/authorizations even though it
  returned only 250 instructions;
- payment analytics reconstructed all payment state in application memory.

Those paths were changed to database-side latest-state queries and bounded
result sets.

Indexes added for the actual query shapes:

- `recovery_findings_review_queue_idx`;
- `recovery_review_latest_idx`;
- `recovery_payment_event_latest_idx`;
- `recovery_payment_instruction_recent_idx`.

## 7. Read-query tests after hardening

A synthetic tenant with 10,000 records + 10,000 findings measured:

- full finding totals aggregate: **12.972 ms**;
- unresolved top-100 review queue: **17.417 ms**;
- confirmed-count query with no dispositions: **0.542 ms**;
- audit chain after 20,001 generated events:
  **0 invalid hashes / 0 broken links**.

A harsher fixture used:

- 10,000 findings;
- 10,000 CONFIRM dispositions;
- 1,000 later REJECT dispositions.

Correct latest-state result: **9,000 confirmed**.

Measured:

- confirmed count: **9.631 ms**;
- confirmed top-500 list: **163.681 ms**;
- audit chain after 31,001 generated events:
  **0 invalid hashes / 0 broken links**.

### The critical result

**163.7 ms for the confirmed-list DB query at only 10K findings is the largest
measured query concern in this step.**

It is acceptable for a human-facing request at this size, but it is not evidence
that the same query will remain comfortable at 100K or 1M findings. That path
needs keyset pagination/materialized latest-state architecture if later scale
tests show nonlinear growth.

## 8. What was not proven

Step 2 does **not** prove:

- 10 million or 100 million records actually processed;
- 1M rows persisted in the production database (100K was executed successfully);
- concurrent writers to the same tenant;
- concurrent writers across many tenants;
- end-to-end HTTP requests/second;
- serverless cold-start latency;
- SFTP/X12/PDF extraction throughput;
- carrier/provider API latency;
- AI analytics latency;
- human-review throughput;
- 99.99% availability;
- production SLA performance.

The CPU-only projection from the actual one-million run is about:

- 10M records: **40.1 minutes** at the conservative canonical 1M rate;
- 100M records: **6.69 hours** at that rate.

Using the slowest successful observed tier gives roughly **41.4 minutes** and
**6.89 hours**.

Those are explicitly **projections, not test results**.

## 9. Permanent regression gate

The repository now contains a dedicated Phase 3 performance workflow and
machine-readable baseline.

CI requires:

- executed 10K / 100K / 1M tiers;
- full deterministic replay;
- minimum throughput floor of 3,000 records/s per tier;
- sampled p99 below 0.75 ms;
- RSS below 128 MB;
- exact missing-authority review routing;
- deterministic interruption recovery;
- no duplicate aggregate dollars after uncertain-chunk replay;
- bounded memory probe.

These thresholds are deliberately looser than the slower successful benchmark.
Two same-commit runs differed by roughly 2×, which makes a 6,000 records/s floor
actively dishonest as a portability gate. Shared GitHub runners are noisy. The gate is intended to catch large regressions, not
fail a release because another tenant on an Azure host sneezed.

## Step 2 verdict

**The core rating engine scales linearly through one million synthetic records
in the tested single-process workload, with deterministic replay and stable
memory. The production database also completed a 100K audited bulk-write test
with a valid chain, and the exercise fixed real unbounded-query and
dashboard-correctness defects.**

But Freight Recovery still does **not** have credible evidence for a million-row
persisted database workload, concurrent tenant traffic, sustained HTTP throughput,
or a production SLA. The confirmed-list query is also visibly the weakest measured
read path and should not be extrapolated beyond the tested 10K finding history.

That is the critical line. Anything stronger would be marketing outrunning the
evidence.
