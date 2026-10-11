# RETALLY Lab 14 — Mission 7: Falsifiable Business Validation

**Status:** research-only, draft, stacked on Mission 6 PR #367 and its unmerged ancestors. No merge, hosted deployment, automatic source fetch, customer contact, legal action, scheduled task, billing, or fee collection.

## Why

Missions 3–6 produced a reviewed public-source register, quote fidelity checks, six falsifiable oppositional decisions and a source refresh queue. None establishes actual RETALLY customer results, LTL error prevalence, market demand, independent vendor superiority or realized contribution. Mission 7 gives those **same six M4 decisions** measurable study designs and explicit gates to guard against the most common confirmation biases.

The module **does not execute any of these six external studies**. It validates a design registry and makes a research-only decision-review queue with preserved dependencies and zero real-world outcomes.

## Studies to prepare

| Protocol | Linked decision | Primary unit and metric | Mandatory contrary evidence |
| --- | --- | --- | --- |
| M7-01 | M4-01 independent pilot | Alert-level, independently substantiated precision | Unsupported positive alerts, missing authority, adjudicator disagreement |
| M7-02 | M4-02 rule chronology | Dated synthetic fixture, correct boundary treatment | Retroactive NMFC supplement, contract exception ignored |
| M7-03 | M4-03 pricing comprehension | Buyer respondent, correct total-fee interpretation | Misunderstanding, nonresponse, leading wording |
| M7-04 | M4-04 serviceable segment | Deduplicated shipper account, qualified/reachable proportion | Frame gaps, LTL mismatch, incumbent access/contract restrictions |
| M7-05 | M4-05 capability comparison | Licensed common fixture, fully supported correct resolution | False positives, bad OCR handling, unlicensed/missing rival access |
| M7-06 | M4-06 recovery economics | All initiated eligible cases, net realized contribution per case | Credit confused with cash, labor omission, reversals, survivor bias |

Every protocol explicitly names its sample frame, selection approach, comparator, numerator, denominator, zero-denominator treatment, independent reviewer, missingness policy, confounders, evidence requirements and stop rule. Numeric success thresholds and target sample sizes **must be reviewed and preregistered separately**; absent thresholds never count as an approval or experimental success.

**Caution:** alert precision is not the same as overall invoice accuracy, recall, positive cash recovery, or financial profitability. Market reachability in a convenience sample is not a nationally representative TAM. A synthetic tariff regression does not establish legal authority for a particular shipment. Missing competitor test access is NOT_TESTED, not a competitor failure. Pilot credit is not necessarily collected money.

## Data permissions and go/no-go

To become eligible for an external study, each protocol would need a separately approved prospective study plan and sample size; buyer consent and documented data rights when applicable; independent ground-truth assignment; permitted storage/retention, privacy/security clearance, and any required carrier/contract/legal review. Any result must maintain its full sample and missing-data denominator. Additional commercial, legal, privacy, security and financial controls would still apply independently.

Current research files deliberately record `preregistration_approved=false`, `threshold_approved=false`, `sample_size_target=null`, `observed_sample_count=0`, `independently_verified_outcomes=0`, and `protocol_execution_status=NOT_RUN`. They cannot be set to successful/approved inside this scope: the validator rejects such promotion.

No real invoice, buyer identifiers, customer response, competitor private code, carrier submission, contract signatures or bank information is stored in the protocol registry.

## Run offline

From repository root with Python 3.11+:

```bash
PYTHONPATH=. python -m pytest -q freight/test_research_validation_protocols.py
PYTHONPATH=. python -m freight.research_validation_protocols --as-of-date 2026-10-10 --out /tmp/retally-m7
# Artifacts: validation_protocols.json and validation_protocols.html
PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-control
```

The existing Lab 14 exercises the source-bound registry and negative-control mutation. The Control Center links the static report. The existing read-only research workflow runs offline tests and retains HTML/JSON artifacts without collecting new web or customer data. A SHA-256 report receipt checks deterministic in-repository data integrity, **not** external truth, third-party endorsement, or validation of an executed study.

## Research methods and source distinctions

- [AAPOR survey best practices](https://aapor.org/standards-and-ethics/best-practices/) inform sample frame disclosure, neutral questionnaires, pretesting, assignment transparency, missingness and nonresponse handling. These are methodological references, not an endorsement of RETALLY's drafts.
- [AAPOR disclosure standards](https://aapor.org/standards-and-ethics/disclosure-standards/) inform reporting denominators, sampling frame, method, weighting and limitations before any inference.
- [BTS 2022 Commodity Flow Survey](https://www.bts.gov/newsroom/commodity-flow-survey-2022-data-released) describes physical shipments and their value; shipment value is **not** an estimate of freight-audit addressable revenue, billing error incidence, eligible refunds, or realized RETALLY fees.
- Existing Mission 6 eCFR source and NMFTA issuance/effective-date distinction remain the authoritative *research citation objects* for legal/tariff chronology. Individual legal applicability and contractual authority remain unanswered.

## Independence and red-team acceptance

The tests deliberately reject: fake preregistration approval, study execution without evidence, made-up verified samples, nonzero invented outcomes, guessed numeric thresholds, missing denominator/zero-case treatment, sample-frame omission, fabricated external authority, duplicate or cross-bound opposition decisions, absent contrary evidence and unsafe HTML. A changed older public source can only add review debt, never automatically promote the study.

### What this does not claim

- No completed external customer experiment, pilot, survey, verified market forecast, A/B test, live product benchmark, independent audit certification, competitor superiority, profits or recovered dollars.
- No published public performance claim.
- No automated recruitment, competitor scraping, regulatory applicability decision, carrier contact, bank action or live data intake.
- The original 14 laboratory IDs and 26 historical open findings remain unchanged.

**Review-only / DO NOT MERGE OR DEPLOY.**
