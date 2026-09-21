# HUNTER-03 R21 — EXP-003 source-authority and cursor fixture

Date: 2026-09-21

Status: **synthetic fixture executed; provider/bank completeness authority remains external**

## Question

Can an EXP-003 bank/return observer distinguish a genuinely verified empty window from transport, authentication, pagination, source-freshness, account-scope and durable-commit failures—while advancing its cursor only after complete durable ingestion?

## Executed fixture

`referrals/hunt03-r21-2026-09-21-exp003-source-authority-fixture.py` implements separate `CONTENT` and `COVERAGE` states and executes 12 provider-neutral cases:

- current verified empty and present windows;
- transport and authentication failure;
- incomplete pagination;
- historical data still initializing;
- locally successful but upstream-stale data;
- upstream failure newer than the latest success;
- durable commit failure;
- one mapped sibling account failing commit;
- silently changed account scope; and
- refresh requested without a newer upstream update.

It also executes two lifecycle checks: delayed/backdated data appearing after an earlier stale empty observation, and a late return appearing after an earlier valid as-of empty receipt.

Observed result: **12/12 base cases plus both lifecycle checks passed**. Three unsafe evaluators were killed: local HTTP success as `VERIFIED_EMPTY`, unconditional cursor advancement, and silent source-scope acceptance.

Deterministic result digest: `6ba2240d4a43408fb01eee4d01e0b877aed71bcf259c2a05c5c1d4fba456a843`.

## Material result

Only a current, scope-complete, fully paginated and durably committed empty run receives `VERIFIED_EMPTY + VERIFIED_WINDOW`. Transport/auth/page/commit/sibling/scope failures cannot advance the cursor. A fully committed local delta may advance its ingestion cursor while still receiving `STALE`, `INITIALIZING`, or `UNAVAILABLE` coverage; cursor continuity therefore never becomes source-currentness authority.

The late-return lifecycle preserves the earlier empty receipt as an as-of fact but creates a new `PRESENT` receipt. The old receipt cannot continue to authorize a current no-return conclusion.

## Claims and limits

**Locally tested:** deterministic receipt classification, cursor gating, scope completeness, delayed-data handling and revocable as-of absence in a synthetic Python model.

**Not verified:** any real provider's negative-authority contract, live bank/payroll data, actual institution refresh completeness, database crash durability, customer-authorized settlement evidence or realized recovery. A provider can still expose only `OBSERVED_EMPTY`; this fixture cannot promote that to `VERIFIED_EMPTY` without external authority.

## Handoff

- **Capability delta:** CAP-019 now has an executable source-health/cursor corpus for EXP-003 rather than only a written receipt proposal.
- **Graph edge:** strengthens `CAP-019 -> CAP-018 -> EXP-003` without establishing bank finality.
- **Experiment impact:** removes the synthetic transport/auth/partial-source prerequisite. Adapter-backed verification remains pending.
- **Commercial impact:** blocks false “settled/no return” certificates caused by green local jobs over stale or partial bank data.
- **Negative knowledge:** cursor advancement proves committed ingestion position, not that the upstream institution was current or complete.

## Provenance and next gate

A READY event was published for HUNTER-03, but no activation packet materialized, so this is recorded as unallocated work with no generated-claim assertion.

Next: execute the same corpus against one concrete provider/bank sandbox adapter whose first-party contract exposes enough freshness and scope evidence to define when a bounded zero-result can—and cannot—become `VERIFIED_EMPTY`.
