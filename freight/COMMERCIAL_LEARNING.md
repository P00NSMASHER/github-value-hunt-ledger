# Freight Recovery — Commercial Learning Policy

Updated: 2026-09-20

The commercial model may learn from paid work, but it must not overfit one buyer, one unusually easy population, or synthetic test data.

## Eligibility

A record may enter commercial calibration only when all are true:
- experiment is EXP-001;
- the record is not synthetic;
- direct external commercial evidence is explicitly recorded;
- engagement ID is present;
- pseudonymous buyer-cohort key is present;
- the record represents a paid diagnostic, paid pilot, annual conversion, or directly evidenced Freight revenue.

Internal demos, synthetic rehearsals, proposed prices, pipeline estimates and "potential savings" do not enter the calibration sample.

## Anti-overfit rule

The configurable contingency rate, free-audit qualification thresholds, and
delivery-cost assumptions remain priors. Optional fixed-fee forensic work is a
separate cohort.

A repricing/scope review is not unlocked until there are at least:
- **5 unique buyer cohorts**;
- **5 paid engagements**; and
- usable contribution evidence from **5 unique buyers**.

These are internal anti-overfit thresholds aligned with the technology-intelligence system's cautious small-sample policy. They are not claimed industry benchmarks.

Repeated engagements from one buyer are collapsed to buyer-level medians before overall margin/effort medians are calculated. This prevents a single large account from dominating the learning signal.

## What the calibrator may recommend

`freight/commercial_learning.py` can return:
- KEEP_PRIOR;
- REVIEW_RAISE_PRICE_OR_NARROW_SCOPE;
- PROTECT_MARGIN_NO_AUTOMATIC_DISCOUNT.

It never changes prices automatically.

Potential recovery never rescues free-audit economics. Only evidenced actual
recovery may enter realized contribution, and it remains separate from the cost
of audits that do not advance. Optional fixed-fee cohorts are calibrated
separately.

## Metrics learned

When direct evidence exists, preserve:
- commercial model and agreed contingency rate or optional fixed fee;
- delivery cost;
- reviewer hours;
- invoices reviewed;
- buyer-level gross margin;
- buyer-level hours per 100 invoices;
- diagnostic -> pilot conversion;
- pilot -> annual conversion;
- buyer concentration.

Conversion rates use buyer cohorts rather than raw engagements and include Wilson 95% intervals.

## Current state

Until enough real paid Freight outcomes exist, the correct calibration action is **KEEP_PRIOR**.
