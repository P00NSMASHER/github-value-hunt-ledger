import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {DatabaseSync} from "node:sqlite";
import {webcrypto} from "node:crypto";
import {onRequestPost} from "../../functions/api/internal/inquiry-case.js";
import {onRequestPost as onResponsePost} from "../../functions/api/internal/inquiry-response.js";
const issuer="https://qa-retally.cloudflareaccess.com";
const audience="a".repeat(30);
const reviewer={sub:"sub-reviewer-1",email:"reviewer@example.org"};
const approver={sub:"sub-approver-2",email:"approver@example.org"};
const roleLists={
  RETALLY_INQUIRY_REVIEWERS:JSON.stringify([reviewer]),
  RETALLY_INQUIRY_APPROVERS:JSON.stringify([approver])
};
const now=()=>Math.floor(Date.now()/1000);
const b64=x=>Buffer.from(x).toString("base64url");
const digest="a".repeat(64);
const uuid=n=>"aaaaaaaa-bbbb-4ccc-8ddd-"+String(n).padStart(12,"0");
let pair,publicJwk;
const req=(token,raw={action:"ACKNOWLEDGE",reference:"RA-20261008-AAAABBBB",
  actionId:uuid(1),evidenceDigest:digest},opts={})=>
  new Request("https://www.retallyrecovery.com/api/internal/inquiry-case",
    {method:"POST",headers:{"Content-Type":"application/json",
     Origin:opts.origin||"https://www.retallyrecovery.com",
     ...(token?{"Cf-Access-Jwt-Assertion":token}:{}),...(opts.headers||{})},
    body:JSON.stringify(raw)});
