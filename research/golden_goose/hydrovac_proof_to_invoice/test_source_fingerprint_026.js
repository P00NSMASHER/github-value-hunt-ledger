/* Golden Goose #026: adversarial synthetic source fingerprint + identity holdout.
 * Invoke: node test_source_fingerprint_026.js (no network or customer data).
 */
'use strict';
const assert=require('node:assert/strict');
const {createHash}=require('node:crypto');
const {inspectSourceFingerprints:inspect}=require('./source_fingerprint_026.js');
const clone=global.structuredClone;
const pack=s=>({source_bytes_base64:Buffer.from(s).toString('base64'),
 claimed_sha256:createHash('sha256').update(s).digest('hex')});
function fixture(n=100){
 const expected=Array.from({length:n},(_,i)=>'SYN-026-'+String(i+1).padStart(3,'0'));
 const docs=expected.map((job_id,i)=>({job_id,lines:[{
  line_index:0,issuer_ref:'SYN-VENDOR-A',invoice_ref:'SYN-INV-'+String(i+1).padStart(3,'0'),
  invoice_line_id:'1',version_ref:'V1',
  ...pack('synthetic-only-invoice-image-'+String(i+1).padStart(3,'0'))}]}));
 return {docs,expected};
}
let passed=0;
function test(name,mutate,check){
 const f=fixture();if(mutate)mutate(f);
 const out=inspect(f.docs,f.expected);
 assert.equal(out.status,'DIAGNOSTIC_ONLY',name);
 assert.equal(out.document_authenticity_verified,false,name);
 assert.equal(out.signatory_verified,false,name);
 assert.equal(out.financial_clearance_allowed,false,name);
 assert.equal(out.global_bridge_review_unchanged,true,name);
 assert.equal(out.verified_collectible_usd,null,name);
 assert.equal(out.verified_owner_revenue_usd,'0.00',name);
 assert.equal(out.actual_customer_invoices_reviewed,0,name);
 check(out);
 passed++;return out;
}
const ok=out=>{assert.equal(out.scan,'COMPLETE_FOR_SUPPLIED_BYTES_ONLY');
 assert.equal(out.digest_matches_supplied_bytes_only,true);};
const blocked=reason=>out=>{assert.equal(out.scan,'INDETERMINATE');
 assert.equal(out.digest_matches_supplied_bytes_only,false);
 assert.equal(out.reason,reason);};
const base=test('100 unrelated docs with line 1',null,out=>{
 ok(out);assert.equal(out.supplied_jobs,100);assert.equal(out.supplied_lines,100);
 assert.equal(out.distinct_document_refs,100);
 for(const k of ['same_document_line_references','same_version_content_conflicts',
  'multiple_document_versions','identical_bytes_multiple_document_refs'])
  assert.equal(out[k].length,0);
});
test('repeated line 1 in same doc and same bytes',f=>{
 f.docs[1].lines[0].invoice_ref=f.docs[0].lines[0].invoice_ref;
 Object.assign(f.docs[1].lines[0],pack('synthetic-only-invoice-image-001'));
},out=>{ok(out);assert.equal(out.same_document_line_references.length,1);
 assert.equal(out.same_document_line_references[0].job_ids.length,2);
 assert.equal(out.same_version_content_conflicts.length,0);
 assert.equal(out.identical_bytes_multiple_document_refs.length,0);});
test('same doc/version but different bytes',f=>{
 f.docs[1].lines[0].invoice_ref=f.docs[0].lines[0].invoice_ref;
},out=>{ok(out);assert.equal(out.same_version_content_conflicts.length,1);
 assert.equal(out.same_document_line_references.length,1);});
test('same doc with explicit later version',f=>{
 f.docs[1].lines[0].invoice_ref=f.docs[0].lines[0].invoice_ref;
 f.docs[1].lines[0].version_ref='V2';
},out=>{ok(out);assert.equal(out.multiple_document_versions.length,1);
 assert.equal(out.same_version_content_conflicts.length,0);});
test('same doc different line number',f=>{
 const a=f.docs[0].lines[0],b=f.docs[1].lines[0];
 b.invoice_ref=a.invoice_ref;b.invoice_line_id='2';
 Object.assign(b,pack('synthetic-only-invoice-image-001'));
},out=>{ok(out);assert.equal(out.same_document_line_references.length,0);
 assert.equal(out.same_version_content_conflicts.length,0);});
test('different document refs same identical bytes',f=>{
 Object.assign(f.docs[1].lines[0],pack('synthetic-only-invoice-image-001'));
},out=>{ok(out);assert.equal(out.identical_bytes_multiple_document_refs.length,1);
 assert.equal(out.same_document_line_references.length,0);});
test('different issuer same invoice id and same bytes',f=>{
 const a=f.docs[0].lines[0],b=f.docs[1].lines[0];
 b.invoice_ref=a.invoice_ref;b.issuer_ref='SYN-VENDOR-B';
 Object.assign(b,pack('synthetic-only-invoice-image-001'));
},out=>{ok(out);assert.equal(out.identical_bytes_multiple_document_refs.length,1);
 assert.equal(out.same_document_line_references.length,0);});
