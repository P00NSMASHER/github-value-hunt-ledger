# Hunt 13 referral — bank-finality join after provider settlement

Date: 2026-09-20
Lane: Revenue Leverage / Commission Payout Assurance
Experiment: EXP-003 — Commission plan-to-bank acceptance test
Capability: CAP-018
Radar: RAD-006

## Highest-value new component — Modern-Treasury/modern-treasury-python
- Repository: https://github.com/Modern-Treasury/modern-treasury-python
- Exact revision: `406f354a06a98060df0c9f4c242fe56cc65e1526` (main head inspected 2026-09-20; latest commit timestamp 2026-09-17).
- Status: **STRONG COMPONENT / PRODUCTION BANK-RECONCILIATION BRIDGE**
- Score: **26/30** — A4 B5 C5 D4 E5 F3.
- Capability: the public SDK exposes a coherent lineage model across Payment Order -> bank-assigned Payment References -> bank-imported Transaction/Transaction Line Item -> Return/Reversal. `PaymentReference.reference_number_type` explicitly includes `ach_trace_number` and `ach_original_trace_number`; the reference can be searched and is typed to a `payment_order`, `transaction`, `return`, `reversal`, or incoming payment detail. A Payment Order exposes bank reference numbers, transaction IDs, reconciliation status, current return, and lifecycle states including `completed`, `returned`, and `reversed`. Transaction objects represent observed bank-account activity and retain amount/currency, bank/vendor identifiers, posted/reconciled state and bank details. Transaction Line Items connect bank transactions back to transactable objects including Payment Orders and Returns. Returns carry bank references, returnable object ID/type, bank transaction/line-item IDs, return code, reconciliation status and raw bank-return data.
- Evidence inspected beyond README: `src/modern_treasury/types/payment_reference.py`; `src/modern_treasury/resources/payment_references.py`; `src/modern_treasury/types/payment_order.py`; `src/modern_treasury/types/transaction.py`; `src/modern_treasury/types/transactions/transaction_line_item.py`; `src/modern_treasury/types/return_object.py`; current first-party documentation for Payment Order lifecycle, Returns, received-payment reconciliation and bank-statement Transactions.
- Current first-party behavior checked: Modern Treasury documentation currently defines `completed` as bank-executed/posted while warning ACH may still return later; Returns can be created after completion and move the Payment Order to `returned`; Transactions are obtained from the underlying bank via bank API/BAI2 depending on the connection; Payment Orders sent through Modern Treasury are automatically reconciled to those bank Transactions. This is materially stronger than a payment-provider webhook because the observation plane is bank-derived.
- Rights/provenance: SDK repository is MIT. Modern Treasury's hosted API, bank connections, service data and commercial terms are independently owned/external and are **not** covered by the user's repository-code authorization.
- Strongest objection: the server-side automatic reconciliation algorithm is not public in the SDK, so do **not** infer that ACH trace number itself is always the acceptance join key merely because trace references and Transaction Line Items coexist. Feed freshness/completeness is also not expressed as a universal `COMPLETE/PARTIAL/STALE` contract in the inspected SDK. This remains a production integration substrate, not independent proof that every connected bank feed is complete.
- Buyer/wedge: finance/revops/payroll teams with high payout volume. First wedge: closed-month Commission Payout Acceptance Test using exported/API Payment Orders, bank Transactions and Returns, while independently checking entitlement. Report unsupported `paid` states, payment-order/bank-transaction mismatches, later returns/reversals and reviewer hours.
- Build compression: roughly 3–8+ months of bank-connection/reconciliation/reference/return object modeling if the buyer can use the service; less defensible if a fully self-hosted stack is required.
- Combination: OpenPartner/Kleegr/OCA entitlement -> Spree/chase-sets claim/send ambiguity -> Modern Treasury PaymentOrder/reference/bank Transaction -> Return/Reversal -> final outcome. Keep entitlement and settlement authority separate.
- Next test: build a synthetic/provider-neutral EXP-003 corpus that exports the same fields. Treat exact `ach_trace_number`/`ach_original_trace_number` plus bank Transaction linkage as strong evidence, but require explicit source-observation timestamps/coverage and reject ambiguous mappings.

