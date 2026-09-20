# Cross-lane referral — CAP-009 temporal rule authority

Date: 2026-09-20  
From: HUNTER-13 / Revenue Leverage  
Primary lane: workforce scheduling / CAP-009  
Related lanes: payroll assurance, compliance proof, field/service scheduling

## Referral

**Payroll-Engine/PayrollEngine@`2ddb5c770b0a955936562355a1021f06e922886a` + PayrollEngine.Backend@`ecd049ee43a64c130981301192a0f8ab36eed1ed`** provide a strong reusable temporal authority pattern for the missing CAP-009 edge.

Verified runtime evidence: backend `GetDerivedRegulations.sql` filters rule versions on both creation/knowledge cutoff (`Created <= @createdBefore`) and effective date (`ValidFrom <= @regulationDate`) and selects the latest eligible version. The public test corpus contains exact-boundary `validFrom` fixtures and expected payrun results. Timesheet validation loads configured rule data at the actual work date and rejects work/break values outside that date-effective rule object.

This should not replace RosterSpec. Proposed combination:

`source-backed rule bundle -> temporal version selection -> compile selected invariants/outcomes -> RosterSpec hard-lock verify/repair -> evidence receipt`.

Required receipt fields: source identity, rule/version/hash, effective interval, knowledge/approval timestamp, worker/jurisdiction/contract scope, outcome type (`BLOCK|PREMIUM_PAY|REVIEW|ALLOW`), schedule hash, verifier/solver version, verdict, repair delta.

## Negative control

`JayySap/ShiftGaurd@acef23ab97b216c25f58f136443c899fe623c615` demonstrates why this matters. It hard-codes B.C.-labeled rest/break settings with no authority/version provenance; approximates 32-hour weekly rest using only total weekly hours; adds paid coffee-break behavior not required by current general B.C. Employment Standards guidance; and persists violating DRAFT shifts while its scheduler test merely prints a warning and exits successfully. A 7-day × 8-hour schedule (56h, only 16h gaps) passes its weekly-rest heuristic despite lacking a 32-consecutive-hour free interval.

## Exact unanswered technical question

Can a RosterSpec-style verifier consume a frozen, source-backed, effective-dated labor/contract rule bundle and reproduce historical PASS/FAIL/REVIEW plus minimum-disruption repair deterministically across mid-period rule changes, exemptions and alternative economic consequences such as premium-pay-in-lieu-of-rest, without consulting mutable current settings?

Full evidence: `hunters/32-run11-2026-09-20.md`.