const token=async(identity=reviewer,claims={},keyPair=pair)=>{
  const issued=now();
  const payload={iss:issuer,aud:[audience],sub:identity.sub,email:identity.email,
    iat:issued-30,exp:issued+3600,...claims};
  const header={alg:"RS256",kid:"test-key",typ:"JWT"};
  const h=b64(JSON.stringify(header))+"."+b64(JSON.stringify(payload));
  const sig=await webcrypto.subtle.sign("RSASSA-PKCS1-v1_5",
    keyPair.privateKey,new TextEncoder().encode(h));
  return h+"."+b64(new Uint8Array(sig));
};
function dbWithFixture({daysOld=91,refs=["RA-20261008-AAAABBBB"]}={}){
  const db=new DatabaseSync(":memory:");
  for(const file of ["0001_inquiry.sql","0002_inquiry_case_retention.sql",
    "0003_inquiry_verified_case_actions.sql","0004_inquiry_response_receipts.sql"]){
    db.exec(readFileSync(new URL("./migrations/"+file,import.meta.url),"utf8"));
  }
  for(const ref of refs)db.prepare(
    "INSERT INTO inquiries(reference,idempotency_key,fingerprint,full_name,work_email,company_name,annual_spend,modes_json,details_json,accepted_at,notification_status) VALUES(?,?,?,?,?,?,?,?,?,?,?)"
  ).run(ref,"idem-"+ref,"synthetic","Synthetic","sample@example.invalid","Sample Co","$1M-$5M",
    '["LTL"]',"{}",now()-daysOld*86400,"pending");
  const adapter={prepare(sql){
    return {bind(...values){return {async first(){
      return db.prepare(sql).get(...values)??null;
    }}}}
  }};
  return {db,adapter};
}
const env=db=>({
  INQUIRY_DB:db,
  RETALLY_CASE_WRITES_ENABLED:"1",
  RETALLY_CASE_POLICY_APPROVED:"1",
  RETALLY_ACCESS_TEAM_DOMAIN:issuer,
  RETALLY_ACCESS_AUD:audience,
  ...roleLists
});
function count(db,table){return Number(db.prepare("SELECT COUNT(*) AS n FROM "+table).get().n)}
function seedVerifiedResponse(db,ref="RA-20261008-AAAABBBB") {
 // Purely synthetic two-step fixture; no real customer response is claimed.
 const sent=now()-60,verified=now();
 db.prepare(`INSERT INTO inquiry_response_states
  (reference,response_state,responded_at,reported_by,response_evidence_digest,
   last_action_id,last_action,last_actor_sub,last_evidence_digest,last_action_at)
  VALUES(?,'REPORTED',?,?,?,?,?,?,?,?)`).run(
  ref,sent,reviewer.sub,"a".repeat(64),uuid(80),
  "RECORD_RESPONSE",reviewer.sub,"a".repeat(64),sent);
 db.prepare(`UPDATE inquiry_response_states SET response_state='VERIFIED',
  verified_at=?,verified_by=?,verification_evidence_digest=?,
  last_action_id=?,last_action=?,last_actor_sub=?,last_evidence_digest=?,last_action_at=?
  WHERE reference=? AND response_state='REPORTED'`).run(
  verified,approver.sub,"b".repeat(64),uuid(81),
  "VERIFY_RESPONSE",approver.sub,"b".repeat(64),verified,ref);
}
let signerReady;
const setup=async()=>{
  pair=await webcrypto.subtle.generateKey(
    {name:"RSASSA-PKCS1-v1_5",modulusLength:2048,
     publicExponent:new Uint8Array([1,0,1]),hash:"SHA-256"},true,["sign","verify"]);
  publicJwk={...await webcrypto.subtle.exportKey("jwk",pair.publicKey),kid:"test-key",
    alg:"RS256",use:"sig"};
  globalThis.fetch=async url=>{
    if(url!==issuer+"/cdn-cgi/access/certs")throw Error("forbidden outbound URL");
    return Response.json({keys:[publicJwk]});
  };
};
const originalFetch=globalThis.fetch;
signerReady=setup();
test.after(()=>{globalThis.fetch=originalFetch;});
async function run(identity,body,e){
  await signerReady;
  return onRequestPost({request:req(await token(identity),body),env:e});
}
function replyRequest(signed,raw,opts={}){
 return new Request("https://www.retallyrecovery.com/api/internal/inquiry-response",{
  method:"POST",headers:{"Content-Type":"application/json",
   Origin:opts.origin||"https://www.retallyrecovery.com",
   ...(signed?{"Cf-Access-Jwt-Assertion":signed}:{})},
  body:JSON.stringify(raw)
 });
}
async function runResponse(identity,body,e,options={}){
 await signerReady;
 return onResponsePost({request:replyRequest(await token(identity),body,options),env:e});
}
const initial=(action,reference="RA-20261008-AAAABBBB",index=1,extra={})=>({
  action,reference,actionId:uuid(index),evidenceDigest:digest,...extra
});
test("fails closed when operator service is disabled, even with genuine Access JWT",async()=>{
  await signerReady;const {db,adapter}=dbWithFixture();const e=env(adapter);
  e.RETALLY_CASE_WRITES_ENABLED="0";
  assert.equal((await run(reviewer,initial("ACKNOWLEDGE"),e)).status,403);
  assert.equal(count(db,"inquiry_case_dispositions"),0);db.close();
});
test("missing JWT and spoofed email header do not authorize the operation",async()=>{
  await signerReady;const {db,adapter}=dbWithFixture();
  const r=req(null,initial("ACKNOWLEDGE"),{headers:{"X-Forwarded-Email":"reviewer@example.org"}});
  assert.equal((await onRequestPost({request:r,env:env(adapter)})).status,403);
  assert.equal(count(db,"inquiry_case_action_audit"),0);db.close();
});
test("tampered signature fails, even if role claims appear correct",async()=>{
  await signerReady;const {db,adapter}=dbWithFixture();
  const good=await token(reviewer);
  const bad=good.slice(0,-2)+(good.endsWith("AA")?"BB":"AA");
  assert.equal((await onRequestPost({request:req(bad),env:env(adapter)})).status,403);
  db.close();
});
test("issuer audience expiry and future timestamp are verified",async()=>{
  await signerReady;const {db,adapter}=dbWithFixture();
  for(const claims of [
    {iss:"https://imposter.cloudflareaccess.com"},
    {aud:["not-retally"]},{exp:now()-1},
    {iat:now()+900,exp:now()+1000},
    {nbf:now()+900}
  ]){
    const r=await onRequestPost({request:req(await token(reviewer,claims)),env:env(adapter)});
    assert.equal(r.status,403,JSON.stringify(claims));
  }
  db.close();
});
test("role allowlist matches signed sub and email, not just either one",async()=>{
  await signerReady;const {db,adapter}=dbWithFixture();
  const r=await onRequestPost({request:req(await token(
    {sub:reviewer.sub,email:"someone@example.org"})),env:env(adapter)});
  assert.equal(r.status,403);db.close();
});
test("wrong site origin is refused despite valid Access token",async()=>{
  await signerReady;const {db,adapter}=dbWithFixture();
  const r=await onRequestPost({request:req(await token(reviewer),
    initial("ACKNOWLEDGE"),{origin:"https://wrong.example"}),env:env(adapter)});
  assert.equal(r.status,403);db.close();
});
test("valid signed reviewer acknowledges a real inquiry and creates immutable audit",async()=>{
  const {db,adapter}=dbWithFixture();const r=await run(reviewer,initial("ACKNOWLEDGE"),env(adapter));
  assert.equal(r.status,200);
  assert.equal(count(db,"inquiry_case_dispositions"),1);
  assert.equal(count(db,"inquiry_case_action_audit"),1);
  assert.equal(db.prepare("SELECT actor_sub FROM inquiry_case_action_audit").get().actor_sub,
    reviewer.sub);
  assert.throws(()=>db.exec("DELETE FROM inquiry_case_action_audit"),/immutable/);
  db.close();
});
test("identical acknowledgment replay is rejected without double audit",async()=>{
  const {db,adapter}=dbWithFixture();const e=env(adapter);
  assert.equal((await run(reviewer,initial("ACKNOWLEDGE"),e)).status,200);
  assert.equal((await run(reviewer,initial("ACKNOWLEDGE"),e)).status,409);
  assert.equal(count(db,"inquiry_case_action_audit"),1);db.close();
});
test("cannot close or approve a case before acknowledgment",async()=>{
  const {db,adapter}=dbWithFixture();const e=env(adapter);
  assert.equal((await run(reviewer,initial("CLOSE"),e)).status,409);
  assert.equal((await run(approver,initial("APPROVE_PURGE",undefined,2),e)).status,409);
  db.close();
});
test("only a reviewer closes a real acknowledged case",async()=>{
  const {db,adapter}=dbWithFixture();const e=env(adapter);
  await run(reviewer,initial("ACKNOWLEDGE"),e);
  assert.equal((await run(approver,initial("CLOSE",undefined,2),e)).status,403);
  assert.equal((await run(reviewer,initial("CLOSE",undefined,3),e)).status,409);
  seedVerifiedResponse(db);
  assert.equal((await run(reviewer,initial("CLOSE",undefined,3),e)).status,200);
  assert.equal(count(db,"inquiry_case_action_audit"),2);db.close();
});
test("self approval denied; distinct signed approver can approve eligible closed case",async()=>{
  const {db,adapter}=dbWithFixture();const e=env(adapter);
  await run(reviewer,initial("ACKNOWLEDGE"),e);
  seedVerifiedResponse(db);
  await run(reviewer,initial("CLOSE",undefined,2),e);
  assert.equal((await run(reviewer,initial("APPROVE_PURGE",undefined,3),e)).status,403);
  assert.equal((await run(approver,initial("APPROVE_PURGE",undefined,4),e)).status,200);
  const row=db.prepare("SELECT purge_approved_by FROM inquiry_case_dispositions").get();
  assert.equal(row.purge_approved_by,approver.sub);
  assert.equal(count(db,"inquiry_case_action_audit"),3);
  db.close();
});
test("retention-eligible check blocks young cases even with separate approver",async()=>{
  const {db,adapter}=dbWithFixture({daysOld:20});const e=env(adapter);
  await run(reviewer,initial("ACKNOWLEDGE"),e);
  seedVerifiedResponse(db);
  await run(reviewer,initial("CLOSE",undefined,2),e);
  assert.equal((await run(approver,initial("APPROVE_PURGE",undefined,3),e)).status,409);
  db.close();
});
test("an active legal hold blocks purge, and only an approver releases it",async()=>{
  const {db,adapter}=dbWithFixture();const e=env(adapter);
  await run(reviewer,initial("ACKNOWLEDGE"),e);
  assert.equal((await run(reviewer,initial("SET_HOLD",undefined,2,{holdReason:"LEGAL"}),e)).status,200);
  seedVerifiedResponse(db);
  await run(reviewer,initial("CLOSE",undefined,3),e);
  assert.equal((await run(approver,initial("APPROVE_PURGE",undefined,4),e)).status,409);
  assert.equal((await run(reviewer,initial("RELEASE_HOLD",undefined,5),e)).status,403);
  assert.equal((await run(approver,initial("RELEASE_HOLD",undefined,6),e)).status,200);
  assert.equal((await run(approver,initial("APPROVE_PURGE",undefined,7),e)).status,200);
  assert.equal(count(db,"inquiry_case_action_audit"),5);db.close();
});
test("duplicate action ID cannot be replayed against a second case",async()=>{
  const refs=["RA-20261008-AAAABBBB","RA-20261008-CCCCDDDD"];
  const {db,adapter}=dbWithFixture({refs});const e=env(adapter);
  assert.equal((await run(reviewer,initial("ACKNOWLEDGE",refs[0],1),e)).status,200);
  assert.equal((await run(reviewer,initial("ACKNOWLEDGE",refs[1],1),e)).status,409);
  assert.equal(count(db,"inquiry_case_dispositions"),1);
  assert.equal(count(db,"inquiry_case_action_audit"),1);db.close();
});
test("missing or malformed evidence is not accepted",async()=>{
  await signerReady;const {db,adapter}=dbWithFixture();const e=env(adapter);
  for(const raw of [
    initial("ACKNOWLEDGE",undefined,1,{evidenceDigest:"not-a-hash"}),
    initial("ACKNOWLEDGE",undefined,2,{secret:"leak"}),
    initial("SET_HOLD",undefined,3,{holdReason:"ANYTHING"})
  ]){
    assert.equal((await onRequestPost({request:req(await token(reviewer),raw),env:e})).status,400);
  }
  assert.equal(count(db,"inquiry_case_action_audit"),0);db.close();
});
test("operator cannot actually delete a case through this endpoint",async()=>{
  await signerReady;const {db,adapter}=dbWithFixture();
  const r=await onRequestPost({request:req(await token(approver),
    initial("DELETE",undefined,5)),env:env(adapter)});
  assert.equal(r.status,400);
  assert.equal(count(db,"inquiries"),1);db.close();
});

