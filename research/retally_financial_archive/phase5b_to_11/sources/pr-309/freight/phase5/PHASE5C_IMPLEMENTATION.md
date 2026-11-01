# RETALLY Phase 5C | Executed staged reconciliation, financial proof and release boundary

**Evidence date:** October 8, 2026. **GitHub candidate:** draft PR #309, stacked on draft #304. All financial identities, private signing roles and amounts used here are fictional.

## Architecture and reused code

- Published RecoveryOS Floot: `c719b60c-9b3b-4193-a543-0be9d3ceaef2`, PostgreSQL system identifier `7693746749463444100`.
- Unpublished QA Floot: `7257eaf3-a4d7-43db-9136-fe81e5df35bf`, PostgreSQL system identifier `7694294930552894346`. The QA preview uses a synthetic authentication header substitute, never live auth secrets.
- Reused the **unchanged** current RecoveryOS `payment_event_POST.ts` handler, with its existing transaction/row lock and replay helper. Two actual handler test instructions, 400 and 600 cents, each reached `SETTLED`. This is provider-event state only.
- New focused QA financial extension: `helpers/phase5cFinancialEvidence.tsx`, `endpoints/phase5c/financial_document_POST.ts`; exact QA code reviewed in this PR, not published to production.
- New QA-only PostgreSQL `phase5c_qa` schema: versioned fictional signer public keys, immutable case-bound signed documents, source-reference conservation, contract/fee guards and read-only financial summary. The original `public.m7_reconciled_cash_by_currency` view remains intentionally fail-closed with `WHERE 1 = 0`.
- Fictional issuer **private keys generated ephemerally outside the tested application** and never committed to GitHub. Public keys and the 10 matching signatures are in `phase5c_signed_fixture.json`, separately reverified by `phase5c_oracle.py`.
- Existing Phase 4 control center is extended, not replaced, through `phase5c_control_overlay.py`. Its ExperimentLedger records D-07 as **INCONCLUSIVE** because that original affected-code counterexample was not independently reproduced in this phase.

## Actual successful fictional staged lifecycle

| State | Signed source | Amount (USD) |
| --- | --- | ---: |
| Historical contingency contract | BUYER, 30% | 0 |
| First carrier/handler settlement | CARRIER | 4.00 |
| First customer posting | BUYER_ACCOUNTING | 4.00 |
| Second carrier/handler settlement | CARRIER | 6.00 |
| Second customer posting | BUYER_ACCOUNTING | 6.00 |
| Fee invoice after customer postings | RETALLY_BILLING | 3.00 |
| Fee collected | PAYMENT_PROCESSOR | 2.50 |
| Later partial customer reversal | BUYER_ACCOUNTING | -5.00 |
| Fee credit | RETALLY_BILLING | -1.50 |
| Fee refund | PAYMENT_PROCESSOR | -1.00 |

**Independent final calculation (all synthetic):**
- Gross customer-posted credit = **$10.00**.
- Customer reversal = **$5.00**.
- Net fictional customer recovery = **$5.00**.
- Earned contingency at historical 30% = **$1.50**.
- Gross fee invoiced = **$3.00**; fee credit = **$1.50**.
- Gross fee collected = **$2.50**; refund paid = **$1.00**.
- Net retained fee = **$1.50**.
- Remaining fee receivable and refund liability = **$0.00** each.
- Real customer recovered funds, real RETALLY earned revenue = **$0.00**.

The independent Python verifier reconstructs all these values from signed fixture bodies and compares them against the stored PostgreSQL summary. It does not trust an application-generated grand total.

## Adversarial acceptance and root-cause corrections

**Against the hosted unpublished QA endpoint:** deliberately correctly signed requests were rejected for orphan reversal, excess refund, duplicate posted credit, nonexistent carrier settlement, wrong currency, and extra unauthorized fee invoice. A database census after these tests found **10 accepted signed documents and zero failed negative-test insertions**.

**Actual newly reproduced QA defect:** the first implementation of the signed-document endpoint used raw `JSON.stringify` to compare an application body against PostgreSQL `jsonb`. A valid exact replay returned HTTP 400 `CONFLICTING_RECORD_REPLAY` due to reordered fields. Repair replaced raw comparison with RecoveryOS's existing canonical `recoveryHash` function. The same valid signed replay subsequently returned HTTP 200 and `replay:true`, and a modified amount with its stale signature returned HTTP 400. This is an **actual Phase 5C staging implementation repair**, not formal closure of an older finding.

**Additional SQL hardening:** corrected a PostgreSQL `FOUND`-flag overwrite in the reversal reference check; added duplicate-source relabel prevention and a fee-credit prerequisite for refunds. Disposable PostgreSQL tests reproduce these negative cases against the hardened implementation. No historical-original finding was automatically advanced.

## CI and reproducibility

- `freight/phase5/test_phase5c_oracle.py`: Ed25519 signature, role, source, tenant, historical contract, credit conservation, reversal, fee and refund tampering tests.
- `freight/phase5/test_phase5c_postgres.py`: run against dedicated **disposable** PostgreSQL 16 using the existing Phase 5 CI database only. The migration's QA cluster guard is explicitly rewritten for the disposable CI cluster after verifying its database name and identifier. Never run this harness against Floot.
- `freight/phase5/test_phase5c_control_overlay.py`: dashboard and ExperimentLedger non-claims verification.
- `.github/workflows/freight-phase5c.yml` and inherited `freight-phase5.yml` run at the exact draft commit with pinned dependencies. The first CI round found one invalid cross-tenant adversarial test *setup* and fixed it; the first 14 tests were already passing. The final workflow verdict is reported independently.
- `freight/phase5/phase5c_signed_fixture.json` is frozen **QA evidence exported read-only**; GitHub CI does not make live Floot API requests.

## Three founding customer scenarios

Customer A's complicated recovery is executed through the actual copied RecoveryOS handler and the isolated QA financial extension. Customer B's defensible zero-recovery case and Customer C's uneconomic-dispute case remain the **previously verified synthetic Python-domain simulations** from Phase 3/4; neither has been represented as a hosted application execution, a signed real customer engagement, or actual business revenue.

## Historical defect and production readiness

**D-07:** the original finding says "Idempotency replay ignores attempted actor identity" (`REPRODUCED_OFFLINE_PRIOR_AUDIT`). The QA SQL function now enforces fictional actor authorization and binds attempted actors to replay checks; the copied production-source TypeScript handler authorizes an API key but does not independently bind a separately attested actual carrier actor to a settled customer bank credit. The original historical D-07 reproducer against the original affected implementation was not independently re-executed in this phase; authentic external actor authority is unavailable. **D-07 remains OPEN_UNVERIFIED. The entire historical register remains 26 open.**

**Not established:** genuine customer posting, bank reconciliation, real contingency contract signature, independent signer ownership in production, hosted production-auth/schema parity, real customer outcomes, final customer security certification, or real production cash/refund handling. No production data was modified, no PR merged, no app published, and no real customer/carrier/payment/scheduled-task action took place.

The next production-readiness gate is provisioned external issuer authority, actual bank/customer statement admission, and application-level end-to-end tests with production-equivalent authentication and schema. Research correctness is not a commercial guarantee.
