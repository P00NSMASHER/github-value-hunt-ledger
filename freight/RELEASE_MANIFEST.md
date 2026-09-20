# Freight Recovery v15.3 — Canonical Release Manifest

Release checkpoint: **v15.3-commercialization-2026-09-20**

## Source identity

- Repository: `P00NSMASHER/github-value-hunt-ledger`
- Current merged source commit: `36d0bacd29ce7e7c55d583189b9fac608e667a26`
- v15 commercialization PR: **#7**
- v15.1 machine-gates PR: **#8**
- v15.2 readiness/gap-control PR: **#10**
- v15.3 proof-derived reporting PR: **#11**

## Verified CI checkpoints

### Research/hunter model contracts
- v15.2 PR-head run: `35518475666`
- Result: **success**
- Covers deterministic hunter/model production-contract tests including the EXP-001 freight work gate.

### Freight commercial contracts
- v15.3 PR-head run: `35518677018`
- Result: **success**
- Covers:
  - frozen population/truth/incumbent ordering;
  - authority identity binding;
  - REVIEW = $0 validated;
  - same-dollar finding identity preservation;
  - settlement deduplication and partial caps;
  - recovery-certificate binding;
  - component-rights pilot gate;
  - canonical gap-register validity;
  - machine-scored readiness;
  - proof-derived pilot reporting;
  - automatic incumbent-known exclusion from fee eligibility.

## Current commercial control plane

- `freight/BUSINESS_MODEL.md` — ICP, offer ladder, pricing, stop rules.
- `freight/DATA_READINESS_DIAGNOSTIC.md` — $5k–$7.5k first-offer delivery specification.
- `freight/readiness.py` — BLOCKED / CONDITIONAL / READY machine assessment.
- `freight/PILOT_PROTOCOL.md` — buyer-owned blind protocol.
- `freight/contracts.py` — deterministic population/truth/incumbent/settlement proof objects.
- `freight/pilot_reporting.py` — proof-derived pilot financial and review metrics.
- `freight/PILOT_REPORT_TEMPLATE.md` — buyer-facing result structure.
- `freight/COMPONENT_RIGHTS_REGISTRY.json` — exact revisions / rights-operability state.
- `freight/RELEASE_AND_SECURITY_GATE.md` — controlled-pilot vs annual-enterprise gates.
- `freight/GAP_REGISTER.json` — canonical freight gap state.
- `freight/gap_registry.py` — research authorization from registered gaps.
- `freight/ROADMAP.md` — value-maximization sequence.

## Commercial state

Freight Recovery v15.3 is **commercially specified, machine-gated, and internally diligence-hardened; EXP-001 remains BLOCKED_EXTERNAL**.

The repository currently authorizes **zero ACTIVE_SEARCH freight gaps**. This is deliberate.

Remaining high-value blockers are not generic GitHub-discovery problems:
1. first authorized frozen buyer population through later settlement;
2. actual executed-rights documentation for hosted/SaaS/change-of-control questions where still unknown;
3. tenant/business-unit isolation proof in the real pilot data service;
4. hostile-input/parser isolation in the real ingestion path;
5. reproducible production artifact/SBOM/signed provenance for annual deployment.

## Money semantics now enforced

Buyer-facing reporting separates:
1. **reviewed discrepancy dollars**;
2. **validated finding dollars**;
3. **challenger-only validated dollars**;
4. **uniquely attributable realized dollars**.

A separate **fee-eligible realized** field is derived for commercial billing.

Rules:
- discrepancy is not savings;
- validated is not realized;
- realized cannot exceed validated;
- fee-eligible cannot exceed realized;
- fee-eligible cannot exceed challenger-only validated;
- incumbent-known findings are automatically non-fee-eligible when the ledger is bound to the frozen incumbent output;
- automatic/preexisting credits remain non-fee-eligible;
- ambiguous settlement allocation remains $0 realized.

## Current offer ladder

1. **$5k–$7.5k** Data Readiness / Authority Diagnostic.
2. **$15k–$25k** Blind Freight Audit Acceptance Test.
3. **15–20%** only on uniquely attributable realized credit/refund/cash.
4. After customer proof: initial **$60k–$150k annual assurance**, larger multi-BU **$150k–$300k+** depending on scope/integrations.

## Engineering freeze

Do **not** cut a new freight version merely because another technically interesting repository appears.

Internal freight engineering reopens only when one of these occurs:
- EXP-001 begins and exposes a concrete missing capability;
- a paying customer exposes a required integration/authority/settlement gap;
- a security or rights diligence blocker requires remediation;
- an independent falsifier reproduces a money-bearing disagreement;
- a measured reviewer bottleneck can be reduced without raising false-dollar risk.

Otherwise the correct next action is commercial validation, not more freight architecture.

## Next canonical milestone

**Paid blind pilot -> unique incumbent miss -> buyer-approved action -> issued credit/refund/remittance -> unambiguous settlement -> recovery certificate -> annual assurance conversion.**

That milestone, not another internal subsystem, is the next event expected to materially increase the business's defensible value.
