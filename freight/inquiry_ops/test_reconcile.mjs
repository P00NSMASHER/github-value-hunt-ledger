import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {DatabaseSync} from "node:sqlite";
import {readOnlyQueries,reconcile,collect,dryRun} from "./reconcile.mjs";

const TIME=Math.floor(Date.parse("2026-10-08T16:00:00Z")/1000);
const empty=()=>({
  notification_aging:[],
  retention_review:[{aged_total:0,aged_pending:0,aged_provider:0,aged_delivered:0}],
  rate_limits:[{expired_total:0}],
  get qa_scope(){
    return [{raw_total:this.notification_aging.reduce((n,r)=>n+Number(r.total||0),0),qa_total:0}];
  },
  get case_lifecycle(){
    const n=this.notification_aging.reduce((sum,x)=>sum+Number(x.total||0),0);
    return [{total:n,unacknowledged:n,acknowledged:0,closed:0,
      reported:0,verified:0,waived:0,held:0,closed_unverified:0,
      aged_unacknowledged:0,aged_response_incomplete:0,
      expired_unresolved:0,expired_closed_unapproved:0}];
  }
});
function notification(s,n,age=300,overHour=0,overDay=0) {
  return {notification_status:s,total:n,oldest_at:TIME-age,aged_hour:overHour,aged_day:overDay};
}
const clone=x=>JSON.parse(JSON.stringify(x));
test("SQL is exclusively read-only, aggregate-only, bounded and avoids personal data",()=>{
  const queries=readOnlyQueries(TIME);
  assert.deepEqual(queries.map(x=>x.name),["notification_aging","retention_review","case_lifecycle","qa_scope","rate_limits"]);
  for(const q of queries) {
    assert.match(q.sql,/^SELECT /);
    assert.doesNotMatch(q.sql,/\b(?:DELETE|UPDATE|INSERT|DROP|ALTER|REPLACE|TRUNCATE)\b/i);
    assert.doesNotMatch(q.sql,/\b(?:full_name|work_email|company_name|details_json|idempotency_key|fingerprint)\b/i);
  }
});
test("dry run has no credential values or API request",()=>{
  const x=dryRun("2026-10-08T16:00:00Z");
  assert.equal(x.statements.length,5);
  assert.match(x.warning,/Never interpret provider acceptance/);
});
test("reject malformed UTC time",()=>{
  assert.throws(()=>dryRun("2026-10-08"),/ISO-8601/);
  assert.throws(()=>dryRun("2026-13-08T16:00:00Z"),/Invalid UTC/);
});
test("empty D1 aggregates are valid zero workload, NOT proof of operation",()=>{
  const r=reconcile(TIME,empty());
  assert.equal(r.inquiry_total,0);
  assert.equal(r.operational_acceptance,"CASE_ENFORCEMENT_CONFIGURED_ACTUAL_HUMAN_REVIEW_NOT_PROVEN");
  assert.ok(r.alerts.some(a=>a.code==="NO_LEADS_DOES_NOT_PROVE_RESPONSE_OPERATIONS"));
});
test("pending case under hour still requires reconciliation",()=>{
  const p=empty();
  p.notification_aging=[notification("pending",1)];
  const r=reconcile(TIME,p);
  const a=r.alerts.find(x=>x.code==="UNDELIVERED_NOTIFICATION");
  assert.equal(a.priority,"P1");
  assert.equal(a.count,1);
});
test("pending case beyond hour escalates P0",()=>{
  const p=empty();
  p.notification_aging=[notification("pending",2,7200,1,0)];
  const a=reconcile(TIME,p).alerts.find(x=>x.code==="UNDELIVERED_NOTIFICATION");
  assert.equal(a.priority,"P0");
});
test("provider acceptance is not human receipt or follow-up",()=>{
  const p=empty();
  p.notification_aging=[notification("provider_accepted",1,90000,1,1)];
  const r=reconcile(TIME,p);
  assert.equal(r.alerts.find(x=>x.code==="PROVIDER_NOT_INBOX_PROOF").priority,"P0");
  assert.equal(r.operational_acceptance,"CASE_ENFORCEMENT_CONFIGURED_ACTUAL_HUMAN_REVIEW_NOT_PROVEN");
});
test("delivery_verified still does not establish human handling",()=>{
  const p=empty();
  p.notification_aging=[notification("delivery_verified",3,90,0,0)];
  const r=reconcile(TIME,p);
  assert.equal(r.inquiry_total,3);
  assert.ok(r.alerts.some(a=>a.code==="UNACKNOWLEDGED_LEADS"));
});
test("retention review includes unresolved older-than-90-day cases",()=>{
  const p=empty();
  p.notification_aging=[notification("pending",2,120*86400,2,2),
    notification("provider_accepted",1,120*86400,1,1),
    notification("delivery_verified",2,120*86400,2,2)];
  p.retention_review=[{aged_total:3,aged_pending:2,aged_provider:1,aged_delivered:0}];
  const r=reconcile(TIME,p);
  assert.equal(r.retention.over_90_days,3);
  assert.equal(r.alerts.find(a=>a.code==="RETENTION_DECISION_REQUIRED").priority,"P0");
});
test("older delivered case still requires operator clearance before deletion",()=>{
  const p=empty();
  p.notification_aging=[notification("delivery_verified",1,100*86400,1,1)];
  p.retention_review=[{aged_total:1,aged_pending:0,aged_provider:0,aged_delivered:1}];
  const r=reconcile(TIME,p);
  assert.equal(r.alerts.find(a=>a.code==="RETENTION_DECISION_REQUIRED").priority,"P1");
});
test("expired rate-limit rows never justify a customer data deletion",()=>{
  const p=empty();p.rate_limits=[{expired_total:7}];
  const r=reconcile(TIME,p);
  assert.equal(r.rate_limit.expired_buckets,7);
  assert.equal(r.alerts.find(a=>a.code==="EXPIRED_RATE_BUCKETS").priority,"P2");
});
test("reject unrecognized status, duplicate status and unexpected columns",()=>{
  for(const a of [
    [notification("secret",1)],
    [notification("pending",1),notification("pending",1)],
    [{...notification("pending",1),work_email:"private@example.org"}]
  ]) {
    const p=empty();p.notification_aging=a;
    assert.throws(()=>reconcile(TIME,p),/Unknown|Unexpected/);
  }
});
test("reject false-zero, inconsistent or negative counts",()=>{
  let p=empty();delete p.rate_limits;
  assert.throws(()=>reconcile(TIME,p),/Incomplete/);
  p=empty();p.notification_aging=[notification("pending",1,1000,2,0)];
  assert.throws(()=>reconcile(TIME,p),/Inconsistent/);
  p=empty();p.retention_review=[{aged_total:1,aged_pending:0,aged_provider:0,aged_delivered:0}];
  assert.throws(()=>reconcile(TIME,p),/conservation/);
  p=empty();p.rate_limits=[{expired_total:-1}];
  assert.throws(()=>reconcile(TIME,p),/Invalid aggregate/);
});
test("mocked remote D1 collector requests only exact SELECT statements, one per status group",async()=>{
  const p=empty(),asked=[];
  const fetcher=async(url,options)=>{
    const q=JSON.parse(options.body).sql;
    asked.push(q);
    assert.match(q,/^SELECT /);
    assert.equal(options.method,"POST");
    assert.match(url,/\/d1\/database\/qa-id\/query$/);
    let rows=q.includes("GROUP BY")?p.notification_aging:
      q.includes("LEFT JOIN inquiry_case_dispositions")?p.case_lifecycle:
      q.includes("(SELECT COUNT(*) FROM inquiry_qa_registry)")?p.qa_scope:
      q.includes("FROM inquiry_limits")?p.rate_limits:p.retention_review;
    return {ok:true,json:async()=>({success:true,result:[{results:rows}]})};
  };
  const r=await collect(TIME,{accountId:"qa",databaseId:"qa-id",token:"synthetic"},fetcher);
  assert.equal(r.inquiry_total,0);assert.equal(asked.length,5);
});
test("remote permission denial fails closed, never interprets as no leads",async()=>{
  const fetcher=async()=>({ok:false,status:403});
  await assert.rejects(()=>collect(TIME,{accountId:"qa",databaseId:"qa",token:"synthetic"},fetcher),/HTTP 403/);
});
test("missing or partial operator credentials fail closed",async()=>{
  await assert.rejects(()=>collect(TIME,{accountId:"qa",databaseId:"qa"}),/credentials/);
});
test("missing actual D1 result fails closed",async()=>{
  const bad=async()=>({ok:true,json:async()=>({success:false,result:[]})});
  await assert.rejects(()=>collect(TIME,{accountId:"qa",databaseId:"qa",token:"synthetic"},bad),/unavailable/);
});

