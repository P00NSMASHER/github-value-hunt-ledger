/* Golden Goose #027: adversarial commercial gate for hypothetical hydrovac audit.
 * Independent fixed inputs; no customer data or invoice adjudication.
 * Run: node test_review_economics_gate_027.js
 */
'use strict';
const assert=require('node:assert/strict');
const {assessReviewEconomics:assess}=require('./review_economics_gate_027.js');
const base={jobs:100,held_jobs:100,reviewed_jobs:100,
 seconds_per_reviewed_job:300,hypothetical_fee_cents:10000,
 hypothetical_overhead_cents:1000,hypothetical_labor_cents_per_hour:3500};
let passed=0;
function test(label,patch,expected){
 const x=assess({...base,...patch});
 assert.equal(x.verified_collectible_cents,null,label);
 assert.equal(x.verified_owner_revenue_cents,0,label);
 assert.equal(x.audited_invoices,0,label);
 assert.equal(x.actual_buyers,0,label);
 assert.equal(x.commercially_validated,false,label);
 assert.equal(x.billed_fee_cents,0,label);
 if(x.status==='SYNTHETIC_ECONOMICS_ONLY'){
  assert.equal(x.counts_as_completed_audit,false,label);
  assert.equal(x.illustrative_margin_is_collectible,false,label);
  assert.equal(x.vendor_head_to_head_performed,false,label);
 }
 for(const [k,v]of Object.entries(expected))assert.deepEqual(x[k],v,label+':'+k);
 passed++;return x;
}
const full=test('100/100 held at assumed 5min',{}, {
 modeled_labor_cents:29167,modeled_contribution_cents:-20167,
 minimum_hypothetical_fee_to_cover_modeled_costs_cents:30167,
 break_even_seconds_per_held_job:92.57,
 unreviewed_held_jobs:0,commercial_go_no_go:'FAILS_ASSUMED_MARGIN'});
test('90 seconds per job narrow margin', {seconds_per_reviewed_job:90},{
 modeled_labor_cents:8750,modeled_contribution_cents:250,
 commercial_go_no_go:'MARGIN_POSSIBLE_IF_BUYER_PAYS'});
test('2-job triage cannot bill as completed 100-job audit', {reviewed_jobs:2},{
 unreviewed_held_jobs:98,modeled_labor_cents:583,
 modeled_contribution_cents:8417,commercial_go_no_go:'INCOMPLETE',
 reason:'INCOMPLETE_REVIEW_CANNOT_PRICE_AS_DELIVERED'});
test('no review, all held is incomplete', {reviewed_jobs:0},{
 unreviewed_held_jobs:100,commercial_go_no_go:'INCOMPLETE'});
test('100 at zero time is only hypothetical',{seconds_per_reviewed_job:0},{
 modeled_labor_cents:0,modeled_contribution_cents:9000,
 counts_as_completed_audit:false,commercially_validated:false});
test('50 held, 50 reviewed', {held_jobs:50,reviewed_jobs:50},{
 modeled_labor_cents:14583,modeled_contribution_cents:-5583,
 commercial_go_no_go:'FAILS_ASSUMED_MARGIN'});
test('zero held jobs cannot prove delivery', {held_jobs:0,reviewed_jobs:0},{
 break_even_seconds_per_held_job:null,counts_as_completed_audit:false});
test('small fee triggers negative margin', {hypothetical_fee_cents:2500},{
 modeled_contribution_cents:-27667,commercial_go_no_go:'FAILS_ASSUMED_MARGIN'});
test('fixed overhead above fee', {hypothetical_overhead_cents:11000},{
 break_even_total_review_seconds:0,commercial_go_no_go:'FAILS_ASSUMED_MARGIN'});
test('one second rounding', {jobs:1,held_jobs:1,reviewed_jobs:1,seconds_per_reviewed_job:1},{
 modeled_labor_cents:1,modeled_contribution_cents:8999});
test('invalid negative', {reviewed_jobs:-1},{status:'INVALID_SCENARIO'});
test('invalid reviewed greater than held', {reviewed_jobs:101},{status:'INVALID_SCENARIO'});
test('invalid float', {hypothetical_fee_cents:10000.5},{status:'INVALID_SCENARIO'});
test('invalid unknown trusted flag', {revenue_verified:true},{status:'INVALID_SCENARIO'});
test('invalid huge population', {jobs:10001},{status:'INVALID_SCENARIO'});
test('invalid fee type', {hypothetical_fee_cents:'10000'},{status:'INVALID_SCENARIO'});
assert.equal(passed,16);
// Supplier-marketing comparison only, not equivalent product prices or validated demand.
const advertisedPricePerTicketCents=25,advertised100TicketPriceCents=100*advertisedPricePerTicketCents;
assert.equal(advertised100TicketPriceCents,2500);
assert.equal(10000/advertisedPricePerTicketCents,400);
console.log(JSON.stringify({experiment:'Golden Goose 027 synthetic review economics',
 passed,cohort_jobs:100,hypothetical_fee_usd:'100.00',
 full_review_assumed_labor_usd:'291.67',
 full_review_assumed_contribution_usd:'-201.67',
 max_model_review_seconds_per_job:full.break_even_seconds_per_held_job,
 triage_only_unreviewed_held:98,
 vendor_advertised_price_per_ticket_usd:'0.25',
 vendor_price_comparison_not_like_for_like:true,
 owner_revenue_usd:'0.00',actual_customers:0,
 verified_collectible_usd:null,real_head_to_head_comparison:false,
 commercially_validated:false}));