test('case-sensitive invoice reference not folded',f=>{
 const a=f.docs[0].lines[0],b=f.docs[1].lines[0];
 b.invoice_ref=a.invoice_ref.toLowerCase();
},out=>{ok(out);assert.equal(out.same_document_line_references.length,0);});
test('split job across distinct invoices both line 1',f=>{
 const a=f.docs[0].lines[0];
 f.docs[0].lines.push({...clone(a),line_index:1,
   invoice_ref:'SYN-INV-OTHER',...pack('synthetic-only-split-invoice')});
},out=>{ok(out);assert.equal(out.supplied_lines,101);
 assert.equal(out.same_document_line_references.length,0);});
test('within same job same doc/line twice',f=>{
 const a=f.docs[0].lines[0];
 f.docs[0].lines.push({...clone(a),line_index:1});
},out=>{ok(out);assert.equal(out.same_document_line_references.length,1);
 assert.equal(out.same_document_line_references[0].job_ids.length,1);});
test('wrong claimed hash is not authenticated',f=>{
 f.docs[0].lines[0].claimed_sha256='0'.repeat(64);
},blocked('DIGEST_MISMATCH_TO_SUPPLIED_BYTES'));
test('payload changed after hash',f=>{
 f.docs[0].lines[0].source_bytes_base64=Buffer.from('edited-payload').toString('base64');
},blocked('DIGEST_MISMATCH_TO_SUPPLIED_BYTES'));
test('non-canonical base64 refused',f=>{
 f.docs[0].lines[0].source_bytes_base64='AAAA=';
},blocked('NONCANONICAL_OR_OVERSIZE_SOURCE_BYTES'));
test('missing bytes',f=>{
 f.docs[0].lines[0].source_bytes_base64='';
},blocked('MISSING_OR_INVALID_SOURCE_DIGEST'));
test('oversized payload',f=>{
 const p=pack('x'.repeat(8193));Object.assign(f.docs[0].lines[0],p);
},blocked('NONCANONICAL_OR_OVERSIZE_SOURCE_BYTES'));
test('missing issuer',f=>{f.docs[0].lines[0].issuer_ref='';},
 blocked('INVALID_OR_UNTRUSTED_LINE_REFERENCE'));
test('blank version',f=>{f.docs[0].lines[0].version_ref='';},
 blocked('INVALID_OR_UNTRUSTED_LINE_REFERENCE'));
test('unknown paid claim rejected',f=>{f.docs[0].lines[0].paid_usd='500.00';},
 blocked('INVALID_OR_UNTRUSTED_LINE_REFERENCE'));
test('unknown verified flag rejected',f=>{f.docs[0].lines[0].verified=true;},
 blocked('INVALID_OR_UNTRUSTED_LINE_REFERENCE'));
test('duplicate job in source evidence',f=>{f.docs[1].job_id=f.docs[0].job_id;},
 blocked('INVALID_OR_DUPLICATE_JOB_EVIDENCE'));
test('missing job entry not treated as complete',f=>{f.docs.pop();},
 blocked('INVALID_OR_INCOMPLETE_EVIDENCE'));
test('foreign job entry not treated as coverage',f=>{f.docs[1].job_id='SYN-UNLISTED';},
 blocked('INCOMPLETE_EXPECTED_JOB_COVERAGE'));
test('duplicate expected job rejects even if evidence present',f=>{
 f.expected[1]=f.expected[0];},blocked('INVALID_EXPECTED_JOB_IDS'));
test('duplicate position in split job',f=>{
 f.docs[0].lines.push(clone(f.docs[0].lines[0]));
},blocked('INVALID_OR_UNTRUSTED_LINE_REFERENCE'));
test('position gap in job',f=>{f.docs[0].lines[0].line_index=1;},
 blocked('INCOMPLETE_LINE_POSITION_MAP'));
test('noninteger source position',f=>{f.docs[0].lines[0].line_index=0.5;},
 blocked('INVALID_OR_UNTRUSTED_LINE_REFERENCE'));
test('untrusted mixed-case hash silently prohibited',f=>{
 f.docs[0].lines[0].claimed_sha256=f.docs[0].lines[0].claimed_sha256.toUpperCase();
},blocked('MISSING_OR_INVALID_SOURCE_DIGEST'));
test('same document version content conflict is not chargeable',f=>{
 f.docs[1].lines[0].invoice_ref=f.docs[0].lines[0].invoice_ref;
},out=>{ok(out);assert.equal(out.verified_collectible_usd,null);
 assert.equal(out.reason,'SUPPLIED_SOURCE_IDENTITY_REVIEW_FLAGS');});
assert.equal(passed,28);
const hypotheticalReviewUsd=Number((100*5/60*35).toFixed(2));
const hypotheticalFee=100,assumedOverhead=10,assumedLaborPerHour=35;
const breakEvenHours=(hypotheticalFee-assumedOverhead)/assumedLaborPerHour;
assert.equal(hypotheticalReviewUsd,291.67);
assert.ok(breakEvenHours>2.57&&breakEvenHours<2.58);
console.log(JSON.stringify({experiment:'GG-026 synthetic source fingerprint adversarial holdout',
 passed,synthetic_jobs:base.supplied_jobs,identical_doc_collisions:0,
 sha256_valid_for_supplied_bytes:true,document_identity_authenticated:false,
 hypothetical_full_review_usd:hypotheticalReviewUsd,
 hypothetical_break_even_hours:Number(breakEvenHours.toFixed(3)),
 actual_customer_invoices_reviewed:0,verified_collectible_usd:null,
 verified_owner_revenue_usd:'0.00',release_ready:false,
 commercially_validated:false}));
