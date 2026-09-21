# Commercial direct-money systems shadow results

Append-only shadow log. These findings are NOT authoritative MASTER promotions.

## 2026-09-20 — Shadow run 1

**DATE:** 2026-09-20

**HYPOTHESIS:** Direct-money assurance engines are most commercially useful when they bind effective-dated authority to deterministic expected-vs-actual money math, fail closed on stale/missing evidence, and emit idempotent audit evidence; this should outperform generic reconciliation dashboards that only surface mismatches.

**DISCOVERY METHODS:**
1. Direct domain/problem search across revenue leakage, quote-to-cash assurance, AP reconciliation, commissions/claims and billing controls.
2. Code/file/invariant search for effective dates, source freshness, deterministic finding keys, three-way match, tolerance receipts, subset-sum matching, control assertions and property tests.
3. Obscure/low-attention discovery emphasizing new/low-star portfolio and specialist finance-engine repositories rather than established billing suites.

**CANDIDATE + URL + EXACT REVISION:** `Etherlabs-dev/revenue_leakage_system` — https://github.com/Etherlabs-dev/revenue_leakage_system — `64c1af79ac0a22915cfb49f1a2dd6d870059b78a`.

**IMPLEMENTED:**
- Deterministic rules for outdated/catalog-vs-negotiated pricing, missing overages, invalid/expired discounts and feature-entitlement mismatches.
- Effective/end-date authority selection with customer-negotiated terms taking precedence over catalog terms.
- Exact `Decimal` money calculations, currency mismatch blocking, billing-window alignment, grace periods, duplicate usage-event conflict detection and stable finding-key generation.
- Fail-closed source controls: missing timestamps, future timestamps, stale source data, missing charges and wrong-customer charges return `BLOCKED` rather than `CLEAR`.
- PostgreSQL data model preserves source timestamps, rule versions, expected/actual/difference/impact values, evidence JSON and idempotent active-finding persistence keyed by a 64-char finding hash.
- Dockerized rule service and FastAPI-facing service boundary exist; n8n/provider adapters are artifacts rather than verified production integrations.

**TESTED:**
- `tests/test_rules.py` directly covers negotiated-price precedence, effective/end-date boundaries, missing/correct overages, grace/window alignment, duplicate/conflicting usage events, expired discounts, entitlement mismatch/grace, decimal precision, currency mismatch, stale/missing data blocking and stable finding deduplication.
- CI runs locked Python dependencies, formatting/lint, pytest, a frozen synthetic benchmark, PostgreSQL schema/sample-data smoke tests and Docker build.
- Committed synthetic benchmark has 11 designed cases, including stale and missing inputs, with 4 TP / 7 TN / 0 FP / 0 FN; its own claim boundary explicitly says this does not establish production recovery or generalization.

**CLAIMED / PLANNED / UNKNOWN:**
- Repository explicitly does **not** claim client deployment, recovered dollars, ROI, payback, production coverage or live operating performance.
- Live Stripe/product adapter validation, tenant authorization/RLS, production observability, delivery testing, review UX and representative historical evaluation remain deployment work.
- UNKNOWN: production precision/recall, customer-specific contract-authority completeness, realized revenue recovery and time-to-resolution economics.

**EVIDENCE:** Frozen evidence manifest `sha256:1e61fc66b254020c75b8102645529863de558fea3c559864ab80c2355b73df48` over exact revision plus these Git blobs:
- `src/revenue_leakage/engine.py` — `ae90eca24f1872bceb59e11562255eeca4df2e60`
- `tests/test_rules.py` — `a0d30c91358a2e634611af0af495cbd61187a8bf`
- `database/schema.sql` — `6e1cae258d6b6fb7e98d2e6a820d791e39898129`
- `.github/workflows/ci.yml` — `1d833e165f186891eeaf5fecbf2056eb34690`
- `results/synthetic_benchmark.json` — `3c5dabe1ddceebd634cd9949237d891dcff9baf5`
- `README.md` — `c81c381a1155cfbc8bd4325822d8d4acca4216f7`
- `LICENSE` — `b3d263aac194f2d123791598011223490c10cc2d` (MIT)

**CONTRADICTIONS / COMPARATORS:**
- Deep-inspected `dylanpulver/recon@e6b787213bb023568c99c432ea4733e1f2456a5e`: stronger generic settlement-matching invariants than most finance demos (five-tier deterministic ladder, explicit match receipts, bounded many-to-one subset sum, property tests for partition/conservation/receipts/determinism), but it does not reconstruct contractual expected charges or source authority; it is a strong matching component rather than a revenue-leakage oracle.
- Deep-inspected `ai-frankie/ap-close-engine@db38c8476ccd21155a5dc161c5f36b9747e88e64`: useful AP controls with 3-way match, duplicate detection, GL/subledger tie, GRNI, vendor reconciliation and an independent reviewer that catches planted errors. Evidence is synthetic and the inspected root had no LICENSE file; commercially useful as a controls-pattern reference, but narrower and less authority-aware than the selected candidate.

**RED-TEAM OBJECTION:** The strongest failure mode is false confidence from synthetic truth. The rule engine can be perfectly correct on designed fixtures yet generate incorrect money findings if customer-specific contract amendments, pricing exceptions, source freshness semantics or provider fields are incomplete. Stable hashes prove idempotency, not legal/contractual authority. The architecture is still a reference implementation, and the closest commodity alternative is a normal RevOps/warehouse reconciliation pipeline plus hand-maintained SQL rules. Evidence that would reverse this objection: a frozen, independently labeled historical SaaS billing population with authoritative contract snapshots and blinded expected-vs-actual scoring, followed by realized adjustment/credit evidence for accepted findings.

**VERIFIER VERDICT:** **PASS** on the narrowly scoped technical claim: this exact revision implements and tests an authority-aware, fail-closed expected-vs-actual revenue-leakage rule engine with structured evidence and idempotent persistence. The verifier was not given the A-F score and does **not** validate production accuracy, recovered dollars, ROI or live-provider integration. No sensitive-source contamination observed in the inspected evidence packet.

**A-F SCORE (proposed only, post-verifier):** **26/30** — A4 / B4 / C5 / D4 / E5 / F4.
- A4: fixed-price leakage diagnostic can be piloted from exported contract/billing/usage data without moving money.
- B4: recurring billing assurance can support meaningful RevOps/finance value, but realized economics are unproven.
- C5: compresses nontrivial rule, freshness, evidence, schema and idempotency work.
- D4: the combination of effective-dated authority + source freshness + deterministic evidence is less common than generic reconciliation, though not unique.
- E5: unusually explicit source/tests/schema/CI/claim boundaries for a small reference system.
- F4: MIT and Docker are clean; production adapters, tenancy and historical external validation remain unfinished.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: SaaS CFO/Controller, RevOps or Billing Operations lead with Stripe/Zuora/Chargebee-style billing plus negotiated contracts and usage-based charges.
- Pain: underbilling from stale pricing, missed overages and contract exceptions; overdiscounting; unsupported feature entitlement; manual spreadsheet sampling that cannot prove source currency/freshness.
- First paid wedge: a read-only **Billing Leakage Acceptance Test** over one closed historical billing period. Freeze authorized contract/pricing/usage/charge snapshots, run deterministic rules, return only evidence-backed findings, and measure accepted-dollar corrections plus false-positive review burden.

**SEARCH EFFORT:** 7 public discovery queries across three modes; 3 serious candidates deep-inspected; 4 private-ledger dedupe searches after discovery; 41 tool calls total including required shadow-memory reads and one local manifest-hash computation; 0 untrusted-repository code executions.

**LOCAL LESSON:** Searching for `effective-date authority × source freshness/unknown-state × expected-vs-actual money delta × idempotent evidence` was substantially higher signal than searching for “revenue leakage” alone. Generic leakage searches produced many dashboard/portfolio projects with synthetic dollar claims; requiring negative tests for missing/stale authority quickly separated stronger engines.

**REFERRALS:** None this run. The best next question remains inside the commercial lane rather than AI/science.

**NEXT TEST:** Find an independent repository or lawful public technical artifact that closes this candidate’s missing edge: production-grade contract/rate authority ingestion or settlement-grounded outcome evidence for subscription billing, then test whether its authority model can be combined with this engine without silently treating missing amendments/exceptions as current truth.

## 2026-09-20 — Shadow run 2

**DATE:** 2026-09-20

**HYPOTHESIS:** The highest-value next component will make subscription-billing authority itself versioned/immutable or will produce exact settlement/credit evidence linking a corrective money movement to the original obligation. Combining that with run 1's leakage detector should close the gap between “suspected leakage” and an auditable correction.

**DISCOVERY METHODS:**
1. Direct problem search for subscription billing, contract pricing, amendments, effective dates, credit notes, refunds and settlement/reconciliation.
2. Code/invariant search for immutable/effective-dated contract versions, source-of-truth ownership, supersession, idempotency, ledger reversals, credit-note evidence and negative money controls.
3. Deliberate low-attention discovery, prioritizing zero/low-star operational billing repositories and then comparing them against a mature commodity system.

**BEST CANDIDATE + URL + EXACT REVISION:** `michaelayoade/dotmac_sub` — https://github.com/michaelayoade/dotmac_sub — `fdc85559d9677480090596f88009d2d3eed29e56`.

**IMPLEMENTED:**
- `billing.contracts` turns an accepted commercial commitment or authorized service change into an immutable `BillingContractVersion` plus lines, with structural source kind/id/version, effective half-open intervals, contracted price/currency, cadence, proration, tax/discount terms, actor/reason/correlation and supersession lineage.
- The model distinguishes `shadow` from `authoritative` financial records. Shadow rows are expressly forbidden from producing financial effect; the owner returns authoritative state only after the canonical source-of-truth migration state reaches cut-over/complete.
- Entitlement/history lookup fails closed on missing contracts, shadow versions and gaps in authoritative interval coverage rather than treating absence as entitlement.
- Contract changes supersede rather than rewrite history. Effective-version resolution uses half-open boundaries, rejects out-of-order versions/mixed currencies/duplicate charge components and requires idempotency.
- The billing correction plane applies issued credit notes to specific invoices, records exact ledger and consumption-ledger evidence, supports application reversal, restores invoice/credit balances on reversal, and uses scoped idempotency keys plus row locking to prevent duplicate or concurrent over-application.

**TESTED / EVIDENCE IN SOURCE:**
- `tests/test_billing_contracts.py` verifies shadow authority, one-version idempotent replay, contiguous supersession with old price preserved, line lineage across versions, exact effective-boundary resolution, cadence round-trip, mixed-currency rejection, out-of-order rejection, duplicate-line rejection, idempotency-key requirement and transaction-boundary controls.
- `tests/test_credit_notes.py` verifies invoice balance reduction, exact ledger linkage, application reversal through `reversal_of_entry_id`, restored balances, idempotent reversal, `SELECT ... FOR UPDATE` of credit-note and invoice rows, over-application rejection, one-row replay and HTTP 409 when an idempotency key is reused for a different confirmation.
- Dedicated migrations add credit-application evidence, credit-note lifecycle evidence and a legacy balance-invariant backfill, showing the correction model is carried through schema evolution rather than only test fixtures.
- `tests/test_subscription_billing_cadence.py` explicitly exercises contract-derived billing cadence as source-of-truth with offer pricing as fallback-only.
- Repository history is active and the exact inspected HEAD is a signed/verified GitHub merge commit dated 2026-09-20; the relevant billing-contract path has substantive prior evolution rather than being introduced only by the version-bump HEAD.

**CLAIMED / PLANNED / UNKNOWN:**
- The load-bearing limitation is explicit in source: the versioned billing-contract owner is presently an **expand-and-shadow migration plane**. Current shadow rows are review evidence and must not drive real money until a cut-over gate is passed.
- UNKNOWN: whether the inspected deployment has completed that cut-over anywhere; whether every negotiated amendment/exception is captured; whether any historical customer population has been independently reconciled; realized recovered dollars and ROI.
- UNKNOWN: third-party Splynx/provider feeds and external data/API rights. The user's standing commercial authorization applies to repository-owned public code, not third-party systems/data.
- GitHub exposes no public repository-license metadata at this revision; treat rights provenance as `no detected public license`, while applying the user's separate commercial-code authorization assumption for this analysis.

**FROZEN EVIDENCE MANIFEST:** `sha256:389ee6adf32452a7f4da461c30bbd4efe2883a9bd4c68fdc529b63b9b412cca2`, binding exact revision to these inspected paths: `app/services/billing/contracts.py`, `app/models/billing_contract.py`, `tests/test_billing_contracts.py`, `app/services/billing/credit_notes.py`, `tests/test_credit_notes.py`, `alembic/versions/293_credit_application_evidence.py`, `alembic/versions/294_credit_note_lifecycle_evidence.py`, `alembic/versions/346_credit_note_legacy_balance_backfill.py`, and `tests/test_subscription_billing_cadence.py`. No repository code was executed.

**COMPARATORS:**
- `cboxdk/laravel-billing@ac3305f2a857baf5208a1170387f7771dba40ca7` is a strong low-attention MIT component. Its tests verify effective-dated catalog versions and subscriber grandfathering; refund tests verify credit-note tax reversal, ledger reversal, gateway money movement with a scoped idempotency key, no over-refund, retry no-op and a recorded gateway settlement. It is cleaner as a reusable billing library, but its authority model is primarily catalog-price pinning rather than the selected candidate's customer-specific immutable commercial-contract chain. Its current HEAD also fixes a CI configuration that had prevented the suite from running for a period, so historical green-CI assumptions require caution.
- `getlago/lago@53082583d6bf65f54717bebd41cea8f47e8601a4` is the mature commodity reference: a highly adopted AGPL usage-billing platform with subscriptions, pricing, metering, payments and invoicing. It is important as the “simpler/commonplace alternative” check, but it does not by itself invalidate the narrower value here: explicit customer-contract authority lineage joined to reversible correction evidence.

**RED-TEAM OBJECTION:** The candidate can be over-promoted if “versioned billing contract” is silently read as “production-authoritative customer contract.” The implementation itself says the opposite today: this owner is shadowing, and shadow rows must not affect money. A sophisticated architecture with excellent tests is not evidence of recovered cash, complete contract ingestion or successful cut-over. The closest cheaper alternative is a mature billing platform plus a controlled contract table and credit-note workflow. Evidence that would reverse this objection: a cut-over revision/test proving invoice generation consumes authoritative contract versions, a frozen authorized historical contract/order population showing complete amendment coverage, and an end-to-end accepted leakage case whose correction is traced from contract authority to invoice delta to posted credit/refund/settlement.

**INDEPENDENT VERIFIER VERDICT:** **PASS_WITH_LIMITS** on the narrow claim that this exact revision implements and tests (a) an explicit, fail-closed versioned billing-contract authority migration plane and (b) idempotent, reversible credit-note-to-ledger correction evidence. The verifier does **not** certify that the contract plane is currently production-authoritative, that third-party feeds are complete, or that any dollars have been recovered. No sensitive-source material was used.

**A-F SCORE (proposed only, after verifier):** **26/30 — A3 / B5 / C5 / D5 / E5 / F3.**
- A3: a read-only authority/correction diagnostic can be piloted quickly, but production integration is materially heavier than run 1's standalone rules.
- B5: contract/billing authority and correction assurance can touch direct revenue, refunds, receivables and audit controls.
- C5: compresses substantial contract-versioning, temporal correctness, idempotency, ledger-correction and migration knowledge.
- D5: the combination of source-of-truth migration semantics + half-open immutable contract history + exact reversible correction evidence is unusually rich for a zero-star repository.
- E5: strong source/models/tests/migrations/history evidence, with the shadow-vs-authoritative limitation explicitly encoded rather than hidden.
- F3: no detected public license metadata, current contract authority is shadow-only, and external integration/data boundaries remain unresolved; standing user commercial authorization is assumed only for repository-owned code.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: billing/finance systems owner, Controller/CFO, or revenue-assurance lead at a subscription/telecom-style company with negotiated terms, plan changes and credit/refund workflows.
- Pain: mutable catalog/account/subscription state makes it difficult to prove what a customer actually contracted to pay at a historical moment and whether a correction truly reversed the right receivable once.
- First paid wedge: a read-only **Contract-to-Correction Audit** over one closed period. Reconstruct customer-specific terms into immutable versions, compare those terms to issued invoices, then trace accepted discrepancies through existing credit-note/refund/ledger evidence without posting money automatically. Measure unresolved-authority rate, false-positive review load, accepted correction dollars and time to produce audit evidence.

**COMBINATION WITH SHADOW RUN 1:** `dotmac_sub` supplies two missing layers around `Etherlabs-dev/revenue_leakage_system`: authoritative-term lineage (once cut over) before the expected-vs-actual rule engine, and correction/ledger evidence after a finding is accepted. The prospective stack becomes **contract authority → fail-closed leakage decision → human acceptance → idempotent credit/refund/ledger correction → realized-outcome verification**. The current shadow status means the first edge must still be proven before this can be called a production recovery loop.

**SEARCH EFFORT / COST PROXIES:** 3 materially different discovery modes; roughly 9 public search/query formulations; 2 serious low-attention candidates deep-inspected plus 1 mature commodity comparator; source/tests/schema/history inspection at exact revisions; approximately 40 external tool calls including required shadow-memory reads; 0 untrusted-repository code executions and 0 external commitments.

**LOCAL LESSON:** Run 1's local skill transferred: authority/freshness/evidence terms again outperformed generic billing searches. Adding `supersede`, `source of truth`, `credit note`, `reversal_of_entry_id`, `idempotency` and explicit shadow/authoritative states exposed a stronger missing-edge component. This is a second distinct successful application of the underlying authority-aware search principle inside the commercial shadow lane, but it remains lane-local because shadow hunters cannot globalize skills.

**NEXT TEST:** Find or falsify the **cut-over/outcome edge**: a production-shaped path where immutable customer-contract versions actually become invoice/rating authority and an accepted discrepancy can be followed through posted adjustment/refund/settlement to a reconciled receivable without silently defaulting missing terms.

## 2026-09-20 — Shadow run 3

**DATE:** 2026-09-20

**HYPOTHESIS:** A higher-value direct-money component will prove the entire internal economic chain, not merely one layer: effective-dated contract authority must select rating, billing close must consume rated facts into an issued receivable, settlement must be idempotently allocated, and reconciliation must prove the resulting money state. This should outperform repositories that only model authority or only validate settlement evidence.

**DISCOVERY METHODS:**
1. Direct repository/domain search for subscription billing, contract invoicing, credit/refund and reconciliation engines.
2. Code/invariant search for `contract_version_id`, effective intervals, rated usage, invoice lines, payment allocation, idempotency, append-only corrections and reconciliation checks.
3. Obscure-name/low-attention discovery: followed financial code hidden inside unrelated public products/context platforms rather than relying on billing-oriented repository names. This surfaced serious candidates with 0 stars and rich internal finance subsystems.

**BEST CANDIDATE + URL + EXACT REVISION:** `cyber-entrepreneur/wingcaster` — https://github.com/cyber-entrepreneur/wingcaster — `0d97a4ab8310d68b109e3a11ebdeda5eb3d3c829`.

**IMPLEMENTED:**
- `rating/engine.js` resolves an **ACTIVE**, effective-dated customer contract version for the metered timestamp, then resolves an ACTIVE effective-dated price version from that contract's meter components. The immutable rating payload pins contract version, price version, meter facts, model/tier/dimension inputs, billable units and amount.
- The rating path is append-only: corrections create new rated facts rather than mutating prior economic facts.
- `period-close.js` implements an idempotent 12-step close. It refuses to advance while usage is unmetered or active metered usage lacks a rating, snapshots rated facts, assembles/drafts the invoice, verifies totals, approves/issues the invoice, marks the billing period invoiced and only then finalizes it.
- `payment-allocation.js` records received payments with deterministic command idempotency and optional provider/provider-event deduplication, maintains unapplied cash, locks invoices in stable order, writes both payment→invoice and invoice→payment allocation evidence, transitions receivables through PART_PAID/PAID, and can reverse prior allocation state.
- The reconciliation engine contains explicit blocking checks spanning ledger balance, usage/rating, invoice-line/rated-usage equivalence, contract/currency consistency, and payment-allocation mirrors. Critical drift can block billing close rather than merely create a dashboard warning.

