/* Golden Goose #025: synthetic scoped-ID holdout, 18 adversarial cases.
 * node test_invoice_scope_holdout_025.js
 */
'use strict';
const assert=require('node:assert/strict');
const {inspectScopedLineIds:inspect}=require('./invoice_scope_holdout_025.js');
const {bridge}=require('./cohort_amount_bridge_019.js');
const copy=x=>structuredClone(x);
let passed=0;
function fixture(n=100){
 const rows=Array.from({length:n},(_,i)=>({job_id:'SYN-GG025-'+String(i+1).padStart(3,'0'),
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
  posted:[{job_id:r.job_id,invoice_line_id:'1',state:'ISSUED',
    hours_qty:'4.00',dumps_qty:'1.00',hourly_unit_usd:'175.00',
    dump_unit_usd:'180.00',hours_extended_usd:'700.00',
    dumps_extended_usd:'180.00',line_total_usd:'880.00'}]}));
 const docs=rows.map((r,i)=>({job_id:r.job_id,lines:[{line_index:0,
  issuer_ref:'SUP-1',invoice_ref:'SYN-DOC-'+String(i+1).padStart(3,'0')}]}));
 return {q,posted,docs};
}
function test(label,mutate,expected){
 const f=fixture();if(mutate)mutate(f);
 const out=inspect(f.q,f.posted,f.docs);
 assert.equal(out.financial_clearance_allowed,false,label);
 assert.equal(out.global_bridge_review_unchanged,true,label);
 assert.equal(out.document_identity_authenticated,false,label);
 assert.equal(out.verified_collectible_usd,null,label);
 assert.equal(out.verified_owner_revenue_usd,'0.00',label);
 assert.equal(out.actual_customer_invoices_reviewed,0,label);
 for(const [key,val] of Object.entries(expected))assert.deepEqual(out[key],val,label+': '+key);
 passed++;return out;
}
const clean=test('100 different documents reuse local line 1',null,{
 scope_scan:'COMPLETE_FOR_UNVERIFIED_ANNOTATIONS',
 suspected_same_document_line_collisions:[],supplied_job_count:100,
 supplied_document_line_count:100,
 cross_document_reused_line_ids:[{invoice_line_id:'1',distinct_supplied_document_scopes:100}]
});
assert.equal(clean.scoped_collision_job_ids.length,0);
const allHeld=bridge(fixture().q,fixture().posted);
assert.equal(allHeld.reason,'DUPLICATE_POSTED_LINE_ACROSS_COHORT');
assert.equal(allHeld.needs_review,100);
assert.equal(allHeld.arithmetic_only,0);
const same=test('same issuer and document shares line number across jobs',f=>{
 f.docs[1].lines[0].invoice_ref=f.docs[0].lines[0].invoice_ref;
},{reason:'SAME_DOCUMENT_ID_REUSE_SUSPECTED',
 scoped_collision_job_ids:['syn-gg025-001','syn-gg025-002']});
assert.equal(same.suspected_same_document_line_collisions.length,1);
assert.equal(same.suspected_same_document_line_collisions[0].occurrences,2);
test('same invoice number different issuers',f=>{
 f.docs[1].lines[0].invoice_ref=f.docs[0].lines[0].invoice_ref;
 f.docs[1].lines[0].issuer_ref='SUP-2';
},{suspected_same_document_line_collisions:[],scope_scan:'COMPLETE_FOR_UNVERIFIED_ANNOTATIONS'});
test('same job split between two documents using line 1',f=>{
 f.posted[0].posted.push(copy(f.posted[0].posted[0]));
 f.docs[0].lines.push({line_index:1,issuer_ref:'SUP-1',invoice_ref:'SYN-OTHER'});
},{suspected_same_document_line_collisions:[],supplied_document_line_count:101});
const sameJob=test('same document repeated line within job',f=>{
 f.posted[0].posted.push(copy(f.posted[0].posted[0]));
 f.docs[0].lines.push(copy({...f.docs[0].lines[0],line_index:1}));
},{reason:'SAME_DOCUMENT_ID_REUSE_SUSPECTED',scoped_collision_job_ids:['syn-gg025-001']});
assert.equal(sameJob.suspected_same_document_line_collisions[0].occurrences,2);
test('same document two different line numbers',f=>{
 f.posted[0].posted.push({...copy(f.posted[0].posted[0]),invoice_line_id:'2'});
 f.docs[0].lines.push(copy({...f.docs[0].lines[0],line_index:1}));
},{suspected_same_document_line_collisions:[]});
test('case-sensitive document refs are not silently folded',f=>{
 f.docs[1].lines[0].invoice_ref=f.docs[0].lines[0].invoice_ref.toLowerCase();
},{suspected_same_document_line_collisions:[]});
test('JSON tuple key resists separator collision',f=>{
 f.docs[0].lines[0].issuer_ref='A:B';f.docs[0].lines[0].invoice_ref='C';
 f.docs[1].lines[0].issuer_ref='A';f.docs[1].lines[0].invoice_ref='B:C';
},{suspected_same_document_line_collisions:[]});
test('missing all annotations',f=>{f.docs=[]},{
 scope_scan:'INDETERMINATE',reason:'MISSING_OR_INCOMPLETE_DOCUMENT_ANNOTATIONS'});
