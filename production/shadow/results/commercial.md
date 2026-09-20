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