**TESTED / HISTORY:**
- `runner-billed-green.test.js` is the strongest evidence: on PostgreSQL it seeds a rated case, runs `rateMeteredUsage`, opens and closes a billing period through FINAL, verifies one invoice, records a payment, allocates the exact invoice balance, runs the full reconciliation suite, and requires every non-error reconciliation check to be GREEN.
- Separate rating, append-only, period-close and reconciliation suites are present; the search also exposed dedicated R040–R046 and R080–R083 reconciliation groups.
- Finance history is staged rather than one-shot: the rating engine first entered in the verified 2026-08-19 Stage 5 commit, with later vendor-economics/reconciliation work on 2026-08-21; current repository HEAD is a verified GitHub commit dated 2026-09-20.

**CLAIMED / PLANNED / UNKNOWN:**
- This proves an **internal accounting/reconciliation loop**, not bank or payment-processor truth. `recordPayment` may bind provider/provider-event identity, but the inspected evidence does not independently read back settlement from a PSP/bank before declaring the internal payment record authoritative.
- Contract versions are operationally authoritative inside the engine once ACTIVE, but the inspected packet does not prove how signed customer amendments enter that table or whether all exceptions are captured.
- The end-to-end test uses repository-generated fixtures and the same system's reconciliation checks; it demonstrates strong invariant coherence but is not an independent economic oracle and does not prove recovered revenue, production precision or customer adoption.
- GitHub reports `license: null` and no root LICENSE was found. Record public rights as `no detected public license`; for this hunt only, the user's standing separate commercial-code permission remains the working repository-code assumption.

**FROZEN EVIDENCE MANIFEST:** `sha256:d33da4ed4c5b25cc3d64b33e064680c75238ffcf7152557b44f7f2acbaa4bd65`, binding exact revision plus:
- `backend/src/fin/rating/engine.js` — Git blob `26b00ca28f04fb31cbd4ea7b5feced73837e440e`
- `backend/src/fin/billing/period-close.js` — `6d35212e474061f87c62c2ebe61fb7e98f04890a`
- `backend/src/fin/billing/payment-allocation.js` — `8d55727c0d796df625c6cf4f1f56a211bb82fa04`
- `backend/src/fin/reconciliation/checks.js` — `2911955fb0438143bd9146f86b33f38df8040b92`
- `backend/src/fin/reconciliation/runner-billed-green.test.js` — `ad2d3eaf91e049816564c42489b23d06ab047c46`
No repository code was executed.

**COMPARATORS:**
- `UnlikeOtherAI/UnlikeOtherAuthenticator@102b16ccd900418b36fa846c90daa75cb48a7587` is a close second and publicly MIT-licensed. Its source materializes forward-only customer contract versions into custom/manual tariffs, calculates invoices from the effective contract version, hashes calculation evidence including contract version and metering/credit snapshots, freezes invoice evidence after calculation, and records idempotent PAYMENT/REFUND/WRITE_OFF events. Its database tests are excellent. The decisive limitation for this hypothesis is that the inspected contract-invoice settlement source is explicitly **MANUAL**; it therefore proves receivable-state accounting better than provider-grounded outcome truth.
- `yvgude/lean-ctx@613e95ff64a69845a61b0025065d18a214039b53` has a sophisticated content-addressed settlement-evidence verifier with explicit Baseline/Price/Contract/Quality/Attribution/PeriodCompletion/CustomerApproval roles and out-of-band trust anchors. Its own source expressly says it does **not** validate contracts, calculate prices, issue invoices or mutate settlement state. That makes it valuable as an evidence-oracle component but a direct falsification of the idea that settlement evidence alone closes the money loop.

**RED-TEAM / INDEPENDENT VERIFIER VERDICT:** **PASS_WITH_LIMITS.** On the frozen packet, the narrow claim is supported: this exact revision implements and tests an internal chain from effective-dated ACTIVE contract/price selection → append-only rating → gated billing close/invoice issue → idempotent payment allocation → all-green reconciliation. The verifier specifically rejects stronger wording such as “processor-settled,” “bank-reconciled,” “customer-contract complete,” or “recovered revenue.” The strongest objection is circular authority: contract rows, payment records and reconciliation facts are largely produced or accepted inside the same system. External signed-contract ingestion and PSP/bank readback are not independently proven.

**A-F SCORE (proposed only, after verifier):** **26/30 — A3 / B5 / C5 / D5 / E5 / F3.**
- A3: a read-only trace/reconciliation diagnostic is sellable without moving money, but integrating all source systems is heavier than a single leakage rule service.
- B5: contract-to-receivable integrity touches billing correctness, cash application, collections and close controls.
- C5: compresses a large amount of temporal rating, invoice state-machine, idempotency, allocation and reconciliation engineering.
- D5: a tested effective-contract→rating→invoice→payment→reconciliation chain is unusually rich in a zero-star public repository.
- E5: source, integration tests, invariant checks and staged history strongly support the narrow internal-loop claim.
- F3: operational surface is broad and public licensing is absent; external contract/provider authority remains unresolved even under the user's separate repository-code permission assumption.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: Controller/CFO, billing-platform owner or revenue-assurance lead at a usage/subscription business with negotiated pricing and nontrivial cash application.
- Pain: finance teams can prove pieces of the chain but cannot cheaply answer one question end-to-end: “Which contract version priced this usage, which receivable did it create, what cash/credit settled it, and do all independent ledgers still agree?”
- First paid wedge: a read-only **Revenue-to-Receivable Trace Audit** over one closed period. Reconstruct contract/rate authority, freeze rated usage and invoice evidence, trace payment/credit allocation, then return only broken invariants and unresolved authority gaps. Measure dollars with broken provenance, unreconciled receivables, duplicate/over-applied cash prevented and analyst hours saved.

**COMBINATION WITH PRIOR SHADOW RUNS:** This closes most of the internal outcome edge around the run-1/run-2 stack. `dotmac_sub` remains stronger for explicit commercial-contract provenance/migration; `Etherlabs-dev/revenue_leakage_system` remains stronger for fail-closed expected-vs-actual leakage decisions; Wingcaster supplies a tested **rating → receivable → cash-allocation → reconciliation** backbone. Combined shape: **contract authority → leakage decision → accepted correction → rated/issued receivable → idempotent cash/credit allocation → reconciliation proof**. The remaining high-value gap is external authority/readback, not another internal billing engine.

**SEARCH EFFORT / COST PROXIES:** 3 materially different discovery modes; 3 serious candidates deep-inspected; source/tests/history verified at exact revisions; 67 external connector/tool calls including required shadow-memory reads and repository writes, plus one local manifest-hash computation; 0 untrusted-repository code executions, contacts, spend or commitments.

**LOCAL LESSON:** `SK-COM-001` transferred for a third distinct shadow run: authority/effective-date/idempotency terms again outperformed generic billing keywords. A new lane-local refinement also worked once: require a single integration test that crosses **authority → rating → invoice → settlement → reconciliation**, then inspect the source at each transition rather than awarding completeness from module names. This refinement remains LOCAL after one success and is not promoted to shared search skills.

**REFERRALS:** No new cross-lane referral; the existing provider/system-of-record readback referral already captures the remaining gap and should not be duplicated.

**NEXT TEST:** Find or falsify an external-authority bridge: a component that binds signed/order-system contract amendments and PSP/bank settlement readback into immutable evidence, so the internal closed loop cannot declare itself correct using only its own contract and payment records.

## 2026-09-20 — Shadow run 4

**DATE:** 2026-09-20

**HYPOTHESIS:** The highest-value missing money-control component will make the crash window around an external money mutation explicit: persist the exact action and provider idempotency identity before the call, hold economic capacity when provider outcome is ambiguous, and resolve the ambiguity through read-only provider truth rather than silently retrying with a new action. This should outperform ordinary webhook/retry code that conflates “request failed” with “no financial effect.”

**DISCOVERY METHODS:**
1. Direct problem search for billing/payment reconciliation, refund recovery, settlement and ambiguous provider outcomes.
2. Code/invariant search for `PaymentIntent.retrieve`, `Refund.retrieve`, deterministic idempotency, `outcome_unknown`, provider operation IDs, read-only reconciliation, durable reservations and effect/non-effect conclusions.
3. Deliberate low-attention exact-money-mutation search around Stripe refund recovery and billing execution consoles, followed by comparison with a broader SaaS billing implementation that has provider readback but weaker money-domain lifecycle semantics.

**BEST CANDIDATE + URL + EXACT REVISION:** `auths-dev/auths-proof` — https://github.com/auths-dev/auths-proof — `34fa1f33cf365fa54075a2002710aee52ab42394`.

**IMPLEMENTED:**
- The bounded Stripe refund service writes a durable decision and aggregate reservation before credential acquisition/provider entry. The reservation binds the exact action digest, policy/evidence/configuration commitments, amount/currency/account and a digest of the deterministic Stripe idempotency key.
- Provider execution is modeled as an exact-idempotent lifecycle intent. If the Stripe gateway returns `OutcomeUnknown`, the service transitions the reservation to durable `OutcomeUnknown` instead of releasing it or assuming non-effect. Provider-response mismatch is handled the same fail-closed way.
- Aggregate capacity accounting includes `committed + reserved + outcome_unknown`; ambiguous refunds therefore continue consuming the bounded money budget until reconciliation proves effect or non-effect. Rolling-window tests explicitly show unresolved capacity does not age out merely because time advances.
- `reconcile_bounded_refund` accepts only an ambiguous workflow, binds the original provider-request digest into a reconciliation observation, records a read-only provider evidence source (`stripe-api-refund-list/1`), and atomically maps the outcome to committed/effect or released/non-effect in both shared lifecycle and Stripe-domain reservation state.
- The qualification adapter exposes provider **Execute** and **Reconcile** as separate call kinds. Reconciliation reads the original idempotent refund from stored profile state; `observe_provider_truth` independently reads provider truth with a runtime-read credential rather than issuing another mutation.

**TESTED / SCHEMA / HISTORY:**
- `reservation.rs` contains direct tests that `OutcomeUnknown` capacity remains held until reconciliation; that durable state survives process restart and can then reconcile to released/non-effect; that unresolved rolling-window capacity does not age out; that concurrent last-capacity reservation succeeds only once; and that shared lifecycle + Stripe capacity reservation commit atomically.
- The durable reservation schema explicitly distinguishes `Reserved`, `Committed`, `Released`, `OutcomeUnknown`, `ReconciledCommitted`, and `ReconciledReleased`, with canonical persisted state validation and no silent migration of obsolete prelaunch state.
- The exact-refund specification independently states the intended ambiguous-response rule: preserve the action claim as `outcome_unknown`, reuse identical idempotency/parameters only within bounded recovery, retrieve/list-correlate the provider refund, classify created/not-created/indeterminate, and never silently create a new action or idempotency key.
- Relevant history is staged: `1c1ab690...` (“Add Stripe-local bounded refunds”, 2026-07-29), `91b84cc5...` (“Decouple Stripe profile receipts and credentials”, 2026-07-30), and `4e44d0a0...` (“feat(stripe): adopt shared durable lifecycle”, 2026-07-31).
- Rights are unusually clear for this class of component: the workspace declares `MIT OR Apache-2.0`, and repository release docs state both license texts are present.

**CLAIMED / PLANNED / UNKNOWN:**
- This exact repository state does **not** prove production-qualified Stripe recovery. The live-provider qualification specification explicitly says the initial Stripe refund production state is **unqualified / synthetic testkit only** and requires a protected real-provider run, crash testing on both sides of provider boundaries, replay/no-second-effect proof, response-loss/restart convergence, signed attestation and matching semantic-closure digest before a production route may be advertised.
- The exact-refund profile is intentionally test-mode-only and explicitly does not claim that an accepted Stripe refund has settled through banking networks.
- Current HEAD is prelaunch/pre-audit. GitHub check-runs inspected for this exact SHA show several fuzz/fuzz-implementation jobs failing on 2026-09-20, while a fuzz-plan job succeeded; therefore no blanket “green CI” claim is allowed.
- UNKNOWN: a checked-in live Stripe qualification attestation for this exact semantic closure, independent production audit, real customer recovery/duplicate-prevention economics, and bank-settlement truth.

**FROZEN EVIDENCE MANIFEST:** `sha256:a0c699be814934e676b1cbfd81b48ded0a3f25b404aaecfbca104ed361cfbdf5`, binding exact revision plus:
- `product/integrations/auths-stripe/src/bounded_service.rs` — `94bb6dbec8c8b3f026c828fea94b74e35894cba6`
- `product/integrations/auths-stripe/src/reservation.rs` — `ad43968ddd6caacded232e616b301b0dcfee6c39`
- `product/integrations/auths-stripe/src/qualification.rs` — `7b3907daa590aab0576c4bb027348dcecf67f8a0`
- `docs/specs/0010-stripe-exact-refunds.md` — `35cbe401e6322d661c97b112f91e680787c47b82`
- `docs/specs/0044-live-provider-qualification-and-recovery-evidence.md` — `36e678bffe324de02e2fe3aef3455e3c9efd4438`
- `Cargo.toml` — `f039a8786967a3f4e25ea5df2ee97c66fd9fea2b`
No repository code or provider mutation was executed in this shadow run.

**COMPARATORS:**
- `sunny-aryan/billing-recovery-execution-console@b0f688eeec3ecf6f2d6d751ac25e3e2f4c811f24` is a simpler, portfolio-oriented execution console whose actual source creates Stripe **test-mode** PaymentIntents/refunds with stable idempotency keys, stores the refund ID, performs `Refund.retrieve` readback, classifies unknown lookup failures safely, and has mock reconciliation tests for provider-success/internal-failure and internal-success/provider-missing mismatches. It is easier to understand and closer to a conventional billing-ops UI, but its automated reconciliation evidence inspected here is mostly mock-shaped and it lacks Auths' explicit bounded-capacity `OutcomeUnknown` semantics.
- `magasiev13/AOC-SMS-Admin@2b3db60eb2161f25cbb5c4d5a13930b1b2311edc` contains production-shaped billing code that performs `PaymentIntent.retrieve`, tracks settlement versions and keeps a per-message usage ledger for billing reconciliation. Its relevant tests use mocked Stripe objects, and the broader application does not expose an equally narrow crash-window/effect-state contract in the inspected packet.

**RED-TEAM OBJECTION:** The candidate is easiest to overrate precisely because its recovery specification is excellent. Its own strongest launch-gate document says Stripe refund is currently **unqualified**, so the architecture cannot be cited as proof that a real-provider crash/restart path has already passed protected qualification. A simpler worker with a durable command table, one stable provider idempotency key and `Refund.retrieve`/webhook reconciliation may be sufficient for many billing teams. Current fuzz failures further reduce confidence in treating HEAD as release-clean. Evidence that would reverse this objection: a trusted qualification attestation bound to this exact semantic closure; a protected run showing a crash after provider entry then restart/read-only convergence against real Stripe test infrastructure with no duplicate refund; clean relevant CI; and, for a stronger commercial claim, independent settlement/readback beyond API-object existence.

**INDEPENDENT VERIFIER VERDICT:** **PASS_WITH_LIMITS.** On the frozen evidence packet, the narrow claim passes: this exact revision implements and source-tests a durable Stripe refund lifecycle that holds money capacity when provider effect is ambiguous and can reconcile effect/non-effect without silently creating a new action or idempotency identity. The verifier rejects the stronger claim that this revision is production-qualified against Stripe: the repository's own qualification contract explicitly marks Stripe refund unqualified, and current HEAD has failing fuzz jobs. It also rejects any claim of bank settlement, recovered dollars or customer-contract authority. No sensitive-source material was used.

**A-F SCORE (proposed only, after verifier):** **26/30 — A3 / B5 / C5 / D5 / E4 / F4.**
- A3: the first sellable wedge is a controlled refund/correction execution-safety layer, but integration into an existing billing/provider stack is nontrivial.
- B5: duplicate refunds, uncertain corrections and unsafe retries are direct-money risks with high downside and audit value.
- C5: compresses difficult state-machine, idempotency, crash-recovery, bounded-capacity and evidence-design work.
- D5: explicit money-capacity treatment of provider-unknown outcomes plus separate reconciliation/qualification semantics is unusually rigorous.
- E4: source, state schema, focused tests and history are strong, but exact live-provider qualification is absent and current fuzz CI is not clean.
- F4: MIT/Apache licensing and explicit operational gates are clear; live provider qualification/prelaunch status still blocks drop-in production use.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: billing/payments platform lead, Controller/RevOps owner of high-volume corrections/refunds, or fintech engineering team operating money-mutating workflows.
- Pain: after a timeout or worker crash, teams often cannot distinguish “provider never received it” from “money moved but local state did not,” creating duplicate-refund risk, manual provider spelunking and weak audit evidence.
- First paid wedge: a **Provider Outcome Guard** around one existing approved refund/correction path. Persist the exact authorized command and idempotency identity before dispatch, represent ambiguous effects explicitly, perform read-only provider reconciliation, and report unresolved/duplicate-risk cases without autonomously creating new financial actions. Start in test mode/read-only recovery; measure ambiguous-case resolution time, duplicate-effect prevention and manual investigation hours.

**COMBINATION WITH PRIOR SHADOW RUNS:** This adds a missing execution-safety layer after run 1's leakage decision and run 2's accepted correction evidence, and it strengthens run 3's internal rating/receivable/reconciliation backbone. The prospective architecture becomes **external contract authority → fail-closed leakage decision → human-approved correction → durable exact money command/idempotency → provider effect or `OutcomeUnknown` → read-only provider reconciliation → receivable/ledger reconciliation**. It still does not close signed-contract ingestion or independently attested bank/processor settlement.

**SEARCH EFFORT / COST PROXIES:** 3 materially different discovery modes; 3 serious candidates deep-inspected; source/tests/state schema/history inspected at exact revisions; roughly 50 external connector/tool calls including required shadow-memory reads and write-SHA refreshes; one local frozen-manifest hash; 0 untrusted-repository code executions, provider writes, contacts, spend or commitments.

**LOCAL LESSON:** `SK-COM-002` transferred to a second distinct shadow run. Tracing one money-state transition all the way across **durable intent → provider entry → ambiguous outcome → read-only provider truth → terminal effect/non-effect** was higher signal than searching for “Stripe reconciliation” alone. The most important new discriminator is **qualification state**: adapter code or even a live-test design must not be silently upgraded into externally proven provider truth when the repository itself gates that route as unqualified.

**REFERRALS:** No new cross-lane referral; existing provider/system-of-record readback referrals already ask the correct structural question and should not be duplicated.

**NEXT TEST:** Find a candidate with **checked-in, revision-bound external outcome evidence**—for example a real-provider qualification attestation or integration artifact proving crash-after-dispatch → restart → read-only convergence with no duplicate money effect—or falsify whether public repositories expose enough lawful evidence to distinguish this from well-designed but still unqualified recovery code.

## 2026-09-20 — Shadow run 5

**DATE:** 2026-09-20

**HYPOTHESIS:** A stronger external-outcome component should contain revision-bound evidence from a real provider or provider sandbox showing an ambiguous post-dispatch money action, process restart, read-only provider reconciliation and no duplicate effect. Merely documenting this recovery design or proving it against a simulator is insufficient.

**DISCOVERY METHODS:**
1. Direct problem search for `OutcomeUnknown`, refund/payment idempotency, reconciliation and provider readback.
2. Code-invariant search for crash/restart, response-loss, stable idempotency and retrieve/reconcile paths.
3. External-evidence search for live/sandbox smoke suites, qualification attestations, CI artifacts and checked-in run records rather than README claims.
4. Comparator inspection of synthetic restart/no-duplicate harnesses and ambiguous-withdrawal recovery code to separate architectural quality from external proof.

**BEST CANDIDATE + URL + EXACT REVISION:** `revaly-co/RAP-sdk` — https://github.com/revaly-co/RAP-sdk — `b0c7f0e80042f654155d72c7663340f46985865e`.

**IMPLEMENTED:**
- Six server-side SDK runtimes implement a failover contract that classifies an uncertain after-send transport failure as `OutcomeUnknown` rather than guessing toward “safe,” performs no automatic resubmission, and exposes bounded read-only reconciliation by merchant transaction identity.
- Reconciliation returns `Found` or `NotFoundYet`; absence is explicitly not treated as proof that the original action did not occur.
- Stage-4 CI contains six language-specific live contract-smoke jobs, environment-scoped provider credentials, fail-closed secret requirements and a staging-only `pre-dispatch` fault seam.

