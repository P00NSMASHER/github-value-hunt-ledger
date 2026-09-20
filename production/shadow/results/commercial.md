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