function withCase(p,values){
 Object.defineProperty(p,"case_lifecycle",{value:[{...p.case_lifecycle[0],...values}],configurable:true});
 return p;
}
test("an opened lead with only a reported reply still requires independent verification",()=>{
 const p=empty();p.notification_aging=[notification("delivery_verified",1)];
 withCase(p,{total:1,unacknowledged:0,acknowledged:1,reported:1});
 const result=reconcile(TIME,p);
 assert.equal(result.case_lifecycle.reported,1);
 assert.ok(result.alerts.some(a=>a.code==="OPEN_LEADS_REQUIRE_VERIFIED_RESPONSE"));
 assert.ok(result.alerts.some(a=>a.code==="REPORTED_RESPONSE_UNVERIFIED"));
});
test("aged ownerless and unresponded leads are escalated without exposing personal data",()=>{
 const p=empty();p.notification_aging=[notification("delivery_verified",2,90000,2,1)];
 withCase(p,{total:2,unacknowledged:1,acknowledged:1,aged_unacknowledged:1,aged_response_incomplete:1});
 const result=reconcile(TIME,p);
 assert.equal(result.alerts.find(a=>a.code==="UNACKNOWLEDGED_LEADS").priority,"P0");
 assert.equal(result.alerts.find(a=>a.code==="OPEN_LEADS_REQUIRE_VERIFIED_RESPONSE").priority,"P0");
 assert.equal(JSON.stringify(result).includes("work_email"),false);
});
test("closed lead without independently verified reply or waiver is a critical inconsistency",()=>{
 const p=empty();p.notification_aging=[notification("delivery_verified",1)];
 withCase(p,{total:1,unacknowledged:0,closed:1,closed_unverified:1});
 const x=reconcile(TIME,p);
 assert.equal(x.alerts.find(a=>a.code==="IMPOSSIBLE_CLOSED_CASE").priority,"P0");
});
test("older unresolved lead cannot silently disappear from retention review",()=>{
 const p=empty();p.notification_aging=[notification("delivery_verified",1,101*86400,1,1)];
 p.retention_review=[{aged_total:1,aged_pending:0,aged_provider:0,aged_delivered:1}];
 withCase(p,{total:1,unacknowledged:1,expired_unresolved:1});
 const x=reconcile(TIME,p);
 assert.equal(x.alerts.find(a=>a.code==="RETENTION_EXCEPTION_OR_APPROVAL_REQUIRED").priority,"P0");
});
test("an incomplete or internally inconsistent case aggregate cannot be shown as a clean queue",()=>{
 const p=empty();p.notification_aging=[notification("delivery_verified",1)];
 delete p.case_lifecycle;
 assert.throws(()=>reconcile(TIME,p),/Incomplete/);
 const q=empty();q.notification_aging=[notification("delivery_verified",1)];
 withCase(q,{total:0,unacknowledged:0});
 assert.throws(()=>reconcile(TIME,q),/inconsistent/i);
});

