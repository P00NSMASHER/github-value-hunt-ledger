# RETALLY Laboratory Intelligence v1: independent proof and actionable triage

**Scope:** isolated, read-only research implementation based on the cumulative findings of PR #279. **Not a product patch, production certification, deployed control room, or recovered customer money.** Historic defects remain OPEN_UNVERIFIED. No donor code is installed.

## What was inspected

- The canonical freight module directory on repository main, including existing \`freight/rating_engine.py\`, \`freight/payment_orchestration.py\`, \`freight/settlement_store.py\`, \`freight/deal_economics.py\`, \`freight/audit_ledger.py\`, and \`freight/backup_restore.py\`.
- Draft PRs #263 (rating), #264 (customer lifecycle), #271 (blind pilot), #272 (Labs 4–10), #273 (Labs 11–14), #275 (unified workbench), and #279 (findings and donors).
- PR #279's original 26 historical findings plus two standalone proof-gate bugs, including 11 shared failure clusters.
- The nine donor assessments and their exact revisions recorded under \`freight/research/HUNTED_CODE_REUSE_CANDIDATES.json\`.
- The original and hidden-bug forensic research findings, which explicitly limit conclusions to synthetic/offline testing.

**Access boundary:** The standalone multi-GB simulation archives and source-bearing portable lab bundles are not present in this repository branch. Hosted Floot/RecoveryOS behavior, customer source entitlements, real tariffs, actual remittances, signed contracts, staging API equivalence, and externally controlled blind gold were **not independently inspected or tested** in this change.

## 14-lab usefulness map

| Lab | Code presently represented | Most useful real-world question | Improvement needed |
| --- | --- | --- | --- |
| 1 Rating | PR #263 probes actual rating module with designed synthetic inputs | Can it correctly identify valid invoice discrepancies? | Buyer-controlled blind tariff truth, independent rate provenance |
| 2 Lifecycle | PR #264 tests actual payment-domain code, separate simulated customers | Does the workflow preserve customer trust through credit and fee events? | Verified lifecycle state/cost evidence and behavioral calibration |
| 3 Pilot | PR #271 covers blind-pilot acceptance methodology | Are recommendations independently correct? | Real approved holdouts and adjudicators |
| 4 Integration | PR #272 synthetic source and adapter checks | Are invoice source and ownership intact? | Immutable external source anchors and tenant-bound permissions |
| 5 Claims-to-cash | PR #272; existing settlement store | Can every credit, allocation, and reversal be explained? | Shared independent ledger comparison across labs |
| 6 Security | PR #272; existing security and audit modules | Does actual hosted tenant isolation hold? | Authenticated deployed staging negative tests |
| 7 Sales | PR #272 synthetic lead scenarios | Which qualified buyers are economical to serve? | Empirical funnel calibration and permissioned buyer outcomes |
| 8 Economics | PR #272; existing deal economics module | Is a deal profitable after labor and delayed collection? | Explicit signed negative net, uncertainty and fee authority |
| 9 Procurement | PR #272 supporting buyer readiness | Can buyer concerns be answered with evidence? | Buyer-verifiable audit/security receipts |
| 10 Freight research | PR #272 source-oriented research | Are billing/competitor rules authoritative and current? | Dated primary-source anchors and legal rate-term checks |
| 11 Reliability | PR #273 constructed resilience scenarios | Can the real service survive and restore after outages? | Actual staging load, clean restore and source census |
| 12 Fraud | PR #273 adversarial claims | Are erroneous claims caught without label leakage? | Protected gold and bidirectional scoring |
| 13 Savings | PR #273 modeled counterfactuals | Does an opportunity remain profitable including costs? | Real effort and signed downside, causal uncertainty |
| 14 Competitive evidence | PR #273 vendor evidence exercises | Are claims accurate enough for prospective buyers? | Trusted archival citations and independence rules |

Existing source code should be retained where its contract is sound. More synthetic rows are not a substitute for external buyer, bank or carrier evidence.

## New work in this draft

**1. \`freight/lab_intelligence.py\`: read-only independent synthetic consistency verifier.**

Accepts an *independently supplied* tenant/invoice/source manifest with explicit receipt capacities and pinned fee-term digest; does not accept the lab's own claimed totals as evidence. Replays the event stream by economic issue and checks allocation capacity *across cases*. Enforces no intake money, no cash above earned fees, no earned fees above recovered-and-unreversed credit, and exact reconstruction of four reported financial balances.

It explicitly labels a clean outcome \`PASS_SYNTHETIC_ONLY\`; even a clean manifest is not authenticated merely by being passed to this function.

**2. \`freight/lab_intelligence_runner.py\`: machine-readable executive triage.**

Uses the existing cumulative register to rank *currently unresolved* findings by severity, offline evidence, number of laboratory interfaces, reproduction availability and **explicit planning-only** estimated effort. Returns the original IDs, suggested next experiments, impacted labs and donor candidates. This is a transparent engineering heuristic, **not** an estimate of profit, dollars at risk or ROI. The register remains immutable to the runner.

**3. \`modeled_offer_value\`: signed fixed-fee business economics.**

Requires explicitly supplied collection probability, labor, and other expenses; reports signed expected net rather than flooring losses to zero. Demonstration: a fictional $100 fee with 50% collection probability, two analyst hours at $70/hour and $20 other costs produces **-$110 expected net**. This is an assumption-driven illustration, not evidence of customer demand.

**4. Read-only CI and exact reproduction tests.**

The independently exercised synthetic cases include positive controls, phantom intake money, rehashed summary inflation, altered source binding, unauthorized tenant, duplicated economic issue, duplicate receipt allocation across distinct issues, legitimate split allocations, unsupported fee terms, missing reversal source, reversal/refund accounting, outstanding receivables and duplicate events. A separate suite checks triage rank, non-mutation, historical count agreement, and invalid inputs.

Run:

\`\`\`bash
PYTHONPATH=. python -W error::ResourceWarning -m unittest -v freight.test_lab_intelligence freight.test_lab_intelligence_runner
PYTHONPATH=. python -m freight.lab_intelligence_runner --limit 10
\`\`\`

The first command operates only on synthetic in-memory objects. The second reads the PR #279 register and prints JSON without changing any file.

## Demonstrated *research* improvement loop

1. **Observe:** existing offline audit identified a phantom-cash semantic gap (LAB-P0-03).
2. **Reproduce an equivalent class of defect:** an INTAKE event that claims to post money is fed to the new checker.
3. **Reject:** the independent checker raises \`INTAKE_CANNOT_POST_MONEY\`.
4. **Positive control:** an independently bounded credit, accrual, and fee collection produces \`PASS_SYNTHETIC_ONLY\`.
5. **Adversarial expansion:** duplicate economic issues, split receipt over-allocation, unsupported terms and wrong source scope also fail.
6. **Document boundary:** this adds a **new research verifier**, not a repair of the original Unified Laboratory's \`StagingTwin.verify()\` or hosted RecoveryOS. LAB-P0-03 remains OPEN_UNVERIFIED.

No real carrier/bank source was contacted; independence of the *input authority* is a caller obligation until a protected source connector is introduced.

## Prioritized follow-on integration gates

1. **Proof gate consolidation:** Check in the original standalone proof CLI and frozen original 24-case fixtures after verifying their exact hashes. Compare this new verifier to it and to existing \`freight/settlement_store.py\`. Do not pretend this simplified replay is a production accounting engine.
2. **Repair the original lab verifier:** import the portable Unified Laboratory into an isolated dev branch or test harness; make the original LAB-P0-01/03, X-01, Y-02 reproductions fail before fixing, then verify exact-head remediation and regression. Update findings only after independent receipts.
3. **Event/proof contract v2:** add source-entitlement evidence, cryptographically anchored signed historical fee terms, currency/precision semantics, event timestamps, provider operation identity, gross-versus-net credit and complete credit-note bookkeeping. Reject source-provenance gaps rather than inventing external authority.
4. **Automated experiment ledger:** immutable run IDs, frozen configs, seed/fixture checksums, measured cost, discovered defect novelty, independent test verdicts, and artifact-bound approved repairs. Keep a limited queue of high-information experiments.
5. **Cross-lab event routing:** rating → lifecycle → claims/settlement → economics → buyer experience → reliability. Use adapters; preserve each lab's independent truth and avoid exposing gold labels to detectors.
6. **Private actual-code staging:** authenticated real RecoveryOS APIs, migrations and worker behavior with mocked external providers and cross-tenant negative tests. No production effects.
7. **Operator interface:** show real verified defects, actionable remediation, bounded evidence, stale/source gaps, and modeled business scenarios; never misleading PASS badges.

## Integration/donor guidance

Keep PayOps, TrustMesh, Canon, Effect Broker, FireDrill, in-toto, Minigraf, Microsoft BCApps, and Assay as pinned, license-reviewed **research candidates**. Prefer targeted source-comparison and small proofs. Direct Python integration requires independent API compatibility and dependency/license checks; TypeScript/Go/Rust/AL projects are mostly design references or external comparators. No donor code is incorporated here.

## Permanent guardrails

- Do not merge the old lab drafts merely because each has green CI.
- Do not close any of the 26 historical findings on the strength of these new unit tests.
- Do not present simulated revenue, recovery, customer behavior or savings as measured results.
- Keep all external payment, customer communication, production deployment and recurring task changes out of this work.
- The next meaningful milestone is a **failing-before and passing-after change to the actual defective laboratory code**, with independent source and monetary evidence retained.
