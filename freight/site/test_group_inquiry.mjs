import test from "node:test";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";
import assert from "node:assert/strict";
import {normalize, BUSINESSES, notificationText, onRequestPost, onRequestGet} from "../../functions/api/group-inquiry.js";
import {onRequestPost as freightPost} from "../../functions/api/inquiry.js";

const key = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
const good = () => ({
  business:"capturebrief",fullName:"Synthetic Test",workEmail:"qa@example.org",companyName:"Example Research",
  message:"I have a public opportunity link and a scope question.",consent:true,
  idempotencyKey:key,turnstileToken:"test-token",website:""
});
function env(db) {return {
  FREIGHT_INQUIRY_ENABLED:"1",FREIGHT_INQUIRY_MAILBOX_VERIFIED:"1",
  TURNSTILE_SITEKEY:"sitekey-synthetic-123456",TURNSTILE_SECRET:"secret",
  INQUIRY_RATE_SECRET:"salt",RESEND_API_KEY:"re_synthetic_test_key",
  INQUIRY_NOTIFY_TO:"jay@retallyrecovery.com",INQUIRY_DB:db
};}
function mockDb({failInsert=false,failNotificationUpdate=false}={}) {
  const inquiries=new Map(),limits=new Map(),sqlCalls=[],inserts=[];
  return {inquiries,limits,sqlCalls,inserts,
    prepare(sql) {sqlCalls.push(sql);return { bind(...params) {return {
      async first() {
        if(sql.startsWith("SELECT reference")) return inquiries.get(params[0]) || null;
        if(sql.startsWith("INSERT INTO inquiry_limits")) {
          const hits=(limits.get(params[0]) || 0)+1;
          limits.set(params[0],hits);
          return {hits};
        }
        throw Error("Unexpected first SQL: "+sql);
      },
      async run() {
        if(sql.startsWith("INSERT INTO inquiries")) {
          inserts.push(params);
          if(failInsert) throw Error("Simulated durable-store failure");
          if(inquiries.has(params[1])) return {success:true,meta:{changes:0}};
          inquiries.set(params[1],{reference:params[0],fingerprint:params[2],notification_status:"pending"});
          return {success:true,meta:{changes:1}};
        }
        if(sql.startsWith("UPDATE inquiries")) {
          if(failNotificationUpdate) throw Error("Simulated notification status write failure");
          for(const r of inquiries.values()) if(r.reference===params[1])r.notification_status="provider_accepted";
          return {success:true,meta:{changes:1}};
        }
        if(sql.startsWith("DELETE FROM inquiries")) {
          // Reproduce the original destructive behavior on historical records.
          for(const [k,v] of inquiries) if(v.accepted_at < params[0]) inquiries.delete(k);
          return {success:true};
        }
        if(sql.startsWith("DELETE FROM inquiry_limits")) return {success:true};
        throw Error("Unexpected run SQL: "+sql);
      }
    };}}; }
  };
}
function request(data=good(),{origin="https://www.retallyrecovery.com",host="www.retallyrecovery.com",contentType="application/json"}={}) {
  return new Request("https://"+host+"/api/group-inquiry",{
    method:"POST",headers:{"Origin":origin,"Content-Type":contentType,"CF-Connecting-IP":"198.51.100.4"},
    body:JSON.stringify(data)
  });
}
function mockRemote({captcha=true,notify=true,providerResponse=null,providerStatus=null,transportThrows=false,action="retally_group"}={}) {
  const real=globalThis.fetch;
  let verifications=0,notifications=0;
  const sent=[];
  globalThis.fetch=async (url, options={}) => {
    if(String(url).includes("siteverify")) {
      verifications++;
      return Response.json({success:captcha,action,hostname:"www.retallyrecovery.com"});
    }
    if(String(url)==="https://api.resend.com/emails") {
      notifications++;
      sent.push({url:String(url),method:options.method,headers:options.headers,
        body:JSON.parse(options.body)});
      if(transportThrows) throw Error("Synthetic network timeout");
      if(providerResponse==="invalid-json") return new Response("{invalid", {status:200});
      return Response.json(providerResponse ?? {id:"96bb5678-1234-4fbc-8fed-123456789abc"},
        {status:providerStatus ?? (notify?200:503)});
    }
    throw Error("Unexpected URL");
  };
  return { get verifications(){return verifications;},get notifications(){return notifications;},
    get sent(){return sent;},restore(){globalThis.fetch=real;} };
}