**EXTERNAL / REVISION-BOUND EVIDENCE:**
- `docs/adr/024-stage4-contract-smoke-environment.md` is a checked-in implementation/evidence record for live staging smoke. It records the stage-4 build commit lineage, six-language live runs, real validation/auth/fault rows and `reconcile Found/NotFoundYet` behavior. History independently shows merge commit `e1410c2ed9a23068bfca2f9c49328921e88f4f19` adding the six live suites and pipeline jobs.
- `docs/prod-sandbox-validation.md` is stronger external evidence: it records a 2026-07-25 run against `https://api.revaly.co` through the production edge using a sandbox-scoped merchant key and released v0.4.1 artifacts across all six languages. The checked-in record reports **39 passed / 0 failed / 8 skipped**, with approved and declined charges, 400 classification, `reconcile Found(Approved)`, real-404 `NotFoundYet` and secondary read surfaces.
- The same evidence record explicitly states that no language retried or resubmitted and that the reconcile helper was the only loop.
- Apache-2.0 public licensing is reported at the exact inspected revision; repository metadata shows 0 stars / 0 forks, so this was low-attention despite substantive live-provider evidence.

**CRITICAL FALSIFICATION:** The exact row this run was trying to prove is **not externally proven**. The production-sandbox record explicitly marks `charge-outcome-unknown` as **SKIP — no deterministic live trigger / preflight-only**. The staging fault seam is `pre-dispatch`, which is useful for proving `not_processed` but cannot prove crash-after-provider-effect ambiguity. Searches for `post-dispatch`, response-loss/restart and crash reconciliation did not surface a live test in this repository. Thus RAP-sdk proves live provider classification + read-only reconciliation, but not **crash-after-dispatch → restart → no duplicate effect**.

**EVIDENCE / HISTORY PACKET:**
- `docs/prod-sandbox-validation.md` — Git blob `ac4f402ee4a57e1b7b3449e3e648d665ee2d40a6`
- `docs/adr/024-stage4-contract-smoke-environment.md` — `06d40d78dbd47676fe8d80339752dbd27cc7149f`
- `.github/workflows/pipeline.yml` — `cd50d183fd6ea15523717bebb4ce3ef37eb34690`
- `docs/failover-contract.md` — `8d8ebd4a94d062c47193f06719dfd53417dec618`
- `languages/typescript/smoke/contract.smoke.ts` — `747b4f475eee4b91c665ad581d3a36c98d482dc0`
- Stage-4 merge lineage: `e1410c2ed9a23068bfca2f9c49328921e88f4f19`.
No repository code, provider mutation or credentialed external action was executed in this shadow run.

**COMPARATORS:**
- `mastra-ai/mastra@fbce7580675247e5b4986637463f4328ceb77f34` has an excellent refund-recovery integration test: durable attempt registry, stable idempotency, synthetic “drop after commit,” process recovery and provider-truth reconciliation with an assertion against duplicate refund. The decisive limitation is that the inspected Stripe transport is synthetic, so it proves the crash invariant more directly than RAP but not against an external provider.
- `Layr-Labs/d-inference@d78ae77efaad100ad59d7ea35487a09085f04889` correctly recognizes an ambiguous Stripe Connect transfer window and records an unconfirmed state rather than simply restoring balance. The inspected recovery path is more operator/manual and did not provide checked-in external restart/readback/no-duplicate proof.

**RED-TEAM OBJECTION:** RAP's checked-in evidence is unusually concrete, but it remains self-authored evidence. Historical workflow-run IDs referenced in the docs are no longer retrievable through the current GitHub Actions API (consistent with run-retention limits), and the production-sandbox evidence itself discloses that the separate harness's v0.4.1 working-copy upgrade was not pushed at run time. More importantly, the live environment could not deterministically trigger the post-send ambiguity row. It would be incorrect to combine the repository's excellent `OutcomeUnknown` design with its live smoke evidence and silently conclude that a real-provider crash/restart recovery was proven.

**INDEPENDENT VERIFIER VERDICT:** **PASS_WITH_LIMITS** on the narrow claim that this exact revision contains implementation, history and checked-in live-provider/sandbox evidence for safe failure classification plus read-only reconciliation across six runtimes. **FAIL / NOT PROVEN** for the stronger run hypothesis: there is no revision-bound live proof of post-dispatch response loss or crash → restart → read-only convergence → no duplicate money effect. No sensitive-source material was used.

**A-F SCORE (proposed only, after verifier):** **25/30 — A3 / B4 / C4 / D4 / E5 / F5.**
- A3: commercially useful as a qualification/reconciliation pattern, but not a drop-in money-recovery product.
- B4: avoiding duplicate charges/refunds and misclassified failover has direct financial value, though this SDK is tied to a particular provider contract.
- C4: compresses six-runtime error taxonomy, bounded reconcile semantics and live qualification machinery.
- D4: live production-edge sandbox evidence plus explicit unknown-state semantics is uncommon in a zero-star SDK repository.
- E5: source, smoke suites, CI wiring, ADR history and checked-in real-environment evidence are unusually strong; the missing ambiguity row is disclosed rather than hidden.
- F5: Apache-2.0, public provenance and explicit operational/environment boundaries are clean.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: payments-platform engineering lead, merchant reliability team or finance-systems owner integrating a processor/failover path.
- Pain: payment clients often confuse network failure with non-effect, then retry unsafely or cannot prove which recovery behavior has actually been exercised against a real environment.
- First paid wedge: an **External Reconciliation Qualification Harness** for one existing money-moving API. It remains read-only/recommend-only in this shadow context: enumerate failure classes, bind a stable business id, prove live `Found/NotFoundYet` readback, record which rows cannot be triggered safely, and refuse to certify crash recovery until a controlled post-dispatch response-loss test exists.

**COMBINATION WITH PRIOR SHADOW RUNS:** RAP-sdk supplies something run 4's Auths candidate lacked: checked-in evidence that real external provider/sandbox classification and read-only reconciliation were actually exercised. Auths supplies the stronger durable crash/`OutcomeUnknown` state machine. Together they define a much better qualification target, but they do **not** close the proof gap because the real-environment RAP run skipped `OutcomeUnknown` and the Auths real-provider route was unqualified.

**SEARCH EFFORT / COST PROXIES:** 4 materially different discovery modes; 3 serious candidates deep-inspected; source/tests/protocol shape/history/live-evidence records verified at exact revisions; no untrusted code execution, provider writes, contacts, spend or commitments.

**LOCAL LESSON:** Add an **external-outcome evidence ladder** when evaluating money recovery: (1) mock/unit retry semantics; (2) synthetic provider + restart/no-duplicate; (3) real provider/sandbox smoke; (4) revision-bound external readback evidence; (5) controlled post-dispatch ambiguity + restart + no-duplicate proof. Do not collapse tiers 3–4 into tier 5. This discriminator succeeded once and remains lane-local.

**REFERRALS:** No new referral. The existing external provider/system-of-record readback referral remains precise; this run adds evidence that live smoke alone still leaves the ambiguity gap open.

**NEXT TEST:** Find a lawful public component or evidence record with a **controlled post-dispatch response-loss seam** against a real provider/sandbox, where the original action is externally visible after restart and a read-only lookup proves convergence without a second money effect. If none exists after repeated targeted runs, treat the absence itself as durable negative knowledge and shift toward building a safe qualification harness rather than hunting indefinitely.

## 2026-09-20 — Shadow run 6

**DATE:** 2026-09-20

**HYPOTHESIS:** A verifier-passable upgrade exists in a low-attention repository whose test harness performs a real provider-sandbox money mutation, deliberately suppresses the response only after provider commit, persists/quarantines the ambiguous local state, then uses a later read-only provider observation to converge without issuing a second mutation. Literal OS process restart is a separate proof obligation and must not be inferred from a fresh recovery invocation.

**DISCOVERY METHODS:**
1. Direct problem search for post-dispatch response loss, payment/refund reconciliation, provider idempotency and ambiguous outcomes.
2. Code/invariant search for `drop response after commit`, `SIMULATED_LOST_RESPONSE`, stable provider idempotency, recovery-blocked/unknown states and retrieve-before-retry logic.
3. Real-environment/fault-seam search for Stripe test-mode/sandbox integration tests that wrap the production provider adapter, mutate first, throw second, then reconcile from provider state.

**BEST CANDIDATE + URL + EXACT REVISION:** `mileswallace06/peanutgalleryfinal` — https://github.com/mileswallace06/peanutgalleryfinal — `ebe3df6ad36b159e26d11adda7498c99a801d9c5`.

**IMPLEMENTED:**
- `base44/shared/stripeCancelProvider.js` is the shared production Stripe cancellation adapter. It retrieves the exact PaymentIntent first; cancellable states are canceled using a supplied stable Stripe idempotency key, already-canceled state returns success without a second cancel, captured/succeeded state fails closed, and retrieve/cancel network uncertainty maps to `unknown`.
- `base44/shared/abortCanaryOrchestrator.js` begins a durable cancel action before provider entry, carries the stable Stripe idempotency identity, invokes the provider outside Postgres, records `succeeded|failed|unknown`, and fail-closes unknown/failed results into `recovery_blocked` state rather than releasing the reservation.
- On a later invocation with `recovery_blocked=true`, the orchestrator resolves the pre-existing action, skips `begin_cancel`, reuses the original action/idempotency identity, calls the provider adapter once, and records the reconciled result. The provider adapter itself retrieves first, so an externally canceled PaymentIntent is observed as already canceled with no second cancel API call.
- The schema makes ambiguity durable rather than cosmetic: payment bindings include `cancel_requested`, `cancel_unknown`, `cancel_failed`, `canceled`; payment actions include `pending`, `in_flight`, `succeeded`, `failed`, `unknown`, a unique Stripe idempotency key, leasing/crash-recovery fields and partial unique indexes preventing concurrent pending cancel/capture/refund actions per purchase.

**REAL PROVIDER TEST / EXTERNAL EVIDENCE:**
- `tests/abort-canary-real-stripe.test.mjs` explicitly targets the same production routing seam and production provider adapter. It creates real Stripe **TEST-mode** manual-capture PaymentIntents (`livemode=false`). Its observability wrapper first awaits the real adapter's successful cancel and only then throws `SIMULATED_LOST_RESPONSE`; therefore the external provider mutation has occurred before the application loses the response.
- T3 then verifies the first invocation becomes `cancel_unknown`, `recovery_blocked`, binding=`cancel_unknown`, with exactly one real cancel. A second invocation uses a **fresh adapter instance**, reads the persisted authority/action state, retrieves Stripe's actual PaymentIntent state, observes `canceled`, clears recovery blocking, resolves the incident and asserts **zero additional cancel calls** plus one provider retrieve.
- T1/T2 separately assert one real cancel, provider readback and replay with no additional provider mutation. The checked-in certification manifest records `real-Stripe abort 92/92` and describes the exact suite as “lost-response reconcile without recancel”; it also explicitly limits certification to Stripe test mode and keeps the canary flag OFF for production/live money.
- A sibling real-Stripe capture harness independently contains the same mutate-then-throw fault shape (`throwAfterCapture` after successful provider capture), which is useful evidence that the pattern is not unique to cancellation, although this run's verifier claim remains scoped to cancellation.

**SOURCE / TEST / SCHEMA / HISTORY VERIFICATION:**
- Production adapter source verified: `base44/shared/stripeCancelProvider.js`.
- Orchestration/recovery source verified: `base44/shared/abortCanaryOrchestrator.js`.
- Real-provider test source verified: `tests/abort-canary-real-stripe.test.mjs`.
- Durable-state schema verified: `database/authority_v1/001_schema.sql`.
- Revision-bound certification record verified: `src/docs/AUTHORITY_V1_CANARY_CERTIFICATION.md`.
- History independently shows commit `d2fe443b40e07bbc79bbfc20a1bcea45d6f1081f` on 2026-08-31 with message **“Implement real Stripe checkout abort functionality”** introducing the real-Stripe abort test path; current inspected HEAD is `ebe3df6ad36b159e26d11adda7498c99a801d9c5` dated 2026-09-17.
- Repository metadata at inspection: 0 stars / 0 forks; GitHub public license metadata is null.

**CLAIMED / PLANNED / UNKNOWN:**
- The strongest run hypothesis is only **partially** proven. T3 is a real Stripe test-mode post-dispatch response-loss + later-provider-readback/no-recancel proof, but the second phase is a later invocation with a fresh adapter inside the same test process; it is **not** a literal OS process kill/restart test.
- The 92/92 certification result is a checked-in, self-authored certification record. I did not find a separate machine-readable raw P0-01P result artifact at the exact revision, and the credentialed suite was not independently rerun in this shadow pass.
- The canary route is explicitly flag-OFF and live Stripe is explicitly **not certified**. No real customer money, real customer data, bank settlement, recovered dollars or ROI is proven.
- Public repository licensing is `no detected public license`; the user's standing separate commercial-code authorization is the repository-code working assumption only and does not extend to Stripe services/data.

**FROZEN EVIDENCE MANIFEST:** `sha256:75b1280a0e8433519728c59ceea4b819bca5c0cd0fcb64312102e1d45f3fd1bf`, binding exact revision to:
- `tests/abort-canary-real-stripe.test.mjs` — Git blob `e23c824c0c3a935a27de8d94b7d6810a68016dd5`
- `base44/shared/stripeCancelProvider.js` — `7ecf1d11bdf9daf3868b343702dbde64aea608d6`
- `base44/shared/abortCanaryOrchestrator.js` — `0f691315e5d7f6a0c2412ad0fdbd762643b3474a`
- `database/authority_v1/001_schema.sql` — `1853674c35c3d2554a071cbb0dd527f6c9a0cd74`
- `src/docs/AUTHORITY_V1_CANARY_CERTIFICATION.md` — `46382f8eebe9e223369ea9b1bed661660d448f76`
- feature-lineage commit `d2fe443b40e07bbc79bbfc20a1bcea45d6f1081f`.
No repository code, Stripe mutation, credentials, contacts, spend or commitments were executed by this shadow run.

**COMPARATORS / FALSIFIERS:**
- `nidhi1603/proofcart@52d978bb4c2e5f4f9db4446d90c949ee14a0b1a4` implements a strong dropped-response-after-create simulator and a real Stripe test-mode rail, but its README explicitly says the dangerous dropped-response proof is deterministic/local and the live demo **skips** the response-drop test to avoid a second real charge. It also explicitly says a real OS process kill/restart is not tested. This makes it a good architecture comparator but weaker external evidence than the selected candidate.
- Run-5 `revaly-co/RAP-sdk@b0c7f0e80042f654155d72c7663340f46985865e` has stronger multi-language checked-in live-provider smoke evidence and cleaner Apache-2.0 provenance, but its dangerous `OutcomeUnknown` row is explicitly skipped because no deterministic live trigger exists. PeanutGallery closes that specific gap for Stripe cancellation by mutating a real test-mode object, suppressing the response after success, and reconciling later without recanceling.
- The closest cheaper alternative is a normal durable command table + one provider idempotency key + retrieve-before-retry worker. The selected candidate's extra value is the concrete real-provider ambiguity certification path, not the general architecture alone.

**RED-TEAM OBJECTION:** The repository is easy to over-promote because “fresh adapter on second invocation” can sound like “process restart.” It is not. The harness preserves durable Postgres state across two calls but does not kill and restart the runtime process around the provider boundary. The 92/92 claim is self-authored and was not independently rerun here; live Stripe remains uncertified; the production canary is flag-OFF; and cancellation of an uncaptured test PaymentIntent is economically safer than proving a refund or captured-charge correction after money has settled. Evidence that would reverse these limits: a committed runner that terminates the application process immediately after the real provider mutation, restarts against the same durable DB, performs read-only provider reconciliation, proves no second mutation, and emits a revision-bound machine-readable attestation.

**INDEPENDENT VERIFIER VERDICT:** **PASS_WITH_LIMITS.** On the frozen evidence packet, the narrow claim passes: this exact revision contains a production-shared Stripe test-mode cancellation path where a real provider mutation completes, the response is deliberately lost afterward, the application durably records an unknown/recovery-blocked state, and a later fresh recovery invocation observes provider state and resolves without a second cancel. The verifier **does not** accept stronger wording such as “OS crash/restart proven,” “live-money certified,” “bank-settled,” “independently attested 92/92,” or “production enabled.” No sensitive-source material was used.

**A-F SCORE (proposed only, after verifier):** **26/30 — A4 / B5 / C5 / D5 / E4 / F3.**
- A4: a provider-outcome qualification audit can be sold as a bounded sandbox/read-only reliability engagement without moving live money.
- B5: duplicate money effects and unresolved provider ambiguity are high-value payments/recovery risks.
- C5: compresses durable action state, idempotency, incident quarantine, provider readback, concurrency controls and qualification-harness design.
- D5: a zero-star repository with a real-provider mutate-then-lose-response test and no-second-mutation reconciliation is unusually rare.
- E4: source/test/schema/history plus a checked-in certification manifest are strong, but the 92/92 result was not independently rerun and literal process restart is missing.
- F3: no detected public license, production canary remains OFF and live Stripe is uncertified; standing commercial repository-code authorization does not solve external-service operability.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: payments/billing engineering lead, fintech platform owner, or Controller/RevOps team operating refunds, cancellations or corrective money actions.
- Pain: network/process failures after provider commit create the worst retry ambiguity—teams cannot tell whether to retry, quarantine or reconcile, and a wrong choice can duplicate a refund/charge or strand an obligation.
- First paid wedge: a **Payment Mutation Ambiguity Certification** for one existing Stripe/test-provider workflow. Instrument the real sandbox path, persist the command before dispatch, intentionally suppress the response after a safe test-mode mutation, verify durable UNKNOWN quarantine, perform a later read-only provider observation and certify no duplicate effect. Deliver a failure matrix plus the exact rows that remain unproven; do not touch live money in the first engagement.

**COMBINATION WITH PRIOR SHADOW RUNS:** This materially upgrades runs 4-5. Auths supplies the stronger generic durable `OutcomeUnknown`/bounded-capacity state model; RAP supplies multi-runtime live-smoke/readback evidence; PeanutGallery supplies the missing **real Stripe test-mode post-dispatch response suppression → durable unknown → later provider readback → zero second mutation** example. The combined target stack is now much more concrete, but a literal process-kill restart and externally sourced contract/bank authority remain open.

**SEARCH EFFORT / COST PROXIES:** 3 materially different discovery modes; about 8 targeted public search formulations; 3 serious candidates/comparators inspected; exact source/test/schema/history and repository metadata verified; roughly 45 connector/tool calls including shadow-memory reads and evidence freezing; 0 untrusted-repository code executions, provider writes, credentials, contacts, spend or commitments.

**LOCAL LESSON:** `SK-COM-003` transferred to a second distinct shadow run and is now eligible for separate Skill Promoter review, but remains **LOCAL**. Refine the external-outcome ladder: tier 5 should split into **5A = real-provider post-dispatch response suppression + later fresh-invocation readback + no second mutation** and **5B = literal process termination/restart across the boundary + durable-state recovery + provider readback + no second mutation**. This run reaches 5A, not 5B. Do not let “new adapter instance” silently become “process restart.”

**REFERRALS:** No new cross-lane referral. Existing provider/system-of-record readback referrals remain valid; this run partially answers them with a concrete Stripe test-mode pattern rather than creating a duplicate referral.

**NEXT TEST:** Find or build evidence for **tier 5B**: a lawful public test/certification that kills the process immediately after a real sandbox/provider mutation, restarts against the same durable state, performs read-only provider reconciliation and proves zero duplicate money effects. Separately, test whether the same pattern exists for refunds/credits after captured money rather than only cancellation of an uncaptured PaymentIntent.

## 2026-09-20 — Shadow run 7

**DATE:** 2026-09-20

**HYPOTHESIS:** A low-attention public repository exists with tier-5B evidence on captured money: a real provider/test-mode refund is accepted, the dedicated application worker is literally SIGKILLed after provider response but before local completion, a new process resumes from durable state, and provider-ground-truth readback/replay proves exactly one external refund object. Such evidence should materially exceed same-process/fresh-adapter ambiguity tests.

