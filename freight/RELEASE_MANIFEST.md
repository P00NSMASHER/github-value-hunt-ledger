# Freight Recovery v15.4 — Canonical Release Manifest

Release checkpoint: **v15.4-commercial-ops-learning-2026-09-20**

## Freight source identity

- Repository: `P00NSMASHER/github-value-hunt-ledger`
- Freight v15.4 merge commit: `bd3745530b29bcf201a6ceb3f178c03057d9a025`
- v15 commercialization PR: **#7**
- v15.1 machine-gates PR: **#8**
- v15.2 readiness/gap-control PR: **#10**
- v15.3 proof-derived reporting PR: **#11**
- v15.4 commercial-ops/outcome-learning PR: **#12**
- Note: repository `main` may advance independently as other hunters/integrators commit. The Freight merge commit above is the canonical v15.4 code checkpoint.

## Verified CI checkpoint

### Freight Commercial Contracts
- v15.4 PR-head run: `35522536180`
- Result: **success**
- Covers the existing Freight proof/security/readiness suite plus:
  - persistent SQLite settlement attribution and concurrency/reversal controls;
  - fixed-fee diagnostic/pilot economics;
  - maximum analyst-hour budget at target margin;
  - no expected-recovery/success-fee input in qualification;
  - Freight→global outcome evidence rules;
  - synthetic commercial value/revenue rejection;
  - full synthetic readiness → qualification → blind proof → settlement → report rehearsal;
  - reconciliation between proof-derived reporting and the persistent settlement store.

## Current commercial control plane

- `freight/BUSINESS_MODEL.md` — ICP, offer ladder, pricing and fixed-fee margin discipline.
- `freight/COMMERCIAL_QUALIFICATION.md` — deal-routing and analyst-hour-budget policy.
- `freight/DATA_READINESS_DIAGNOSTIC.md` / `freight/readiness.py` — BLOCKED / CONDITIONAL / READY assessment.
- `freight/PILOT_PROTOCOL.md` — buyer-owned blind protocol.
- `freight/contracts.py` — frozen population/truth/incumbent/recovery proof objects.
- `freight/settlement_store.py` — durable exact-cents claim/event/allocation/counter-event reference store.
- `freight/pilot_reporting.py` / `freight/PILOT_REPORT_TEMPLATE.md` — proof-derived buyer financial and review metrics.
- `freight/deal_economics.py` — fixed-fee economics; success-fee upside excluded from qualification.
- `freight/GAP_REGISTER.json` / `freight/gap_registry.py` — research authorization.
- `freight/outcome_adapter.py` / `freight/OUTCOME_RECORDING.md` — evidence-gated feedback to the global technology-intelligence outcome loop.
- `freight/COMPONENT_RIGHTS_REGISTRY.json` — exact revisions / rights-operability state.
- `freight/RELEASE_AND_SECURITY_GATE.md` — controlled-pilot vs annual-enterprise gates.
- `freight/ROADMAP.md` — value-maximization sequence.

## Commercial state

Freight Recovery v15.4 is **commercially specified, machine-gated, internally rehearsed and settlement-persistence hardened; EXP-001 remains externally unproven**.

The structured learning ledger now contains one Freight **PARTIAL technical-only** outcome:
- directly evidenced revenue: **$0**
- directly evidenced customer value: **$0**
- paid diagnostic/pilot/annual conversion: **none recorded**

The repository intentionally authorizes **zero ACTIVE_SEARCH freight gaps**.

## Fixed-fee economics

Internal planning default until real paid delivery data exist:
- target fixed-fee gross margin: **>=50%**
- diagnostic/pilot must be viable on fixed fee alone
- success-fee or expected-recovery upside is **excluded** from qualification
- analyst-hour budget is calculated from fee, loaded hourly cost, other delivery costs and target margin
- if expected work exceeds budget: narrow scope, improve process, raise fixed fee or HOLD

This 50% target is an internal operating assumption, not a claimed industry benchmark; real paid outcomes should update it.

## Money semantics

Buyer-facing totals remain separate:
1. reviewed discrepancy;
2. validated finding;
3. challenger-only validated;
4. uniquely attributable realized;
5. fee-eligible realized.

Rules:
- discrepancy is not savings;
- validated is not realized;
- realized <= validated;
- fee-eligible <= realized;
- fee-eligible <= challenger-only validated;
- incumbent-known, automatic and preexisting credits are non-fee-eligible;
- ambiguous settlement remains $0 realized;
- persistent settlement events and counter-events are immutable/replay-safe reference evidence.

## Outcome-learning invariant

Synthetic rehearsals may improve technical confidence but **may not create revenue or customer value** in the global outcome ledger.

Positive commercial value requires direct external evidence plus:
- origin search-run attribution;
- contributing capability attribution;
- evidence location;
- actual paid engagement and/or buyer-controlled settlement proof.

## Remaining value blockers

1. first authorized frozen buyer population through actual later settlement;
2. actual executed-rights documentation for hosted/SaaS/change-of-control questions where unresolved;
3. tenant/business-unit isolation evidence in the real pilot data service;
4. hostile-input/parser isolation in the real ingestion path;
5. reproducible production artifact/SBOM/signed provenance for annual deployment.

## Engineering freeze

Do not cut another Freight version for repository novelty alone.

Reopen engineering only for:
- an EXP-001/paying-customer named capability gap;
- a security or rights diligence blocker;
- a reproduced independent money-bearing disagreement;
- a measured reviewer bottleneck that can be reduced without increasing false-dollar risk.

## Next canonical milestone

**Paid diagnostic/pilot → frozen real population → challenger-only validated finding → buyer-approved action → issued credit/refund/remittance → unambiguous realized settlement → outcome record with direct evidence → annual assurance conversion.**

That external milestone is now more valuable than additional unsponsored Freight architecture.
