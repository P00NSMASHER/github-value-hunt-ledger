# Freight Recovery — Commercial Qualification

Updated: 2026-09-23

## Purpose

Keep the free audit low-friction for a good prospect without creating unlimited
manual work. Qualification decides the next operational step; it does not
promise that a discrepancy or recovery exists.

## Progressive sequence

1. Collect contact and company metadata.
2. Collect annual freight-spend and monthly-shipment bands, freight modes, and
   active-carrier count.
3. Collect available invoice history, approximate invoice count, record types,
   prior-audit status, and whether an issue is known or suspected.
4. Route the lead with `freight/lead_qualification.py`.
5. Review the routing decision and confirm a named buyer, records owner,
   supported mode, likely authority sources, and a safe intake route.
6. Define a bounded audit population and analyst budget before requesting data.
7. Issue the approved secure route or explain the missing prerequisite.

The public page does not accept file uploads. Do not request invoices,
credentials, rates, or payment records as ordinary email attachments.

## Internal routing states

| State | Default action |
|---|---|
| High-priority recovery candidate | Human review promptly; confirm data and scope before any conclusion |
| Qualified | Invite to a scoped secure intake when capacity is available |
| Needs review | Resolve the specific uncertainty before committing analyst time |
| Insufficient data | Request only the missing prerequisite or provide preparation guidance |
| Low expected recovery | Decline, defer, or offer a tightly bounded alternative without overstating value |

The thresholds are internal operating assumptions and should not be shown as a
customer score. Record the reason for a manual override.

## Minimum evidence before substantive work

- a real business and reachable work contact;
- a defined entity or business unit;
- a usable date range and invoice population;
- invoices plus at least one supporting authority/evidence source appropriate
  to the proposed checks;
- a records owner and decision owner;
- no obvious conflict with a prior auditor or active claim process;
- an approved data-handling route; and
- reserved analyst/reviewer capacity.

If those conditions are not met, provide a short readiness response rather than
performing open-ended forensic work.

## Economic screen

The free audit receives an explicit time and population budget. Estimate intake,
normalization, analyst review, independent review, customer support, and likely
recovery administration at fully loaded cost. Unpaid founder time is not free.

Use expected value conservatively: probability-adjusted, net of exclusions and
reversals, and never represented to the customer as a promised result. If
expected fee contribution cannot support responsible delivery, narrow the
sample, defer, decline, or propose a separately scoped fixed-fee forensic audit
when that genuinely fits the buyer's objective.

The contingency fee is calculated later from actual fee-eligible recovery. It
must not be charged on potential recovery or approved claim value.

## What to measure

- lead source and funnel stage dates;
- qualification state and override reason;
- time spent before secure intake;
- records requested and received;
- audit population, coverage, and analyst/reviewer hours;
- potential range and confidence at summary time;
- approved claim value;
- actual recovered funds and evidence date;
- fee-eligible recovered funds, reversals, and fee collected; and
- contribution by customer cohort.

Use these results to revise thresholds only after multiple independent buyer
cohorts. Do not tune the screen to a single unusually large recovery.
