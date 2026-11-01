/* Golden Goose #023: bounded synthetic cost-of-review falsifier.
 * Use the actual #019 bridge. No buyer records or collectibility inference.
 * node test_blast_radius_023.js
 */
'use strict';
const assert = require('node:assert/strict');
const {bridge} = require('./cohort_amount_bridge_019.js');
const COUNT = 100;
const summary = {
  total_jobs: COUNT,
  rows: Array.from({length:COUNT}, (_,i)=>({
    job_id:'SYN-GG023-'+String(i+1).padStart(3,'0'),
    status:'CLEAR_RECONCILED', gross_variance_usd:'0.00', collectible_usd:null
  })),
  candidate_discrepancies:0, review_only:0, clear:COUNT,
  illustrative_candidate_gross_usd:'0.00',
  verified_collectible_usd:null, verified_customer_revenue_usd:0
};
const proofs = summary.rows.map((r,i)=>({
  legacy_quantity_status:'CLEAR_RECONCILED',job_id:r.job_id,
  signed_rate_reviewed:true,rate_versions_reviewed:true,
  full_ledger_verified:true,credits_reviewed:true,discounts_reviewed:true,
  waivers_reviewed:true,no_dispute:true,job_identity_reviewed:true,
  has_credit_memo:false,has_waiver:false,has_unapplied_cash:false,
  approved_hours:'4.00',approved_dumps:'1.00',
  signed_hourly_usd:'175.00',signed_dump_usd:'180.00',
  ledger_total_usd:'880.00',
  posted:[{job_id:r.job_id,
    invoice_line_id:'SYN-INV-'+String(i+1).padStart(3,'0'),
    state:'ISSUED',hours_qty:'4.00',dumps_qty:'1.00',
    hourly_unit_usd:'175.00',dump_unit_usd:'180.00',
    hours_extended_usd:'700.00',dump_extended_usd:'180.00',
    line_total_usd:'880.00'}]
}));
const clean = bridge(summary,proofs);
assert.equal(clean.arithmetic_only,COUNT,'Synthetic arithmetic baseline changed');
assert.equal(clean.needs_review,0);
assert.equal(clean.verified_collectible_usd,null);
assert.equal(clean.verified_owner_revenue_usd,'0.00');
const collided = structuredClone(proofs);
collided[1].posted[0].invoice_line_id=collided[0].posted[0].invoice_line_id;
const withCollision = bridge(summary,collided);
assert.equal(withCollision.status,'REVIEW');
assert.equal(withCollision.reason,'DUPLICATE_POSTED_LINE_ACROSS_COHORT');
assert.equal(withCollision.arithmetic_only,0);
assert.equal(withCollision.needs_review,COUNT);
assert.equal(withCollision.verified_collectible_usd,null);
assert.equal(withCollision.verified_owner_revenue_usd,'0.00');
// A document-ID collision directly touches two jobs. Review of the other 98 is
// a conservative cohort-wide hold, not proof those 98 are billing errors.
const touched=2,otherHeld=COUNT-touched;
const minutesPerReview=5,hourlyLaborUsd=35,hypotheticalReportFeeUsd=100;
const excessMinutes=otherHeld*minutesPerReview;
const excessLaborUsd=Number((excessMinutes/60*hourlyLaborUsd).toFixed(2));
assert.equal(otherHeld,98);
assert.equal(excessMinutes,490);
assert.equal(excessLaborUsd,285.83);
assert.ok(excessLaborUsd>hypotheticalReportFeeUsd);
console.log(JSON.stringify({test:'GG-023 synthetic cohort review-amplification',
  cases:COUNT,unaffected_arithmetic_before:COUNT,
  duplicate_invoice_id_pairs:1,directly_touched_jobs:touched,
  cohort_review_after:withCollision.needs_review,
  other_jobs_conservatively_held:otherHeld,review_amplification_ratio:COUNT/touched,
  hypothetical_minutes_each:minutesPerReview,
  hypothetical_labor_usd_per_hour:hourlyLaborUsd,
  hypothetical_other_job_review_cost_usd:excessLaborUsd,
  hypothetical_fixed_report_fee_usd:hypotheticalReportFeeUsd,
  real_customer_invoices:0,observed_review_minutes:null,
  verified_collectible_usd:null,verified_owner_revenue_usd:'0.00',
  conclusion:'REVIEW_AMPLIFICATION_RISK_NOT_PROVEN_REAL_WORKLOAD'}));