test("response writes are disabled unless independent signed operator policy is enabled",async()=>{
 const {db,adapter}=dbWithFixture(),e=env(adapter);
 e.RETALLY_CASE_WRITES_ENABLED="0";
 assert.equal((await runResponse(reviewer,initial("RECORD_RESPONSE",undefined,11),e)).status,403);
 const unsigned=replyRequest(null,initial("RECORD_RESPONSE",undefined,12),{});
 assert.equal((await onResponsePost({request:unsigned,env:env(adapter)})).status,403);
 assert.equal(count(db,"inquiry_response_states"),0);db.close();
});
test("response cannot be recorded before genuine case acknowledgment",async()=>{
 const {db,adapter}=dbWithFixture(),e=env(adapter);
 assert.equal((await runResponse(reviewer,initial("RECORD_RESPONSE",undefined,11),e)).status,409);
 assert.equal(count(db,"inquiry_response_action_audit"),0);db.close();
});
test("recorded reply is not independently verified and cannot close the lead",async()=>{
 const {db,adapter}=dbWithFixture(),e=env(adapter);
 await run(reviewer,initial("ACKNOWLEDGE"),e);
 assert.equal((await runResponse(reviewer,initial("RECORD_RESPONSE",undefined,11),e)).status,200);
 assert.equal(db.prepare("SELECT response_state FROM inquiry_response_states").get().response_state,"REPORTED");
 assert.equal((await run(reviewer,initial("CLOSE",undefined,12),e)).status,409);
 assert.equal((await runResponse(reviewer,initial("VERIFY_RESPONSE",undefined,13),e)).status,403);
 assert.equal((await runResponse(reviewer,initial("RECORD_RESPONSE",undefined,14),e)).status,409);
 assert.equal(count(db,"inquiry_response_action_audit"),1);db.close();
});
test("distinct signed approver verifies response evidence, then case can close",async()=>{
 const {db,adapter}=dbWithFixture(),e=env(adapter);
 await run(reviewer,initial("ACKNOWLEDGE"),e);
 assert.equal((await runResponse(reviewer,initial("RECORD_RESPONSE",undefined,11),e)).status,200);
 assert.equal((await runResponse(approver,initial("VERIFY_RESPONSE",undefined,12,{evidenceDigest:"b".repeat(64)}),e)).status,200);
 assert.equal(db.prepare("SELECT response_state FROM inquiry_response_states").get().response_state,"VERIFIED");
 assert.equal((await run(reviewer,initial("CLOSE",undefined,13),e)).status,200);
 assert.equal(count(db,"inquiry_response_action_audit"),2);
 assert.throws(()=>db.exec("DELETE FROM inquiry_response_action_audit"),/immutable/);
 assert.throws(()=>db.exec("UPDATE inquiry_response_states SET response_state='REPORTED'"),/transition_denied|CHECK/);
 db.close();
});
test("authorized approver can waive reply only with explicit reason and separate actor",async()=>{
 const {db,adapter}=dbWithFixture(),e=env(adapter);
 await run(reviewer,initial("ACKNOWLEDGE"),e);
 assert.equal((await runResponse(reviewer,initial("WAIVE_RESPONSE",undefined,11,{reason:"SPAM"}),e)).status,403);
 assert.equal((await runResponse(approver,initial("WAIVE_RESPONSE",undefined,12),e)).status,400);
 assert.equal((await runResponse(approver,initial("WAIVE_RESPONSE",undefined,13,{reason:"ANYTHING"}),e)).status,400);
 assert.equal((await runResponse(approver,initial("WAIVE_RESPONSE",undefined,14,{reason:"SPAM"}),e)).status,200);
 assert.equal(db.prepare("SELECT response_state,waiver_reason FROM inquiry_response_states").get().response_state,"WAIVED");
 assert.equal((await run(reviewer,initial("CLOSE",undefined,15),e)).status,200);
 assert.equal((await runResponse(reviewer,initial("RECORD_RESPONSE",undefined,16),e)).status,409);
 db.close();
});
test("wrong origin, unrecognized input and missing evidence fail with zero response writes",async()=>{
 const {db,adapter}=dbWithFixture(),e=env(adapter);
 await run(reviewer,initial("ACKNOWLEDGE"),e);
 assert.equal((await runResponse(reviewer,initial("RECORD_RESPONSE",undefined,11),e,{origin:"https://other.example"})).status,403);
 assert.equal((await runResponse(reviewer,initial("RECORD_RESPONSE",undefined,12,{evidenceDigest:"not-verified"}),e)).status,400);
 assert.equal((await runResponse(reviewer,initial("RECORD_RESPONSE",undefined,13,{extra:"leak"}),e)).status,400);
 assert.equal(count(db,"inquiry_response_states"),0);
 assert.equal(count(db,"inquiry_response_action_audit"),0);db.close();
});
test("response evidence survives approved retention purge only as immutable action receipt",async()=>{
 const {db,adapter}=dbWithFixture({daysOld:91}),e=env(adapter);
 await run(reviewer,initial("ACKNOWLEDGE"),e);
 await runResponse(reviewer,initial("RECORD_RESPONSE",undefined,11),e);
 await runResponse(approver,initial("VERIFY_RESPONSE",undefined,12,{evidenceDigest:"b".repeat(64)}),e);
 await run(reviewer,initial("CLOSE",undefined,13),e);
 assert.equal((await run(approver,initial("APPROVE_PURGE",undefined,14),e)).status,200);
 db.exec("PRAGMA foreign_keys=ON");
 db.exec("DELETE FROM inquiries WHERE reference='RA-20261008-AAAABBBB'");
 assert.equal(count(db,"inquiries"),0);
 assert.equal(count(db,"inquiry_response_states"),0);
 assert.equal(count(db,"inquiry_response_action_audit"),2);
 assert.equal(count(db,"inquiry_purge_audit"),1);
 db.close();
});

