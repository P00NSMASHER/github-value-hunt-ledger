# RecoveryOS Five-Step Unified Laboratory — October 2026

**Classification: offline synthetic engineering PASS, not production integration or real customer results.**

This PR adds a **small, reviewable adapter to real existing RecoveryOS Python domain code**, while the larger runnable five-step laboratory and its private sealed synthetic fixture are delivered as a downloadable self-contained ZIP in the associated ChatGPT conversation. Do not commit full synthetic populations or customer-specific data.

## Step 1 · Source reconciliation

Five existing draft PR heads are recorded in `freight/unified_labs_domain_bridge.py`:
- #263 audit/rating bench
- #264 customer lifecycle/payment guards
- #271 first-customer methodology
- #272 Labs 04–10
- #273 Labs 11–14

The portable workbench inventories five corresponding versioned ZIP archives and hashes each file. It maintains a shared fictional identity `(tenant_id, source_customer_id, invoice_id, source_sha256, case_id)` and preserves ten colliding Python basenames behind their original package namespaces. **None of these five PRs is merged, nor should source files be blindly overlaid.** Current branch heads must be refreshed again before a real merge.

## Step 2 · Staging digital twin

A local-only, Python/SQLite, six-freight-mode **reference twin** has:
- tenant-specific views with role-checked simulated identity tokens on loopback HTTP;
- fictional buyer consent, source freeze, immutable evidence events and review;
- explicit buyer authorization before mocked carrier submission;
- mocked carrier acknowledgement, partial settlement and fictional credit receipt;
- separated receipt, customer reconciliation, fee recognition and fee collection;
- revocation, reversal, customer fee refund and immutable journal entries;
- append-only event SHA256 chain, idempotency and independent financial replay.

This twin is **not** the Floot hosted application, bank/payment/EDI provider, validated enterprise SSO or a tested production SLA. In this PR, `run_actual_domain_shadow` separately exercises *existing real repository* `freight.rating_engine` and `freight.payment_orchestration` classes with the frozen 20-case internal gold fixture. It requires exact fictional invoice ID, source hash and customer mapping, as well as independent reviewer and buyer approval before modeled carrier events. A simulated provider `SETTLED` state cannot earn a fee without a *separately flagged simulated buyer reconciliation*. A reversal returns fee eligibility to zero.

## Step 3 · Defect-to-fix

Four intentionally vulnerable *isolated training adapters* are subject to:
1. failing regression reproduction,
2. generated candidate diff,
3. patched-isolated regression PASS,
4. immutable before/after SHA256 and review-only patch export.

These are **not four production RecoveryOS defects** and **not** automatically merged. Production code edits always require actual reproducible defects plus owner review.

## Step 4 · Adaptive adversarial campaign

The local deterministic coverage-guided mutator tests 24 classes of unsafe actions over six modes and three synthetic truth states (432 combinatorial cells) against the twin. Reports exactly whether an unsafe request was rejected, and preserves the scenario seed, failure family, and staging state. **This is not an independent external penetration test.**

## Step 5 · Buyer simulation and data policy

Detailed fiction-based customer scenarios use unmodified invoice, rate, class, distance, fuel, charge, payment and prior-credit *synthetic* fields from the existing Lab 1 frozen source. Twelve relationship outcomes include:
- $0 audit with angry customer and review request,
- partial recovery after buyer authority and carrier dispute,
- carrier denial with zero fee,
- authorized submission later revoked,
- partial credit received, separately reconciled and fee collected,
- a post-fee credit reversal with simulated fee refund,
- incomplete evidence and false-negative second review.

Every case has an event timeline, multiple-role message thread, and separate sealed synthetic gold file. **No actual emails are sent and no customer or carrier records are copied from public repositories.** Research references can use U.S. BTS Freight Analysis Framework aggregate regional flows; those statistics are **not** per-invoice customer truth and are not imported in the current lab. Fair Source / competitive-use restricted Trenova code is **not** copied or executed; license clearance for any later integration is separate.

## Measured local results (not production)

- Five existing toolkit archives inventoried with SHA256 digests and preserved namespaces.
- 10,000 frozen fictional invoice rows sampled for the standalone workbench.
- 240 complete simulated buyer case histories and thousands of fictional communications.
- 1,200 targeted unsafe staging requests rejected, all 432 targeted combinations covered.
- Four injected defects reproduced red then independently patched/tested green.
- Local regression suite passes 59 tests with ResourceWarning escalation enabled.
- Control-room interactions pass Chromium desktop, iPhone 390px and tablet checks with no external network calls or browser errors.
- JSON reports and sealed synthetic gold remain separate from staging API/UI.

Exact reproducible receipts and tests are included in the portable artifact. This file intentionally does not claim that a real buyer signed an agreement, a customer payment was recovered, or any hosted app passed an end-to-end staged load test.

## Release gates

| Gate | State |
|---|---|
| Offline namespace reconciliation | PASS_SYNTHETIC |
| Local reference staging SQL/HTTP | PASS_SYNTHETIC |
| Isolated fail-first/patch-pass demonstrations | PASS_SYNTHETIC |
| Local adversarial mutation/coverage | PASS_SYNTHETIC |
| Fictional multi-role customer replay | PASS_SYNTHETIC |
| Actual RecoveryOS Python-domain synthetic smoke | CI_TESTED |
| Production Floot staging equivalence | NOT TESTED |
| Real blind independent customer pilot | BLOCKED_EXTERNAL |
| Actual bank/credit reconciliation | NOT TESTED |
| Merge into main/deploy or scheduled monitoring | **NOT AUTHORIZED; NO ACTION** |

`real_customer_release_gate` never authorizes live use automatically, even if all inputs are asserted true. Legal, privacy, security, rights and buyer controls must be separately established and reviewed.
