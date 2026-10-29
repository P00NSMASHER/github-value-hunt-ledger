/* Golden Goose #019: Python quantity summary -> posted amount guard bridge.
 * SYNTHETIC / READ-ONLY ONLY. No receivable, payment, or claim authority.
 * Source check: https://www.acquisition.gov/far/subpart-32.9
 */
'use strict';
const {postedAmountGuard}=require('./posted_amount_guard_018.js');
const norm=x=>typeof x==='string'&&x.trim()?x.trim().toLowerCase():null;
const row=(id,status,reason)=>({job_id:id,status,reason,collectible_usd:null,
  verified_owner_revenue_usd:'0.00',actual_customer_invoices_reviewed:0});
function fail(rows,reason){
  return {status:'REVIEW',reason,rows:rows.map(x=>row(x&&x.job_id||'UNKNOWN','REVIEW',reason)),
    arithmetic_only:0,needs_review:rows.length,verified_collectible_usd:null,
    verified_owner_revenue_usd:'0.00',actual_customer_invoices_reviewed:0};
}
function bridge(quantitySummary,postedProofRows){
  const rows=quantitySummary&&Array.isArray(quantitySummary.rows)?quantitySummary.rows:[];
  if (!quantitySummary||!Array.isArray(quantitySummary.rows)||
      !Array.isArray(postedProofRows)||!Number.isSafeInteger(quantitySummary.total_jobs)||
      !rows.length||quantitySummary.total_jobs!==rows.length)
    return fail(rows,'INCOMPLETE_COHORT');
  // User-provided data and signed-rate flags are NOT independently authenticated.
  if(quantitySummary.verified_customer_revenue_usd!==0||
     quantitySummary.verified_collectible_usd!==null)
    return fail(rows,'UNSUPPORTED_MONEY_ASSERTION');
  // Close the upstream quantity-summary trust boundary before accepting even
  // a synthetic arithmetic-clear label. The Python summary has a fixed shape:
  // unknown money/adjustment fields or contradictory aggregate counters must
  // NOT be silently discarded during the JS bridge.
  const summaryKeys=new Set(['total_jobs','rows','candidate_discrepancies',
    'review_only','clear','illustrative_candidate_gross_usd',
    'verified_collectible_usd','verified_customer_revenue_usd']);
  const rowKeys=new Set(['job_id','status','gross_variance_usd','collectible_usd']);
  const amount=/^(?:0|[1-9][0-9]*)\.[0-9]{2}$/;
  if(Object.keys(quantitySummary).some(k=>!summaryKeys.has(k)))
    return fail(rows,'UNMODELED_QUANTITY_SUMMARY_FIELD');
  let candidateCount=0,reviewCount=0,clearCount=0,grossCents=0n;
  for(const r of rows){
    if(!r||typeof r!=='object'||Array.isArray(r)||
       Object.keys(r).some(k=>!rowKeys.has(k))||
       typeof r.job_id!=='string'||!r.job_id.trim()||
       typeof r.status!=='string'||!amount.test(r.gross_variance_usd)||
       r.collectible_usd!==null)
      return fail(rows,'UNMODELED_OR_INVALID_QUANTITY_ROW');
    if(r.status==='CLEAR_RECONCILED'){
      clearCount++;
      if(r.gross_variance_usd!=='0.00')
        return fail(rows,'CONTRADICTORY_QUANTITY_CLEAR');
    }else if(r.status.startsWith('REVIEW_')){
      reviewCount++;
      if(r.gross_variance_usd!=='0.00')
        return fail(rows,'CONTRADICTORY_QUANTITY_REVIEW');
    }else if(r.status.startsWith('POTENTIAL_')){
      candidateCount++;
      grossCents+=BigInt(r.gross_variance_usd.replace('.',''));
    }else return fail(rows,'UNKNOWN_QUANTITY_STATUS');
  }
  for(const [key,want] of [['candidate_discrepancies',candidateCount],
                            ['review_only',reviewCount],['clear',clearCount]])
    if(Object.prototype.hasOwnProperty.call(quantitySummary,key)&&quantitySummary[key]!==want)
      return fail(rows,'CONTRADICTORY_QUANTITY_SUMMARY_COUNTER');
  if(Object.prototype.hasOwnProperty.call(quantitySummary,'illustrative_candidate_gross_usd')){
    const provided=quantitySummary.illustrative_candidate_gross_usd;
    if(!amount.test(provided)||BigInt(provided.replace('.',''))!==grossCents)
      return fail(rows,'CONTRADICTORY_QUANTITY_GROSS');
  }
  const ids=new Set(),proofIds=new Set(),lineIds=new Set(),proofs=new Map();
  for(const r of rows){
    const id=norm(r&&r.job_id);
    if(!id||ids.has(id)||r.collectible_usd!==null)
      return fail(rows,'QUANTITY_ID_COLLISION_OR_MONEY_ASSERTION');
    ids.add(id);
  }
  for(const p of postedProofRows){
    const id=norm(p&&p.job_id);
    if(!id||proofIds.has(id)||!ids.has(id))
      return fail(rows,'DUPLICATE_OR_FOREIGN_PROOF');
    proofIds.add(id);proofs.set(id,p);
    if(!Array.isArray(p.posted))continue; // Sidecar reviews missing ledger.
    for(const l of p.posted){
      const line=norm(l&&l.invoice_line_id);
      if(!line||lineIds.has(line))
        return fail(rows,'DUPLICATE_POSTED_LINE_ACROSS_COHORT');
      lineIds.add(line);
    }
  }
  const results=rows.map(r=>{
    if(r.status!=='CLEAR_RECONCILED')
      return row(r.job_id,'REVIEW','QUANTITY_EXCEPTION_OR_REVIEW_NOT_MONEY');
    if(r.gross_variance_usd!=='0.00')
      return row(r.job_id,'REVIEW','CONTRADICTORY_QUANTITY_CLEAR');
    const p=proofs.get(norm(r.job_id));
    if(!p)return row(r.job_id,'REVIEW','MISSING_POSTED_AMOUNT_PROOF');
    if(p.legacy_quantity_status!==r.status)
      return row(r.job_id,'REVIEW','LEGACY_STATUS_MISMATCH');
    const checked=postedAmountGuard(p);
    return row(r.job_id,checked.status==='SYNTHETIC_ARITHMETIC_ONLY'?
      'SYNTHETIC_ARITHMETIC_ONLY':'REVIEW',checked.reason);
  });
  const n=results.filter(r=>r.status==='SYNTHETIC_ARITHMETIC_ONLY').length;
  return {status:n===results.length?'SYNTHETIC_ARITHMETIC_ONLY':'REVIEW',
    reason:'SYNTHETIC_ARITHMETIC_NOT_A_RECEIVABLE',
    rows:results,arithmetic_only:n,needs_review:results.length-n,
    verified_collectible_usd:null,verified_owner_revenue_usd:'0.00',
    actual_customer_invoices_reviewed:0};
}
function holdout(){
  const base=()=>{
    const q={total_jobs:1,rows:[{job_id:'SYN-1',status:'CLEAR_RECONCILED',
      gross_variance_usd:'0.00',collectible_usd:null}],
      verified_customer_revenue_usd:0,verified_collectible_usd:null};
    const p={legacy_quantity_status:'CLEAR_RECONCILED',job_id:'SYN-1',
      signed_rate_reviewed:true,rate_versions_reviewed:true,full_ledger_verified:true,
      credits_reviewed:true,discounts_reviewed:true,waivers_reviewed:true,
      no_dispute:true,job_identity_reviewed:true,has_credit_memo:false,
      has_waiver:false,has_unapplied_cash:false,approved_hours:'4.00',
      approved_dumps:'1.00',signed_hourly_usd:'175.00',signed_dump_usd:'180.00',
      ledger_total_usd:'880.00',posted:[{job_id:'SYN-1',
        invoice_line_id:'INV-1',state:'ISSUED',hours_qty:'4.00',
        dumps_qty:'1.00',hourly_unit_usd:'175.00',dump_unit_usd:'180.00',
        hours_extended_usd:'700.00',dump_extended_usd:'180.00',
        line_total_usd:'880.00'}]};
    return {q,p:[p]};
  };
  const addSecond=o=>{
    const q=JSON.parse(JSON.stringify(o.q.rows[0]));q.job_id='SYN-2';
    o.q.rows.push(q);o.q.total_jobs=2;
    const p=JSON.parse(JSON.stringify(o.p[0]));
    p.job_id='SYN-2';p.posted[0].job_id='SYN-2';
    p.posted[0].invoice_line_id='INV-2';o.p.push(p);
  };
  const cases=[
    ['valid_one',()=>{},1],['valid_two',addSecond,2],
    ['out_of_order',o=>{addSecond(o);o.p.reverse()},2],
    ['no_proof',o=>{o.p=[]},0],
    ['foreign_proof',o=>{o.p[0].job_id='SYN-9'},0],
    ['duplicate_proof',o=>{o.p.push(o.p[0])},0],
    ['duplicate_quantity',o=>{o.q.rows.push({...o.q.rows[0]});o.q.total_jobs=2},0],
    ['cross_job_line',o=>{addSecond(o);o.p[1].posted[0].invoice_line_id='INV-1'},0],
    ['no_posted_line',o=>{o.p[0].posted=[]},0],
    ['bad_rate',o=>{o.p[0].posted[0].hourly_unit_usd='160.00'},0],
    ['bad_extended',o=>{o.p[0].posted[0].hours_extended_usd='699.00'},0],
    ['bad_total',o=>{o.p[0].ledger_total_usd='875.00'},0],
    ['credit',o=>{o.p[0].has_credit_memo=true},0],
    ['discount_unreviewed',o=>{o.p[0].discounts_reviewed=false},0],
    ['waiver',o=>{o.p[0].has_waiver=true},0],
    ['unapplied_cash',o=>{o.p[0].has_unapplied_cash=true},0],
    ['quantity_gap',o=>{o.q.rows[0].status='POTENTIAL_HOURS_GAP'},0],
    ['quantity_review',o=>{o.q.rows[0].status='REVIEW_RATE_AUTHORITY'},0],
    ['status_spoof',o=>{o.p[0].legacy_quantity_status='POTENTIAL_HOURS_GAP'},0],
    ['contradictory_gross',o=>{o.q.rows[0].gross_variance_usd='60.00'},0],
    ['fake_revenue',o=>{o.q.verified_customer_revenue_usd=100},0],
    ['fake_collectible',o=>{o.q.verified_collectible_usd='100.00'},0],
    ['row_claim',o=>{o.q.rows[0].collectible_usd='60.00'},0],
    ['wrong_row_count',o=>{o.q.total_jobs=50},0],
    ['hidden_invoice_discount',o=>{o.p[0].posted[0].discount_usd='100.00'},0],
    ['hidden_job_adjustment',o=>{o.p[0].discount_total_usd='100.00'},0],
    ['unsigned_rate',o=>{o.p[0].signed_rate_reviewed=false},0],
    ['unverified_ledger',o=>{o.p[0].full_ledger_verified=false},0]
  ];
  let passed=0,arithmeticCases=0,reviewCases=0;
  for(const [name,mutate,want] of cases){
    const o=base();mutate(o);const got=bridge(o.q,o.p);
    if(got.arithmetic_only!==want||got.verified_collectible_usd!==null||
       got.verified_owner_revenue_usd!=='0.00'||
       got.actual_customer_invoices_reviewed!==0||
       (want===0&&got.status!=='REVIEW'))
       throw Error(name+': '+JSON.stringify(got));
    passed++;if(want)arithmeticCases++;else reviewCases++;
  }
  return {passed,total:cases.length,arithmetic_only_cases:arithmeticCases,
    review_cases:reviewCases,real_customer_records:0,verified_owner_revenue_usd:'0.00'};
}
if(typeof module!=='undefined'&&module.exports){
  module.exports={bridge,holdout};
  if(require.main===module)console.log(JSON.stringify(holdout()));
}