**DISCOVERY METHODS:**
1. Direct money-domain search for Stripe refunds, lost/unknown outcomes, process restart and idempotent reconciliation.
2. Code-level fault-boundary search for `SIGKILL`, post-send/post-response crash seams, refund metadata lookup, stable idempotency keys and provider-ground-truth rereads.
3. Analog/low-attention traversal through durable-workflow, fault-injection and exactly-once billing repositories, including repositories whose names do not advertise payments.

**BEST CANDIDATE + URL + EXACT REVISION:** `az-said/Interlock` — https://github.com/az-said/Interlock — `822ec54692b30e1fdce04b55dfab62d0b56a60b2`.

**IMPLEMENTED / SOURCE-VERIFIED:**
- `scenarios/stripe_dispute/worker.py` deliberately runs one refund step as its own OS process. `crash_point()` calls `os.kill(os.getpid(), signal.SIGKILL)`. In the `after` fault, `_send()` first returns from the Stripe refund request and then immediately SIGKILLs the worker, before the caller can record the result.
- The first worker persists the decision in `STATE_DIR`; a restarted worker never asks the model again. The no-check baseline replays the same Stripe idempotency key; the careful baseline first looks up provider refunds carrying the case metadata; Interlock uses a deterministic effect key, provider lookup and durable hash-chained receipt/recovery state.
- `experiments/scenario_stripe_dispute.py` launches the worker via a subprocess, requires the first process return code to equal `-signal.SIGKILL`, changes external Stripe state while that process is dead, then launches a genuinely new worker process and finally rereads Stripe's refund list as ground truth.
- `scenarios/stripe_dispute/dispute.py` is test-mode-only and rejects non-test Stripe credentials through the underlying client. It creates a real $100 Stripe test PaymentIntent, issues a $20 refund with a stable idempotency key and metadata, escalates a Stripe test inquiry into a chargeback, and judges all refund objects—including failed refunds—rather than trusting local application state.

**CHECKED-IN EXTERNAL EVIDENCE:**
- `results/scenarios/stripe_dispute.json` and `.md` are revision-bound run artifacts generated 2026-09-13. They state every crash is a real SIGKILL and Stripe test mode is used; the JSON records `first_worker_exit: -9` for the tested cells.
- In `crash_after_send_chargeback_during_outage`, all three systems converge to exactly **one** Stripe refund object after restart: no-check reports `REPLAYED_BY_STRIPE`, the hand-check baseline reports `FOUND_BY_LOOKUP`, and Interlock reports `COMMITTED_ON_QUERY`. The ground-truth reread finds no second refund object and no refund created at or after the chargeback.
- The important economic caveat is also recorded: that refund object later reached `failed (charge_for_pending_refund_disputed)`, so no money was ultimately returned in that cell. The result therefore proves external-object exactly-once recovery across a real process death, not successful refund settlement.
- A separate checked-in five-minute gap probe shows the opposite economic edge case: a $20 refund stayed `succeeded` and a later $100 chargeback still withdrew the full amount, leaving the merchant down $120 on a $100 payment in Stripe test mode. This is strong negative evidence that “exactly one refund object” is not sufficient to claim economic correctness.

**SOURCE / TEST / HISTORY / RIGHTS VERIFICATION:**
- Current `main` SHA independently verified as `822ec54692b30e1fdce04b55dfab62d0b56a60b2`.
- Repository metadata at inspection: public, 1 star / 0 forks, MIT license.
- Scenario history independently traces to commit `fe498692079dd251b88ac455e06c09dbc582f446` (2026-09-13), whose message explicitly says the suite runs live services with real SIGKILL and ground-truth readback and, importantly, says a fair handwritten check tied Interlock on outcomes while Interlock's consistent edge was tamper-evident receipts.
- Frozen evidence manifest `sha256:f0eb1f1f3bc6386e4002207eb69f2d3f83e4442e70f9d747e31c5398e4c09527` binds the exact revision to:
  - `results/scenarios/stripe_dispute.md` — Git blob `eb08f045feb06f0f765bcf1998227f39b9e2f4dd`
  - `results/scenarios/stripe_dispute.json` — `855ab74c9e2d0dd57afd6a2015315600e4cb51f6`
  - `scenarios/stripe_dispute/worker.py` — `4bd0fae8eb567bed59316cde01f0928687d56dd6`
  - `experiments/scenario_stripe_dispute.py` — `771b4d33d6eed642a494243a5a028dd2571f6a37`
  - `scenarios/stripe_dispute/dispute.py` — `47960cfce188a7e95ffca2bf767224d6542b4582`
  - `LICENSE` — `f84454625104c633d7b7500f03202f6b4143f516`
  - scenario-lineage commit `fe498692079dd251b88ac455e06c09dbc582f446`.
- No repository code, Stripe mutation, credentials, contacts, spend or external commitments were executed in this shadow run.

**COMPARATORS / FALSIFIERS:**
- `temporal-community/agent-memory-and-state@59fb4186bc50daefe09653a850197a985b3fa1cf` is a strong source-design comparator. Its documented real Stripe test-mode demo seeds a succeeded payment, creates an idempotent refund, opens a post-effect restart window, exposes a CLI that SIGKILLs the Worker, and on replacement Worker attempt 2 reuses the same run-derived Stripe idempotency key. Its code also supports Stripe refund-list readback. I did not find an equally strong checked-in machine-readable completed tier-5B run artifact at the inspected revision, so it does not displace Interlock on evidence quality.
- `getvelox/velox@3568ab3d540970dc0ad4f9dda3593ff924187acf` has excellent internal exactly-once billing failover tests: it SIGKILLs the billing leader at multiple commit positions, starts a successor and proves one invoice per subscription plus invariant-clean totals. Its payment provider in the failover proof is a sentinel, so it proves internal billing crash safety rather than external-provider refund ambiguity.
- `dzaramelcone/reaper@6cb28ddb47ccd6526c4edf363ddcd3cc3d89f731` has real-process campaign machinery and explicit `STRIPE_REQUEST`/`STRIPE_RECEIVE` fault boundaries, but its documented ordinary Stripe provider tier uses Stripe's maintained mock image rather than real Stripe test-mode truth. It therefore ranks below the selected candidate on the external-outcome ladder for this hypothesis.

**RED-TEAM OBJECTION:** Tier 5B is reached only for **provider-object convergence**, not settlement. The harness kills after Stripe's HTTP response has returned to the worker, not by dropping the network response before the client receives it; local state is still ambiguous because the worker dies before recording completion, but this is a narrower boundary than transport-level response loss. The checked-in run is self-authored and was not independently rerun here. Most importantly, the accepted refund later failed due the chargeback, while the gap probe shows a succeeded refund can coexist with a later full chargeback and create a $120 loss on $100 paid. It would be false to market this evidence as “prevents money loss” or “proves settled refunds.” The repository's own history also undercuts a moat claim by stating a careful handwritten baseline tied Interlock on outcomes; the differentiated value is reusable crash/evidence machinery and tamper-evident receipts, not unique refund correctness.

**INDEPENDENT VERIFIER VERDICT:** **PASS_WITH_LIMITS.** The narrow claim is supported at the frozen revision: source and checked-in results show a real Stripe test-mode refund request completing, the dedicated OS worker then terminating by SIGKILL before local completion is recorded, a new worker process resuming from persisted state, and provider-ground-truth reread/replay converging to exactly one Stripe refund object with no second external refund object. The verifier rejects stronger claims of transport-level lost-response proof, successful refund settlement, bank reconciliation, live-money production qualification, recovered dollars or independently rerun attestation. No sensitive-source material was used in the claim packet.

**A-F SCORE (proposed only, after verifier):** **27/30 — A4 / B4 / C5 / D5 / E5 / F4.**
- A4: a sandbox crash-certification engagement can be sold without touching live customer money.
- B4: preventing duplicate refunds/charges and proving ambiguous-effect recovery has direct value, but the current artifact does not establish settled-money economics.
- C5: compresses real process fault injection, stable provider identity, durable recovery, external truth reread and tamper-evident evidence design.
- D5: real Stripe test-mode refund + literal SIGKILL + new-process recovery + checked-in provider-ground-truth artifact is rare, especially in a one-star repository.
- E5: implementation, machine-readable run artifact, human-readable analysis, external provider reread and candid contradictory evidence are all present and revision-bound.
- F4: MIT and test-mode boundaries are clear; real customer settlement/live qualification remains unproven.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: fintech/payments engineering lead, billing-platform owner, Controller's systems team or reliability group operating refunds/credits.
- Pain: a process can die after a provider accepts a money mutation but before local state records success, creating duplicate-refund risk and expensive manual reconciliation.
- First paid wedge: **Payment Effect Crash Certification** for one existing Stripe test-mode refund/correction path. Run controlled pre- and post-effect real SIGKILLs, restart against the same durable state, reread provider truth, prove whether exactly one external effect exists, and deliver a revision-bound evidence bundle. Keep the first engagement sandbox-only; separately score final settlement/economic outcome rather than conflating it with object-level exactly-once.

**COMBINATION WITH PRIOR SHADOW RUNS:** This closes the exact tier-5B gap left by run 6. Auths remains stronger as a generic `OutcomeUnknown`/bounded-capacity state model; RAP remains stronger for multi-runtime production-edge smoke; PeanutGallery proves real-provider mutate-then-lose-response tier 5A; Interlock adds literal OS process death and new-process recovery on a captured-payment refund path with checked-in Stripe-ground-truth results. The combined architecture now has strong sandbox evidence for **durable intent → provider mutation → ambiguous local completion → process restart → provider truth → exactly-one provider object**. The next missing edge is economic settlement correctness, not another object-level idempotency proof.

**SEARCH EFFORT / COST PROXIES:** 3 materially different discovery modes; 3 serious candidates/comparators deep-inspected; about 9 targeted repository/web query formulations; source, result artifact, external-provider readback code, history, rights and repository metadata verified at exact revisions; approximately 45 connector/web calls including required shadow-memory reads and write-SHA refreshes; 0 untrusted-repository code executions, provider writes, contacts, spend or commitments.

**LOCAL LESSON:** `SK-COM-003` now has a third distinct shadow success but remains **LOCAL**. Tier 5B should require four facts simultaneously: **(1) a dedicated process boundary, (2) kill ordering after provider effect but before local durable completion, (3) a genuinely new process resuming from preserved state, and (4) provider-ground-truth reread with an exact effect count.** A bare `SIGKILL` test is insufficient. Add a separate axis for **economic terminality**: provider-object exactly-once, provider status finality and actual settlement/balance outcome are different claims.

**REFERRALS:** No new referral. Existing provider/system-of-record readback referral is now partially answered at tier 5B object-convergence level; a new duplicate referral would add noise.

**NEXT TEST:** Find a tier-5C artifact: literal post-effect process death on a **refund/credit that ultimately remains succeeded**, new-process recovery with no duplicate effect, and later processor/balance/settlement evidence showing the economic outcome—not merely the existence of one provider refund object. Prefer an independently rerunnable or independently attested artifact over another self-authored result record.

## 2026-09-20 — Shadow run 8

**DATE:** 2026-09-20

**HYPOTHESIS:** The next useful evidence tier is not another exactly-once provider object. A stronger money-control artifact will prove that, after a real post-effect process death and new-process recovery, the correction is later **consumed by the provider's own accounting/billing engine** exactly once and changes the resulting receivable. This should separate provider-object convergence from economic application, even if bank/payout settlement remains unproven.

**DISCOVERY METHODS:**
1. Direct search for real Stripe refund/credit crash-restart evidence combined with balance transactions, invoices, payouts and settlement state.
2. Code-signature/fault-seam search for `SIGKILL`, `balance_transaction`, post-send crashes, restart workers, provider idempotency and later billing/settlement reads.
3. Adjacency/history traversal from the prior tier-5B candidate into sibling scenarios and checked-in machine artifacts, specifically testing whether any scenario closes the provider-accounting application edge rather than merely reproducing one provider object.

**BEST EVIDENCE DELTA + URL + EXACT REVISION:** `az-said/Interlock` — `billing_credit` scenario — https://github.com/az-said/Interlock — `822ec54692b30e1fdce04b55dfab62d0b56a60b2`.

This is **not a new repository**; it is a materially stronger economic-outcome scenario inside the prior run's exact revision. It is recorded because the shadow protocol values falsification/capability refinement even when no new repository is promoted.

**IMPLEMENTED / SOURCE-VERIFIED:**
- `scenarios/billing_credit/billing.py` is explicitly Stripe **test-mode only**. A support approval authorizes one $10 goodwill credit, implemented as a Stripe customer-balance adjustment (`amount=-1000`) tagged with case/effect metadata. Stripe applies customer balance to the next finalized invoice.
- `post_credit()` performs the real provider POST and, for `crash="after_send"`, calls `SIGKILL` only **after** the Stripe response has been parsed. The local worker therefore dies after provider effect but before the caller records completion.
- `experiments/scenario_billing_credit.py` launches the decision worker as a subprocess, requires return code `-SIGKILL`, reads Stripe observations while the worker is dead, advances the customer's Stripe test clock through a real subscription renewal, launches a genuinely new `restart` worker process, then rereads Stripe ground truth.
- The Interlock path recovers through the durable journal and the same effect identity. The careful handwritten baseline first queries Stripe by case metadata. Both avoid a second economic credit; the no-check baseline relies on Stripe's stable idempotency key.
- The durable state contract is split across fsynced `decision.json` / case approval state, Interlock's hash-chained `journal.jsonl`, and Stripe's own customer-balance/invoice objects. There is no separate relational schema for this scenario; the relevant state transitions are explicit in source and published JSON artifacts.

**CHECKED-IN TIER-5C-A EVIDENCE:**
- `results/scenarios/billing_credit.md` records Stripe Billing test mode with test clocks and states that **every crash is a real SIGKILL of the worker process**. In both `after_send / renewal` and `after_send / proration`, all three systems finish with exactly one $10 case credit and the invariant held.
- The machine-readable `results/scenarios/billing_credit.json` is stronger. In the `after_send / renewal` path the first worker exits `-9`; the credit exists at crash time; after the outage/restart, Stripe ground truth contains exactly one case adjustment of `-1000` and one later `applied_to_invoice` balance transaction of `+1000`.
- That same ground truth shows the subscription-cycle invoice is `paid`, with `total=3000`, `starting_balance=-1000`, and `amount_due=2000`. In other words, the one crash-surviving $10 correction was consumed once by Stripe Billing and reduced the paid renewal receivable by exactly $10.
- For the Interlock cell, the recovery result is `COMMITTED_BY_RETRY` / `retry-idempotent`; Stripe returns the existing credit (`already_processed`), the published receipt verifies as valid/tamper-evident with `happened_once=true`, and the provider ground truth still contains one adjustment plus one invoice application—not two credits.
- The `after_send / proration` row independently shows the same one-credit invariant surviving process death while the later provider-native invoice path changes; the result is not dependent on one fixed invoice shape.

**TEST / HISTORY / RIGHTS VERIFICATION:**
- `tests/test_scenario_billing_credit.py` verifies incident-scoped compensation semantics, lookup-after-send, send-once/find-on-retry behavior, stale-premise/refused-approval cases, judge invariants and offline re-verification of every published Interlock receipt against `billing_credit.json`.
- Current `main` remains `822ec54692b30e1fdce04b55dfab62d0b56a60b2`.
- Scenario history traces to `fe498692079dd251b88ac455e06c09dbc582f446` (2026-09-13), whose commit message explicitly says the suite uses live services with real SIGKILL and ground-truth readback, including a Billing credit across a test-clock renewal. It also candidly states the fair handwritten check ties Interlock on outcomes and the consistent edge is tamper-evident receipts.
- MIT license verified at blob `f84454625104c633d7b7500f03202f6b4143f516`.
- Frozen evidence manifest: `sha256:9ecd448a9045672a38c76ff0a80fc86a64b4b186d6bdc2e849771ba7496f9eac`, binding the exact revision to:
  - `results/scenarios/billing_credit.md` — `88051af0a2326755dc273a2d2f489971f5c955ae`
  - `results/scenarios/billing_credit.json` — `b45daad2ac699e94cd3cea73ca6608abd912e476`
  - `scenarios/billing_credit/billing.py` — `db5fe079ce53a6e0676390ad6a75c9deeaabed08`
  - `scenarios/billing_credit/worker.py` — `12d463bf7f5dafbdb104eda2f38f3639336fdb14`
  - `tests/test_scenario_billing_credit.py` — `4e1572bdc9794c5b840e2ad9e2547e0859437a64`
  - `LICENSE` — `f84454625104c633d7b7500f03202f6b4143f516`
  - scenario-lineage commit `fe498692079dd251b88ac455e06c09dbc582f446`.
- No repository code, Stripe mutation, credentials, contacts, spend or commitments were executed in this shadow run.

**COMPARATORS / FALSIFIERS:**
- `stripe/stripe-commercetools-checkout-app@12b31a218eb87b622ef2dbc4b6ecde92b4b78097` is an important production-lifecycle comparator. Its current source/tests explicitly distinguish a refund being created from a refund later failing on delayed rails, route `refund.updated` / `refund.failed`, and avoid double-booking successful refunds. This reinforces the economic-terminality rule: provider-object creation and final money/accounting state must be scored separately. It does not, in the inspected evidence, provide the same literal post-effect SIGKILL/new-process experiment.
- `temporal-community/agent-memory-and-state@59fb4186bc50daefe09653a850197a985b3fa1cf` remains a strong source-design comparator: real Stripe test payment seeding, idempotent refund execution, a Worker SIGKILL command and provider refund-list readback are implemented. The inspected revision still lacks an equally strong checked-in completed machine-readable run artifact proving the full tier-5C accounting application path.

**RED-TEAM OBJECTION:** This closes **provider-accounting application**, not bank settlement. A Stripe customer-balance adjustment is an internal customer credit, not a refund returned to a card/bank and not a merchant payout. The test clock accelerates time; although Stripe's own test Billing engine creates/finalizes/charges the renewal, no external acquiring/banking settlement is proven. The crash seam still occurs after Stripe's HTTP response has reached the worker rather than at transport-level response loss. The checked-in run is self-authored and was not independently rerun here. Most importantly, the repository's own history says a careful handwritten baseline tied Interlock on every money outcome; therefore Interlock's moat cannot be claimed as unique money correctness. Its differentiated value is reusable recovery/evidence machinery and verifiable receipts. The published receipts are hash-chained but unsigned, so they establish internal tamper evidence rather than independent signer identity.

**INDEPENDENT VERIFIER VERDICT:** **PASS_WITH_LIMITS.** The frozen packet supports the narrow claim that this exact revision contains checked-in Stripe test-mode evidence for: real post-effect worker SIGKILL, genuinely new-process recovery, exactly one approved customer-balance credit, and later provider-native consumption of that credit by a paid renewal invoice whose amount due is reduced by exactly $10. The verifier rejects stronger claims of card/bank refund settlement, payout reconciliation, live-money production qualification, transport-level response loss, independent attestation or recovered-dollar ROI. The verifier also rejects any claim that Interlock uniquely achieves the money outcome because the handwritten baseline ties it in the published scenario.

**A-F SCORE (proposed only, after verifier):** **27/30 — A4 / B5 / C5 / D4 / E5 / F4.**
- A4: a sandbox billing-correction crash certification can be sold without touching live customer money.
- B5: duplicate credits and failed-to-apply corrections directly change receivables, customer balances and support/finance exposure.
- C5: compresses process fault injection, durable effect identity, authority/premise checking, provider readback, invoice-ground-truth validation and receipt construction.
- D4: the exact evidence bundle is rare, but the fair handwritten baseline proves the core money outcome is reproducible without the framework.
- E5: source, tests, machine-readable external-provider artifact, provider-native invoice application, history and contradictory evidence are all revision-bound.
- F4: MIT and test-mode boundaries are clear; live settlement and independent attestation remain outside scope.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: billing/payments engineering lead, Controller's systems team, subscription-platform owner or reliability team responsible for credits/refunds.
- Pain: a worker can die after a customer correction is accepted but before local completion is recorded. A duplicate credit loses revenue; a missing/unapplied credit creates customer and reconciliation failures; ordinary “refund object exists” checks do not prove the correction reached the next receivable.
- First paid wedge: **Billing Credit Crash Certification** for one Stripe test-mode correction flow. Inject pre/post-effect process deaths, restart from preserved state, prove exactly one approved correction exists, advance through the next provider-native billing event, and deliver evidence that the correction was consumed once against the resulting invoice/receivable. Keep the engagement test-mode first and explicitly separate provider-accounting application from cash/bank settlement.

