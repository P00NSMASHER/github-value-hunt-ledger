// Exercise the actual Pages entry points. All provider traffic is intercepted.
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { onRequestPost as freight } from "../functions/api/inquiry.js";
import { onRequestPost as group } from "../functions/api/group-inquiry.js";

const db = new DatabaseSync(process.argv[2], {enableForeignKeyConstraints:true});
const migrations = new URL("../freight/site/migrations/", import.meta.url);
for (const f of readdirSync(migrations).filter(x=>x.endsWith(".sql")).sort()) {
  db.exec(readFileSync(new URL(f,migrations),"utf8"));
}
db.exec(readFileSync(new URL("./retally_inquiry_feed.sql",import.meta.url),"utf8"));
assert.equal(db.prepare("SELECT count(*) AS n FROM inquiries").get().n,0,"use a new fixture database");
db.exec("CREATE TABLE retally_fixture_identity(singleton INTEGER PRIMARY KEY CHECK(singleton=1),source_id TEXT NOT NULL)");
db.prepare("INSERT INTO retally_fixture_identity VALUES(1,?)").run(crypto.randomUUID());
const env = {FREIGHT_INQUIRY_ENABLED:"1", FREIGHT_INQUIRY_MAILBOX_VERIFIED:"1",
  TURNSTILE_SITEKEY:"local", TURNSTILE_SECRET:"local", INQUIRY_RATE_SECRET:"fixture",
  RESEND_API_KEY:"re_fixture_only",INQUIRY_NOTIFY_TO:"jay@retallyrecovery.com",
  INQUIRY_DB:{prepare(sql){return {bind(...args){const s=db.prepare(sql);return {
    first:async()=>s.get(...args) ?? null,
    run:async()=>({success:true,meta:{changes:s.run(...args).changes}})};}};}}};
let captured = 0;
globalThis.fetch = async (url,opts)=>{
  if (String(url).startsWith("https://challenges.cloudflare.com/turnstile/")) {
    const token=opts.body.get("response");
    const isGroup=token==="local_group";
    return Response.json({success:token!=="invalid",action:isGroup?"retally_group":"retally_audit",
      hostname:isGroup?"group.retallyrecovery.com":"www.retallyrecovery.com"});
  }
  if (String(url)==="https://api.resend.com/emails"){captured++;return Response.json({id:crypto.randomUUID()});}
  throw new Error("unexpected transport");
};
const payload={fullName:"Riley Fixture",workEmail:"riley@example.invalid",companyName:"Fixture Distribution",
 annualSpend:"$1M–$5M",modes:["LTL"],campaign:{utm_source:"instagram",utm_medium:"organic_social",
 utm_campaign:"retally_os_freight_pilot",utm_content:"liftgate_evidence"},idempotencyKey:crypto.randomUUID(),turnstileToken:"local"};
async function request(body,kind="freight",ip="192.0.2.1") {
  const isGroup=kind==="group";
  const req=new Request("https://www.retallyrecovery.com/api/"+(isGroup?"group-inquiry":"inquiry"),
   {method:"POST",headers:{Origin:"https://"+(isGroup?"group":"www")+".retallyrecovery.com",
   "Content-Type":"application/json","CF-Connecting-IP":ip},body:JSON.stringify(body)});
  return (isGroup?group:freight)({request:req,env});
}
const changes=()=>db.prepare("SELECT total_changes() AS n").get().n;
async function measure(fn){const before=changes();const result=await fn();return [result,changes()-before];}
const [invalid,invalidWrites]=await measure(()=>request({...payload,website:"spam"}));
assert.equal(invalid.status,400);
const [rejected,rejectedWrites]=await measure(()=>request({...payload,turnstileToken:"invalid"}));
assert.equal(rejected.status,400);
const [pair,firstPairWrites]=await measure(()=>Promise.all([request(payload),request(payload)]));
assert.deepEqual(pair.map(x=>x.status),[202,202]);
const receipts=await Promise.all(pair.map(x=>x.json()));
assert.equal(receipts[0].reference,receipts[1].reference);
assert.deepEqual(receipts.map(x=>x.duplicate).sort(),[false,true]);
const [replay,replayWrites]=await measure(()=>request(payload));
assert.equal(replay.status,202);assert.equal(replayWrites,0);
assert.equal((await request({...payload,fullName:"Different Name"})).status,409);
const groupBody={fullName:"Riley Fixture",workEmail:payload.workEmail,companyName:payload.companyName,
 business:"capturebrief",message:"Synthetic scoped research inquiry",consent:true,
 turnstileToken:"local_group",idempotencyKey:crypto.randomUUID()};
const [groupResult,groupWrites]=await measure(()=>request(groupBody,"group","192.0.2.2"));
assert.equal(groupResult.status,202);
assert.equal(db.prepare("SELECT count(*) AS n FROM retally_inquiry_feed").get().n,2);
assert.equal(captured,2);
console.log(JSON.stringify({fixture:true,accepted:2,freight_reference:receipts[0].reference,
 capturebrief_reference:(await groupResult.json()).reference,unique_freight_leads_expected:1,
 mail_intercepted:captured,external_sends:0,sqlite_row_mutations_including_triggers:{
 invalid:invalidWrites,rejected_turnstile:rejectedWrites,concurrent_freight_pair:firstPairWrites,replay:replayWrites,group:groupWrites}}));
db.close();
