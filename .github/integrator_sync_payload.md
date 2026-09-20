MARKER: <!-- INTEGRATOR-R11-SAAS-REVENUE-2026-09-20T0102-0400 -->

=== APPEND COMBINATIONS.md ===
## SaaS Revenue Integrity v1 — contract state -> entitlement/access -> metered usage -> invoice parity -> money state
- Core components: `Mima-N/gitlab_mrr_pipeline_dbt@e43562f48a9bf70e58383f453ababd6bbe342f36` for Salesforce↔Zuora contract/subscription drift + `geminimir/meterguard@9147d6fdf9fd8ee8761d732e956fc0a8c86989bd` for local-usage↔Stripe pre-invoice reconciliation and late-event/idempotent correction + optional entitlement/access checks from `Mayreeobi/SaaS-User-Access-vs-Billing-Reconciliation-System@9b5bbd9c28538d5533031889fe4abba57a20bb66` / `Wondermove-Inc/saaslens@10a93ea490d1d7d98df041b368d04d292096c7f5` + Recurso/Summae/provider/bank evidence for later journal/settlement truth.
- Buyer/problem: usage-based B2B SaaS controllers, RevOps and billing engineering teams can have a correct Stripe integration yet still underbill/overbill because CRM contract state, entitlement/access, metered events, reported usage and the closed invoice disagree at different boundaries.
- First paid wedge: **SaaS Revenue Integrity Acceptance Test** on one customer-owned closed/open billing period. Independently seed/reconcile contract/start/term/churn state, entitlement, product usage, Stripe-reported quantity and invoice dollars; quantify orphaned revenue, duplicate/missing units, overcharge/refund exposure and analyst reconciliation time.
- Critical evidence boundary: MeterGuard's ADR targets 0% quantity drift at invoice finalization, but the inspected current validator exits success when either absolute drift is zero **or percentage drift is within epsilon**. That is adequate for an open-period pre-invoice health check, not proof of the stronger finalization invariant. Do not market final invoice parity until an independent fixture verifies exact quantity and dollar equality after the finalization boundary.
- Hard invariant: CRM close, subscription activation, entitlement/access, usage event, provider-reported quantity, invoice issuance, journal posting and cash settlement are distinct facts. Missing authority or ambiguous cross-system identity remains REVIEW, not recovered revenue.
- Validation: seeded cases for orphaned closed-won, wrong start/term/MRR, zombie churn, duplicate usage IDs, late events inside/outside watermark, Stripe 429/5xx/retry, `local > Stripe`, `Stripe > local`, partial replay, finalization and post-close credit note. Require exact final quantity and independently recomputed invoice-dollar parity.

## SaaS License True-Up / Renewal Savings — adjacent FinOps wedge
- Use `Wondermove-Inc/saaslens@10a93ea490d1d7d98df041b368d04d292096c7f5` as the installed schema/workflow substrate linking subscription spend/seats, assignments, `lastUsedAt`, employment termination, payment/card records, renewals and audit logs.
- Buyer / first paid wedge: IT/FinOps/procurement; reconcile authorized subscription contracts + payment/card records + SSO/app usage + HR termination state to quantify unused-seat spend, offboarded-user licenses, duplicate/unmatched SaaS payments and renewal candidates.
- Boundary: usage inactivity is evidence for review/optimization, not automatic proof a license may be removed; contract commitments, shared/service accounts and business-critical access require owner approval.
- Status: monetizable adjacent P1/P2 wedge, but below freight/AP/commission until one customer true-up demonstrates realized savings.

=== APPEND COMPONENTS.md ===
## SaaS revenue-integrity components — post-checkpoint

