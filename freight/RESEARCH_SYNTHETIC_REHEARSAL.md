# RETALLY Research Lab 14 — Mission 8: Synthetic Experimental Rehearsal

**Status: draft, unmerged, research-only, stacked on Mission 7 PR #368.** No 15th laboratory; no new scheduling, autonomous web capture, production API, real buyer recruitment, real invoices, competitor private information, carrier action, fee assessment or spending.

## Purpose

Missions 3–7 now provide evidence registers, an oppositional decision log and six detailed prospective study designs. These are research decisions, not observed real-world results. Before requesting buyer permissions or spending resources on studies, the lab needs to test whether its **instrument logic** handles adverse, inconvenient and ambiguous outcomes.

Mission 8 introduces a completely fictional, on-demand test suite: `freight/research/SYNTHETIC_REHEARSALS_20261010.json` plus `freight/research_rehearsal.py` and negative tests. The authors invented every fictional case specifically to challenge denominators. These fixtures are **not modeled on actual customers** or independent market evidence.

| Protocol | Invented counterexample | Computed metric, not a finding |
| --- | --- | --- |
| M7-01 blind audit adjudication | Unsupported positive alert, unresolved alert and missed true issue | Evidence-supported flagged alerts / **all** flagged alerts; recall and false negatives shown separately |
| M7-02 tariff/NMFC chronology | Engine applies a hypothetically future-effective rule to an earlier fictional shipment | Boundary decisions matching a separately calculated reference; explicitly flags retrospective leakage |
| M7-03 randomized fee comprehension | Incorrect answers and nonresponders retained in both arms | Correct answers / **all** fictional randomized units, including nonresponders |
| M7-04 reachable market | Nonresponse and unknown frame states retained | Qualified fictional accounts / **all** sampled fictional accounts; no TAM or extrapolation |
| M7-05 vendor comparison | Absent competitor test access alongside unequal tested coverage | Supported resolutions per **actually authorized fixture**; untested vendor cases separately flagged, never scored zero |
| M7-06 settlement economics | Fee reversed, expensive zero-recovery claims, carrier credits without fee cash | Exact cents collected minus refunds/costs over **all** initiated fictional cases |

### Important distinctions

- Any apparent vendor performance, price comprehension difference, market share, profit, claimed tariff applicability or audit-precision percentage applies **only to invented test records**. These ratios demonstrate arithmetic, not external statistical inference.
- Lab 14 preserves separate study status: **zero external studies**, **zero real respondents**, **zero independent customer observations**, **zero permissions granted**, **zero public claims authorized**.
- Scores from mismatched competitor coverage are not comparable even when the raw fractions are presented. Missing vendor access becomes `NOT_TESTED`, never a negative capability finding.
- Credits from carriers are excluded from RETALLY cash-fee revenue. Reversed and pending cases contribute costs and remain in the inception denominator.
- An unknown adjudication for an alerted invoice remains in its denominator; it cannot silently become a validated success.
- Fictional year-2030 rule dates were chosen explicitly as hypothetical timeline tests. They do **not** describe the effective date of any NMFC supplement or live carrier tariff.

## Reproducibility and integrity

The fixture validator is deliberately restrictive: exact known JSON keys, local `SIM-` IDs, only specific categorical states and bounded integer-cent values; any extra field such as customer identity, invoice number, raw document or live source causes a hold. Duplicates, missing comparator pairs, false approvals, real-source declarations, illegal states, floating-point money and unlicensed comparator results are rejected.

The validator connects all six exercises to the actual Mission 7 protocol registry and its held research decisions. Its JSON report includes deterministic SHA-256 integrity receipts; these establish only consistency of the locally stored fictional data. They do **not** certify the producer, attest to an external dataset, or confer authority to act.

Statistical claims remain blocked: these invented units are neither a probability sample nor survey participants. In particular, [AAPOR survey disclosure standards](https://aapor.org/standards-and-ethics/disclosure-standards/) distinguish probability and non-probability recruitment and require reporting methods, exact wording, frame coverage, missingness, and limitations. No margin of sampling error, p-value, confidence interval or real-world causal effect is computed from these cases.

### Commands (read-only, no network)

Run from repository root (Python 3.11 or later):

```bash
PYTHONPATH=. python -m pytest -q freight/test_research_rehearsal.py
PYTHONPATH=. python -m freight.research_rehearsal --as-of-date 2026-10-10 --out /tmp/retally-mission8
PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-control-center
```

Outputs: `synthetic_rehearsals.json` and `synthetic_rehearsals.html`, both clearly marked INVENTED TEST CASES. The existing Lab 14 director runs a separate mutated-input negative probe. Existing Research Intelligence CI checks fixture constraints and result arithmetic and uploads the two files to the original operator artifact bundle.

## What would make a real validation study possible?

A **separate authorization step**: approve an actual study preregistration, numeric thresholds, power/sample-size and independent adjudication procedure; secure consent, signed data rights, customer privacy/security review, contractual/legal authority and governed storage. No such approval or trial exists in this mission. Real study intake requires a new, independently reviewed source-admission path; the synthetic CLI does not accept arbitrary external JSON or scrape sources.

**DO NOT MERGE OR DEPLOY. The original 26 historical research findings remain open.**
