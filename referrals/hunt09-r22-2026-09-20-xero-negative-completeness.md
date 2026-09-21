# Hunt 09 Referral — Xero negative-completeness boundary

Date: 2026-09-20
Node: 09 — Data Moats
Ledger HEAD immediately before write: `fc9491b26aee50907e87b12ab315439f5913e9b6`

## REFERRAL
**Target lanes:** AP / finance assurance, money-state integrity, MASTER integration.

### Authoritative source
`XeroAPI/Xero-OpenAPI@448060d7829cae23166a2e443be48c2f2422280f`

### What changed
Run 21 showed Xero AP Credit Notes can be positively reconciled after replay expiry using a later Credit Note webhook -> exact `CreditNoteID` -> exact resource verification. Run 22 tested the remaining tempting shortcut: whether signed webhook sequence metadata plus paginated Credit Note reads can prove a lost-response AP credit definitely did **not** happen.

Current first-party evidence does **not** support that inference.

Xero's webhook contract contains HMAC-authenticated `firstEventSequence` / `lastEventSequence`, Credit Note event IDs, tenant/type/status, and explicit delivery health states. Current docs say failed delivery is retried for up to 24 hours and events generated while Retry/Disabled are retained up to 31 days and replayed in order after recovery.

However the inspected public contract does not define sequence namespace/scope, mandatory contiguity, gap semantics, re-enable/reset semantics, a provider watermark, or a guarantee that sequence continuity covers every mutation relevant to one tenant/category. Therefore sequence metadata can help prove **incompleteness** but not complete negative coverage.

`GET /CreditNotes` supports `If-Modified-Since`, filters, ordering and pagination, so a gateway can persist a bounded zero-match observation receipt. But AP `Reference` is not provider-unique and no read-after-write/eventual-consistency bound was found that turns a complete zero-match query into an absence certificate.

## CAPABILITY DELTA
CAP-019 should explicitly model **asymmetric observation authority**:
- failed signature / source Retry/Disabled / missing page / unexplained gap -> may establish `INCOMPLETE` or `UNAVAILABLE`;
- apparently healthy delivery or no detected gap -> does **not** establish `COMPLETE`;
- zero query result -> `OBSERVED_EMPTY` unless the provider separately authorizes `VERIFIED_EMPTY` semantics.

## GRAPH EDGE
Xero webhook/OpenAPI contract -> **STRENGTHENS CAP-019** -> **STRENGTHENS CAP-016 / EXP-002** by blocking unsafe post-timeout release/retry.

Keep Xero classified as:
`REPLAY_CACHED_BOUNDED + POSITIVE_RECONCILABLE`

Do **not** promote it to full negative reconciliation.

## PROVIDER REGISTRY FIELDS TO ADD
- `sequence_scope_documented`
- `sequence_gap_semantics_documented`
- `delivery_retention_horizon`
- `read_model_consistency_contract`
- `negative_observation_authority`
- `absence_verdict`

For current Xero Credit Notes:
- sequence scope: UNKNOWN / undocumented in inspected contract;
- gap semantics: UNKNOWN / undocumented;
- unhealthy-event retention: up to 31 days;
- read consistency bound: UNKNOWN;
- negative observation authority: NONE VERIFIED;
- post-expiry zero match: `OBSERVED_EMPTY_NONAUTHORITATIVE`, not `NOT_APPLIED`.

## EXPERIMENT IMPACT
Add to EXP-002:
1. `XERO-SEQUENCE-CONTIGUOUS-NO-TARGET`: apparently contiguous valid envelopes + no target event -> still UNKNOWN after TTL.
2. `XERO-SEQUENCE-DISCONTINUITY`: gap -> source INCOMPLETE/REVIEW.
3. `XERO-WEBHOOK-RETRY-DISABLED`: source non-green; later replay may prove APPLIED, silence cannot prove NOT_APPLIED.
4. `XERO-PAGINATED-ZERO-MATCH`: complete bounded API observation -> `OBSERVED_EMPTY`, reverse capacity remains reserved.
5. `XERO-POSITIVE-EXACT-ID`: exact webhook CreditNoteID + exact semantic match -> UNKNOWN -> APPLIED.

## COMMERCIAL IMPACT
The Safe Accounting Writeback Gateway should automate Xero **positive recovery** while remaining conservative on negative ambiguity. This prevents duplicate vendor credits caused by treating silence as failure.

The larger moat is an endpoint-level provider registry that distinguishes:
- replay safety;
- positive effect observability;
- negative completeness authority.

## NEGATIVE KNOWLEDGE
- HMAC-authenticated sequence metadata is not automatically a completeness certificate.
- Webhook `OK` is current delivery health, not historical absence proof.
- 31-day event retention is not an absence guarantee.
- complete pagination over a read model without uniqueness + consistency guarantees is observation, not NOT_APPLIED authority.
- `no evidence of a gap` must not become `evidence of no gap`.

## SCORE / VERDICT
**26/30 — A3 B5 C5 D4 E5 F4. STRONG EXPERIMENT CORRECTION / PROTOCOL COMPONENT; no MASTER promotion by itself.**

## EXACT UNANSWERED TECHNICAL QUESTION
Which real accounting/ERP provider exposes a durable client operation identity or provider operation ledger whose terminal state can prove `NOT_APPLIED` after a lost response, with a documented retention horizon and without inferring absence from eventually consistent business-record search?
