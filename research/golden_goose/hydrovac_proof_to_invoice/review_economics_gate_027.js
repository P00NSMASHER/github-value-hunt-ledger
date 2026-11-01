/* Golden Goose #027: conservative, hypothetical unit-economics gate.
 * This is a mathematical scenario analyzer, not billing, revenue or payment proof.
 * Labor minutes and prices are assumed, not observed or price-validated.
 */
'use strict';
const own = (o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const fields=['jobs','held_jobs','reviewed_jobs','seconds_per_reviewed_job',
 'hypothetical_fee_cents','hypothetical_overhead_cents','hypothetical_labor_cents_per_hour'];
function invalid(reason){return {
  status:'INVALID_SCENARIO',reason,commercially_validated:false,
  audited_invoices:0,actual_buyers:0,observed_review_seconds:null,
  verified_collectible_cents:null,verified_owner_revenue_cents:0,
  billed_fee_cents:0,settlement_money_cents:0
};}
function assessReviewEconomics(s){
  if(!s||typeof s!=='object'||Array.isArray(s)||
     Object.keys(s).length!==fields.length||
     Object.keys(s).some(k=>!fields.includes(k))||
     fields.some(k=>!own(s,k)||!Number.isSafeInteger(s[k])))
    return invalid('STRICT_INTEGER_CENTS_AND_SECONDS_REQUIRED');
  if(s.jobs<1||s.jobs>10000||s.held_jobs<0||s.held_jobs>s.jobs||
     s.reviewed_jobs<0||s.reviewed_jobs>s.held_jobs||
     s.seconds_per_reviewed_job<0||s.seconds_per_reviewed_job>7200||
     s.hypothetical_fee_cents<0||s.hypothetical_fee_cents>1e9||
     s.hypothetical_overhead_cents<0||s.hypothetical_overhead_cents>1e9||
     s.hypothetical_labor_cents_per_hour<1||s.hypothetical_labor_cents_per_hour>1e7)
    return invalid('OUT_OF_RANGE_OR_INCONSISTENT_REVIEW_POPULATION');
  const seconds=s.reviewed_jobs*s.seconds_per_reviewed_job;
  // Round modeled labor to nearest cent; cents are NOT real paid costs.
  const labor=Math.round(seconds*s.hypothetical_labor_cents_per_hour/3600);
  const contribution=s.hypothetical_fee_cents-s.hypothetical_overhead_cents-labor;
  const available=s.hypothetical_fee_cents-s.hypothetical_overhead_cents;
  const breakEvenSeconds=available>=0?
    Math.floor(available*3600/s.hypothetical_labor_cents_per_hour):0;
  const unreviewed=s.held_jobs-s.reviewed_jobs;
  return {
    status:'SYNTHETIC_ECONOMICS_ONLY',
    completion:unreviewed>0?'UNREVIEWED_HELD_JOBS_REMAIN':'HYPOTHETICALLY_ALL_HELD_REVIEWED',
    reason:unreviewed>0?'INCOMPLETE_REVIEW_CANNOT_PRICE_AS_DELIVERED':
      'HYPOTHETICAL_COMPLETE_REVIEW_NOT_REAL_WORLD_VALIDATION',
    ...s,
    total_modeled_review_seconds:seconds,
    modeled_labor_cents:labor,
    modeled_contribution_cents:contribution,
    minimum_hypothetical_fee_to_cover_modeled_costs_cents:s.hypothetical_overhead_cents+labor,
    break_even_total_review_seconds:breakEvenSeconds,
    break_even_seconds_per_held_job:s.held_jobs>0?
      Number((breakEvenSeconds/s.held_jobs).toFixed(3)):null,
    unreviewed_held_jobs:unreviewed,
    commercial_go_no_go:unreviewed>0?'INCOMPLETE':contribution<0?'FAILS_ASSUMED_MARGIN':'MARGIN_POSSIBLE_IF_BUYER_PAYS',
    counts_as_completed_audit:false,
    illustrative_margin_is_collectible:false,
    vendor_head_to_head_performed:false,
    demand_observed:false,
    commercially_validated:false,
    audited_invoices:0,actual_buyers:0,observed_review_seconds:null,
    verified_collectible_cents:null,verified_owner_revenue_cents:0,
    billed_fee_cents:0,settlement_money_cents:0
  };
}
module.exports={assessReviewEconomics};
