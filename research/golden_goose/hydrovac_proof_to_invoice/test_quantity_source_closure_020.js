/* Golden Goose #020: frozen, entirely synthetic upstream-provenance bridge holdout.
 * No customer files; never claims dollars owed, recoverable or earned.
 * Run: node test_quantity_source_closure_020.js
 */
'use strict';
const {bridge}=require('./cohort_amount_bridge_019.js');
function base(){
  const q={total_jobs:1,rows:[{job_id:'SYN-1',status:'CLEAR_RECONCILED',
    gross_variance_usd:'0.00',collectible_usd:null}],
    verified_customer_revenue_usd:0,verified_collectible_usd:null};
  const p={legacy_quantity_status:'CLEAR_RECONCILED',job_id:'SYN-1',
    signed_rate_reviewed:true,rate_versions_reviewed:true,
    full_ledger_verified:true,credits_reviewed:true,
    discounts_reviewed:true,waivers_reviewed:true,
    no_dispute:true,job_identity_reviewed:true,
    has_credit_memo:false,has_waiver:false,has_unapplied_cash:false,
    approved_hours:'4.00',approved_dumps:'1.00',
    signed_hourly_usd:'175.00',signed_dump_usd:'180.00',
    ledger_total_usd:'880.00',
    posted:[{job_id:'SYN-1',invoice_line_id:'INV-1',
      state:'ISSUED',hours_qty:'4.00',dumps_qty:'1.00',
      hourly_unit_usd:'175.00',dump_unit_usd:'180.00',
      hours_extended_usd:'700.00',dump_extended_usd:'180.00',
      line_total_usd:'880.00'}]};
  return {q,p:[p]};
}
const mutations=[
  ['hidden_waiver',o=>o.q.rows[0].waiver=true],
  ['hidden_job_discount',o=>o.q.rows[0].discount_usd='100.00'],
  ['hidden_credit',o=>o.q.rows[0].credit_memo_id='CREDIT-X'],
  ['hidden_payment',o=>o.q.rows[0].payment_total_usd='870.00'],
  ['hidden_summary_credit',o=>o.q.credit_memo_usd='100.00'],
  ['hidden_summary_revenue',o=>o.q.owner_revenue_usd='100.00'],
  ['misstated_clear_count',o=>o.q.clear=0],
  ['misstated_candidate_count',o=>o.q.candidate_discrepancies=1],
  ['misstated_review_count',o=>o.q.review_only=1],
  ['fake_total_gross',o=>o.q.illustrative_candidate_gross_usd='9999.00'],
  ['malformed_gross',o=>o.q.illustrative_candidate_gross_usd='bogus'],
  ['clear_with_gross',o=>o.q.rows[0].gross_variance_usd='100.00'],
  ['invalid_row_null',o=>o.q.rows[0]=null],
  ['invalid_row_string',o=>o.q.rows[0]='x'],
  ['invalid_row_status',o=>o.q.rows[0].status='PAID'],
  ['invalid_row_collectible',o=>o.q.rows[0].collectible_usd='100.00'],
  ['negative_variance',o=>o.q.rows[0].gross_variance_usd='-100.00'],
  ['review_with_gross',o=>{o.q.rows[0].status='REVIEW_RATE_AUTHORITY';o.q.rows[0].gross_variance_usd='100.00';}]
];
function runHoldout(){
  let pass=0;
  for(const [name,mutate] of mutations){
    const o=base();mutate(o);
    const got=bridge(o.q,o.p);
    if(got.status!=='REVIEW'||got.arithmetic_only!==0||
       got.verified_collectible_usd!==null||
       got.verified_owner_revenue_usd!=='0.00'||
       got.actual_customer_invoices_reviewed!==0)
      throw Error(name+' unexpectedly accepted: '+JSON.stringify(got));
    pass++;
  }
  const full=base();
  Object.assign(full.q,{candidate_discrepancies:0,review_only:0,clear:1,
    illustrative_candidate_gross_usd:'0.00'});
  const valid=bridge(full.q,full.p);
  if(valid.status!=='SYNTHETIC_ARITHMETIC_ONLY'||valid.arithmetic_only!==1||
     valid.verified_owner_revenue_usd!=='0.00')
    throw Error('native-format arithmetic-only control did not pass');
  pass++;
  const c=base();
  Object.assign(c.q,{candidate_discrepancies:1,review_only:0,clear:0,
    illustrative_candidate_gross_usd:'60.00'});
  c.q.rows[0].status='POTENTIAL_HOURS_GAP';
  c.q.rows[0].gross_variance_usd='60.00';
  const candidate=bridge(c.q,c.p);
  if(candidate.status!=='REVIEW'||candidate.verified_owner_revenue_usd!=='0.00')
    throw Error('synthetic candidate converted to invoice proof');
  pass++;
  return {passed:pass,total:mutations.length+2,refused:mutations.length+1,
    arithmetic_only_controls:1,real_customer_invoices:0,
    verified_owner_revenue_usd:'0.00'};
}
if(typeof module!=='undefined'&&module.exports){
  module.exports={runHoldout};
  if(require.main===module)console.log(JSON.stringify(runHoldout()));
}