## Strong rare architecture oracle — szapata85/ACHInterbank
- Repository: https://github.com/szapata85/ACHInterbank
- Exact revision: `395a359230eff35e49cc196b49995ed4c49509b9`.
- Status: **STRONG COMPONENT / RETURN-LINEAGE + AMBIGUITY-GUARD ORACLE**
- Score: **25/30** — A3 B4 C5 D5 E5 F3.
- Capability: an incoming ACH/NACHA-style return linker that first attempts exact `OriginalTraceRef`, then exact 15-digit trace, then a composite business key. A unique match becomes final; multiple matches become `Ambiguous`; zero becomes `NotFound`. Ambiguous/NotFound results do not mutate the money state and instead persist candidate IDs, trace/original trace and source-file provenance for manual review. Deterministic return application is idempotent and emits counter-events/state transitions.
- Evidence inspected beyond README: `IncomingNachaTransactionLinker.cs`; `IncomingNachaPostParseProcessor.cs`; `AchIncomingReturnApplicationAndOrphanCharacterizationTests.cs`; additional search-confirmed tests for duplicate-file/orphan idempotency and manual resolution.
- Tested behaviors observed in repository tests: exact return can move a transaction to returned and emit a state event; missing/unknown original trace creates no state transition; duplicate semantic return across different files does not double-apply; duplicated original trace across two candidate transactions is explicitly rejected as ambiguous and both original transactions remain unchanged.
- Rare value: the system makes a distinction most payout systems omit: **exact / ambiguous / not found is a money-state decision**, not just a confidence score. It also preserves source evidence including file hash, file size, receive time, clearing/cycle/date, return reason, trace and candidate IDs.
- Rights/provenance: no root LICENSE established at the pinned revision. User standing commercial authorization applies to repo-owned code/content only. The repository references/bundles ACH Colombia/CENIT normative material; those independently owned standards/regulatory materials were **not** treated as covered by repository authorization and were not used as authoritative rule evidence in this evaluation.
- Strongest objection: README itself says the system is a controlled-UAT candidate and must not be declared production without UAT/security/business evidence. It is region-specific and does not supply the provider-payout-ID -> independent bank-statement observation edge by itself.
- Commercial reuse: use as an adversarial design oracle for EXP-003: exact return lineage may finalize; duplicate/ambiguous trace must remain UNKNOWN/manual; a later counter-event is one-use/idempotent.
- Next test: port its Exact/Ambiguous/NotFound and duplicate-return fixtures into the common Commission Payout Acceptance corpus without copying jurisdiction-specific rule authority.

## Watch component — OCA/bank-statement-import
- Repository: https://github.com/OCA/bank-statement-import
- Exact revision: `01be32ea73e485e9b2495ea80fcce934badedeea` (18.0 branch).
- Status: **WATCH / INDEPENDENT BANK-READBACK + SOURCE-CURSOR COMPONENT**
- Score: **23/30** — A3 B4 C4 D3 E4 F5.
- Capability: CAMT parsers preserve `AcctSvcrRef`, structured creditor reference and `EndToEndId` into reconciliation-facing fields. CAMT fixtures/tests exercise statement ingestion. The Ponto online-bank connector persists the last transaction identifier, pulls backward until reaching already observed data/date overlap, uses each provider transaction ID as `unique_import_id`, and preserves raw source data.
- Evidence inspected: `account_statement_import_camt54/models/parser.py`; CAMT053/054 fixtures/golden outputs; `account_statement_import_camt54/tests/test_statement.py`; `account_statement_import_online_ponto/models/online_bank_statement_provider_ponto.py`.
- Rights/provenance: AGPL-3.0 public license; user standing repository-code authorization applies to repo-owned code. Ponto service/API and bank data remain external.
- Strongest objection: the inspected tests prove statement import shape/count/amount behavior, not a complete provider-payout-ID -> trace -> statement -> return acceptance chain. The Ponto cursor is useful continuity metadata but is not a universal explicit `COMPLETE/PARTIAL/STALE` source-health contract.
- Reuse: candidate bank-observation adapter, especially useful when combined with provider/bank references from Dub/Increase/Modern Treasury. Never label money realized solely because a fuzzy/label-based Odoo reconciliation occurs.

## Watch / negative oracle — sebastienrousseau/bankstatementparser
- Repository: https://github.com/sebastienrousseau/bankstatementparser
- Exact revision: `b3309b78f0bd8da872a09ec2b586a694379d5d83` (v0.0.19, 2026-09-01).
- Status: **WATCH / PARSER + ADVERSARIAL RECONCILIATION ORACLE**
- Score: **22/30** — A3 B4 C4 D4 E4 F3.
- Capability: broad deterministic bank-statement normalization and a payment-to-statement reconciliation engine across PAIN.001/ERP -> CAMT.053/MT940/CSV/BAI2.
- Critical negative finding: the money-bearing reconciliation path calls a payment `EXACT_REFERENCE` when the payment reference is a **substring** of statement reference/remittance/description; it takes the first unmatched statement rather than proving global uniqueness; an exact-reference/amount-difference case becomes `PARTIAL_AMOUNT_DEDUCTION`; fuzzy matches are counted as matched; and `total_reconciled_volume` sums matched rows. The helper intentionally converts invalid/unparseable money strings to `0.00`. Tests explicitly lock in fuzzy matching and the partial-deduction case.
- Why useful: excellent EXP-003 negative fixture showing why `reference present`, `amount close`, or `fuzzy party` can identify review candidates but must not become asserted/final settlement dollars.
- Rights/provenance: source files are SPDX Apache-2.0 OR MIT; validate repository release/license files if reused directly.
- Next test: add false-equality cases with duplicate references, substring collisions, equal totals with swapped identities and unparseable amount to the common acceptance corpus. Expected outcome: REVIEW/UNKNOWN, not realized money.