test("a known synthetic receipt is reconciled separately, not represented as a failed customer response",()=>{
 const p=empty();
 Object.defineProperty(p,"qa_scope",{value:[{raw_total:1,qa_total:1}],configurable:true});
 const result=reconcile(TIME,p);
 assert.equal(result.raw_inquiry_total,1);
 assert.equal(result.synthetic_qa_excluded,1);
 assert.equal(result.inquiry_total,0);
 assert.ok(!result.alerts.some(a=>a.code==="UNACKNOWLEDGED_LEADS"));
});
test("an alleged QA exclusion cannot conceal an unaccounted real lead",()=>{
 const p=empty();Object.defineProperty(p,"qa_scope",{value:[{raw_total:2,qa_total:1}],configurable:true});
 assert.throws(()=>reconcile(TIME,p),/QA conservation/);
});
test("unexpected QA count schema, missing QA scope and negative count all fail closed",()=>{
 for(const row of [{raw_total:1,qa_total:-1},{raw_total:1,qa_total:2},
   {raw_total:0,qa_total:0,work_email:"hidden@example.invalid"}]){
   const p=empty();Object.defineProperty(p,"qa_scope",{value:[row],configurable:true});
   assert.throws(()=>reconcile(TIME,p),/Invalid|conservation|Unexpected/);
 }
 const p=empty();delete p.qa_scope;
 assert.throws(()=>reconcile(TIME,p),/Incomplete/);
});
test("SQLite migration registers only the exact proven owner QA case, never a real customer lead",()=>{
 const db=new DatabaseSync(":memory:");
 try{
  db.exec("PRAGMA foreign_keys=ON");
  for(const n of ["0001_inquiry.sql","0002_inquiry_case_retention.sql",
    "0003_inquiry_verified_case_actions.sql","0004_inquiry_response_receipts.sql"]){
    db.exec(readFileSync(new URL("../site/migrations/"+n,import.meta.url),"utf8"));
  }
  const seed=db.prepare(`INSERT INTO inquiries
   (reference,idempotency_key,fingerprint,full_name,work_email,company_name,
    annual_spend,modes_json,details_json,accepted_at,notification_status)
   VALUES(?,?,?,?,?,?,?,?,?,?,'delivery_verified')`);
  const t=TIME-90000;
  seed.run("RA-20261017-26F3BC58","qa-key","qa-fingerprint","RETALLY QA TEST",
   "synthetic@example.invalid","RETALLY INTERNAL TEST","Under $250k",
   '["Parcel"]',"{}",t);
  seed.run("RA-20261017-CAFEBABE","lead-key","lead-fingerprint","Real Example",
   "lead@example.invalid","Example Shipper","$250k–$1M",'["LTL"]',"{}",t);
  const sql=readFileSync(new URL("../site/migrations/0005_inquiry_qa_registry.sql",import.meta.url),"utf8");
  db.exec(sql);db.exec(sql); // additive reruns preserve the one approved provenance row
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM inquiry_qa_registry").get().n,1);
  assert.throws(()=>db.exec("UPDATE inquiry_qa_registry SET tagged_at=1"),/immutable/);
  assert.throws(()=>db.exec("DELETE FROM inquiry_qa_registry"),/denied/);
  assert.throws(()=>db.prepare(`INSERT INTO inquiry_qa_registry
    (reference,provenance,evidence_ref,tagged_at)
    VALUES(?,'OWNER_LIVE_SYNTHETIC_ACCEPTANCE_20261017','github-value-hunt-ledger#466',?)`)
    .run("RA-20261017-CAFEBABE",TIME),/unreviewed/);
  // A real customer-like record must still produce the normal unanswered-lead alert.
  const parts=Object.fromEntries(readOnlyQueries(TIME).map(q=>[q.name,db.prepare(q.sql).all()]));
  assert.equal(parts.qa_scope[0].raw_total,2);
  assert.equal(parts.qa_scope[0].qa_total,1);
  assert.equal(parts.notification_aging.length,1);
  const result=reconcile(TIME,parts);
  assert.equal(result.raw_inquiry_total,2);
  assert.equal(result.inquiry_total,1);
  assert.equal(result.synthetic_qa_excluded,1);
  assert.equal(result.case_lifecycle.unacknowledged,1);
  assert.ok(result.alerts.some(a=>a.code==="UNACKNOWLEDGED_LEADS"&&a.count===1));
 }finally{db.close();}
});
