# RETALLY Priority 1 — financial integrity and recovery controls (source only)

Scope: 2026-10-22 software hardening. **No customer pilot, provider
credentials, real bank data, contracts, legal approvals, spending, or release
authority** are supplied by the code or synthetic tests. Do not interpret an
HMAC test witness, source-declared credit, reviewer-role string or matching hash
as proof that a real person, contract or bank approved an action.

## Control mapping to the approved Priority 1 improvement list

| ID | Improvement | Enforced behavior / reusable test source |
|---|---|---|
| 6 | Central financial validation | `financial_assurance.require_exact_cents` and `require_cent_currency` used by `payment_orchestration` and `settlement_store`; reject bool, float, overprecision, unsupported minor units. |
| 7 | Authenticated approval identity | `PaymentOrchestrator(require_trusted_approval=True)` denies all approval without a verified scope/purpose/authorization-hash-bound `SourceAttestation` against separately provisioned issuer keys. **No live issuer is provisioned; not a real human identity gate**. |
| 8 | Immutable financial history | Preserve existing `settlement_schema.sql` immutable SQL UPDATE/DELETE triggers, scoped SQLite snapshots, exact source hashes; tests cover immutable source, stale reporting and replay. |
| 9 | Idempotency | Exact provider event replay returns the original event without appending; same provider/reference/state with differing evidence rejects. Existing SQLite claim/event/counter replays and uniqueness checks remain intact. |
| 10 | Concurrency | Preserve `BEGIN IMMEDIATE` and scoped SQL capacity triggers. Concurrent synthetic allocation exercises assert no duplicate consumed credits. |
| 11 | Partial settlements | Preserve reviewed many-to-one allocations, exact residuals and bounded individual partial settlement amounts. |
| 12 | Reversals | Preserve append-only counters and reversal edges; old currency reports invalidate on new reversal; net amounts and fee-base candidates adjust. |
| 13 | Fee integrity | Source-scope/contract-hash-bound `FeeTerms` plus exact integer-bps cap/exclusion quote. Exclude incumbent/disputed/reversed/disqualified amounts. **Billable amount stays zero** without independently authenticated customer settlement, signed commercial authority and fee approval. |
| 14 | Independent financial provenance | Receipt verifier requires externally supplied trusted issuer keys and canonical scope/purpose/source digests; no `BANK_CLEARED` source label or SHA alone becomes verified cash. Existing `financial_integrity` retains unverified amount/status. |
| 15 | Exact money | Explicit ISO minor-unit precision for reviewed currencies. Money and cents reject implicit FX, noncanonical Unicode/commas/exponents and float inputs. Cent-based engine refuses 0-/3-decimal currencies. |
| 16 | Currency separation | `currency_reporting` provides net source-declared allocations, reversals and fee-base candidates per currency, hash-bound to one database snapshot; deliberately **no FX or cross-currency total**. Historical USD-only customer financial reports remain fail-closed for non-USD frozen truth. |
| 17 | Signed invoice adjustments | Preserve schema v2 `InvoiceAdjustment` discount/credit source binding and reconciliation against the immutable invoice source. Original discounts cannot become post-invoice payment or new cash; targeted tests include the original-document GlobalTranz arithmetic fixture. |

## Scope boundaries and missing external acceptance

1. `SourceAttestation` is HMAC integrity against **configuration supplied by the caller**; no live provider onboarding, independent reviewer appointment, real buyer identity verification, legal signatures or credentials are created. No default `trusted_issuers` exist.
2. `FeeQuote.estimated_fee_cents` is illustrative underwriting only; `billable_cents=0` permanently at this source-only layer. A separate authorized billing product cannot derive permission from this quote.
3. `CurrencySettlementReport` means `SOURCE_DECLARED_NOT_BANK_VERIFIED`; source-reported receipts and verified bank transfers remain distinct. This addition does not alter the existing USD-only rated-freight pilot report or purport to calculate cross-currency savings.
4. Existing customer private host and buyer/contract/retention/independent truth gates remain in effect. No production financial service has been activated.
5. Existing draft #461 touches `payment_orchestration.py`. Before that draft is ever integrated, reconcile against this protected source and re-run exact-head financial regression; never overwrite this work from an older branch.

## Verification design

- `freight/test_priority1_financial_assurance.py`: exact numeric/FX guards,
  untrusted approval negatives, authenticated synthetic proof positives, event
  idempotency/conflicting replay, signed-terms fee-base calculations, reversals,
  concurrency, multicurrency snapshot invalidation and original adjustment proof.
- `freight/test_priority0_financial_integrity.py`: all five original adversarial
  source defects remain regression-blocking.
- `freight/test_financial_integrity_r1.py`, `freight/test_settlement_store.py`,
  `freight/test_phase2_recoveryos.py`, `freight/test_settlement_report.py`,
  `freight/test_settlement_lifecycle_workflow.py`, and original-document lab
  tests: unchanged monetary/release safety contract coverage.

### Release status

A source patch is not a real-customer financial approval. Release classification
must be set only from GitHub's actual exact-head CI and protected-main readback,
never by passing a synthetic local test alone.