**COMBINATION WITH PRIOR SHADOW RUNS:** Run 7 proved tier-5B provider-object convergence after literal process death. This sibling scenario advances the evidence ladder one economically meaningful step: **provider object → provider accounting application / receivable effect**. Combined with the earlier authority/leakage/correction components, the stack can now target **contract authority → discrepancy decision → approved correction → crash-safe external effect → provider-native receivable application → reconciliation evidence**. The remaining hard boundary is independently grounded **cash settlement/payout/bank truth**, not another provider-object test.

**SEARCH EFFORT / COST PROXIES:** 3 materially different discovery modes; 3 serious candidate/comparator paths inspected; targeted source/result/test/history/license verification at exact revisions; roughly two dozen connector/search/file inspections in this run; 0 untrusted-repository code executions, provider writes, credentials, contacts, spend or commitments.

**LOCAL LESSON:** Refine `SK-COM-003` with a two-part tier 5C. **Tier 5C-A = provider-accounting application:** after tier-5B recovery, the one external correction is later consumed by a provider-native accounting/billing event and changes the resulting obligation/receivable exactly once. **Tier 5C-B = external cash settlement:** processor balance/payout/bank evidence confirms the money movement beyond the provider's own accounting plane. This run reaches **5C-A**, not 5C-B. The separation prevents “paid invoice after a credit” from being overclaimed as bank-settled refund money.

**REFERRALS:** No new referral. The existing provider/system-of-record readback referral already contains the unresolved settlement question; another referral would duplicate it.

**NEXT TEST:** Find tier-5C-B evidence: a post-effect process death around a cash refund/payout/credit that remains economically successful, new-process recovery with no duplicate mutation, and later processor balance/payout/bank-settlement evidence that is independently grounded rather than only internally reconciled.

## 2026-09-20 — Shadow run 9

**DATE:** 2026-09-20

**HYPOTHESIS:** Tier-5C-B can only be claimed when two independent axes intersect in one executable path: **effect-boundary crash safety** (post-provider-effect process death, restart, no duplicate) and **economic terminality** (later provider balance/payout/settlement evidence). A strong candidate may close the terminality half even if it fails the crash half; that gap is itself commercially useful negative knowledge.

**DISCOVERY METHODS:**
1. Direct money-domain/code search for Stripe payouts/refunds combined with `SIGKILL`, restart, idempotency, balance transactions and `payout.paid`/terminal status.
2. Analog/gap traversal from the prior Interlock tier-5B/5C-A evidence into Connect payout and cash-settlement paths, explicitly testing whether provider-object crash safety extends to payout finality.
3. Low-attention implementation search for payout tables, exact provider IDs, connected-account balance readback and signed payout-event handling inside obscure repositories rather than payment-framework names.
4. Commit-history + GitHub Actions archaeology to pin the strongest **successful exact revision**, and to challenge later revisions rather than assuming HEAD improved the evidence.

**BEST CANDIDATE + URL + EXACT REVISION:** `karfalacisse900-alt/Flames-up.com` — https://github.com/karfalacisse900-alt/Flames-up.com — `2ba5fa878da26f405bfae1846c8c90f1d0e69c10` (`Stabilize Stripe payout acceptance`, 2026-09-09).

**IMPLEMENTED / SOURCE-VERIFIED:**
- `backend-cf/scripts/stripe-sandbox-runtime.mjs` drives a real isolated Captro Worker, local Supabase Auth/Postgres and real Stripe **test-mode** APIs. It creates a paid event, creates and confirms a real PaymentIntent, waits for the signed `payment_intent.succeeded` webhook, records the creator earning, then reads the connected Stripe balance until at least $20 is instant-available.
- It requests an actual creator payout for $20, accepts only `pending|in_transit|paid` initially, then waits until the application payout history reports that same $20 payout as `paid` and requires a processed signed `payout.paid` webhook audit record.
- `backend-cf/scripts/verify-stripe-native.mjs` is a separate read-only acceptance verifier. It refuses live mode and production infrastructure, retrieves the real Stripe PaymentIntent, event, connected account and balance, asserts application `available`/`pending` balances equal Stripe's `/balance`, polls the exact Stripe payout until terminal and **requires `payout.status == 'paid'`**, requires `method == 'instant'`, requires the destination be an eligible debit card, then binds the same payout ID/amount/destination to `app_payout_requests`, `app_payouts`, the real Stripe `payout.paid` event, the processed webhook audit row and the application's payout history.
- The payout schema is not an in-memory demo. `app_payout_requests` stores creator/account/external-card identity, request key, amount/fee/net/currency/status and a unique `provider_payout_id`, with `unique (creator_id, request_key)`; payout/readback rows are separated from reconciliation issues. The environment itself is explicitly pinned to one Stripe mode.
- Static source-contract tests in `stripe_connect_marketplace.test.mjs` assert payout/connect webhook handling, real balance and payout-list endpoints, payout readiness, refund/dispute reversal paths and one immutable earning/entitlement path.

**REVISION-BOUND TEST / HISTORY EVIDENCE:**
- For exact SHA `2ba5fa878da26f405bfae1846c8c90f1d0e69c10`, GitHub Actions records `Stripe Sandbox Integration` run `34357947547` as **completed / success** on 2026-09-09. `Validate Native Payments` also completed successfully on the same SHA.
- The commit itself changes the sandbox runtime to wait for payment-webhook audit evidence and is titled `Stabilize Stripe payout acceptance`, which is consistent with the successful protected acceptance run rather than an unrelated code snapshot.
- History shows payout work evolved through multiple commits rather than appearing once: native Stripe/debit payout requests, payout acceptance stabilization, payout-flow fixes, reconciliation repair and later debit-token proof work.
- A crucial contrary data point: the later `ea4b3c5eb803534fe1b57cf579dc9928404ba308` (`test: prove native debit token payout path`) had its exact `Stripe Sandbox Integration` workflow **fail** on 2026-09-12. Therefore the evidence is deliberately pinned to `2ba5...`, not silently upgraded to a newer but failing revision.
- Repository metadata at inspection is low-attention (0 stars / 0 forks) and GitHub reports no public license metadata. Per the standing hunt rule this does not erase technical value, but public provenance must remain recorded as `no detected public license`; the user's separate authorization assumption applies only to repository-owned code.

**CRITICAL FALSIFICATION / TIER RESULT:**
- This revision strongly closes the **economic terminality / provider-finality half** of the target: real Stripe test-mode purchase → connected-account balance parity → instant payout → provider `status=paid` → real `payout.paid` event → matching application payout/ledger evidence.
- It does **not** close tier-5C-B as currently defined because the payout mutation is not wrapped in a post-effect fault seam. The `SIGKILL` in `stripe-sandbox-runtime.mjs` appears only in final process cleanup after `main()` completes; it is not a crash injected after Stripe accepts the payout and before local completion.
- No inspected exact-revision path proves: payout accepted → process killed before local completion → genuinely new process recovery → no duplicate payout → same payout later `paid` with balance/settlement evidence.
- `payout.paid` in Stripe test mode is meaningful provider-grounded terminality but still not an external bank statement or live-network settlement. It must not be described as independent bank settlement.

**SPECIALIST PASSES:**
- **CODE INSPECTOR:** froze `2ba5...`; verified the sandbox runtime, read-only verifier, payout schema and source-contract tests. Conclusion: provider and application state are cross-read rather than inferred from one local table.
- **FAILURE/RELIABILITY ANALYST:** traced every process-kill occurrence. Conclusion: the only SIGKILL in the inspected payout runtime is teardown, so no effect-boundary crash claim is allowed.
- **ECOSYSTEM/HISTORY ANALYST:** compared exact workflow runs and payout-history commits. Conclusion: `2ba5...` has successful revision-bound Stripe sandbox evidence, while a later stricter debit-token commit has a failing sandbox workflow; exact-revision selection materially changes confidence.
- **COMMERCIAL ANALYST:** the reusable wedge is not another payout UI; it is an evidence pack that proves provider balance, payout terminality and local ledger parity, then can be combined with a crash injector to certify the missing boundary.

**INDEPENDENT RED-TEAM / VERIFIER VERDICT:** **PASS_WITH_LIMITS.** The frozen evidence supports the narrow claim that exact revision `2ba5...` executed a successful real Stripe **test-mode** path from purchase and connected balance to a $20 instant payout that reached Stripe `paid`, emitted a real `payout.paid` event and reconciled to application payout/ledger state. The verifier rejects the stronger tier-5C-B claim because there is no post-effect payout crash/restart/no-duplicate proof in this path. It also rejects “bank-settled,” “live-money production proof,” and any inference that newer HEAD is stronger merely because it is newer; the later debit-token sandbox run failed.

**A-F SCORE (proposed only, after verifier):** **25/30 — A4 / B5 / C4 / D4 / E5 / F3.**
- A4: a payout-finality qualification engagement can be delivered in provider test mode without touching live customer money.
- B5: payout duplication, stuck creator balances and false paid-state reconciliation are direct-money risks.
- C4: compresses connected-account readiness, balance readback, instant-payout execution, signed event processing and ledger/provider acceptance checks, but lacks crash-recovery machinery.
- D4: real payout terminality plus cross-system balance/event/ledger binding is uncommon in a 0-star repository, though not conceptually unique.
- E5: exact successful workflow, real-provider test-mode calls, separate read-only verifier, schema/tests and contradictory later-CI evidence make the narrow claim unusually well supported.
- F3: no detected public license, protected provider test credentials/environment are required, and cash/bank settlement plus crash-safe payout recovery remain outside scope.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: marketplace/payments engineering lead, creator-platform finance owner, Controller's systems team or payout reliability group.
- Pain: teams can mark a withdrawal `paid` locally without proving the same provider payout, provider balance transition and signed terminal event agree; adding crashes makes this harder and can create duplicate payouts.
- First paid wedge: **Payout Settlement Qualification Pack** for one Stripe test-mode marketplace flow. Prove purchase/earning → provider balance parity → exact payout ID → terminal `payout.paid` → matching internal payout/ledger state, and emit a revision-bound evidence report. Then, as a separate higher tier, add controlled effect-boundary crash/restart testing before claiming crash-safe payout settlement.

**COMBINATION WITH PRIOR SHADOW RUNS:** Run 7/8 Interlock supplies the missing fault-boundary discipline: literal post-effect SIGKILL, new-process recovery and exact provider-effect counting, plus provider-native accounting application. This run supplies a complementary terminal-payout evidence pattern: connected balance parity, instant payout, provider `paid`, signed `payout.paid`, and local ledger/API match. Together they specify a concrete composite qualification harness, but **the two halves cannot be merged into a stronger factual claim until one executable path demonstrates both**.

**SEARCH EFFORT / COST PROXIES:** 4 materially different discovery modes; two new low-attention payout paths plus the prior Interlock comparator triaged; exact source/test/schema/history and Actions evidence inspected; several dozen GitHub searches/reads; 0 untrusted-repository code executions, provider writes, credentials, contacts, spend or commitments.

**LOCAL LESSON:** Refine `SK-COM-003` into a **two-axis evidence matrix** rather than a single linear ladder. Axis A is **fault-boundary proof** (`none → response suppression → process death/restart → no duplicate`). Axis B is **economic terminality** (`provider object → provider final status → provider accounting application → payout/balance/bank evidence`). A candidate strong on Axis B must not inherit Axis A, and vice versa. Exact-revision CI archaeology is now a required sub-step when provider qualification claims depend on historical workflow runs; a later commit can regress the evidence.

**REFERRALS:** No new referral. The existing provider/system-of-record readback referral already captures the intersection problem; duplicating it would add noise.

**NEXT TEST:** Find the **intersection in one executable path**: a cash refund or payout with post-effect process death, new-process recovery and exact no-duplicate proof, followed by the same provider effect reaching terminal success with balance/payout/bank readback. Search for repositories where `payout.paid`/refund terminality, stable idempotency and an effect-boundary kill seam appear in the same integration harness rather than in separate projects.

## 2026-09-20 — Shadow run 10

**DATE:** 2026-09-20

**HYPOTHESIS:** A single public payment stack may already combine application-side crash/ambiguity safety with provider-defined refund/payout terminality in one executable path. If it does not, a multi-provider refund layer that explicitly reserves refundable capacity under unknown outcomes should still expose the missing durability/provider-evidence boundary and sharpen tier-5C-B qualification.

**DISCOVERY METHODS:**
1. Direct search for Stripe/provider refunds or payouts combined with `SIGKILL`, restart, idempotency, terminal events and balance/settlement readback.
2. Code/invariant search for atomic refund claims, explicit refund idempotency, unknown/pending status, provider fetch/reconcile and over-refund prevention.
3. Provider-contract analog search through SDKs exposing refund/payout executed/failed and funds-received/reversal events.
4. Adjacency comparison against the prior Temporal/Stripe Worker-kill path to separate source-implemented crash safety from checked-in economic terminality.

**BEST NEW COMPONENT + URL + EXACT REVISION:** `ken-de-nigerian/payzephyr` — https://github.com/ken-de-nigerian/payzephyr — `2583da04970be2017f1806adf72ef0c8b3454989`.

**IMPLEMENTED / SOURCE-VERIFIED:**
- `src/Refund.php` uses an atomic shared-cache `Cache::add` in-flight claim per original transaction before provider refund entry. It supports an explicit caller-supplied idempotency key rather than deriving identity only from amount, which matters because multiple legitimate partial refunds can have equal amounts.
- The lock is deliberately held when a `RefundException` reports an ambiguous provider outcome. PayZephyr refuses provider fallback and tells the caller to reconcile first rather than risking a second refund. Definite failures release the lock; success releases it after the provider returns.
- `Refund::fetch()` delegates to the provider's read surface. `docs/idempotency.md` separately distinguishes business reference, provider idempotency key and provider transaction/refund identity and recommends provider readback for ambiguous transmitted/no-response cases.
- Refund accounting is conservative: pending, processing and unknown/unrecognized provider statuses count against refundable capacity until authoritative resolution, preventing a second partial refund from spending the same remaining balance merely because status normalization is incomplete.
- The refund transaction schema preserves unique refund reference, original transaction reference, provider, status, decimal amount, currency, reason, metadata and timestamps.

**TEST / SCHEMA / HISTORY / CI VERIFICATION:**
- `tests/Unit/RefundAdversarialSafetyTest.php` exercises aggregate refund conservation across retries/concurrency/partials, counts pending/processing and unknown/unrecognized statuses against refundable balance, excludes failed refunds and protects terminal state from late webhook changes. The suite candidly includes a local-persistence-loss case showing that the DB validator alone cannot know a provider-side refund happened if the refund row was never recorded.
- Exact HEAD GitHub Actions run `32368037426` completed successfully on 2026-08-20. The workflow runs static analysis, a PHP/Laravel Pest matrix, coverage enforcement and dependency audit; it is not a credentialed real-provider qualification run.
- History is staged: `537462778bf7d1eafcff1c08d85fe516d0b5d359` added refunds across eight providers, logging/validation/webhook handling; `4abc20f1dd97e766ac6e69ca4e0fb3425d3197e5` then hardened payment safety so ambiguous charge/refund outcomes no longer fall through to alternate providers and concurrent refund claims remain held on ambiguity.
- Repository metadata at inspection: public, 73 stars / 8 forks, MIT license. This is not a low-attention/zero-star find; its value is the unusually candid safety contract and tests rather than obscurity.

**FROZEN EVIDENCE MANIFEST:** `sha256:ed7d37009015c0b32bdbb2aa0cc380ce146504bbbf6ff0953ddfd565352f553a`, binding exact revision to:
- `src/Refund.php` — Git blob `2f2995ddeb622d203ad25b1014e45a1e25c8444f`
- `docs/idempotency.md` — `7bed5947de4ef6cd4ee9a489f3c437f791364b97`
- `tests/Unit/RefundAdversarialSafetyTest.php` — `f533147ca149244375307361ba4dac08aff00cfa`
- `database/migrations/2024_01_02_000000_create_refund_transactions_table.php` — `f02a6fdbcea342420c2d039b6bd94f4f4846dbe6`
- `.github/workflows/tests.yml` — `a27f05cf988719fd2297327a46511c4e0730d6f8`
- `LICENSE` — `73374178d5521aa5d4dbc34e00b7d8e01db369d2`
- exact-HEAD Actions run `32368037426`
- refund-lineage commits `537462778bf7d1eafcff1c08d85fe516d0b5d359` and `4abc20f1dd97e766ac6e69ca4e0fb3425d3197e5`.
No repository code, provider mutation, credentials, contacts, spend or commitments were executed.

**CRITICAL FALSIFICATION:** This does **not** close tier-5C-B. The in-flight claim has a hard 60-second TTL. The project's own idempotency document explicitly says that if the process dies after the provider confirms but before local persistence, no local transaction trace may exist; after lock expiry, reconciliation is required. It also says PayZephyr cannot verify that a provider actually honors its idempotency contract and instructs users to consult provider docs and sandbox-test each rail. Therefore the strong claim is application-side conservation/ambiguity handling, not durable exactly-once external recovery. A transient lock must not be upgraded into a durable `OutcomeUnknown` record.

**COMPARATORS / FALSIFIERS:**
- `temporal-community/agent-memory-and-state@59fb4186bc50daefe09653a850197a985b3fa1cf` remains stronger on Axis A source design: its real Stripe test-mode demo deliberately opens the post-effect window, SIGKILLs the Worker and has replacement Worker attempt 2 reuse the same run-derived Stripe idempotency key. It still lacks an equally strong checked-in completed tier-5C-B artifact binding that recovered refund to downstream terminal settlement.
- `TrueLayer/truelayer-php@016c885a15b581435c0390c1785beb03f6eb3010` is the opposite comparator: provider lifecycle types distinguish `refund_executed`/`refund_failed`, `payout_executed`/`payout_failed`, `payment_funds_received`, `payment_reversed` and `payment_disputed`. Its own `payment_funds_received` semantics acknowledge that received funds can still later be reversed. No inspected path couples those terminality events to a post-effect process-kill/restart experiment.

**SPECIALIST PASSES:**
- **CODE INSPECTOR:** verified refund dispatch, lock acquisition/release ordering, explicit idempotency input and provider fetch surface.
- **TEST/SCHEMA INSPECTOR:** verified adversarial refund-conservation tests, unknown/pending capacity behavior, refund schema and exact-revision green CI.
- **ECOSYSTEM/PROVIDER ANALYST:** compared application guarantees with provider lifecycle semantics and confirmed PayZephyr's own docs refuse to claim provider-side idempotency certainty.
- **COMMERCIAL ANALYST:** evaluated a multi-provider ambiguity audit as the smallest paid wedge that does not require moving live money.
- **RED-TEAM/VERIFIER:** challenged durability, provider truth and terminality independently before scoring.

**INDEPENDENT RED-TEAM / VERIFIER VERDICT:** **PASS_WITH_LIMITS.** The frozen packet supports the narrow claim that this exact revision implements and tests a conservative multi-provider refund-safety layer: one atomic in-flight claim, caller-controlled stable provider idempotency, no failover on ambiguous provider outcome, provider fetch/reconcile support, and refundable-capacity accounting that treats unknown/pending states as economically reserved. The verifier rejects `exactly once`, post-TTL crash recovery, verified provider idempotency, real-provider qualification, terminal refund/payout settlement and tier-5C-B. No sensitive-source material was used.

