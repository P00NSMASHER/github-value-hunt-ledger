# Golden Goose candidate 004: PA nursing-home licensure notice delta

**Status: RESEARCH / NOT COMMERCIALLY VALIDATED.** This proof of concept stores *manually reviewed public administrative notice rows* and compares dated snapshots offline. It never logs in, scrapes, submits comments, obtains private documents, or contacts facilities. Realized revenue: **$0**.

## First-party observation: October 28, 2026

PA Department of Health public-review board: https://sais.health.pa.gov/CommonPOC/Licensing/IPA-NCF/PublicReviewFacList.aspx

- **One pending initial provider application** posted Oct 23: Chandler Hall Health Services (Bucks County).
- **Two approved applications** posted Sep 9: Ivory Nursing & Rehabilitation and Onyx Nursing & Rehabilitation (Montgomery County). The portal calls this section **"Approved or Denied for an Initial or Change of Ownership Nursing Home license"**. It does not differentiate the two statuses in the list. **Zero CHOWs can be confirmed from this snapshot alone.** An application is not a completed sale.
- 28 Pa. Code §201.12a(d) requires website notices of new-license or change-of-ownership applications and a ten-day public comment period: https://www.law.cornell.edu/regulations/pennsylvania/28-Pa-Code-SS-201-12a
- Federal CMS Skilled Nursing Facility CHOW series is published **quarterly** and its later files may backfill previous periods. Official metadata: https://catalog.data.gov/dataset/skilled-nursing-facility-change-of-ownership-2026-06-01 ; independent lag illustration: https://nursinghomechecker.com/reports/ownership-changes/ .

**Research hypothesis:** a versioned state-license application bulletin might provide earlier **administrative application signals** than quarterly CMS ownership records for vendors, staffing suppliers, or transaction analysts. It is **NOT YET PROVEN** that any *matched facility event* appears earlier. These records must not be described as confirmed acquisitions or sales.

## Competitive evidence and stop rules

- CMS ownership change tracking already exists at Nursing Home Checker: https://nursinghomechecker.com/reports/ownership-changes/
- A specialized Apify actor already reads CMS CHOW records: https://apify.com/jserle/snf-change-of-ownership-tracker
- No evidence yet of users willing to pay for a PA-specific bulletin. An initial application alone is not an ownership-transfer lead.
- **No fabricated TAM or earnings.** Illustrative, not a forecast: two purchasers at $50/month would be $100/month gross, whereas **zero paying purchasers currently equal $0**.
- Reject if a matched-event study does not show a meaningful lead time, the accessible notices are too sparse, or every foreseeable purchaser can get equally useful alerts free. Do not promote this over current value-hunt priorities based only on the snapshot.

## Run offline

```sh
cd research/golden_goose/pa_ncf_notices
python3 notice_watch.py pa_snapshot_2026-10-28.json
python3 -m unittest discover -s . -p 'test_notice_watch.py' -v
python3 notice_watch.py later_snapshot.json --previous pa_snapshot_2026-10-28.json
```

`NOT_ON_CURRENT_PAGE` means disappearance only, **not** closure, denial, transfer, or wrongdoing. Exact source URL and source category are mandatory. Duplicate, contradictory, future-dated, or unverified ownership-assertion inputs fail closed. A future notice collection method must comply with source terms and be explicitly versioned/validated.

### Local QA: completed

In ordinary local Python, **17/17 unit tests passed** on October 28, 2026, with a three-record manual snapshot. Scope: offline classification/delta logic only. No live HTTP integration, no production monitoring, no independent CI review, no real CHOW match and no paid customer.

### Next falsifiable experiment

Collect **at least 10 paired, independently dated facility events** across the state board and CMS CHOW release history. For each, verify actual application/transfer semantics, compare first observation timestamps, quantify true positive rate and the distribution of lead times, and preserve unmatched/ambiguous events. Then separately validate actual willingness-to-pay without unauthorized outreach. Any sign of weak lead-time advantage or source sparsity should demote or reject the candidate.

The first-$100 goal remains governed by **verified receipts**, not a projected fund, board count, or hypothetical subscriber.

Coordination: dedicated Golden Goose scratchpad issue #863; this is an unclaimed, isolated research branch and not a hunter lease, integrator promotion, or production deployment.
