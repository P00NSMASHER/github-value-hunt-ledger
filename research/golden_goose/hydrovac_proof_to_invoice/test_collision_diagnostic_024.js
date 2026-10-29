/* Synthetic-only regressions. Run with node test_collision_diagnostic_024.js */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const bridgeAvailable=fs.existsSync(require('node:path').join(__dirname,'cohort_amount_bridge_019.js'));
const bridge=bridgeAvailable?require('./cohort_amount_bridge_019.js').bridge:null;
const {diagnoseInvoiceIdCollisions:diagnose}=require('./collision_diagnostic_024.js');
let passed=0;
const clone=x=>structuredClone(x);
function fixture(n=100){
 const rows=Array.from({length:n},(_,i)=>({job_id:'SYN-GG024-'+String(i+1).padStart(3,'0'),
  status:'CLEAR_RECONCILED',gross_variance_usd:'0.00',collectible_usd:null}));
 const q={total_jobs:n,rows,candidate_discrepancies:0,review_only:0,clear:n,
  illustrative_candidate_gross_usd:'0.00',verified_collectible_usd:null,
  verified_customer_revenue_usd:0};
 const posted=rows.map((r,i)=>({job_id:r.job_id,
  legacy_quantity_status:'CLEAR_RECONCILED',signed_rate_reviewed:true,
  rate_versions_reviewed:true,full_ledger_verified:true,credits_reviewed:true,
  discounts_reviewed:true,waivers_reviewed:true,no_dispute:true,
  job_identity_reviewed:true,has_credit_memo:false,has_waiver:false,
  has_unapplied_cash:false,approved_hours:'4.00',approved_dumps:'1.00',
  signed_hourly_usd:'175.00',signed_dump_usd:'180.00',ledger_total_usd:'880.00',
  posted:[{job_id:r.job_id,invoice_line_id:'SYN-INV-'+String(i+1).padStart(3,'0'),
   state:'ISSUED',hours_qty:'4.00',dumps_qty:'1.00',hourly_unit_usd:'175.00',
   dump_unit_usd:'180.00',hours_extended_usd:'700.00',dumps_extended_usd:'180.00',
   line_total_usd:'880.00'}]}));
 return {q,posted};
}
function invariant(name,o,expected){
 const got=diagnose(o.q,o.posted);
 assert.equal(got.cohort_clearance_allowed,false,name);
 assert.equal(got.complete_ledger_verified,false,name);
 assert.equal(got.global_bridge_review_unchanged,true,name);
 assert.equal(got.verified_collectible_usd,null,name);
 assert.equal(got.verified_owner_revenue_usd,'0.00',name);
 assert.equal(got.actual_customer_invoices_reviewed,0,name);
 for(const [k,v] of Object.entries(expected))assert.deepEqual(got[k],v,name+' '+k);
 passed++;return got;
}
const clean=fixture();
invariant('clean supplied ids',clean,{collision_scan:'COMPLETE_FOR_SUPPLIED_IDENTIFIERS',
 affected_job_ids:[],not_flagged_job_count:100,collision_groups:[]});
const single=fixture();single.posted[1].posted[0].invoice_line_id=single.posted[0].posted[0].invoice_line_id;
const global=bridgeAvailable?bridge(single.q,single.posted):null;
if(global){
 assert.equal(global.reason,'DUPLICATE_POSTED_LINE_ACROSS_COHORT');
 assert.equal(global.needs_review,100);assert.equal(global.arithmetic_only,0);
}
const one=invariant('two-job collision',single,{collision_scan:'COMPLETE_FOR_SUPPLIED_IDENTIFIERS',
 reason:'DUPLICATE_ID_LOCATED',affected_job_ids:[single.q.rows[0].job_id.toLowerCase(),single.q.rows[1].job_id.toLowerCase()],
 not_flagged_job_count:98});
assert.equal(one.collision_groups.length,1);
assert.equal(one.collision_groups[0].occurrence_count,2);
assert.equal(one.collision_groups[0].cross_job,true);
const alias=clone(single);alias.posted[1].posted[0].invoice_line_id='  SYN-inv-001  ';
invariant('whitespace and case alias',alias,{affected_job_ids:one.affected_job_ids,
 not_flagged_job_count:98});