**A-F SCORE (proposed only, after verifier):** **24/30 — A4 / B4 / C4 / D3 / E5 / F4.**
- A4: a refund-safety audit/retrofit can be piloted quickly in staging or read-only review without live money mutation.
- B4: duplicate and over-refund prevention is a direct-money control with meaningful downside avoidance.
- C4: compresses multi-provider validation, atomic claims, ambiguity handling, status normalization and refund-capacity logic, but durable post-crash reconciliation remains missing.
- D3: the implementation is solid but the core patterns are not uniquely rare and the repository already has visible adoption.
- E5: source, adversarial tests, schema, candid docs, history and exact-revision green CI strongly support the narrow claim.
- F4: MIT and public provenance are clean; provider-specific idempotency/readback contracts still require external qualification.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: payments-platform lead, marketplace finance engineering team, Controller systems owner or SaaS billing team operating multiple payment providers.
- Pain: a refund timeout or process failure can leave teams unsure whether capacity is still available; naïve provider failover or a second partial refund can duplicate money while local state looks incomplete.
- First paid wedge: **Multi-Provider Refund Ambiguity Audit**. In staging/read-only analysis, map each provider's refund idempotency/readback behavior, enforce one shared atomic claim, treat unknown statuses as consuming refundable capacity, and return a provider-by-provider matrix of safe retry, reconcile-first and unsupported cases. Measure duplicate/over-refund exposure, ambiguous-case resolution time and manual reconciliation hours; do not execute live refunds in the initial engagement.

**COMBINATION WITH PRIOR SHADOW RUNS:** PayZephyr adds a pragmatic multi-provider application-side conservation layer, but it does not replace the durable recovery evidence from Auths/Interlock or the provider-terminal payout evidence from Flames-up.com. The strongest composed qualification target is **durable action identity/UNKNOWN beyond lock expiry → literal post-effect process death → provider readback/no duplicate → same action terminal provider event → balance/payout settlement evidence**. Facts from separate repositories remain separate until one executable path proves the intersection.

**SEARCH EFFORT / COST PROXIES:** four materially different discovery modes; three serious candidate/comparator paths deep-inspected; source/tests/schema/history/CI/provider-semantics checked at exact revisions; no untrusted code execution, provider writes, credentials, contacts, spend or commitments.

**LOCAL LESSON:** Add a **durability-horizon check** to the two-axis evidence matrix. A 60-second cache lock can prevent concurrent over-refund but cannot stand in for durable ambiguity evidence after a crash. If the provider can commit while the local write is lost, the unknown state must survive independently of lock expiry until authoritative provider readback. Separately, treating unknown/unrecognized refund status as consuming refundable capacity is a valuable direct-money invariant and should be searched explicitly.

**REFERRALS:** No new referral. Existing provider/system-of-record and external-outcome referrals already cover the unresolved intersection; duplicating them would add noise.

**NEXT TEST:** Find one refund/payout implementation where the ambiguous action state survives beyond any transient lock TTL, a literal post-effect process death/restart occurs, authoritative provider readback proves exact no-duplicate, and the **same action identity** later reaches provider terminal success plus balance/payout/bank evidence. Prioritize ecosystems exposing explicit `refund_executed`/`payout_executed` events and pair those terms with fault-injection/process-restart search signatures.

## 2026-09-20 — Shadow run 11

**DATE:** 2026-09-20

**HYPOTHESIS:** A reusable money-safety substrate can be commercially valuable even without tier-5C-B if it makes the narrow crash window between external effect and durable inverse identity explicit: persist intent before dispatch, recover only from authoritative action identity, and fail closed when a result-derived compensation descriptor never became durable. A framework that exposes this gap should outperform ordinary “WAL + retry” code that silently assumes intent logging makes external side effects recoverable.

**DISCOVERY METHODS:**
1. Direct search for Stripe refunds/payouts combined with `SIGKILL`, restart and reconciliation.
2. Code/invariant search for WAL ordering, intent/commit records, leases, deterministic recovery tokens, result-derived compensation and provider idempotency.
3. External issue/patch search for ambiguous Stripe refund retries and duplicate financial effects.
4. Low-attention proof-gate comparison against provider/settlement runbooks that require reconciliation evidence but lack a post-effect crash seam.

**BEST NEW COMPONENT + URL + EXACT REVISION:** `thomasjgeorge23/agent-saga` — https://github.com/thomasjgeorge23/agent-saga — `4310ff570e60c42c081ae216e87a1ccb093525d4`.

**IMPLEMENTED / SOURCE-VERIFIED:**
- `SagaContext.execute()` appends `STEP_INTENT` before the effect and forces a WAL barrier for COMPENSABLE/IRREVERSIBLE actions.
- On success, it derives the compensation from the actual provider result, appends `STEP_COMMITTED` with the compensation descriptor, then forces another durability barrier. The source explicitly explains why this second barrier matters for money paths.
- On timeout/exception, the forward effect becomes `UNKNOWN` rather than being assumed absent; the UNKNOWN record is durably logged and recovery fails closed when a safe inverse cannot be derived.
- `saga-recoveryd` uses expired leases rather than PIDs to identify abandoned work and uses deterministic recovery tokens. Recovery tests cover daemon restart, concurrent recovery actors, fail-closed irreversible work and missing compensator registration.
- The Stripe charge connector uses a deterministic forward idempotency key; refund compensation uses stable `agent-saga-refund-{charge_id}` identity and treats provider “already refunded” responses as success.
- If charge outcome is UNKNOWN and no returned charge ID exists, the Stripe connector explicitly refuses to invent an automatic refund and tells the operator to reconcile against the known forward idempotency key.

**TEST / HISTORY / CI VERIFICATION:**
- `tests/test_recovery.py` exercises real-process orphan detection/recovery, lease expiry, deterministic tokens, daemon-restart idempotency, one-winner recovery and escalation cases.
- `tests/test_durable.py` exercises durable restoration around a genuinely crashed subprocess.
- `tests/test_connectors.py` verifies Stripe idempotency, gate behavior, secret handling and UNKNOWN behavior but explicitly states **no network, no real credentials, no live database**; Stripe money evidence is therefore mock/synthetic.
- Connector history is staged: `b17a79673d8504907d4ce2486e8ec46bf91e4e84` introduced Stripe/PostgreSQL/Salesforce reference connectors; `0d55c8a884b8c568c70bd9818e4039b6cbb521b0` fixed a pre-flight policy bypass caused by closure-hidden amounts and added regression coverage.
- Exact revision CI is **not green**: GitHub check run `88683078599` failed at `python -m pytest -q`; benchmark/report jobs were skipped. No blanket CI-pass claim is allowed.
- Repository metadata at inspection: public, 2 stars / 0 forks, Apache-2.0.

**FROZEN EVIDENCE MANIFEST:** `sha256:b144b6d52406de1d080f8b5fb9c83b3794cd6e3e371baa310f9553d30bacb2d6`, binding exact revision to:
- `agent_saga/context.py` — `9ddbc666fc78910aee238a641471b91e7e4af644`
- `agent_saga/recovery.py` — `4935b30ebb1707963ac47f4512ac55e84c9a372e`
- `agent_saga/connectors/stripe.py` — `a3d46a37c977ca7df813d5526b3be12c8415adec`
- `tests/test_recovery.py` — `c55f309eca664e584a72359b21a1f2a5621bf1a8`
- `tests/test_connectors.py` — `319dd7a7caec249b426fcff0dd191afd8f0be64b`
- `tests/test_durable.py` — `67099867980ac061b56840b59fc3dc5699b24b75`
- `LICENSE` — `d645695673349e3947e8e5ae42332d0ac3164cd7`
- exact-revision check run `88683078599`.
No untrusted repository code, provider mutation, credentials, contacts, spend or commitments were executed.

**CRITICAL FALSIFICATION — COMPENSATION-DESCRIPTOR BIRTH GAP:**
- This does **not** close tier-5B or tier-5C-B.
- The framework's own ordering exposes why: a compensation descriptor is derived only after the external call returns. A SIGKILL after provider effect but before `STEP_COMMITTED` can leave durable `STEP_INTENT` but no returned provider ID/inverse descriptor. The recovery daemon then has evidence that something may have happened but no safe automatic inverse; the framework correctly escalates instead of pretending the side effect is recoverable.
- Therefore “intent durably written before effect” is necessary but insufficient for external exactly-once recovery when inverse identity is result-derived. A stronger design must persist a pre-dispatch business/action identity that can rediscover provider truth after crash.
- The Stripe connector is mock-tested rather than externally qualified, and the exact revision's pytest check failed.

**EXTERNAL COMMERCIAL SIGNAL:** `Wei-Shaw/sub2api` issue #5187 reports a Stripe refund path without explicit idempotency where an ambiguous provider response followed by operator retry could create a second real partial refund. PR #5193 was merged the next day to add deterministic refund idempotency and tests. This corroborates the pain pattern, but remains an author-reported bug/fix rather than an independently reproduced incident. Also, amount-derived idempotency is not sufficient as a universal business action identity because two legitimate same-amount partial refunds can be distinct actions.

**COMPARATOR:** `chase-sets/chase-sets@9899efdd2d0f9a2303862444fc9348234e776a39` has strong production proof discipline: provider-neutral payment/payout ports, signed/idempotent webhooks, settlement-ledger source-of-truth rules, `payout.paid`/`payout.failed`, balance/reconciliation requirements and explicit launch-evidence gates. No inspected path supplied the missing post-effect process-death/recovery proof, so it is a valuable operating-control comparator rather than a tier upgrade.

**SPECIALIST PASSES:**
- **CODE INSPECTOR:** verified intent-before-effect ordering, result-derived inverse registration and Stripe idempotency semantics.
- **FAILURE/RELIABILITY ANALYST:** isolated the crash window between external effect and durable result-derived compensation identity.
- **TEST/CI/HISTORY ANALYST:** verified real-process recovery tests, mock-only Stripe tests, connector lineage and exact-revision failing pytest check.
- **COMMERCIAL ANALYST:** mapped the substrate to a sellable money-action crash-safety review rather than claiming a new payments product.
- **RED-TEAM/VERIFIER:** challenged exactly-once, external provider truth, CI quality and automatic post-effect recovery before scoring.

**INDEPENDENT RED-TEAM / VERIFIER VERDICT:** **PASS_WITH_LIMITS.** The frozen evidence supports the narrow claim that this exact revision implements write-ahead intent, real-process orphan detection/recovery mechanics, deterministic recovery tokens, fail-closed ambiguous states and Stripe-specific deterministic compensation/idempotency logic. The verifier rejects real-Stripe crash recovery, provider-ground-truth no-duplicate proof, tier-5B/5C-B, exactly-once semantics and any blanket green-CI claim. In particular, a post-effect crash before result-derived compensation becomes durable is intentionally an orphan/escalation case, not a proven automatic recovery path.

**A-F SCORE (proposed only, after verifier):** **24/30 — A4 / B4 / C5 / D4 / E3 / F4.**
- A4: a crash-safety audit/retrofit can be sold quickly in staging/code review without touching live money.
- B4: duplicate refunds/charges and unreconciled unknown outcomes are direct-money risks, with a concrete external bug/fix signal.
- C5: compresses WAL ordering, leases, orphan recovery, deterministic recovery tokens, dynamic compensators, secret handling and preflight policy design.
- D4: runtime-derived compensators plus an independent recovery daemon are less common than ordinary saga/retry libraries, though the broader patterns are not unique.
- E3: source/tests/history are strong, but the real-process money path is synthetic, Stripe tests are no-network mocks and exact-revision pytest CI failed.
- F4: Apache-2.0 and operational boundaries are clear; provider reconciliation and distributed recovery-ledger deployment remain integration obligations.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: payments engineering lead, Controller's systems owner, fintech reliability team or AI/support automation owner whose agents can trigger charges/refunds/credits.
- Pain: teams can log an intended money action and still be unable to determine or reverse what happened if the process dies after provider effect but before the provider result ID/inverse is durably recorded.
- First paid wedge: **Money-Action Crash-Safety Review**. For one existing test-mode refund/charge workflow, map each crash boundary, verify which identities are durable before dispatch, inject safe process failures, classify recoverable versus orphaned windows, and deliver an exact unsafe-window/reconciliation plan. Do not execute live money in the first engagement.

**COMBINATION WITH PRIOR SHADOW RUNS:** Agent-Saga contributes a reusable dynamic compensation/recovery substrate and, more importantly, makes the inverse-identity crash gap explicit. Auths remains stronger for durable `OutcomeUnknown` money-capacity reservation; Interlock remains stronger for real Stripe post-effect SIGKILL → new-process → provider-ground-truth no-duplicate evidence; Flames-up remains stronger on payout terminality. Those facts must remain separate until one executable path proves their intersection.

**SEARCH EFFORT / COST PROXIES:** Four materially different discovery modes; three serious paths/comparators inspected; exact source/tests/history/CI and public rights checked; no untrusted code execution, provider writes, credentials, contacts, spend or commitments.

**LOCAL LESSON:** Extend `SK-COM-003` with a **compensation-descriptor birth-gap check**. For every money mutation ask: (1) what stable business/action identity is durable before dispatch; (2) whether provider effect can be rediscovered from that identity after process death; (3) whether the inverse/compensation depends on a result ID born only after the response; and (4) whether the recovery path fails closed or blindly retries when that result never became durable. “WAL before effect” without post-crash provider discoverability is not enough.

**REFERRALS:** No new referral. Existing external-provider/system-of-record referrals already cover the unresolved provider-truth edge.

**NEXT TEST:** Find one refund/payout path where a **pre-dispatch durable business action identity is sufficient to rediscover the exact provider effect after immediate post-effect process death**, a genuinely new process proves no duplicate mutation, and that same effect later reaches terminal payout/balance/bank evidence.

## 2026-09-20 — Shadow run 12

**DATE:** 2026-09-20

**HYPOTHESIS:** The run-11 compensation-descriptor gap can be closed without a provider-side search endpoint if the client durably persists the exact semantic request plus a stable provider idempotency identity **before dispatch**, and the provider’s replay contract can return the original outcome. The strongest public evidence should also independently prove the resulting external effect count; however, replay-window expiry and literal process death must remain separate proof obligations.

**DISCOVERY METHODS:**
1. Direct domain search for post-effect failure, restart, idempotency replay, refund/payout recovery and terminal provider evidence.
2. Code-signature search for `SIGKILL`, response-loss-after-commit, fsync-before-send, stable idempotency keys, retrieve/reconcile and exact external-effect counting.
3. Deliberate low-attention search through one-star/zero-star reliability repositories whose names do not advertise billing, then exact source/evidence/history inspection.
4. Comparator traversal against real-process internal-wallet crash recovery and mock-rail SIGKILL harnesses to separate external rediscovery proof from process-kill proof.

**BEST NEW COMPONENT + URL + EXACT REVISION:** `winsznx/keeperhub-flightcheck` — https://github.com/winsznx/keeperhub-flightcheck — `1d0142d2e401872ffe020b2a4110d85be31e0750`.

**IMPLEMENTED / SOURCE-VERIFIED:**
- `agent/src/runstore.ts` persists and `fsync`s the run record **before the outbound execution request**. The record binds run ID, unique challenge, chain/canary, intended operation, canonical request body, body hash and deterministic idempotency key.
- The idempotency key is derived from the semantic work identity rather than held only in memory. The canonical body bytes are persisted so recovery can replay a value-identical request even when the original response never yielded an execution ID.
- Recovery is explicitly bounded by the provider’s replay horizon. `assertResumable()` refuses automatic replay after the configured 24-hour idempotency window because the provider may have forgotten the prior response and a second execution could then occur. Durable local state therefore does not silently outlive provider-side dedupe semantics.
- `runFlightcheck()` loads the persisted record on resume, skips preflight simulation, reuses the exact body/key, and treats an idempotent replay as recovery of the prior result rather than creation of a new action.

**REVISION-BOUND EXTERNAL EVIDENCE:**
- `agent/tests/fault-injection.ts` states and implements a non-mock fault: it sends the real KeeperHub contract-call request, waits for the real HTTP response after server-side work completed, drains/discards it, then throws. It deliberately loses the immediate replay response too, causing the first invocation to end with no execution ID or transaction hash in local state.
- A second independent invocation resumes the same run from the persisted record. The checked-in `evidence/recovery/fault-injection.json` records two broadcast requests, `idempotentReplay: true`, a recovered execution/transaction identity and exactly **one** matching Base Sepolia canary event for the run’s unique challenge.
- The same artifact independently verifies the public-chain receipt as success and binds the emitted event, challenge, chain ID and sender back to the run; its agreement section records KeeperHub completion, public transaction landing and independent event match as all true.
- Commit `18e4adb4284a3eb11c64b84e7ee66f7281f7c10a` explicitly says the live fault-injection was rerun before recording and passed with “two broadcast attempts, one successful execution carrying the challenge.” Current exact HEAD is `1d0142d2e401872ffe020b2a4110d85be31e0750`.
- Repository metadata at inspection: public, 1 star / 0 forks, MIT license. No exact-HEAD workflow runs were returned by the GitHub Actions query, so no green-CI claim is made.

**FROZEN EVIDENCE MANIFEST:** `sha256:f6e9ba2d07cb91819e82b2d8adc2021b658dc3f7b62b2b678d318cb4512eb6eb`, binding the exact revision to:
- `agent/src/runstore.ts` — Git blob `4fbe06b132b54aeef1cc6bac9e549d94440587a7`
- `agent/tests/fault-injection.ts` — `7a40bb9753bae1cdd886a21982a98353f738e3e5`
- `evidence/recovery/fault-injection.json` — `bd4b054397edc80e2a2f80c8b4f05e70135c5c6c`
- `LICENSE` — `d08c87a4f86146842ca208114854acec66150819`
- live-fault-evidence history commit `18e4adb4284a3eb11c64b84e7ee66f7281f7c10a`.
No repository code, external mutation, credentials, contacts, spend or commitments were executed in this shadow run.

**CRITICAL FALSIFICATION / TIER RESULT:**
- This does **not** close tier-5B or tier-5C-B for money. The recovery phase is a second `runFlightcheck()` invocation inside the same Node process/script; no literal OS process death/restart occurs around the external effect.
- The external action is a sponsored zero-value contract-call on Base Sepolia, not a cash refund, charge or payout. The public-chain success receipt proves an external effect but not monetary settlement economics.
- The exact-one proof counts successful canary event logs for the run’s unique challenge. It strongly proves one successful external effect, but it would not count a hypothetical duplicate transaction that reverted before emitting that event.
- Provider rediscovery is time-bounded: after the 24-hour replay window, this exact design deliberately refuses replay because identical key/body may execute again. Thus “durable identity” must always be evaluated together with the provider’s dedupe-retention horizon.
- The evidence bundle is self-authored and was not independently rerun in this shadow pass.

**COMPARATORS / FALSIFIERS:**
- `strale-io/strale@2a65ffd66d5a5416a21bbdaac1505e2d0c41489a` has a strong literal-SIGKILL/PostgreSQL test around an internal wallet debit. A child process drives the real route, dies after the debit, and a reservation reconciler refunds exactly once; a second reconciler pass refunds nothing. It is stronger on actual process-death proof but weaker on this run’s missing edge because no external provider effect must be rediscovered.
- `Mustaqeem-Rafi/interlock@523ec30551b58de9fbad5ed6b0e3cf2f7c93876f` has an impressive real-process SIGKILL matrix and durable ledger, but its own recording notes say v0.1 is validated against a **mock rail** and the live Razorpay adapter is not present. It therefore cannot displace real external-effect evidence.
- Prior `az-said/Interlock@822ec54692b30e1fdce04b55dfab62d0b56a60b2` remains materially stronger for direct-money tier-5B because it combines a real Stripe test refund with literal process death/new-process recovery. KeeperHub’s incremental value is narrower: it demonstrates that a **pre-dispatch exact request/idempotency identity can itself be the provider-rediscovery anchor even when no provider object ID was observed**.

**SPECIALIST PASSES:**
- **CODE INSPECTOR:** verified canonical-request/idempotency derivation, fsync-before-send ordering, bounded replay-window enforcement and resume behavior.
- **EXTERNAL-EVIDENCE ANALYST:** verified the checked-in response-loss artifact, external chain receipt/event agreement and one-event ground-truth count.
- **HISTORY/RIGHTS ANALYST:** pinned exact HEAD, evidence-lineage commit, 1-star/0-fork metadata and MIT license; no exact-HEAD Actions run was available.
- **COMMERCIAL ANALYST:** mapped the pattern to qualification of ambiguous money mutations rather than treating the zero-value canary itself as a payments product.
- **RED-TEAM/VERIFIER:** separately challenged process-boundary strength, money terminality, idempotency-window expiry and the exact-one event-count semantics before scoring.

