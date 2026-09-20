# Hunt 13 referral — provider payout ID -> bank trace/reference -> statement observation

Date: 2026-09-20
Lane: Revenue Leverage / Commission Payout Assurance
Experiment: EXP-003
Capability: CAP-018
Radar: RAD-006

## Best new component — dubinc/dub
- Repository: https://github.com/dubinc/dub
- Exact revision: `70350f7664db7076b95bacce0b2199c510836419`
- Status: **STRONG COMPONENT / TRACE-BRIDGE**
- Score: **25/30** — A4 B5 C4 D4 E4 F4.
- Concrete capability: Stripe Connect payout webhook captures the provider payout ID together with Stripe `trace_id.value`, amount, currency and arrival date; downstream persistence updates payouts by `stripePayoutId` and stores `stripePayoutTraceId`. A later `payout.failed` path can move the same provider payout to failed. This is a real production-oriented implementation of the previously missing `provider payout ID -> bank-created trace/reference` edge.
- Evidence inspected: `apps/web/app/(ee)/api/stripe/connect/webhook/payout-paid.ts`; `apps/web/app/(ee)/api/cron/payouts/payout-paid/route.ts`; payout schema/search paths; `payout-failed` handling; exact main commit.
- Rights/provenance: public repository; root is Open Core. The inspected `(ee)` server paths are subject to Dub's commercial-license layer rather than ordinary AGPL-only treatment. User standing repository-commercial authorization applies only to repo-owned material; Stripe service/API terms remain separate.
- Caveat: this is **not independent bank finality**. Dub marks local payout `completed` from Stripe's `payout.paid` callback. Stripe itself documents that a payout can later change from paid to failed, and trace IDs can remain pending/unsupported. No independent statement ingestion or trace-to-statement join was found in the inspected payout path.
- Commercial implication: materially strengthens Commission Payout Acceptance by preserving a provider identifier and bank-created tracking reference that can be handed to an independent readback layer rather than relying only on amount/date matching.

## Strong/watch component — sebastienrousseau/reconcile-mcp
- Repository: https://github.com/sebastienrousseau/reconcile-mcp
- Exact revision: `d5e81b593060f6a99b03b28efb253262d2b0eb0b`
- Status: **STRONG COMPONENT / STATEMENT-MATCH ENGINE**
- Score: **24/30** — A4 B4 C4 D4 E4 F4.
- Concrete capability: Apache-2.0 deterministic ISO 20022 reconciliation. `pain.001` expected records and `camt.053` observed entries are normalized into canonical IDs/references; CAMT IDs include `acct_svcr_ref`. The engine uses Decimal money, strict currency by default, exact/partial reference signals, deterministic scoring, amount mismatch, one-to-many split settlement and many-to-one batch credit.
- Evidence inspected: `reconcile_mcp/adapters.py`, `reconcile_mcp/engine.py`, `tests/test_engine.py`, `tests/test_adapters.py` search evidence, exact main commit.
- Caveat: generic expected-vs-observed matching is not economic identity by itself. It does not directly ingest Stripe payout IDs/trace IDs, ACH returns or prove source-feed freshness/completeness. `probable`/subset matches must remain review candidates, not realized-money authority.
- Combination: feed Dub's provider payout trace/reference as the expected reference and independent CAMT statement entries as observed records; require an exact trace/reference or independently governed mapping contract before treating a bank observation as conclusive.

## Watch / negative oracle — hannosirkel/robobook
- Repository: https://github.com/hannosirkel/robobook
- Exact revision: `264d61610d7a40c359f09692d200fc7a8e9616eb`
- Status: **WATCH / NEAR-MISS ARCHITECTURE**
- Score: **23/30** — A3 B4 C4 D4 E5 F3.
- Concrete capability: its normalization layer already retains Stripe payout `trace_id` + `trace_id_status` and parses CAMT.053 `AcctSvcrRef`; its bookkeeping workflow separates processor settlement evidence from imported bank cash evidence and blocks when payout rows lack bank receipts.
- Critical negative finding: the actual `processor-payouts-vs-bank` reconciliation aggregates payout amounts and positive bank transactions by inferred processor text, rather than using the retained trace/reference to establish deterministic per-payout identity. This can prove aggregate equality without proving which payout produced which bank receipt.
- Evidence inspected: `README.md`, `scripts/bookprep.py`, `scripts/bookrecon.py`, `tests/test_bookprep.py`, bookkeeping reconciliation documentation, exact main commit.
- Rights/provenance: no root LICENSE was found at the pinned revision; standing user authorization applies only to repo-owned material.
- Reuse value: excellent adversarial fixture for EXP-003: a system can have both trace fields in its data model yet still fail to use them at the money-bearing acceptance transition.