test('blank issuer',f=>{f.docs[0].lines[0].issuer_ref=' '},{
 scope_scan:'INDETERMINATE',reason:'INVALID_OR_UNTRUSTED_DOCUMENT_SCOPE'});
test('blank invoice',f=>{f.docs[0].lines[0].invoice_ref=''},{
 scope_scan:'INDETERMINATE',reason:'INVALID_OR_UNTRUSTED_DOCUMENT_SCOPE'});
test('duplicate line positional map',f=>{f.docs[0].lines.push(copy(f.docs[0].lines[0]))},{
 scope_scan:'INDETERMINATE',reason:'INVALID_OR_UNTRUSTED_DOCUMENT_SCOPE'});
test('missing positional map',f=>{f.docs[0].lines[0].line_index=1},{
 scope_scan:'INDETERMINATE',reason:'UNMAPPED_DOCUMENT_LINE'});
test('foreign annotation job',f=>{f.docs[0].job_id='SYN-FOREIGN'},{
 scope_scan:'INDETERMINATE',reason:'INCOMPLETE_OR_FOREIGN_DOCUMENT_SCOPE'});
test('unsupported trusted claim forbidden',f=>{f.docs[0].verified=true},{
 scope_scan:'INDETERMINATE',reason:'INVALID_OR_DUPLICATE_DOCUMENT_ANNOTATION'});
test('unsupported line paid claim forbidden',f=>{f.docs[0].lines[0].paid_usd='100.00'},{
 scope_scan:'INDETERMINATE',reason:'INVALID_OR_UNTRUSTED_DOCUMENT_SCOPE'});
test('upstream claimed collectible refused',f=>{f.q.verified_collectible_usd='100.00'},{
 scope_scan:'INDETERMINATE',reason:'UPSTREAM_IDENTIFIERS_INDETERMINATE'});
test('missing proof line number refused',f=>{f.posted[0].posted[0].invoice_line_id=''},{
 scope_scan:'INDETERMINATE',reason:'UPSTREAM_IDENTIFIERS_INDETERMINATE'});
assert.equal(passed,18);
const hypotheticalFullReviewUsd=Number((100*5/60*35).toFixed(2));
const hypotheticalFeeUsd=100,hypotheticalOverheadUsd=10,hypotheticalLaborUsdPerHour=35;
const maxHours=(hypotheticalFeeUsd-hypotheticalOverheadUsd)/hypotheticalLaborUsdPerHour;
assert.equal(hypotheticalFullReviewUsd,291.67);
assert.ok(maxHours>2.57&&maxHours<2.58);
console.log(JSON.stringify({experiment:'GG-025 unverified-document-scope falsifier',
 passed,synthetic_jobs:100,globally_reused_local_line_ids:1,
 distinct_supplied_docs:100,scoped_suspected_collisions:0,
 original_bridge_review:allHeld.needs_review,
 hypothetical_full_review_usd:hypotheticalFullReviewUsd,
 hypothetical_break_even_hours:Number(maxHours.toFixed(3)),
 documented_sales:0,actual_customer_invoices_reviewed:0,
 verified_collectible_usd:null,verified_owner_revenue_usd:'0.00',
 release_ready:false,commercially_validated:false}));