**INDEPENDENT RED-TEAM / VERIFIER VERDICT:** **PASS_WITH_LIMITS.** The frozen packet supports the narrow claim that this exact revision persists and fsyncs a stable semantic request/idempotency identity before dispatch, deliberately loses a real external response, later replays that same identity, and has checked-in public-chain evidence that the recovery converged to one successful external effect. The verifier rejects literal crash/restart, direct-money settlement, tier-5B/5C-B, generic provider exactly-once guarantees and safety beyond the provider’s replay window. No sensitive-source material was used.

**A-F SCORE (proposed only, after verifier):** **25/30 — A3 / B3 / C5 / D5 / E5 / F4.**
- A3: the direct wedge is a reliability qualification pattern rather than a ready-made revenue-recovery product.
- B3: external-effect ambiguity is economically important, but the checked-in action is zero-value testnet work rather than money movement.
- C5: strongly compresses pre-dispatch identity design, canonical request persistence, fsync ordering, safe replay cutoffs and independent external-effect verification.
- D5: a one-star repository with real response-loss injection plus checked-in external-chain one-effect evidence is rare.
- E5: implementation, machine-readable run artifact, public-chain verification details and history all support the narrow claim.
- F4: MIT and testnet boundaries are clear; operational value depends on each target provider’s idempotency/replay contract and retention window.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: payments/platform reliability lead, fintech engineering team or AI-agent platform owner whose tools can trigger money-like external effects.
- Pain: teams often persist “intent” but cannot prove that the persisted pre-send identity is actually enough to recover the original provider outcome if the effect happens and the response is lost.
- First paid wedge: **Idempotency Recovery Qualification** for one provider sandbox/test flow. Persist and fsync the exact authorized action identity before dispatch, deliberately suppress the post-effect response, recover only through the same provider identity, independently count external effects, and explicitly test the provider replay-window expiry. For a money rail, keep the initial engagement test/sandbox-only and do not call it settlement certification unless the same action reaches terminal economic evidence.

**COMBINATION WITH PRIOR SHADOW RUNS:** Run 11 exposed the compensation-descriptor birth gap; this run supplies a concrete counter-pattern: the provider result ID need not be known before dispatch if a stable, exact pre-dispatch identity can retrieve the original result by provider replay. Run 10’s durability-horizon lesson now extends beyond transient locks to **provider idempotency retention**: a locally durable command may still become unsafe to replay after the provider forgets its dedupe record. This strengthens the qualification architecture but does not supersede Interlock’s literal process-kill money evidence or Flames-up’s payout terminality evidence.

**SEARCH EFFORT / COST PROXIES:** Four materially different discovery modes; three serious candidate/comparator paths deep-inspected; source/evidence/history/rights and exact-revision workflow status checked; roughly three dozen search/read/tool operations; 0 untrusted-repository code executions, provider writes, credentials, contacts, spend or commitments.

**LOCAL LESSON:** Extend `SK-COM-003` with a **provider replay-window cliff check**. A durable pre-dispatch identity is only as replay-safe as the provider’s dedupe-retention contract. Record the provider’s idempotency horizon as part of the action evidence; before expiry, exact-body/key replay may be a valid rediscovery mechanism even without lookup-by-business-key, but after expiry automatic replay must fail closed or switch to another authoritative read path. Also distinguish **provider rediscovery by exact replay** from ordinary provider lookup: both can close the compensation-descriptor birth gap, but only if their validity horizon is explicit and tested.

**REFERRALS:** No new referral. Existing external-provider/system-of-record referrals already target the remaining direct-money settlement intersection; this run adds a reusable rediscovery primitive rather than a new lane handoff.

**NEXT TEST:** Find one **cash refund or payout** where the pre-dispatch semantic identity and its provider-validity horizon are durable, a literal post-effect process death occurs, a genuinely new process rediscoveries the exact effect with no duplicate, and that same effect later reaches terminal provider balance/payout/bank evidence.

## 2026-09-20 — Shadow run 13

**DATE:** 2026-09-20

**HYPOTHESIS:** The pre-dispatch identity gap and the literal process-death gap can intersect in one real money test path even if terminal settlement still remains open: a durable workflow identity should deterministically derive the provider idempotency key before a Stripe refund, survive post-effect Worker death, and let a genuinely new Worker replay/recover the same provider effect without requiring the response-born refund ID as the recovery anchor.

**DISCOVERY METHODS:**
1. Direct code search for Stripe refunds/payouts combined with `SIGKILL`, Worker restart, idempotency and provider readback.
2. Fault-seam/code-signature search for `effect accepted, result not reported`, stable run/workflow identity, refund-list metadata correlation, process kill and replacement-worker launch.
3. Adjacency/history traversal from prior tier-5B/5C candidates (`az-said/Interlock`, `karfalacisse900-alt/Flames-up.com`) into durable-workflow implementations, then commit-history inspection of the strongest candidate.
4. Broad public comparison against provider-idempotency implementations that explicitly warn against in-memory/generated retry identities after process loss.

**BEST NEW COMPONENT + URL + EXACT REVISION:** `temporal-community/agent-memory-and-state` — https://github.com/temporal-community/agent-memory-and-state — `59fb4186bc50daefe09653a850197a985b3fa1cf`.

**IMPLEMENTED / SOURCE-VERIFIED:**
- `issue_refund()` derives the Stripe idempotency key **before provider dispatch** from the durable Temporal workflow identity plus workflow-run identity: `idempotency_key_for(f"{workflow_id}:{run_id}")`. The source explicitly states that this identity remains stable across an Activity retry inside the same Workflow run while a brand-new run receives a new identity.
- `_real_stripe_refund()` calls Stripe test mode with that exact idempotency key and also writes workflow/idempotency metadata onto the refund. Client-side network retries are disabled so Temporal owns the retry boundary.
- After Stripe returns the refund, `issue_refund()` can open an `EFFECT_RESTART_WINDOW_SECONDS` pause that is deliberately **after the provider effect and before Activity completion**. During that interval it heartbeats `effect accepted, result not reported`; killing the Worker therefore leaves Temporal with an unresolved external-effect Activity rather than a recorded result.
- The Workflow schedules `issue_refund` with heartbeat-based Worker-loss detection, a ten-minute schedule-to-close recovery budget and a retry policy whose next attempt reuses the same workflow/run-derived provider identity.
- The guided stage runner launches the Worker as a dedicated Python subprocess, can hard-kill it, and later starts a fresh `python -m refund_agent.worker` process against the same Temporal state and task queue.
- The inspection path can independently list Stripe test refunds for the seeded PaymentIntent and filter by `temporal_workflow_id`, reporting the exact external refund IDs/statuses and unique refund count rather than trusting only the local mirror.

**TEST / DOCUMENTATION / HISTORY / RIGHTS VERIFICATION:**
- `tests/test_fake_stripe.py` verifies stable workflow-scoped idempotency derivation, two calls with the same key converging to the same refund identity, and conflict rejection when the same key is reused with different economic parameters.
- `tests/test_stage.py` verifies the real-retry CLI surface, separate subprocess lifecycle helpers, replacement-process identity for the naive side, and that the real status-read path performs Stripe `PaymentIntent.retrieve` plus `Refund.list` without creating another refund. The credentialed Stripe crash path itself is not an ordinary unit test and was not rerun here.
- `docs/REFUND_DEMO.md` documents the real Stripe test-mode sequence: seed a succeeded PaymentIntent, wait until attempt 1 is accepted at Stripe, kill the Worker, inspect the ambiguous boundary, launch a replacement Worker, let attempt 2 reuse the same idempotency key, and inspect one unique Stripe refund. This is a manual/rehearsal contract, not a checked-in machine-readable successful provider run artifact.
- Commit `4b632d12a6ab84f4459dd543c3ffb4bab1395cba` is a verified GitHub commit whose message explicitly includes “Run naive recovery in a replacement process,” “Add guided Stripe retry simulation,” and “Add pre-commit Stripe timeout retry demo,” showing the recovery/fault-seam behavior has independent history rather than existing only in current docs.
- No `.github/workflows` directory exists at the inspected revision, so no green-CI claim is made.
- Repository metadata at inspection: public, 1 star / 1 fork, MIT license.

**CLAIM STATUS:**
- **IMPLEMENTED:** pre-dispatch workflow/run-derived provider identity, real Stripe test refund path, post-effect pre-completion restart window, hard Worker kill, replacement Worker, same-identity retry, and provider-side refund listing.
- **TESTED:** deterministic identity/deduplication and process/status-read helper semantics are unit-tested; the durable Workflow orchestration is source-verifiable.
- **DOCUMENTED / NOT INDEPENDENTLY RERUN:** the credentialed real Stripe post-effect kill/replacement-Worker rehearsal.
- **UNKNOWN / UNPROVEN:** processor balance transaction, payout/bank settlement, live-mode behavior, customer money economics and provider-idempotency safety beyond the provider's own retention contract.

**FROZEN EVIDENCE MANIFEST:** `sha256:05a8016dc9293029e656865988a95a64edb489c688df12ba9f7b4c6bd95671f9`, binding exact revision to:
- `src/refund_agent/activities.py` — Git blob `e5497eb7c50249d37c25d4f242ef42fba8aa0bbd`
- `src/refund_agent/workflow.py` — `bc3ab4e1d5e8e1d3cfa828bb343f1774b1480b78`
- `src/refund_agent/stage.py` — `886e56febda774216f9751b49dba3742d3bc8e7d`
- `src/refund_agent/cli.py` — `730c74533a17640a88098de43607fbf0dfd8a552`
- `docs/REFUND_DEMO.md` — `7496660d3d47260bef4dc8edeee4dec95f0f2b1c`
- `tests/test_fake_stripe.py` — `94a73a3ae8dc0a23219cb2e6d7a41e81d1deeb69`
- `tests/test_stage.py` — `dcadf29dc4af744e7973b29a9d5667727e47aa35`
- `LICENSE` — `f29602815c81c78143ca09a57355c05ea2226d2c`
- recovery-lineage commit `4b632d12a6ab84f4459dd543c3ffb4bab1395cba`.
No repository code, Stripe mutation, credentials, contacts, spend or commitments were executed in this shadow run.

**CRITICAL FALSIFICATION / TIER RESULT:**
- This still does **not** close tier-5C-B. Search of the exact revision found no `balance_transaction` settlement path, payout readback or bank evidence tied to the recovered refund.
- Unlike Interlock's checked-in scenario JSON, this repository does not contain a comparable machine-readable artifact proving that a credentialed real-Stripe post-effect Worker kill was actually completed at this exact revision. The strongest real-provider sequence is source + manual rehearsal documentation.
- The recovery identity is durable because Temporal owns the Workflow/run state, but it is not separately persisted as an application database command row. Losing the Temporal execution/history would lose the identity owner that regenerates the provider key.
- The repository does not encode the provider's idempotency-retention horizon beside the command. Therefore the safe-replay window remains an external provider contract and must not be silently treated as indefinite.
- The configured Workflow schedule-to-close is ten minutes in this demo. That is a demonstration recovery budget, not proof of arbitrary-duration ambiguity survival.

**COMPARATORS / FALSIFIERS:**
- Prior `az-said/Interlock@822ec54692b30e1fdce04b55dfab62d0b56a60b2` remains stronger on revision-bound evidence quality: it has checked-in real-Stripe test-mode SIGKILL/new-process/result artifacts and exact provider-effect counting. This Temporal candidate's incremental value is the clean **identity lineage**: durable Workflow/run identity → provider idempotency key → same-effect retry, closing the response-born-ID gap by design.
- Prior `winsznx/keeperhub-flightcheck@1d0142d2e401872ffe020b2a4110d85be31e0750` remains stronger on persisting canonical request bytes and an explicit provider replay-window cutoff, but its recovery invocation is same-process and the effect is zero-value testnet work. The Temporal candidate adds literal Worker-process replacement and a real Stripe refund path.
- Prior `karfalacisse900-alt/Flames-up.com@2ba5fa878da26f405bfae1846c8c90f1d0e69c10` remains stronger on Axis-B terminality—connected balance → payout `paid` → `payout.paid` → local parity—but still has no post-effect payout crash seam.

**SPECIALIST PASSES:**
- **CODE INSPECTOR:** verified the exact identity derivation, Stripe call, post-effect restart window, retry policy and provider-list inspection path.
- **FAILURE/RELIABILITY ANALYST:** verified dedicated Worker subprocess kill/replacement ordering and separated Temporal-owned durable execution identity from a response-born provider refund ID.
- **TEST/HISTORY/RIGHTS ANALYST:** inspected unit tests, manual real-provider rehearsal contract, verified feature-lineage commit, 1-star/1-fork metadata and MIT license; found no exact-revision CI workflow.
- **COMMERCIAL ANALYST:** mapped the narrow capability to a test-mode refund crash qualification service rather than claiming production settlement.
- **RED-TEAM/VERIFIER:** received the frozen claim/evidence packet without the A-F score and challenged real-run evidence, provider-retention assumptions and economic terminality separately.

**INDEPENDENT RED-TEAM / VERIFIER VERDICT:** **PASS_WITH_LIMITS.** The narrow source claim passes: this exact revision implements a real Stripe test-mode refund path in which a durable pre-dispatch Workflow/run identity deterministically supplies the same provider idempotency key after a literal Worker-process loss, and the replacement Worker is designed to retry the unresolved Activity while a separate inspection path can read Stripe refund truth. The verifier rejects any claim that a credentialed run was independently reproduced here, that the repository contains a revision-bound raw successful tier-5B artifact comparable to Interlock, that the provider dedupe window is encoded/indefinite, or that the recovered refund reaches processor/bank settlement. No sensitive-source material was used.

**A-F SCORE (proposed only, after verifier):** **26/30 — A4 / B5 / C5 / D4 / E4 / F4.**
- A4: a Stripe-test refund crash/recovery qualification engagement can be delivered quickly without live money.
- B5: duplicate refunds and unknown-effect incident handling are direct-money reliability risks.
- C5: compresses durable orchestration, process-loss detection, stable provider identity, same-effect retry and provider-ground-truth inspection.
- D4: the conjunction is rare in a one-star repository, though Temporal-style durable execution plus provider idempotency is a known architectural pattern.
- E4: source/tests/history/docs are strong and internally coherent; evidence quality is capped because the real credentialed crash rehearsal is not a checked-in machine-readable completed artifact and was not rerun in this shadow pass.
- F4: MIT, test-mode-only Stripe behavior and local Temporal deployment are clear; provider-retention and terminal-settlement obligations remain external.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: payments engineering lead, marketplace/billing platform owner, fintech reliability team or Controller's systems group with refund workflows.
- Pain: a provider refund can succeed while the Worker dies before application completion is durable; teams then need an identity that survives the process, a safe retry contract, and external proof that the retry is the same business action rather than a second refund.
- First paid wedge: **Refund Crash Recovery Drill**. In Stripe test mode, bind one refund route to a durable workflow/business identity, deterministically derive the provider idempotency key before dispatch, kill the Worker after Stripe acceptance but before local completion, start a fresh Worker, inspect Stripe directly for exactly one workflow-tagged refund, and return a revision-bound unsafe-window/retention report. Do not call the deliverable settlement certification unless processor/balance evidence is separately proven.

**COMBINATION WITH PRIOR SHADOW RUNS:** Run 11 exposed the compensation-descriptor birth gap; run 12 showed pre-dispatch identity can rediscover an external effect by provider replay; this run shows a **durable workflow execution identity can play that pre-dispatch anchor role across an actual Worker-process death on a real Stripe refund path**. Interlock still owns the strongest checked-in tier-5B run artifact, and Flames-up still owns the strongest independent payout-terminality half. The unified tier-5C-B intersection remains open.

**SEARCH EFFORT / COST PROXIES:** Four materially different discovery modes; three serious candidate/comparator paths deep-inspected; exact source/tests/docs/history/repository rights inspected; no untrusted code execution, provider writes, credentials, contacts, spend or commitments.

**LOCAL LESSON:** Extend `SK-COM-003` with an **identity-lineage check**. A pre-dispatch recovery anchor need not be a separate SQL command row if a durable execution system owns a stable business/workflow identity from which the provider idempotency key is deterministically regenerated. Inspect the lineage explicitly as **durable business/workflow identity → provider idempotency identity → provider effect**. Then test two independent failure limits: whether the identity owner itself survives process loss, and whether the provider's replay/dedupe horizon is recorded and still valid. This strengthens, but does not replace, the run-12 provider-window rule.

**REFERRALS:** No new referral. Existing provider/system-of-record referrals already target the remaining settlement intersection; this run adds a local recovery-identity refinement rather than a new cross-lane question.

**NEXT TEST:** Find one **cash refund or payout** where the pre-dispatch durable business/workflow identity and provider-validity horizon are both explicit, a post-effect process death is followed by genuinely new-process recovery and exact no-duplicate provider truth, and the same action then reaches terminal processor balance/payout/bank evidence.

## 2026-09-20 — Shadow run 14

**DATE:** 2026-09-20

**HYPOTHESIS:** A low-attention refund implementation can close part of the replay-window gap by persisting a pre-dispatch business refund identity and distinguishing provably-not-sent from possibly-sent actions, then rediscovering provider truth by business metadata rather than relying only on provider idempotency replay. Full tier-5C-B still requires literal process death plus terminal cash evidence on that same action.

**DISCOVERY METHODS:**
1. Direct money-domain search for refund crash/restart/idempotency/provider readback and settlement evidence.
2. Code-signature search for durable refund fences, `requested`/`dispatched` state, provider retrieval/list correlation and no-reissue invariants.
3. Durable-execution/payment analog search across workflow, reconciliation and contract-to-cash repositories.
4. Deliberate low-attention search emphasizing zero-star operational repositories and commit-history archaeology around refund safety fixes/reverts.

**BEST NEW COMPONENT + URL + EXACT REVISION:** `SmallHeroes/Small_Heroes` — https://github.com/SmallHeroes/Small_Heroes — `ed1da86cc114a767dc1086b71a30a4ef4595c097`.

**IMPLEMENTED / SOURCE-VERIFIED:**
- `lib/payment-refunds.ts` models a durable `RefundFence` with four states: `requested` means the provider refund was never sent; `dispatched` means it was sent/may be in flight/response may be lost; `pending` is accepted but unsettled; `confirmed` is terminal success.
- The Prisma fence is created before provider entry, keyed by stable `refundKey`, and the `requested -> dispatched` transition is an atomic one-winner conditional update. A restarted/concurrent worker that sees `dispatched` cannot issue the physical refund again.
- PayMe reconciliation is deliberately fail-closed: `dispatched`/`pending` always query provider truth and never reissue. A lagging `paid` read leaves the refund pending rather than treating it as permission to send again; `refunded` confirms. `requested` is the only retryable state because the call is known not to have been sent.
- Stripe uses the stable provider idempotency key but adds an important second recovery primitive: before creating a new refund it lists refunds for the PaymentIntent and searches for an earlier recovery refund tagged with stable `orderId` plus `recovery=exception_case`. The source explicitly says Stripe idempotency records are not a permanent ledger and this lookup is meant to rediscover a prior refund after DB-write loss/provider replay-window expiry.
- The design therefore separates **provider replay** from **provider rediscovery by durable business identity**, directly extending run 12's replay-window lesson.

**TEST / SCHEMA / HISTORY VERIFICATION:**
- `lib/__tests__/payment-refunds.spec.ts` verifies existing tagged Stripe refund reuse, one Stripe create with the stable key when no prior refund is found, PayMe fail-closed behavior without a fence, fence-before-call, one-winner dispatch, confirmation without reissue, `requested` retry only when the action was provably not sent, and no reissue from `pending`/`dispatched` even when provider reads lag at `paid`.
- The suite also covers partial-refund safety: a pre-existing partial refund stays pending and does not blind-issue another full refund.
- `backend/migrations/20260630_refund_attempt_fence/migration.sql` creates a durable service-only `RefundAttempt` table with unique `refundKey`, provider/provider-sale identity, status, provider action ID and timestamps; RLS is enabled.
- History is unusually candid. Commit `4894e7529d5b015a281bc625412ee071824ec417` introduced the pre-dispatch `dispatched` marker after tests found double-refund windows. Commit `ef41204c5907ab6653ea7af23e1ae2a41eecf8cc` tried to regain liveness by reattempting supposedly definitive failures. Commit `d1ed7cd73c6a3b187e63da7e853eb6a3c52cdd8d` then reverted that behavior because the provider contract could not prove a 4xx/application rejection had no financial side effect, explicitly choosing never-double over automatic liveness.
- Repository metadata at inspection: public, 0 stars / 0 forks, GitHub public license metadata `null`. Under the hunt's standing rule, repository-code commercial authorization is user-asserted separately; no external-service/data rights are inferred.