## Cross-source authority check
Stripe's first-party payout trace-ID documentation says banking partners create the trace ID to track a payout with the bank; retrieval may be pending for up to 10 days after arrival, or unsupported. Current Stripe SDK semantics also state that some payouts initially reported `paid` can later change to `failed`. Therefore provider `paid` and even trace-ID availability are separate claims from independent bank observation and post-settlement return/reversal finality.

## Combination discovered
`Dub provider payout ID -> Stripe bank-created trace/reference` + `reconcile-mcp expected-reference -> independent CAMT.053 observation` + existing `moov-io/ach` `OriginalTrace -> Return/Reversal` semantics forms the strongest current candidate chain:

`commission entitlement -> provider payout ID -> provider/bank trace/reference -> independent statement observation -> later ACH return/reversal`.

**Do not call this closed yet.** The unresolved technical contract is whether a particular provider trace value is preserved in the buyer bank's statement/reference field or can be deterministically mapped to the ACH trace used by Return Entries. This is bank/provider/rail specific and must be proven with authorized fixtures; heuristic amount/date matching is insufficient.

## Claims tested
- VERIFIED: a live payout implementation can persist provider payout ID and Stripe trace ID together.
- VERIFIED: a deterministic ISO 20022 matcher can use statement service references with amount/currency/date/reference evidence and handle splits/batches.
- FALSIFIED as a safe invariant: provider `paid` == final bank settlement.
- FALSIFIED as sufficient proof: merely retaining trace IDs in normalized data guarantees trace-level reconciliation.
- UNRESOLVED: Stripe/banking-partner `trace_id.value` is always the exact identifier that appears in CAMT `AcctSvcrRef` or Nacha `OriginalTrace`. Treat as a provider/bank-specific mapping hypothesis until proven.

## VALUE HANDOFF
1. **Capability delta:** CAP-018 gains an implementable provider-ID-to-bank-trace bridge plus a separate deterministic statement-observation matcher.
2. **Graph edge:** Dub -> STRENGTHENS CAP-018; reconcile-mcp -> STRENGTHENS external readback; robobook -> CHALLENGES trace-presence-without-trace-use; all -> EXP-003.
3. **Radar signal:** RAD-006 strengthened: money finality increasingly requires authority -> provider identity -> external reference -> independent observation -> counter-event.
4. **Experiment impact:** add exact-trace observation, trace pending/unsupported, trace absent from statement, wrong statement reference, aggregate amount equality with swapped payout identities, split/batch settlement, provider-paid-later-failed and later Return Entry cases. Missing/stale bank feed must remain UNKNOWN.
5. **Commercial impact:** enables a stronger closed-month Commission Payout Acceptance Test that can measure unsupported `paid` states, mislinked bank receipts, stranded payouts, duplicate reissues and later returned deposits.
6. **Negative knowledge:** aggregate provider-vs-bank equality, processor-name matching, provider webhook success and retained-but-unused trace fields are not settlement proof.

## Cross-agent referral
Payments/finance and payroll lanes should look specifically for production adapters where provider trace/reference is persisted **and then consumed** as an authoritative statement/return join key with source freshness/completeness metadata.

## Next highest-value question
Can a production connector prove, for at least one common payout rail/bank pair, the exact mapping `provider payout ID -> provider trace/reference -> independent statement entry -> later return/reversal`, while exposing feed freshness/completeness so absence of evidence cannot become a false success?