test("database rejects direct CLOSED state and unverified closure even by privileged SQL",async()=>{
 const {db,adapter}=dbWithFixture(),e=env(adapter);
 const t=now();
 assert.throws(()=>db.prepare(`INSERT INTO inquiry_case_dispositions
   (reference,case_state,operator_id,acknowledged_at,closed_at)
   VALUES(?,'CLOSED','synthetic-admin',?,?)`).run("RA-20261008-AAAABBBB",t-60,t),
   /inquiry_cannot_start_closed/);
 assert.equal((await run(reviewer,initial("ACKNOWLEDGE"),e)).status,200);
 assert.throws(()=>db.prepare(`UPDATE inquiry_case_dispositions SET
    case_state='CLOSED',closed_at=?,retention_until=?
    WHERE reference=?`).run(t,t+90*86400,"RA-20261008-AAAABBBB"),
   /inquiry_close_requires_verified_response_or_waiver/);
 assert.equal(count(db,"inquiry_case_action_audit"),1);
 db.close();
});
test("database denies fabricated one-step VERIFIED response and raw row removal",async()=>{
 const {db,adapter}=dbWithFixture(),e=env(adapter);
 await run(reviewer,initial("ACKNOWLEDGE"),e);
 const t=now();
 assert.throws(()=>db.prepare(`INSERT INTO inquiry_response_states
    (reference,response_state,responded_at,reported_by,response_evidence_digest,
     verified_at,verified_by,verification_evidence_digest,last_action_id,
     last_action,last_actor_sub,last_evidence_digest,last_action_at)
    VALUES(?,'VERIFIED',?,?,?,?,?,?,?,?,?,?,?)`).run(
       "RA-20261008-AAAABBBB",t-10,reviewer.sub,"a".repeat(64),
       t,approver.sub,"b".repeat(64),uuid(55),"VERIFY_RESPONSE",
       approver.sub,"b".repeat(64),t),/inquiry_response_requires_separate_review_transition/);
 assert.equal((await runResponse(reviewer,initial("RECORD_RESPONSE",undefined,56),e)).status,200);
 assert.throws(()=>db.exec("DELETE FROM inquiry_response_states"),
    /inquiry_response_delete_denied/);
 assert.equal(count(db,"inquiry_response_action_audit"),1);
 db.close();
});