**CLAIM STATUS / CRITICAL FALSIFICATION:**
- **IMPLEMENTED + UNIT-TESTED:** durable pre-dispatch refund fence, explicit not-sent vs maybe-sent semantics, no-reissue invariant, provider query reconciliation, stable Stripe idempotency and metadata-based Stripe rediscovery.
- **NOT EXTERNALLY QUALIFIED:** the inspected tests use mocked provider clients/in-memory test fences; no revision-bound real Stripe/PayMe process-kill artifact was found.
- The repository's own decision gate says a real PayMe sandbox crash/retry proof is mandatory before flag-on, and default tests must not call providers. That self-imposed gate is evidence against overstating production qualification.
- Safety deliberately sacrifices liveness: if a refund is marked `dispatched` but the provider call genuinely never arrived, a later `paid` read stays pending and requires operator/next-phase reconciliation rather than automatic retry.
- Stripe rediscovery itself is not fully proven complete: the code requests `limit:100` and the inspected path has no visible pagination. Retention, pagination/scope and uniqueness of metadata lookup remain provider-contract proof obligations.
- No literal process-kill/new-process run, terminal processor balance, payout or bank evidence is tied to this candidate. Tier-5C-B remains open.

**COMPARATORS / FALSIFIERS:**
- `Zzradar/high-concurrency-ticketing-system@bdd47edf3cbc6a2888461b6ec994b9b49178536e` is stronger on literal process failure: its integration harness uses a real Docker backend SIGKILL/exit 137, leaves a PROCESSING refund row behind, starts a fresh backend and reconciles the provider snapshot. But the provider in that proof is explicitly Fake Stripe, so it does not improve external-provider truth.
- `contract-to-cash/core@df39318eed6063fa03b288b5864a65f21636fccf` cleanly derives durable refund idempotency slots and models compensated/burnt keys, while its adapter documentation warns that provider idempotency retention is finite. Its external-provider tests are fake/httptest shaped and it is weaker than the selected candidate on explicit post-dispatch ambiguous readback.
- Prior `az-said/Interlock@822ec54692b30e1fdce04b55dfab62d0b56a60b2` remains stronger on actual real-Stripe tier-5B evidence; prior `temporal-community/agent-memory-and-state@59fb4186bc50daefe09653a850197a985b3fa1cf` remains stronger on durable workflow→provider-key lineage; prior `karfalacisse900-alt/Flames-up.com@2ba5...` remains stronger on the separate payout-terminality axis.

**SPECIALIST PASSES:**
- **CODE INSPECTOR:** traced fence creation, requested→dispatched ordering, provider-call boundary, Stripe rediscovery and PayMe reconciliation behavior.
- **TEST/SCHEMA INSPECTOR:** verified unit tests, the durable `RefundAttempt` migration and single-flight uniqueness.
- **HISTORY/ECOSYSTEM ANALYST:** inspected the FIX-5/FIX-6/revert lineage and compared replay-window handling with independent payment/recovery repositories.
- **COMMERCIAL ANALYST:** mapped the capability to a refund-ambiguity safety audit rather than claiming a finished payment product.
- **RED-TEAM/VERIFIER:** independently challenged real-provider qualification, process restart, lookup completeness, liveness loss, public provenance and economic terminality before scoring.

**INDEPENDENT RED-TEAM / VERIFIER VERDICT:** **PASS_WITH_LIMITS.** The narrow claim passes: this exact revision implements a durable refund dispatch fence that distinguishes provably-not-sent from possibly-sent actions, refuses automatic reissue once a provider mutation may have been dispatched, and adds Stripe provider-side rediscovery by stable business metadata before creating another refund. Source, focused tests, durable schema and history support that claim. The verifier rejects literal crash/restart proof, real-provider qualification, generic exactly-once semantics, lookup completeness beyond the inspected bounded list query, terminal cash settlement and tier-5C-B.

**A-F SCORE (proposed only, after verifier):** **25/30 — A4 / B5 / C5 / D4 / E4 / F3.**
- A4: a refund-safety/code-path audit or staging retrofit can be sold without moving live money.
- B5: duplicate refunds and ambiguous provider outcomes are direct-money risks with clear finance/reliability value.
- C5: compresses durable state-machine, pre-dispatch fencing, provider rediscovery, fail-closed reconciliation and concurrency knowledge.
- D4: the combination of durable dispatch semantics plus explicit metadata rediscovery after the idempotency window is unusually thoughtful in a zero-star product repository, but the patterns are reproducible.
- E4: source/tests/schema/history are strong and unusually candid; evidence is capped because provider tests are mocks and no exact-revision external run artifact was found.
- F3: public license metadata is absent and provider contracts still require sandbox qualification; standing separate repository-code authorization does not solve external-service operability.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: payments/billing engineering lead, marketplace finance systems owner or Controller's platform team that issues refunds/corrections.
- Pain: provider idempotency keys are often treated as permanent truth even though replay retention is finite; after a response/DB-write loss, a retry can become a second refund if the original effect cannot be rediscovered.
- First paid wedge: **Refund Ambiguity Safety Audit / Exactly-Once Refund Retrofit**. Map each refund path into durable `requested/dispatched/pending/confirmed` states, persist the business refund identity before provider entry, add provider lookup by durable business reference/metadata in addition to idempotent replay, inject safe response-loss/restart cases, and deliver a matrix of safe-retry, reconcile-only and operator-required rows. Keep the first engagement test/sandbox-only.

**COMBINATION WITH PRIOR SHADOW RUNS:** SmallHeroes adds an application-level durable dispatch fence plus a second provider-rediscovery mode after idempotency replay retention. Interlock supplies the strongest checked-in real Stripe SIGKILL/new-process/no-duplicate evidence; Temporal supplies durable workflow→provider-key lineage; Flames-up supplies separate provider payout terminality. Together they define a stronger qualification architecture, but these facts remain separate until one executable path proves their intersection.

**SEARCH EFFORT / COST PROXIES:** Four materially different discovery modes; exactly three serious candidates/comparators deep-inspected; source/tests/schema/history/rights verified at exact revisions; no untrusted repository code execution, provider mutations, credentials, contacts, spend or commitments.

**LOCAL LESSON:** Extend lane-local `SK-COM-003` with a **provider-rediscovery completeness check**. Distinguish **idempotent replay** from **provider lookup by durable business identity/reference**. The latter can remain useful after replay-key retention expires, but only if its retention, pagination/scope, uniqueness and completeness are verified. A bounded/incomplete “query before retry” must not be silently promoted into proof that the original effect is absent; when rediscovery is incomplete, fail closed rather than issue a second money mutation.

**REFERRALS:** No new cross-lane referral. The existing provider/system-of-record referral already asks for the single-path crash-safety + external-truth + terminality intersection; this run adds a local recovery-query discriminator rather than a new lane handoff.

**NEXT TEST:** Find one real cash refund or payout where provider-side rediscovery by durable business identity is proven complete across the relevant retention horizon, then inject literal post-effect process death/new-process recovery and follow that same action to terminal processor balance/payout/bank evidence.

## 2026-09-20 — Shadow run 15

**DATE:** 2026-09-20

**HYPOTHESIS:** The highest-leverage next component may be an outcome-verification layer rather than another payment state machine: if an external verifier binds each money action to an immutable/versioned completion contract, separates provider acknowledgement from actual completion, reads provider truth with independent credentials, and emits signed receipts, it can compress the evidence/qualification layer of a Payment Effect Crash Certification product even if literal process death and external bank settlement remain separate proof obligations.

**DISCOVERY METHODS:**
1. Direct money-domain repository search for Stripe refund/payout `SIGKILL`, restart, idempotency, balance transactions and terminal events.
2. Code-signature search for `refund.paid`, `payout.paid`, lost-response/after-provider seams, provider readback and no-retry-after-ambiguous-effect patterns.
3. External verification-infrastructure search for immutable completion contracts, read-only provider evidence, signed receipts, chaos/conformance cases and version-drift handling.
4. Low-attention source/history archaeology on refund-retry implementations, specifically testing whether durable recovery state is born before or only after provider entry.

**BEST NEW COMPONENT + CANONICAL IDENTITY:** **Provely Stripe integration / `stripe.refund.succeeded@1.0.0`** — https://provely.sh/verify/stripe — Stripe integration version `0.1.0`, provider API `2026-08-26`, signed manifest hash `0a25be438644e157`, conformance artifact digest `866e8fb637cff5a1`, last conformance run `2026-09-05T12:00:00Z`. This is a proprietary external service/integration package rather than a public source repository; no public Provely source repository was found in the GitHub search, so the exact signed package identity is used instead of inventing a Git commit revision.

**IMPLEMENTED / PUBLISHED VERIFICATION CONTRACT:**
- Provely's public protocol is `begin -> act -> action_result -> verify -> status/receipt`. `begin` returns a durable operation ID plus correlation/idempotency metadata; the agent performs the mutation; the provider acknowledgement is submitted separately; a verifier then reads evidence and issues a verdict. Public docs state that an operation outlives the agent session that opened it.
- Completion contracts are immutable, versioned and hashable. They define the exact promise, subject identity, positive completion conditions, false-success blockers, evidence channels, timing/deadline semantics and supported provider versions. Unsupported versions return `UNVERIFIABLE` rather than inheriting semantics from a nearby version.
- The Stripe package deliberately separates two claims. `stripe.refund.created@1.0.0` proves only that the Refund resource exists (`E2` provider readback); `stripe.refund.succeeded@1.0.0` requires the succeeded provider state plus a matching `refund.updated` provider event (`E2 + E3`). The integration explicitly says the lower completion level does not prove the higher one.
- The verifier credential is separate from the agent's write credential and is intended to be read-only where the provider permits. This is a meaningful authority separation for money actions: the system deciding “done” does not need permission to issue another refund.
- Receipts bind operation ID, contract ID/version/hash, integration/provider versions, evidence levels and observation digests. Public docs specify RFC-8785 canonical JSON plus Ed25519 signatures and an offline validator that checks schema, canonical hash, signature, trusted key and evidence claims. Cross-language validator fixtures are described for TypeScript, Python and Rust, including forged/tampered receipts that must be rejected.

**CONFORMANCE / TEST EVIDENCE:**
- The published Stripe manifest reports **30/32 conformance cases passed and 0 critical false VERIFIED** on 2026-09-05. The overall Stripe package is deliberately capped at **49 / Provisional** because an uncertainty remains open and two conformance cases failed; the `stripe.refund.succeeded` contract individually scores **89 / Verified** while `stripe.refund.created` remains 49 / Provisional.
- The benchmark is directly relevant to this lane. Required chaos/false-completion rows include `timeout_after_commit` (must become VERIFIED after authoritative readback, never FAILED), `five_xx_after_execution` (must verify by readback, never blindly retry), duplicate side effect (CONTRADICTED), pre-existing matching state (must not verify), stale readback, wrong subject/amount and unsupported provider version.
- The two failed Stripe case slots occur in precisely the danger classes this lane cares about: `error after execution` is 1/2 and `timeout after commit` is 1/2. That prevents a blanket “ambiguity solved” claim even though the succeeded contract itself is classified Verified.
- The published false-completion benchmark uses an independent oracle with a provider simulator. It is useful qualification evidence, but it is not the same as a revision-bound real-Stripe literal-`SIGKILL` run.

**EVIDENCE-TIER BOUNDARY / CRITICAL FALSIFICATION:**
- Provely explicitly models `E0` agent assertion, `E1` action acknowledgement, `E2` provider readback, `E3` provider event, `E4` independent system, and `E5` external-world outcome such as bank/carrier/recipient acknowledgement.
- The Stripe refund skill has **no E5 channel** and explicitly states that a bank credit/customer external outcome is **not proven**. Therefore `stripe.refund.succeeded` is strong provider-level terminality evidence, not tier-5C-B bank settlement.
- No public evidence inspected here shows a literal OS process kill after a real Stripe refund effect followed by a new process recovering the same Provely operation. “Operation outlives the session” is useful durability semantics but cannot inherit Interlock's tier-5B process-kill proof.
- The published conformance evidence and signed manifests are vendor-authored. They are stronger than ordinary marketing claims because they expose exact versions, hashes, cases, failed rows and signatures, but they were not independently rerun in this shadow pass.
- The service/compiled integrations are proprietary. Provely's terms say Macleod Labs owns the service, software and compiled integrations; the published pricing FAQ says SDKs, contract format, receipt validator and generic verifier interface are always free, but “free” is not an open-source license. The terms also prohibit resale of the service without a written agreement. Do not extend the user's repository-code authorization to this independently owned service.

**COMPARATORS / FALSIFIERS:**
- `yea-80y/WoCo-Event-App@4c67646b0374ff442b6a7db2e448b728ff82ab73` is a useful low-attention source comparator (2 stars / 0 forks, MIT). Its pending-refund queue atomically persists/fsyncs exact refund parameters, lists Stripe refunds by payment intent + `metadata.sessionId` before retrying because Stripe idempotency retention is finite, and has focused disk-reload/no-second-create tests. But the durable pending row is created only inside the `createRefund` catch. A literal process death after Stripe commits but before the catch records the row can therefore leave **no durable recovery row at all**. This reinforces the pre-dispatch-identity/birth-gap rule rather than closing it. Its provider rediscovery is also bounded to `limit:100` without inspected pagination.
- `alexlondoner/salown-docs@406e1cdb4d5cc5916561c2fd91fa94978072bfae` independently models money evidence as append-only provider-object entries plus a mutable generation-fenced refund snapshot. Its design distinguishes capture/refund balance transactions, payout membership, unknown refund fees and reversals, and explicitly treats provider status-transition tables as health checks rather than clocks. The artifact is principally a design/rollout contract and does not supply the missing literal post-effect crash + bank-settlement proof.
- Prior `az-said/Interlock@822ec54692b30e1fdce04b55dfab62d0b56a60b2` remains stronger on actual real-Stripe tier-5B process-kill evidence; prior `karfalacisse900-alt/Flames-up.com@2ba5fa878da26f405bfae1846c8c90f1d0e69c10` remains stronger on provider-payout terminality. Provely adds the **claim/evidence-contract and signed-receipt layer**, not those missing fault/settlement facts.

**SPECIALIST PASSES:**
- **OUTCOME-CONTRACT INSPECTOR:** traced claim levels, evidence tiers, supported provider version, immutable contract semantics and the `created` versus `succeeded` boundary.
- **CONFORMANCE / CHAOS ANALYST:** inspected the false-completion benchmark and exact Stripe 30/32 results, with special attention to post-execution error and timeout-after-commit rows.
- **EVIDENCE / RECEIPT ANALYST:** inspected the signed receipt model, canonicalization/signature checks, evidence-level claims and session-independent operation lifecycle.
- **COMMERCIAL / RIGHTS ANALYST:** checked current published pricing and terms, including the free developer allowance, self-run/hosted verification options, proprietary ownership and no-resale-without-agreement restriction.
- **RED-TEAM / VERIFIER:** received the frozen claim/evidence packet without the proposed score and challenged source availability, independent reproduction, literal process-death proof, E5/bank evidence and service-rights boundaries.

**INDEPENDENT RED-TEAM / VERIFIER VERDICT:** **PASS_WITH_LIMITS.** The narrow claim is supported by exact, current public artifacts: Provely's Stripe integration `0.1.0` publishes immutable/versioned refund completion contracts, separates action acknowledgement from provider readback/events, emits signed evidence receipts, binds provider API version, and publishes a falsifiable conformance record with 30/32 passes and zero critical false VERIFIED. The verifier rejects stronger claims that Provely itself proves literal post-effect OS crash/new-process recovery against Stripe, that all post-commit ambiguity cases pass, that `stripe.refund.succeeded` proves bank/customer receipt, that the signed vendor artifacts were independently reproduced here, or that the proprietary implementation is reusable under the user's repository-code authorization. Tier-5C-B remains open.

**A-F SCORE (proposed only, after verifier):** **26/30 — A5 / B5 / C5 / D4 / E4 / F3.**
- A5: a verification retrofit can be piloted immediately; the Developer plan is published as free for 1,000 verified actions/month and the verifier can sit beside an existing mutation path rather than replace it.
- B5: false completion, duplicate refund and ambiguous-money evidence are direct operational/financial risks, especially for agentic workflows.
- C5: compresses completion-contract design, provider evidence readback, version drift, chaos conformance, signed receipts and audit surfaces that would otherwise take substantial engineering.
- D4: the exact combination is unusual and highly aligned with this lane, but the general concepts are reproducible and the vendor already commercializes them.
- E4: exact signed package identity, explicit conformance cases, failed rows, evidence hierarchy and receipt format are unusually transparent; score is capped because evidence is vendor-authored and no independent credentialed rerun/source audit was performed.
- F3: hosted/self-run deployment and pricing are clear, but the implementation/compiled integrations are proprietary, there is no public source license to inherit, no default SLA, and service resale requires a written agreement.

**BUYER / PAIN / FIRST PAID WEDGE:**
- Buyer: payments/billing engineering lead, AI-agent platform owner, marketplace finance systems team or Controller's automation owner.
- Pain: existing systems often treat a provider 200/accepted response—or an agent saying “done”—as completion even when the action is still pending, later fails, duplicates, or cannot be causally tied to the intended money movement.
- First paid wedge: **Money Outcome Verification Retrofit**. For one approved refund/correction workflow, define the exact completion promise and minimum evidence tier before execution, route the existing action through a durable operation/idempotency identity, read provider truth with separate read-only credentials, and return signed receipts that distinguish PENDING/VERIFIED/CONTRADICTED/FAILED/UNVERIFIABLE. Keep literal crash injection and E5 bank/recipient verification as separately priced higher-assurance tests. If Provely is used, have the customer contract with the service directly or obtain a written resale agreement; do not silently resell it.

**COMBINATION WITH PRIOR SHADOW RUNS:** Provely can supply a missing **evidence-contract / verifier / signed-receipt plane** around the stronger source/recovery assets already found. Interlock can exercise literal post-effect process death; SmallHeroes/Auths can supply durable ambiguity/fencing patterns; Flames-up can supply a provider-terminal payout pattern. Provely can encode what each component is actually allowed to claim and emit version-bound proof, but it cannot merge those separate facts into tier-5C-B. The combined product opportunity is a Payment Effect Crash Certification service whose evidence threshold is executable rather than prose-only.

**SEARCH EFFORT / COST PROXIES:** Four materially different discovery modes; three serious candidate/comparator paths inspected; current provider-integration, benchmark, receipt, versioning, pricing/terms and repository-source evidence checked; no untrusted code execution, provider writes, credentials, contacts, spend or commitments.

**LOCAL LESSON:** Extend lane-local `SK-COM-003` with a **claim/evidence-contract check**. Before a high-risk action runs, bind the exact promise to an immutable/versioned contract that declares the minimum acceptable evidence level. A lower evidence tier must never be silently upgraded into a stronger promise: `E1` acknowledgement is not completion, `E2/E3` provider success is not `E5` external cash/recipient outcome, and unsupported provider/version semantics should become `UNVERIFIABLE` rather than guessed success. Signed receipts are valuable only when the contract hash, provider version and evidence levels are preserved together. This lesson is evidence-backed here and remains lane-local.

**REFERRALS:** No new cross-lane referral. Existing COMMERCIAL↔AI effect-journal/outcome-verification referrals already ask how agent actions should be bound to authoritative evidence; adding Provely as another general agent-verification referral would duplicate the capability question. Record it locally as a commercially actionable component instead.

**NEXT TEST:** Find or build the **E5 verifier** that Provely's Stripe skill explicitly lacks: bind the same durable refund/payout action identity across post-effect process death/new-process recovery, provider E2/E3 terminality, and an independently grounded processor/bank/recipient outcome, then emit one signed claim whose evidence contract prevents any lower tier from being described as external settlement.
