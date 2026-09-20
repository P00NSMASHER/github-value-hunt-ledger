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
- `.github/workflows/ci.yml` — `1d833e165f186891eeaf5fecbf2056eb7be5c317`
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