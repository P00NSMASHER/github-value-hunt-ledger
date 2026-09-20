# Freight Recovery — Outcome Recording

Updated: 2026-09-20

Freight Recovery participates in the repository-wide empirical learning loop.

## Canonical destinations

Every real EXP-001 outcome should be recorded in:
1. root `OUTCOMES.md`; and
2. machine-readable `intelligence/outcomes.jsonl`.

Use the global outcome schema and `freight/outcome_adapter.py`.

## Evidence rule

A technical rehearsal, local benchmark or synthetic corpus may record a technical PARTIAL/PASSED result, but:

- synthetic revenue = forbidden;
- synthetic customer value = forbidden;
- inferred savings = forbidden;
- "potential recovery" = not customer value;
- a dispute submission is not realized recovery.

Positive revenue or customer value requires direct external evidence and must include:
- origin search-run IDs;
- contributing capability IDs;
- evidence location;
- actual paid diagnostic/pilot/annual amount where applicable;
- buyer-controlled settlement proof for realized recovery.

## Freight metrics to preserve

For each real engagement, record where available:
- diagnostic paid: yes/no;
- pilot paid: yes/no;
- annual converted: yes/no;
- revenue USD;
- realized recovery USD;
- customer value USD;
- reviewer hours;
- false-positive USD;
- technical result;
- commercial result;
- unexpected failure modes;
- search-policy consequence.

## Learning consequence

Examples:
- A component repeatedly used in paid pilots and settlement-proven findings should gain evidence weight.
- A search strategy that repeatedly produces capabilities never used by customer experiments should lose freight priority.
- A connector that reduces reviewer hours without increasing false-positive dollars can justify engineering investment.
- A component that creates unsupported dollars, rights friction or deployment burden should be demoted even if technically impressive.
- A paid diagnostic that repeatedly fails readiness for the same data reason should change qualification/data-request strategy before triggering more GitHub hunting.

Commercial reality—not repository novelty—is the target signal.


## Commercial evidence vs customer-value evidence

These are separate claims.

**External commercial evidence** can establish:
- a diagnostic/pilot/annual engagement occurred;
- fixed fee / recognized Freight revenue;
- delivery cost;
- reviewer hours and turnaround;
- invoice/shipment volume;
- diagnostic → pilot or pilot → annual conversion.

It requires a unique `engagement_id` and a pseudonymous `buyer_cohort_key`.

**External value evidence** is stricter. It is required before recording positive customer value or realized recovery. A paid engagement alone does not prove savings.

The buyer cohort key should be stable enough to recognize repeat engagements from the same buyer without placing a buyer's legal name in the learning ledger.

Commercial calibration uses only externally evidenced non-synthetic EXP-001 records and collapses repeated engagements to buyer-level medians. See `freight/COMMERCIAL_LEARNING.md`.
