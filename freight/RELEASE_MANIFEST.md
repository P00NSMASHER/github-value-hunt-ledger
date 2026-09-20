# Freight Recovery v15.5 — Canonical Release Manifest

Release checkpoint: **v15.5-adaptive-authorization-commercial-learning-2026-09-20**

## Freight source identity

- Repository: `P00NSMASHER/github-value-hunt-ledger`
- Freight v15.5 merge commit: `93c4f3e2f0d50806e1e347e15e4170a0f8301d69`
- Adaptive-policy generated-state refresh: `6594c3d744e1f014542fc827ecad0052d34e6998`
- v15 commercialization PR: **#7**
- v15.1 machine-gates PR: **#8**
- v15.2 readiness/gap-control PR: **#10**
- v15.3 proof-derived reporting PR: **#11**
- v15.4 commercial-ops/outcome-learning PR: **#12**
- v15.5 adaptive-authorization/commercial-learning PR: **#17**
- Note: repository `main` continues to advance independently as hunters/integrators commit. The Freight merge commit above is the canonical v15.5 code checkpoint.

## Verified CI checkpoints

### Freight Commercial Contracts
- v15.5 PR-head run: `35523770428`
- Result: **success**
- Added coverage for:
  - buyer-cohort commercial calibration;
  - exclusion of synthetic/unverified outcomes;
  - one-buyer concentration not unlocking repricing;
  - minimum independent-buyer evidence before repricing review;
  - buyer-cohort conversion-rate intervals;
  - separation of engagement/revenue evidence from customer-value/recovery evidence;
  - engagement/buyer identity requirements for real commercial/value outcomes.

### Technology Intelligence System
- v15.5 PR-head run: `35523770174`
- Result: **success**
- Verifies:
  - domain-level search authorization is recomputed from the canonical Freight gap register;
  - generated adaptive policy cannot drift from that register;
  - blocked Freight-exclusive capabilities cannot leak into generic priority-capability gaps;
  - policy remains cautious/lag-aware and retains global exploration for other experiments.

## Live adaptive-policy state after merge

Generated policy evidence:
- measured prospective/benchmark runs: **9**
- valid structured outcomes: **1**
- exploration budget: **50%**
- Freight / EXP-001 search authorized: **no**
- Freight active search gaps: **none**
- Freight-exclusive capability gaps suppressed from generic priority output: **CAP-003, CAP-004, CAP-005**
- shared cross-domain capabilities remain globally usable: **CAP-001, CAP-006, CAP-007, CAP-016**

This closes a v15.4 control conflict: adaptive global gap scoring can no longer silently reopen generic Freight discovery while `freight/GAP_REGISTER.json` says no search is authorized.

## Current commercial control plane

- `freight/BUSINESS_MODEL.md` — ICP, offer ladder, fixed-fee economics and commercial-learning invariants.
- `freight/COMMERCIAL_QUALIFICATION.md` / `freight/deal_economics.py` — fixed-fee deal routing and analyst-hour budget.
- `freight/COMMERCIAL_LEARNING.md` / `freight/commercial_learning.py` — small-sample, buyer-level calibration.
- `freight/DATA_READINESS_DIAGNOSTIC.md` / `freight/readiness.py` — BLOCKED / CONDITIONAL / READY assessment.
- `freight/PILOT_PROTOCOL.md` — buyer-owned blind protocol.
- `freight/contracts.py` — frozen population/truth/incumbent/recovery proof objects.
- `freight/settlement_store.py` — durable exact-cents settlement attribution and reversal handling.
- `freight/pilot_reporting.py` / `freight/PILOT_REPORT_TEMPLATE.md` — proof-derived buyer metrics.
- `freight/outcome_adapter.py` / `freight/OUTCOME_RECORDING.md` — evidence-gated outcome capture.
- `freight/GAP_REGISTER.json` / `freight/gap_registry.py` — Freight research authorization.
- `intelligence/domain_search_policies.json` — binding from global adaptive policy to Freight gap authorization.
- `freight/COMPONENT_RIGHTS_REGISTRY.json` — rights-operability state.
- `freight/RELEASE_AND_SECURITY_GATE.md` — controlled-pilot vs annual-enterprise gates.
- `freight/ROADMAP.md` — value-maximization sequence.

## Commercial-learning state

The existing price bands and 50% fixed-fee gross-margin target remain **priors**, not learned market facts.

A repricing/scope review remains locked until there are at least:
- **5 unique buyer cohorts**;
- **5 paid engagements**; and
- usable fixed-fee margin evidence from **5 unique buyers**.

Additional rules:
- synthetic/internal records do not enter commercial calibration;
- direct external commercial evidence is required for paid-engagement/revenue/delivery metrics;
- direct external value evidence is separately required for positive customer value or realized recovery;
- every real engagement/value record requires a unique engagement ID and a pseudonymous buyer-cohort key;
- repeated engagements from one buyer are collapsed to buyer-level medians;
- diagnostic → pilot and pilot → annual conversion use buyer cohorts and Wilson 95% intervals;
- success-fee/recovery upside does not calibrate fixed-fee margin;
- calibration can recommend review but cannot change price automatically;
- unusually strong margins do not cause automatic discounts.

These thresholds are internal anti-overfit controls, not claimed industry benchmarks.

## Commercial state

Freight Recovery v15.5 is **commercially specified, machine-gated, internally rehearsed, settlement-persistence hardened, adaptive-search constrained and prepared to learn conservatively from real paid work; EXP-001 remains externally unproven**.

Current structured Freight evidence remains:
- directly evidenced Freight revenue in the structured outcome ledger: **$0**
- directly evidenced Freight customer value: **$0**
- paid diagnostic/pilot/annual conversion recorded: **none**
- Freight ACTIVE_SEARCH gaps: **0**

No v15.5 internal engineering result changes those external facts.

## Fixed-fee and money invariants

- diagnostic/pilot must be viable on fixed fee alone;
- target fixed-fee gross margin remains **>=50%** until sufficient real evidence supports review;
- expected recovery/success-fee upside cannot rescue an unprofitable fixed-fee engagement;
- discrepancy is not savings;
- validated is not realized;
- realized <= validated;
- fee-eligible <= realized;
- fee-eligible <= challenger-only validated;
- incumbent-known/automatic/preexisting credits are non-fee-eligible;
- ambiguous settlement remains $0 realized.

## Remaining value blockers

1. first authorized frozen buyer population through actual later settlement;
2. actual executed-rights documentation for hosted/SaaS/change-of-control questions where unresolved;
3. tenant/business-unit isolation evidence in the real pilot data service;
4. hostile-input/parser isolation in the real ingestion path;
5. reproducible production artifact/SBOM/signed provenance for annual deployment.

## Engineering / search freeze

Do not cut another Freight version for repository novelty alone.

Reopen Freight research/engineering only through:
- an explicitly activated mapped Freight search gap;
- an EXP-001/paying-customer named capability failure;
- a security or rights diligence blocker;
- a reproduced independent money-bearing disagreement;
- a measured reviewer bottleneck that can be reduced without increasing false-dollar risk.

The global adaptive policy cannot override this domain gate.

## Next canonical milestone

**Paid diagnostic/pilot → externally evidenced engagement outcome → frozen real population → challenger-only validated finding or defensible clean result → buyer-approved action → issued credit/refund/remittance → unambiguous realized settlement → buyer-cohort learning record → annual assurance conversion.**

That external chain is now the primary path to materially increasing Freight Recovery's defensible value.