## Rejected historical oracle — luojus/bankws
- Repository: https://github.com/luojus/bankws
- Exact revision: `70a500a1a3c85d86bf76a8b9010264ce941c2799` (2012 only commit).
- Status: **REJECT / HISTORICAL ARCHITECTURE ORACLE**
- Score: **16/30**.
- Why: MIT bank-webservice client generates PAIN.001 `EndToEndId` and contains CAMT response structures including `AcctSvcrRef`, documented as an archive code matching the statement entry. However the relevant CAMT parser implementation is inside a disabled/commented block and the source explicitly says it was not tested because the test environment did not provide those reports. Do not mistake an old schema-shaped parser for verified readback.

## Comparison to current leaders
- **Increase/Adyen** remain stronger for provider-native transfer -> ACH trace -> settlement -> later return state.
- **Spree/chase-sets** remain stronger at claim-before-send, ambiguous provider outcomes and one-send semantics.
- **Modern Treasury** is the strongest new bridge in this run for bank-derived Transaction observation + Payment Order/Return linkage.
- **ACHInterbank** supplies the best new fail-closed trace-correlation policy: Exact / Ambiguous / NotFound with no money-state mutation under ambiguity.
- **OCA** supplies a reusable independent statement-ingestion/cursor pattern.
- **bankstatementparser** is a useful negative oracle for why substring/fuzzy/equal-amount matching cannot prove realized money.

## Combination discovered
Best current architecture for EXP-003:

`frozen plan/assignment authority -> independent entitlement -> one payout claim -> provider send/idempotency -> provider/native transfer ID -> bank/network reference (ACH trace) -> bank-derived statement Transaction -> deterministic unique linkage -> later Return/Reversal -> one-use counter-event -> final economic outcome`

No single repository is authority for the whole chain. The strongest implementation strategy is to keep four independent planes: entitlement authority, provider send state, bank observation, and later invalidating counter-events.

## Claims tested
- **SUPPORTED as an implementation capability:** a production treasury stack can expose bank-assigned ACH trace/original-trace references and connect payment objects to bank-derived statement Transactions and later Returns.
- **SUPPORTED:** an ACH return matcher can explicitly refuse to auto-apply under duplicate/ambiguous original trace and preserve review evidence.
- **FALSIFIED as safe authority:** `EXACT_REFERENCE` labels are not inherently exact/unique; at least one active reconciliation engine uses substring inclusion and then counts that match into reconciled volume.
- **FALSIFIED as sufficient:** feed cursors/last IDs by themselves prove complete source coverage.
- **UNRESOLVED:** for each provider/bank pair, whether the provider trace is the exact externally observed statement reference and whether transaction-feed health can prove completeness rather than only freshness/last-seen state.

## VALUE HANDOFF
1. **CAPABILITY DELTA:** CAP-018 gains a production bank-observation bridge model plus a concrete Exact/Ambiguous/NotFound return-correlation policy.
2. **GRAPH EDGE:** Modern Treasury strengthens CAP-018 -> EXP-003 bank observation; ACHInterbank strengthens later return/reversal ambiguity handling; OCA strengthens readback/source continuity; bankstatementparser challenges unsafe matcher authority.
3. **RADAR SIGNAL:** RAD-006 strengthened: independent systems converge on `authority -> explicit uncertain state -> bank readback -> counter-event`, and mature stacks keep `completed` distinct from later `returned`.
4. **EXPERIMENT IMPACT:** add duplicate-trace ambiguity, exact-reference substring collision, equal-total/swapped-identity, unparseable amount, stale cursor, bank-posted transaction with later return, duplicate semantic return across two files, and returned-after-completed cases.
5. **COMMERCIAL IMPACT:** Commission Payout Acceptance can sell not just `wrong commission` detection but unsupported paid status, bank-posting mismatch, unsafe reissue, later return/reversal and reconciliation labor reduction. Buyer-grade realized dollars still require unique external observation and one-use counter-event handling.
6. **NEGATIVE KNOWLEDGE:** no reference label, provider status, fuzzy match, amount equality, last-seen cursor or internal reconciled flag may independently establish realized money.

## Cross-agent referral
Payments/finance and payroll lanes should prioritize adapters where (a) provider/reference lineage is preserved, (b) bank/payroll observation is independently sourced, (c) exact/ambiguous/not-found is explicit, and (d) source-health metadata distinguishes stale/partial/unavailable from verified empty.

## Next highest-value question
Can we find or construct a provider-neutral source-observation contract that proves bank/payroll feed completeness/freshness and exact mapping of a provider transfer/trace to an independently observed transaction, so EXP-003 can move from component discovery to execution rather than another repository hunt?
