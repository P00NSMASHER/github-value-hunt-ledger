# Freight Recovery — Commercial Qualification

Updated: 2026-09-20

## Purpose

Prevent attractive recovery narratives from hiding bad delivery economics.

The engagement must work financially **before** any success fee or recovered dollar is assumed.

## Sequence

1. Run the Data Readiness gate.
2. Route READY buyers to the Blind Freight Audit Acceptance Test; others to the Data Readiness Diagnostic.
3. Enter the proposed fixed fee, loaded analyst cost, non-labor delivery cost and expected analyst hours into `freight/deal_economics.py`.
4. Require the fixed-fee gross margin target to pass.
5. Use the calculated maximum analyst hours as the delivery budget.
6. If the budget is exceeded, choose one:
   - narrow the population;
   - reduce unsupported/custom work;
   - raise fixed fee;
   - improve the repeatable process;
   - HOLD the deal.

Do **not** rescue the economics by assuming a recovery percentage or success fee.

## Default internal planning target

Until real paid pilots provide better evidence:
- target fixed-fee gross margin: **>=50%**;
- success fee: excluded from base qualification;
- initial ICP scale signal: about **$5M+ transportation spend OR 500+ invoices/month**;
- multiple carriers/accessorial complexity preferred.

These are operating assumptions to be updated from actual outcome data, not claims about universal market benchmarks.

## What to measure on every real engagement

- fixed fee contracted;
- analyst hours;
- loaded delivery cost;
- other delivery cost;
- gross profit and gross margin;
- invoices/shipments reviewed;
- reviewer touches/minutes;
- false-positive dollars;
- validated dollars;
- challenger-only validated dollars;
- realized recovery;
- fee-eligible realized recovery;
- days complete data → first finding;
- days complete data → final report;
- diagnostic → pilot conversion;
- pilot → annual conversion.

The goal is to learn which buyer/data profiles produce repeatable high-integrity work at attractive margins.