const within=fixture();within.posted[0].posted.push(clone(within.posted[0].posted[0]));
const withinR=invariant('same-job duplicate line',within,{not_flagged_job_count:99});
assert.equal(withinR.collision_groups[0].cross_job,false);
const pair=clone(single);pair.posted[3].posted[0].invoice_line_id=pair.posted[2].posted[0].invoice_line_id;
invariant('two independent collision pairs',pair,{not_flagged_job_count:96,
 affected_job_ids:pair.q.rows.slice(0,4).map(r=>r.job_id.toLowerCase())});
const triple=clone(pair);triple.posted[4].posted[0].invoice_line_id=triple.posted[0].posted[0].invoice_line_id;
const tripleR=invariant('three-party collision',triple,{not_flagged_job_count:95});
assert.equal(tripleR.collision_groups[0].occurrence_count,3);
function malformed(name,mutate,reason){const f=fixture();mutate(f);invariant(name,f,{
 collision_scan:'INDETERMINATE',reason,not_flagged_job_count:null,
 affected_job_ids:[],collision_groups:[]});}
malformed('empty line identifier',o=>{o.posted[0].posted[0].invoice_line_id='  '},'MISSING_OR_MISATTRIBUTED_LINE_ID');
malformed('missing posted array',o=>{delete o.posted[0].posted},'MISSING_DUPLICATE_OR_FOREIGN_PROOF');
malformed('empty posted lines',o=>{o.posted[0].posted=[]},'MISSING_DUPLICATE_OR_FOREIGN_PROOF');
malformed('foreign proof',o=>{o.posted[0].job_id='SYN-OUTSIDER'},'MISSING_DUPLICATE_OR_FOREIGN_PROOF');
malformed('duplicate proof',o=>{o.posted[1].job_id=o.posted[0].job_id},'MISSING_DUPLICATE_OR_FOREIGN_PROOF');
malformed('missing proof',o=>{o.posted.pop()},'INCOMPLETE_PROOF_COVERAGE');
malformed('line assigned to another job',o=>{o.posted[1].posted[0].job_id=o.posted[0].job_id},'MISSING_OR_MISATTRIBUTED_LINE_ID');
malformed('duplicate quantity ID',o=>{o.q.rows[1].job_id=o.q.rows[0].job_id},'INVALID_OR_DUPLICATE_QUANTITY_JOB');
malformed('unmodelled summary credit',o=>{o.q.discount_usd='15.00'},'UNMODELED_SUMMARY_FIELD');
malformed('claimed collectible',o=>{o.q.verified_collectible_usd='100.00'},'UNSUPPORTED_MONETARY_ASSERTION');
malformed('claimed customer revenue',o=>{o.q.verified_customer_revenue_usd=100},'UNSUPPORTED_MONETARY_ASSERTION');
malformed('money on quantity row',o=>{o.q.rows[0].collectible_usd='100.00'},'INVALID_OR_DUPLICATE_QUANTITY_JOB');
const fiveMinuteReview=5,laborHourly=35,fee=100;
const hypotheticalGlobalCost=Number((100*fiveMinuteReview/60*laborHourly).toFixed(2));
const hypotheticalCollisionTriageCost=Number((2*fiveMinuteReview/60*laborHourly).toFixed(2));
assert.equal(hypotheticalGlobalCost,291.67);
assert.equal(hypotheticalCollisionTriageCost,5.83);
assert.ok(hypotheticalGlobalCost>fee);
console.log(JSON.stringify({test:'GG-024 diagnostic-only duplicate ID localization',
  passed,total:passed,synthetic_cases:100,duplicate_job_count:2,
  bridge_checked:bridgeAvailable,global_bridge_review:global?global.needs_review:null,
  diagnostic_not_flagged:98,
  hypothetical_global_review_cost_usd:hypotheticalGlobalCost,
  hypothetical_two_job_triage_cost_usd:hypotheticalCollisionTriageCost,
  actual_review_cost_usd:null,actual_customer_invoices_reviewed:0,
  verified_collectible_usd:null,verified_owner_revenue_usd:'0.00',
  release_ready:false,commercially_validated:false}));
