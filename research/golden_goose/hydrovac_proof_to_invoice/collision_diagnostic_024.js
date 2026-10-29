/* Golden Goose #024: DIAGNOSTIC-ONLY duplicate invoice-line localization.
 * Research-only; NEVER clears invoices or asserts payable/collectible revenue.
 * A global fail-closed REVIEW from cohort_amount_bridge_019 remains authoritative.
 * Works only from a wholly supplied, syntactically coherent synthetic cohort.
 */
'use strict';
const norm = x => typeof x === 'string' && x.trim() ? x.trim().toLowerCase() : null;
const base = (reason, total) => ({
  status:'DIAGNOSTIC_ONLY', collision_scan:'INDETERMINATE', reason,
  complete_ledger_verified:false, cohort_clearance_allowed:false,
  global_bridge_review_unchanged:true, total_jobs:Number.isSafeInteger(total) && total >= 0 ? total:null,
  affected_job_ids:[], not_flagged_job_count:null, collision_groups:[],
  verified_collectible_usd:null, verified_owner_revenue_usd:'0.00',
  actual_customer_invoices_reviewed:0
});
function diagnoseInvoiceIdCollisions(quantitySummary, postedProofRows){
  const rows=quantitySummary && quantitySummary.rows;
  const total=quantitySummary && quantitySummary.total_jobs;
  const output=base('INVALID_OR_INCOMPLETE_INPUT',total);
  if (!Array.isArray(rows)||!Array.isArray(postedProofRows)||
      !Number.isSafeInteger(total)||total<=0||rows.length!==total)
    return output;
  // This tool localizes an ID issue, NOT an upstream financial-data anomaly.
  if (quantitySummary.verified_collectible_usd!==null ||
      quantitySummary.verified_customer_revenue_usd!==0)
    return {...output,reason:'UNSUPPORTED_MONETARY_ASSERTION'};
  const allowedSummary=new Set(['rows','total_jobs','candidate_discrepancies',
    'review_only','clear','illustrative_candidate_gross_usd',
    'verified_collectible_usd','verified_customer_revenue_usd']);
  const allowedRow=new Set(['job_id','status','gross_variance_usd','collectible_usd']);
  if(Object.keys(quantitySummary).some(k=>!allowedSummary.has(k)))
    return {...output,reason:'UNMODELED_SUMMARY_FIELD'};
  const ids=new Set();
  for(const r of rows){
    const id=norm(r && r.job_id);
    if(!r||typeof r!=='object'||Array.isArray(r)||
       Object.keys(r).some(k=>!allowedRow.has(k))||!id||ids.has(id)||
       r.collectible_usd!==null||typeof r.status!=='string'||
       !/^(?:0|[1-9][0-9]*)\.[0-9]{2}$/.test(r.gross_variance_usd))
      return {...output,reason:'INVALID_OR_DUPLICATE_QUANTITY_JOB'};
    ids.add(id);
  }
  const seenProofs=new Set(), byLine=new Map();
  for(const p of postedProofRows){
    const id=norm(p && p.job_id);
    if(!p||typeof p!=='object'||Array.isArray(p)||!id||
       !ids.has(id)||seenProofs.has(id)||!Array.isArray(p.posted)||
       !p.posted.length)
      return {...output,reason:'MISSING_DUPLICATE_OR_FOREIGN_PROOF'};
    seenProofs.add(id);
    for(const l of p.posted){
      const lineId=norm(l&&l.invoice_line_id);
      if(!l||typeof l!=='object'||Array.isArray(l)||!lineId||
         norm(l.job_id)!==id)
        return {...output,reason:'MISSING_OR_MISATTRIBUTED_LINE_ID'};
      const owners=byLine.get(lineId)||[];
      owners.push(id);byLine.set(lineId,owners);
    }
  }
  if(seenProofs.size!==ids.size)
    return {...output,reason:'INCOMPLETE_PROOF_COVERAGE'};
  const collisionGroups=[];
  const affected=new Set();
  for(const [lineId,owners] of byLine){
    if(owners.length>1){
      const jobs=[...new Set(owners)].sort();
      jobs.forEach(id=>affected.add(id));
      collisionGroups.push({invoice_line_id:lineId,occurrence_count:owners.length,
        job_ids:jobs,cross_job:jobs.length>1});
    }
  }
  collisionGroups.sort((a,b)=>a.invoice_line_id.localeCompare(b.invoice_line_id));
  return {...output,collision_scan:'COMPLETE_FOR_SUPPLIED_IDENTIFIERS',
    reason:collisionGroups.length?'DUPLICATE_ID_LOCATED':'NO_DUPLICATE_ID_IN_SUPPLIED_ROWS',
    affected_job_ids:[...affected].sort(),
    // NOT a claim remaining jobs are reconciled or need no review.
    not_flagged_job_count:total-affected.size,
    collision_groups:collisionGroups};
}
module.exports={diagnoseInvoiceIdCollisions};