### geminimir/meterguard — Stripe usage parity / correction substrate
- Revision: `9147d6fdf9fd8ee8761d732e956fc0a8c86989bd`.
- Integrator score after source-level recheck: **28/30 — A5 B5 C5 D5 E3 F5**. Hunter score was 29/30; evidence/completeness is reduced one point because the strongest finalization-parity claim is documented/demoed more strongly than it is enforced by the inspected validator/tests.
- Rights: MIT repository code. Stripe APIs/terms/trademarks and customer usage/billing data remain separately governed.
- Capability inspected: real reconciler reads local counters and Stripe usage summaries, persists diff reports, raises `investigate`, creates pending corrections/alerts, and tracks parity metrics. ADR defines idempotent delta writes, late-event/watermark handling, rate-limit retry and a 0%-at-finalization target.
- Important implementation caveat: current `demo/stripe-test-clocks/validate.sh` accepts either absolute zero drift **or** drift within epsilon, so it proves an open-period tolerance check rather than exact finalized-invoice parity. Reconciler correction behavior is also asymmetric: `Stripe > local` can generate suggested local adjustments while `local > Stripe` raises manual review. Both directions need an independent seeded oracle before money claims.
- Integration: central engine in SaaS Revenue Integrity v1; upstream Mima-style contract/subscription truth, downstream invoice/journal/settlement truth.
- Promotion gate: independent corpus must prove duplicate/late/replayed events, provider retries, both drift directions and exact final quantity+dollar parity across finalization. Keep out of MASTER until then.

### Mima-N/gitlab_mrr_pipeline_dbt — CRM↔billing contract-state drift layer
- Revision: `e43562f48a9bf70e58383f453ababd6bbe342f36`.
- Integrator score under standing repository-code permission: **26/30 — A5 B5 C4 D3 E4 F5**. Actual public repository had no visible root license; provenance remains recorded, but public-license category is not a value penalty under the user's separate permission assertion.
- Capability: deterministic Salesforce opportunity↔Zuora subscription reconciliation for orphaned won opportunities, start/close-date drift, MRR/term mismatches and active-billing-vs-CRM-churn states with severity/annualized impact.
- Integration / next action: use only as the upstream cross-system truth layer; independently seed the CRM/billing mismatch matrix and keep synthetic README dollars out of commercial proof.

=== APPEND OPPORTUNITIES.md ===
## SaaS Revenue Integrity Acceptance Test
- Core: CRM/contract-state reconciliation -> entitlement/access check where applicable -> MeterGuard-style metered-usage/provider parity -> invoice -> independent ledger/settlement evidence.
- Buyer: usage-based B2B SaaS controllers, RevOps and billing engineering.
- First paid wedge: one-period read-only/shadow acceptance test before or across invoice close, with source-linked missing/duplicate usage, contract-state mismatch, invoice-dollar drift and remediation queue.
- Revenue path: fixed acceptance test -> recurring pre-close monitoring -> recovery/refund-control work on validated exceptions.
- Why it matters: it is a direct-money analog of freight audit with a much easier authorization surface, but promotion depends on exact finalization proof rather than epsilon/demo claims.

## SaaS License True-Up & Renewal Savings Audit
- Core: SaaSLens subscription/payment/user/access schema + customer-owned SSO/app-usage/HR/contract evidence.
- Buyer: IT, FinOps, procurement and controllers.
- First paid wedge: one renewal cohort or top 20 SaaS vendors; quantify unused-seat spend, offboarded-user licenses and duplicate/unmatched payments, with human approval before any access change.
- Revenue path: fixed audit -> recurring renewal calendar/true-up monitoring; realized savings tracked only after contract/vendor action is confirmed.

=== APPEND SEARCH_QUEUE.md ===
## SaaS revenue-integrity refinement from Hunter 28
- **Usage billing:** stop generic metering/Stripe wrapper discovery. Differential-test `geminimir/meterguard@9147d6fdf9fd8ee8761d732e956fc0a8c86989bd` on an independently seeded billing period with duplicate IDs, late events inside/outside watermark, 429/5xx, both drift directions, replay and invoice finalization. Require **exact final quantity and independently recomputed invoice dollars** after finalization; an epsilon-success health check is not sufficient.
- **Quote/contract-to-billing drift:** use `Mima-N/gitlab_mrr_pipeline_dbt@e43562f48a9bf70e58383f453ababd6bbe342f36` as the current mismatch taxonomy for orphaned won business, date/MRR/term drift and zombie subscriptions. Search only for hard source/version/identity or settlement gaps, not another RevOps dashboard.
- **SaaS license true-up:** `Wondermove-Inc/saaslens@10a93ea490d1d7d98df041b368d04d292096c7f5` closes much of the schema/workflow gap. Next search should target authoritative contract-seat/renewal terms, SSO/provider deprovision evidence and confirmed vendor credit/savings outcome — not another spend dashboard.
- **MASTER restraint:** MeterGuard clears the numerical promotion bar but remains a COMPONENT/combination challenger until exact finalized-invoice parity is independently proven. Mima and SaaSLens remain stack components/opportunities rather than overlapping MASTER leaders.
