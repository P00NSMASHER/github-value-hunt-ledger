/* Golden Goose #026: offline synthetic document-byte fingerprint diagnostic.
 * A locally matching SHA-256 digest is NOT a supplier signature, authenticity,
 * legal invoice identity, payment proof, or a basis to release global REVIEW.
 * Source: https://csrc.nist.gov/projects/hash-functions
 * Source: https://www.nist.gov/publications/digital-signature-standard-dss-3
 */
'use strict';
const {createHash}=require('node:crypto');
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const exact=(o,ks)=>o!==null&&typeof o==='object'&&!Array.isArray(o)&&
 Object.keys(o).length===ks.length&&Object.keys(o).every(k=>ks.includes(k));
const ident=s=>typeof s==='string'&&s.length>0&&s.length<=128&&
 s===s.trim()&&!/[\u0000-\u001f\u007f]/.test(s);
const tup=(...args)=>JSON.stringify(args);
function blank(reason){return {
 status:'DIAGNOSTIC_ONLY',scan:'INDETERMINATE',reason,
 hash_algorithm:'SHA-256',digest_matches_supplied_bytes_only:false,
 document_authenticity_verified:false,signatory_verified:false,
 actual_customer_invoices_reviewed:0,
 financial_clearance_allowed:false,global_bridge_review_unchanged:true,
 verified_collectible_usd:null,verified_owner_revenue_usd:'0.00',
 supplied_jobs:0,supplied_lines:0,
 same_document_line_references:[],same_version_content_conflicts:[],
 multiple_document_versions:[],identical_bytes_multiple_document_refs:[]
};}
function inspectSourceFingerprints(evidence,expectedJobIds){
 const out=blank('INVALID_OR_INCOMPLETE_EVIDENCE');
 if(!Array.isArray(evidence)||evidence.length<1||evidence.length>1000||
    !Array.isArray(expectedJobIds)||expectedJobIds.length!==evidence.length)return out;
 const expected=new Set();
 for(const id of expectedJobIds){
  if(!ident(id)||expected.has(id.toLowerCase()))return blank('INVALID_EXPECTED_JOB_IDS');
  expected.add(id.toLowerCase());
 }
 const jobs=new Set(),lineRefs=new Map(),documents=new Map(),hashToDocs=new Map();
 let total=0,bytesTotal=0;
 for(const record of evidence){
  if(!exact(record,['job_id','lines'])||!ident(record.job_id)||
     !Array.isArray(record.lines)||!record.lines.length||record.lines.length>200)
   return blank('INVALID_OR_DUPLICATE_JOB_EVIDENCE');
  const job=record.job_id.toLowerCase();
  if(jobs.has(job))return blank('INVALID_OR_DUPLICATE_JOB_EVIDENCE');
  jobs.add(job);
  const seenIndexes=new Set();
  for(const line of record.lines){
   if(!exact(line,['line_index','issuer_ref','invoice_ref','invoice_line_id',
                  'version_ref','source_bytes_base64','claimed_sha256'])||
       !Number.isSafeInteger(line.line_index)||line.line_index<0||
       seenIndexes.has(line.line_index)||!ident(line.issuer_ref)||
       !ident(line.invoice_ref)||!ident(line.invoice_line_id)||
       !ident(line.version_ref))return blank('INVALID_OR_UNTRUSTED_LINE_REFERENCE');
   seenIndexes.add(line.line_index);
   const payload=line.source_bytes_base64,claimed=line.claimed_sha256;
   if(typeof payload!=='string'||payload.length>11000||
      !/^[A-Za-z0-9+/]+={0,2}$/.test(payload)||
      typeof claimed!=='string'||!/^[0-9a-f]{64}$/.test(claimed))
    return blank('MISSING_OR_INVALID_SOURCE_DIGEST');
   const bytes=Buffer.from(payload,'base64');
   if(!bytes.length||bytes.length>8192||bytes.toString('base64')!==payload)
    return blank('NONCANONICAL_OR_OVERSIZE_SOURCE_BYTES');
   bytesTotal+=bytes.length;
   if(bytesTotal>2*1024*1024)return blank('EVIDENCE_BYTES_LIMIT_EXCEEDED');
   const computed=createHash('sha256').update(bytes).digest('hex');
   if(computed!==claimed)return blank('DIGEST_MISMATCH_TO_SUPPLIED_BYTES');
   const doc=tup(line.issuer_ref,line.invoice_ref),
         lineKey=tup(line.issuer_ref,line.invoice_ref,line.invoice_line_id);
   const entry={job_id:job,line_index:line.line_index};
   if(!lineRefs.has(lineKey))lineRefs.set(lineKey,[]);
   lineRefs.get(lineKey).push(entry);
   if(!documents.has(doc))documents.set(doc,new Map());
   const versions=documents.get(doc);
   if(!versions.has(line.version_ref))versions.set(line.version_ref,new Set());
   versions.get(line.version_ref).add(computed);
   if(!hashToDocs.has(computed))hashToDocs.set(computed,new Set());
   hashToDocs.get(computed).add(doc);
   total++;
   if(total>10000)return blank('LINE_COUNT_LIMIT_EXCEEDED');
  }
  // Split-document mappings require explicit positional evidence, not silently
  // inferred positions. A single missing position invalidates the diagnostic.
  if(seenIndexes.size!==record.lines.length||
     [...seenIndexes].some((i)=>i>=record.lines.length))
   return blank('INCOMPLETE_LINE_POSITION_MAP');
 }
 if([...expected].some(id=>!jobs.has(id)))
  return blank('INCOMPLETE_EXPECTED_JOB_COVERAGE');
 const lineReuses=[],versionConflicts=[],versionGroups=[],byteAliases=[];
 for(const [key,rows] of lineRefs){
  if(rows.length>1)lineReuses.push({scope:JSON.parse(key),occurrences:rows.length,
   job_ids:[...new Set(rows.map(x=>x.job_id))].sort()});
 }
 for(const [key,versions] of documents){
  const document_scope=JSON.parse(key);
  if(versions.size>1)versionGroups.push({document_scope,version_refs:[...versions.keys()].sort()});
  for(const [version,hashes] of versions)
   if(hashes.size>1)versionConflicts.push({document_scope,version_ref:version,
    distinct_supplied_byte_hashes:hashes.size});
 }
 for(const [hash,docs] of hashToDocs)
  if(docs.size>1)byteAliases.push({sha256:hash,distinct_document_refs:docs.size});
 const sort=a=>a.sort((x,y)=>JSON.stringify(x).localeCompare(JSON.stringify(y)));
 const alerts=lineReuses.length+versionConflicts.length+versionGroups.length+byteAliases.length;
 return {...out,scan:'COMPLETE_FOR_SUPPLIED_BYTES_ONLY',reason:alerts?
    'SUPPLIED_SOURCE_IDENTITY_REVIEW_FLAGS':'NO_SUPPLIED_SOURCE_IDENTITY_FLAGS',
    digest_matches_supplied_bytes_only:true,supplied_jobs:jobs.size,
    supplied_lines:total,distinct_document_refs:documents.size,
    same_document_line_references:sort(lineReuses),
    same_version_content_conflicts:sort(versionConflicts),
    multiple_document_versions:sort(versionGroups),
    identical_bytes_multiple_document_refs:sort(byteAliases)};
}
module.exports={inspectSourceFingerprints};