test("all published businesses and general enquiries use the same contact-only contract",()=>{
  assert.equal(Object.keys(BUSINESSES).length,12);
  for(const business of Object.keys(BUSINESSES)){
    const p=normalize({...good(),business,companyName:""});
    assert.ok(p,business);assert.equal(p.inquiryKind,"group_contact");
    assert.equal(p.annualSpend,"");assert.deepEqual(p.modes,[]);
    assert.match(notificationText("RA-20261022-12345678",p),/Contact request only/);
  }
  for(const patch of [{business:"__proto__"},{business:"constructor"},{business:"other"},
    {consent:false},{consent:"true"},{website:"spam"},{message:""},
    {companyName:"bank account"},{message:"Here is an API key"},
    {workEmail:"bad@\nexample.org"},{files:["document"]},{recipient:"other@example.org"},
    {message:"x".repeat(801)},{turnstileAction:"retally_audit"}]){
    assert.equal(normalize({...good(),...patch}),null,JSON.stringify(patch));
  }
});
test("group transport is disabled when existing provider gates are incomplete",async()=>{
  const db=mockDb(),e=env(db);delete e.RESEND_API_KEY;
  assert.equal((await onRequestGet({env:e})).status,503);
  assert.equal((await onRequestPost({request:request(),env:e})).status,503);
  assert.equal(db.sqlCalls.length,0);
});
test("origins, uploads and oversized requests fail before contacting providers",async()=>{
  const e=env(mockDb()),remote=mockRemote();
  try{
    assert.equal((await onRequestPost({request:request(good(),{origin:"https://another.example"}),env:e})).status,403);
    assert.equal((await onRequestPost({request:request(good(),{contentType:"multipart/form-data"}),env:e})).status,415);
    assert.equal((await onRequestPost({request:request({...good(),message:"x".repeat(9000)}),env:e})).status,413);
    assert.equal(remote.verifications,0);assert.equal(remote.notifications,0);
    assert.equal(e.INQUIRY_DB.inquiries.size,0);
  }finally{remote.restore();}
});
test("a freight Turnstile result cannot authorize a group submission",async()=>{
  const e=env(mockDb()),remote=mockRemote({action:"retally_audit"});
  try{
    assert.equal((await onRequestPost({request:request(),env:e})).status,400);
    assert.equal(e.INQUIRY_DB.inquiries.size,0);assert.equal(remote.notifications,0);
  }finally{remote.restore();}
});
test("stores the selected business and returns a durable receipt with one fixed-inbox notification",async()=>{
  const db=mockDb(),e=env(db),remote=mockRemote();
  try{
    const first=await onRequestPost({request:request(),env:e});
    assert.equal(first.status,202);const body=await first.json();
    assert.equal(body.received,true);assert.equal(body.notificationPending,false);
    assert.match(body.reference,/^RA-\d{8}-[A-F0-9]{8}$/);
    const saved=db.inserts[0];
    assert.equal(saved[6],"");assert.equal(saved[7],"[]");
    assert.deepEqual(JSON.parse(saved[8]),{inquiryKind:"group_contact",business:"capturebrief",message:good().message,consent:true});
    const sent=remote.sent[0].body;
    assert.deepEqual(sent.to,["jay@retallyrecovery.com"]);
    assert.equal(sent.subject,"RETALLY Group Inquiry | "+body.reference);
    assert.match(sent.text,/Business: CaptureBrief/);assert.doesNotMatch(sent.text,/Annual freight spend/);
    assert.equal(sent.attachments,undefined);assert.equal(sent.reply_to,good().workEmail);
    const again=await (await onRequestPost({request:request(),env:e})).json();
    assert.equal(again.reference,body.reference);assert.equal(again.duplicate,true);
    assert.equal(remote.notifications,1);assert.equal(remote.verifications,1);
  }finally{remote.restore();}
});
test("a reused request identifier cannot change business or cross into a freight request",async()=>{
  const e=env(mockDb()),remote=mockRemote();
  try{
    assert.equal((await onRequestPost({request:request(),env:e})).status,202);
    assert.equal((await onRequestPost({request:request({...good(),business:"permitplate"}),env:e})).status,409);
    const freight={fullName:"Synthetic Test",workEmail:"qa@example.org",companyName:"Example Research",
      annualSpend:"Under $250k",modes:["LTL"],idempotencyKey:key,turnstileToken:"test-token"};
    assert.equal((await freightPost({request:request(freight),env:e})).status,409);
    assert.equal(remote.notifications,1);assert.equal(e.INQUIRY_DB.inquiries.size,1);
  }finally{remote.restore();}
});
test("provider failure preserves the saved inquiry and never claims mailbox delivery",async()=>{
  const e=env(mockDb()),remote=mockRemote({transportThrows:true});
  try{
    const body=await (await onRequestPost({request:request(),env:e})).json();
    assert.equal(body.received,true);assert.equal(body.notificationPending,true);
    assert.equal(e.INQUIRY_DB.inquiries.size,1);
    const again=await (await onRequestPost({request:request(),env:e})).json();
    assert.equal(again.duplicate,true);assert.equal(again.notificationPending,true);
    assert.equal(remote.notifications,1);
    assert.equal([...e.INQUIRY_DB.inquiries.values()][0].notification_status,"pending");
  }finally{remote.restore();}
});
test("a failed durable write sends no notification",async()=>{
  const e=env(mockDb({failInsert:true})),remote=mockRemote();
  try{
    assert.equal((await onRequestPost({request:request(),env:e})).status,503);
    assert.equal(e.INQUIRY_DB.inquiries.size,0);assert.equal(remote.notifications,0);
  }finally{remote.restore();}
});
test("group route shares the existing hashed rate limit and cannot purge old inquiries",async()=>{
  const e=env(mockDb()),remote=mockRemote();
  try{
    for(let i=0;i<5;i++){
      const data={...good(),idempotencyKey:key.replace("aaaaaaaa","aaaaaaa"+i)};
      assert.equal((await onRequestPost({request:request(data),env:e})).status,202);
    }
    assert.equal((await onRequestPost({request:request({...good(),idempotencyKey:key.replace("aaaaaaaa","aaaaaaa5")}),env:e})).status,429);
    assert.equal(remote.notifications,5);assert.equal(remote.verifications,5);
    assert.ok(e.INQUIRY_DB.sqlCalls.every(sql=>!sql.startsWith("DELETE FROM inquiries")));
    assert.ok([...e.INQUIRY_DB.limits.keys()].every(k=>/^[a-f0-9]{64}$/.test(k)));
  }finally{remote.restore();}
});
