# Golden Goose iteration #022: execute previously untested integration and challenge the moat

**Research only, 2026-10-29 UTC.** Draft [PR #870](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/870) remains the only proposed code change. Existing worker/runbook ownership, integrator priorities and protected `main` are unchanged. No customer records, payments, claim filings, outreach, trades, subscriptions or user funds.

## Real independent test, with provenance

The prior #021 harness was COMMITTED BUT NOT EXECUTED, while the repository's four-lane Release Gate was green. Reading the [Release Gate workflow](https://github.com/P00NSMASHER/github-value-hunt-ledger/blob/main/.github/workflows/repository-release-gate.yml) proved that no hydrovac research files were covered by its required suite. Therefore prior green CI did **not** accept the 100-job integration.

A new dedicated, dependency-free Python unittest wrapper, [test_ti_golden_goose_hydrovac_integration_022.py](../../../../tests/test_ti_golden_goose_hydrovac_integration_022.py), executes three actual Node scripts from the existing required Technology Intelligence CI lane: the posted amount guard, the cohort bridge, and `test_100_job_python_to_js_021.js` with Python `summarize` actually invoked via subprocess. The script is read-only, uses the exact committed synthetic fixtures, and binds `PYTHON` to the test interpreter.

**Material first-run falsifier:** [release CI 40932074533](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/40932074533) exposed a real test defect, `AssertionError: 60 !== 59` at the prior unexecuted integration harness line 87. Its missing-proof mutation `sidecars.slice(1)` removed SYN-HV-001, which was ALREADY among the ten deliberately poisoned records. Correct behavior preserved 60 arithmetic clears rather than decreasing to 59. The original expected 59 falsely assumed the omitted row was clean. This is a **holdout selection bug, not evidence of an incorrectly cleared posted invoice**, and never involved real transactions.

Patched existing [test_100_job_python_to_js_021.js](test_100_job_python_to_js_021.js) without weakening guards: omitting clean SYN-HV-011 must now yield 59 arithmetic-only / 41 review, while omitting already-flagged SYN-HV-001 must preserve 60 / 40. Cohort mutations increase from four to five. Frozen base remains 100 jobs / 70 quantity-clean / 12 potential / 18 review, with ten separately seeded money exceptions. Final revised head must pass new CI before anyone asserts complete integration acceptance. **A passing general release check predating the new unittest is not sufficient.**

## Fresh direct competition: contract checks are not a moat

Read on 2026-10-29; each is a vendor's *own* statement, not observed efficacy, verified revenue, or an audited customer result:

- [FortressTicket](https://fortressticket.com/) advertises AI ticket-to-invoice reconciliation, duplicate protection and a 1,000-ticket free trial, then **$0.25 per ticket**.
- [InvoRec](https://invorec.com/) advertises line-by-line comparison with contracts or rate cards and a free invoice audit, making "check the signed rate" a direct advertised substitute.
- [Paveflow](https://paveflow.ai/) advertises contract-clause and rate-card validation with a free historical audit pilot, directly challenging the differentiation of a no-upfront second look. Its enterprise buyer is not identical to a small hydrovac contractor.
- [Overtrace](https://overtrace.ai/) advertises document-cited T&M review across signed field records, rate schedules, receipts and invoices for restoration/construction; scope and pricing differ but the claimed workflow overlaps.
- [Worcester's official 2026 vacuum-excavation bid](https://www.worcesterma.gov/finance/purchasing-bids/bids/cr-8693-j6) provides contract-pricing *comparison* evidence, not actual invoice errors or collectible accounts.

Quantitative **economic adversary, purely assumed**: a $100 fixed human report equals the advertised marginal price of 400 FortressTicket tickets at $0.25 each, excluding any trial, integration and non-equivalent service scope. With hypothetical $10 variable overhead and $35/h human review, contribution is `100-10-35h`: **+$20 at 2h**, **-$15 at 3h**, break-even `90/35=2.571h`. Ten paid $100 reports would gross $1,000, but no customers, paid reports, prices accepted by buyers or authentic incremental underbilling have been evidenced. The old $4,940 is explicitly *synthetic* raw variance. Municipal bid totals and class-action settlements are unrelated to our collectible revenue.

## Decision and next decisive test

- **NO-GO:** generic invoice matching SaaS or generic contract/rate-card audit as a supposedly rare edge. Existing visible substitutes are too close; vendor marketing is not a reason to infer customer conversion or a difference in actual accuracy.
- **WATCH ONLY:** an externally verifiable, post-incumbent cross-system exception review, conditional on proving *additional legally payable value* in independently permissioned historical records. Do not elevate above the existing RETALLY / integrator priorities without a blind benchmark and actual buyer evidence.
- **Next cheapest experiment:** complete this exact CI 100-job run, inspect the report, then scope a predeclared, blind 100-job comparison against an incumbent's own reconciliation, signed amendments, credits/voids and reviewer time **only after fresh explicit authorization and lawful access**. Stop if there is zero incremental verified collectible discrepancy or if a hypothetical $100 report takes >2.57 review hours.

**Commercial evidence status:** verified owner revenue **$0**; verified collectible **$0**; paid customers **0**; authorized real-world customer invoices **0**. No claim of final entitlement, competitive superiority, repeatable revenue or full CI acceptance until the final run is inspected.
