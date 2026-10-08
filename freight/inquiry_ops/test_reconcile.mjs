import test from "node:test";
import assert from "node:assert/strict";
import {readOnlyQueries,reconcile,collect,dryRun} from "./reconcile.mjs";

const TIME=Math.floor(Date.parse("2026-10-08T16:00:00Z")/1000);
const empty=()=>({
  notification_aging:[],
  retention_review:[{aged_total:0,aged_pending:0,aged_provider:0,aged_delivered:0}],
  rate_limits:[{expired_total:0}]
});
function notification(s,n,age=300,overHour=0,overDay=0) {
  return {notification_status:s,total:n,oldest_at:TIME-age,aged_hour:overHour,aged_day:overDay};
}
const clone=x=>JSON.parse(JSON.stringify(x));
test("SQL is exclusively read-only, aggregate-only, bounded and avoids personal data",()=>{
  const queries=readOnlyQueries(TIME);
  assert.deepEqual(queries.map(x=>x.name),["notification_aging","retention_review","rate_limits"]);
  for(const q of queries) {
    assert.match(q.sql,/^SELECT /);
    assert.doesNotMatch(q.sql,/\b(?:DELETE|UPDATE|INSERT|DROP|ALTER|REPLACE|TRUNCATE)\b/i);
    assert.doesNotMatch(q.sql,/\b(?:full_name|work_email|company_name|details_json|idempotency_key|fingerprint)\b/i);
  }
});
test("dry run has no credential values or API request",()=>{
  const x=dryRun("2026-10-08T16:00:00Z");
  assert.equal(x.statements.length,3);
  assert.match(x.warning,/Never interpret provider acceptance/);
});
test("reject malformed UTC time",()=>{
  assert.throws(()=>dryRun("2026-10-08"),/ISO-8601/);
  assert.throws(()=>dryRun("2026-13-08T16:00:00Z"),/Invalid UTC/);
});
test("empty D1 aggregates are valid zero workload, NOT proof of operation",()=>{
  const r=reconcile(TIME,empty());
  assert.equal(r.inquiry_total,0);
  assert.equal(r.operational_acceptance,"NOT_PROVEN");
  assert.ok(r.alerts.some(a=>a.code==="HUMAN_FOLLOWUP_UNTRACKED"));
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
  assert.equal(r.operational_acceptance,"NOT_PROVEN");
});
test("delivery_verified still does not establish human handling",()=>{
  const p=empty();
  p.notification_aging=[notification("delivery_verified",3,90,0,0)];
  const r=reconcile(TIME,p);
  assert.equal(r.inquiry_total,3);
  assert.ok(r.alerts.some(a=>a.code==="HUMAN_FOLLOWUP_UNTRACKED"));
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
    let rows=q.includes("GROUP BY")?p.notification_aging:q.includes("FROM inquiry_limits")?p.rate_limits:p.retention_review;
    return {ok:true,json:async()=>({success:true,result:[{results:rows}]})};
  };
  const r=await collect(TIME,{accountId:"qa",databaseId:"qa-id",token:"synthetic"},fetcher);
  assert.equal(r.inquiry_total,0);assert.equal(asked.length,3);
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
