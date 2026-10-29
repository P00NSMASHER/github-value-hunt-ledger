/* GG #025: synthetic, diagnostic-only invoice-document namespace holdout.
 * No invoice clearance, payable balance, collectible revenue, or customer verification.
 * This does NOT modify or override cohort_amount_bridge_019.js.
 * https://test-docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice/tree/
 */
'use strict';
const {diagnoseInvoiceIdCollisions}=require('./collision_diagnostic_024.js');
const own=(v,k)=>Object.prototype.hasOwnProperty.call(v,k);
const identity=v=>typeof v==='string'&&v.length>0&&v.length<=128&&v===v.trim()?v:null;
const jobId=v=>identity(v)&&v.toLowerCase();
const keys=(v,expected)=>v&&typeof v==='object'&&!Array.isArray(v)&&
 Object.keys(v).length===expected.length&&Object.keys(v).every(k=>expected.includes(k));
const result=(reason,detail=null)=>({
 status:'DIAGNOSTIC_ONLY',scope_scan:'INDETERMINATE',reason,detail,
 document_identity_authenticated:false,source:'UNVERIFIED_SYNTHETIC_REFERENCES',
 financial_clearance_allowed:false,global_bridge_review_unchanged:true,
 suspected_same_document_line_collisions:[],cross_document_reused_line_ids:[],
 scoped_collision_job_ids:[],verified_collectible_usd:null,
 verified_owner_revenue_usd:'0.00',actual_customer_invoices_reviewed:0
});
function inspectScopedLineIds(quantitySummary,postedProofRows,documentAnnotations){
 const old=diagnoseInvoiceIdCollisions(quantitySummary,postedProofRows);
 if(old.collision_scan!=='COMPLETE_FOR_SUPPLIED_IDENTIFIERS')
  return result('UPSTREAM_IDENTIFIERS_INDETERMINATE',old.reason);
 if(!Array.isArray(documentAnnotations)||documentAnnotations.length!==postedProofRows.length)
  return result('MISSING_OR_INCOMPLETE_DOCUMENT_ANNOTATIONS');
 const scope=new Map();
 for(const d of documentAnnotations){
  if(!keys(d,['job_id','lines'])||!jobId(d.job_id)||scope.has(jobId(d.job_id))||
     !Array.isArray(d.lines)||!d.lines.length)
    return result('INVALID_OR_DUPLICATE_DOCUMENT_ANNOTATION');
  const positions=new Map();
  for(const line of d.lines){
   if(!keys(line,['line_index','issuer_ref','invoice_ref'])||
      !Number.isSafeInteger(line.line_index)||line.line_index<0||
      !identity(line.issuer_ref)||!identity(line.invoice_ref)||
      positions.has(line.line_index))
    return result('INVALID_OR_UNTRUSTED_DOCUMENT_SCOPE');
   positions.set(line.line_index,line);
  }
  scope.set(jobId(d.job_id),positions);
 }
 const byScoped=new Map(),byLocal=new Map();
 let lineCount=0;
 for(const p of postedProofRows){
  const id=jobId(p.job_id),refs=scope.get(id);
  if(!refs||refs.size!==p.posted.length)
   return result('INCOMPLETE_OR_FOREIGN_DOCUMENT_SCOPE');
  for(let i=0;i<p.posted.length;i++){
   const row=p.posted[i],d=refs.get(i),line=identity(row.invoice_line_id);
   if(!d||!line)return result('UNMAPPED_DOCUMENT_LINE');
   // JSON tuple prevents delimiter ambiguity; exact case is deliberately preserved.
   // User-supplied document references are NOT authenticated.
   const doc=JSON.stringify([d.issuer_ref,d.invoice_ref]);
   const compound=JSON.stringify([d.issuer_ref,d.invoice_ref,line]);
   const point={job_id:id,line_index:i,issuer_ref:d.issuer_ref,invoice_ref:d.invoice_ref,invoice_line_id:line};
   if(!byScoped.has(compound))byScoped.set(compound,[]);
   byScoped.get(compound).push(point);
   if(!byLocal.has(line))byLocal.set(line,new Set());
   byLocal.get(line).add(doc);
   lineCount++;
  }
 }
 if(scope.size!==postedProofRows.length||lineCount===0)
  return result('INCOMPLETE_DOCUMENT_SCOPE');
 const suspects=[],affected=new Set(),aliases=[];
 for(const [k,occurrences] of byScoped){
  if(occurrences.length>1){
   occurrences.forEach(p=>affected.add(p.job_id));
   suspects.push({scope:JSON.parse(k),occurrences:occurrences.length,
    job_ids:[...new Set(occurrences.map(p=>p.job_id))].sort()});
  }
 }
 for(const [line,docs] of byLocal)
  if(docs.size>1)aliases.push({invoice_line_id:line,distinct_supplied_document_scopes:docs.size});
 suspects.sort((a,b)=>JSON.stringify(a.scope).localeCompare(JSON.stringify(b.scope)));
 aliases.sort((a,b)=>a.invoice_line_id.localeCompare(b.invoice_line_id));
 return {...result(suspects.length?'SAME_DOCUMENT_ID_REUSE_SUSPECTED':'NO_SAME_DOCUMENT_REUSE_IN_SUPPLIED_ANNOTATIONS'),
  scope_scan:'COMPLETE_FOR_UNVERIFIED_ANNOTATIONS',detail:null,
  supplied_document_line_count:lineCount,supplied_job_count:postedProofRows.length,
  suspected_same_document_line_collisions:suspects,
  cross_document_reused_line_ids:aliases,
  scoped_collision_job_ids:[...affected].sort()};
}
module.exports={inspectScopedLineIds};
