import test from "node:test";
import assert from "node:assert/strict";
import {normalize, validOrigin, notificationText, onRequestPost, onRequestGet} from "../../functions/api/inquiry.js";

const key = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
const good = () => ({
  fullName:"Synthetic Test",workEmail:"qa@example.org",companyName:"Sample Distributor",
  annualSpend:"$1M–$5M",modes:["LTL","Parcel"],monthlyShipments:"50–249",
  invoiceHistory:"6–12 months",suspectedIssues:"Not sure",majorCarriers:"Example Carrier",
  records:["Invoice export"],issueNotes:"Synthetic metadata only",campaign:{utm_source:"controlled_test"},
  idempotencyKey:key,turnstileToken:"test-token"
});
function env(db) {return {
  FREIGHT_INQUIRY_ENABLED:"1",FREIGHT_INQUIRY_MAILBOX_VERIFIED:"1",
  TURNSTILE_SITEKEY:"sitekey-synthetic-123456",TURNSTILE_SECRET:"secret",
  INQUIRY_RATE_SECRET:"salt",CLOUDFLARE_ACCOUNT_ID:"test-account",CLOUDFLARE_EMAIL_API_TOKEN:"test-token",
  INQUIRY_NOTIFY_TO:"jay@retallyrecovery.com",INQUIRY_NOTIFY_FROM:"jay@retallyrecovery.com",INQUIRY_DB:db
};}
function mockDb({failInsert=false}={}) {
  const inquiries=new Map(),limits=new Map();
  return {inquiries,limits,
    prepare(sql) {return { bind(...params) {return {
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
          if(failInsert) throw Error("Simulated durable-store failure");
          if(inquiries.has(params[1])) return {success:true,meta:{changes:0}};
          inquiries.set(params[1],{reference:params[0],fingerprint:params[2],notification_status:"pending"});
          return {success:true,meta:{changes:1}};
        }
        if(sql.startsWith("UPDATE inquiries")) {
          for(const r of inquiries.values()) if(r.reference===params[1])r.notification_status="provider_accepted";
          return {success:true};
        }
        if(sql.startsWith("DELETE FROM")) return {success:true};
        throw Error("Unexpected run SQL: "+sql);
      }
    };}}; }
  };
}
function request(data=good(),{origin="https://www.retallyrecovery.com",host="www.retallyrecovery.com",contentType="application/json"}={}) {
  return new Request("https://"+host+"/api/inquiry",{
    method:"POST",headers:{"Origin":origin,"Content-Type":contentType,"CF-Connecting-IP":"198.51.100.4"},
    body:JSON.stringify(data)
  });
}
function mockRemote({captcha=true,notify=true,delivery="delivered"}={}) {
  const real=globalThis.fetch;
  let verifications=0,notifications=0;
  globalThis.fetch=async (url) => {
    if(String(url).includes("siteverify")) {
      verifications++;
      return Response.json({success:captcha,action:"retally_audit",hostname:"www.retallyrecovery.com"});
    }
    if(String(url).includes("email/sending/send")) {
      notifications++;
      const recipient="jay@retallyrecovery.com";
      const result={delivered:[],queued:[],suppressed_recipients:[],permanent_bounces:[]};
      if(delivery==="delivered")result.delivered=[recipient];
      if(delivery==="queued")result.queued=[recipient];
      if(delivery==="suppressed")result.suppressed_recipients=[recipient];
      if(delivery==="bounced")result.permanent_bounces=[recipient];
      if(delivery==="other")result.delivered=["elsewhere@example.org"];
      return Response.json({success:notify,result},{status:notify?200:503});
    }
    throw Error("Unexpected URL");
  };
  return { get verifications(){return verifications;},get notifications(){return notifications;},
    restore(){globalThis.fetch=real;} };
}
test("normalizes valid inputs and rejects injection, secrets, unknown fields and uploads", () => {
  assert.ok(normalize(good()));
  assert.equal(normalize({...good(),unknown:"value"}),null);
  assert.equal(normalize({...good(),issueNotes:"bank account number 123456"}),null);
  assert.equal(normalize({...good(),website:"spam"}),null);
  assert.equal(normalize({...good(),modes:["Unsupported"]}),null);
  assert.equal(normalize({...good(),workEmail:"bad@\nexample.com"}),null);
  assert.equal(normalize({...good(),file:"base64"}),null);
});
test("only exact HTTPS same-origin RETALLY hosts pass", () => {
  assert.equal(validOrigin(request()),true);
  assert.equal(validOrigin(request(good(),{origin:"https://another.example"})),false);
  assert.equal(validOrigin(request(good(),{origin:"https://retallyrecovery.com"})),false);
});
test("server feature is disabled without verified mailbox and explicit release flag", async () => {
  const e=env(mockDb());delete e.FREIGHT_INQUIRY_MAILBOX_VERIFIED;
  assert.equal((await onRequestGet({env:e})).status,503);
  assert.equal((await onRequestPost({request:request(),env:e})).status,503);
  assert.deepEqual(await (await onRequestGet({env:env(mockDb())})).json(),
    {online:true,siteKey:"sitekey-synthetic-123456"});
});
test("missing notification delivery credential cannot advertise online acceptance", async () => {
  const db=mockDb();
  const e=env(db);
  delete e.CLOUDFLARE_EMAIL_API_TOKEN;
  const get=await onRequestGet({env:e});
  assert.equal(get.status,503);
  assert.deepEqual(await get.json(),{online:false});
  const post=await onRequestPost({request:request(),env:e});
  assert.equal(post.status,503);
  assert.equal(db.inquiries.size,0);
});
test("invalid content type and cross-origin POST fail before any storage", async () => {
  const e=env(mockDb());
  assert.equal((await onRequestPost({request:request(good(),{contentType:"multipart/form-data"}),env:e})).status,415);
  assert.equal((await onRequestPost({request:request(good(),{origin:"https://attacker.example"}),env:e})).status,403);
  assert.equal(e.INQUIRY_DB.inquiries.size,0);
});
test("oversized POST fails closed, no inquiry stored", async () => {
  const data={...good(),issueNotes:"x".repeat(9000)};
  const e=env(mockDb());
  assert.equal((await onRequestPost({request:request(data),env:e})).status,413);
  assert.equal(e.INQUIRY_DB.inquiries.size,0);
});
test("invalid turnstile has no durable acceptance", async () => {
  const remote=mockRemote({captcha:false});
  try {
    const e=env(mockDb());
    assert.equal((await onRequestPost({request:request(),env:e})).status,400);
    assert.equal(e.INQUIRY_DB.inquiries.size,0);
    assert.equal(remote.notifications,0);
  } finally {remote.restore();}
});
test("server stores once and notifies at most once for a duplicate retry", async () => {
  const remote=mockRemote();
  try {
    const e=env(mockDb());
    const first=await onRequestPost({request:request(),env:e});
    assert.equal(first.status,202);
    const body=await first.json();
    assert.equal(body.received,true);
    assert.match(body.reference,/^RA-\d{8}-[A-F0-9]{8}$/);
    const again=await onRequestPost({request:request(),env:e});
    assert.equal(again.status,202);
    assert.equal((await again.json()).reference,body.reference);
    assert.equal(e.INQUIRY_DB.inquiries.size,1);
    assert.equal([...e.INQUIRY_DB.inquiries.values()][0].notification_status,"provider_accepted");
    assert.equal(remote.verifications,1);
    assert.equal(remote.notifications,1);
  } finally {remote.restore();}
});
test("idempotency collisions never overwrite an accepted request", async () => {
  const remote=mockRemote();
  try {
    const e=env(mockDb());
    await onRequestPost({request:request(),env:e});
    const r=await onRequestPost({request:request({...good(),companyName:"Different Corporation"}),env:e});
    assert.equal(r.status,409);
    assert.equal(e.INQUIRY_DB.inquiries.size,1);
  } finally {remote.restore();}
});
test("database failure cannot display a false successful receipt", async () => {
  const remote=mockRemote();
  try {
    const e=env(mockDb({failInsert:true}));
    const r=await onRequestPost({request:request(),env:e});
    assert.equal(r.status,503);
    assert.equal(remote.notifications,0);
  } finally {remote.restore();}
});
test("email provider failure leaves a durable pending record for operator reconciliation", async () => {
  const remote=mockRemote({notify:false});
  try {
    const e=env(mockDb());
    const r=await onRequestPost({request:request(),env:e});
    assert.equal(r.status,202);
    assert.equal([...e.INQUIRY_DB.inquiries.values()][0].notification_status,"pending");
  } finally {remote.restore();}
});
test("email API success for a suppressed or wrong recipient never counts as accepted delivery", async () => {
  for(const delivery of ["suppressed","bounced","other","none"]) {
    const remote=mockRemote({delivery});
    try {
      const e=env(mockDb());
      const response=await onRequestPost({request:request(),env:e});
      assert.equal(response.status,202);
      assert.equal([...e.INQUIRY_DB.inquiries.values()][0].notification_status,"pending");
      assert.equal(remote.notifications,1);
    } finally {remote.restore();}
  }
});
test("email API queued recipient counts as provider acceptance, not proven inbox delivery", async () => {
  const remote=mockRemote({delivery:"queued"});
  try {
    const e=env(mockDb());
    const response=await onRequestPost({request:request(),env:e});
    assert.equal(response.status,202);
    assert.equal([...e.INQUIRY_DB.inquiries.values()][0].notification_status,"provider_accepted");
  } finally {remote.restore();}
});
test("burst attempts limited to five per hour and no notification on rejected request", async () => {
  const remote=mockRemote({captcha:false});
  try {
    const e=env(mockDb());
    for(let i=0;i<5;i++) assert.equal((await onRequestPost({request:request(),env:e})).status,400);
    const rate=await onRequestPost({request:request(),env:e});
    assert.equal(rate.status,429);
    assert.equal(remote.verifications,5);
  } finally {remote.restore();}
});
test("email notification is a plain-text contact summary, not an invoice package", () => {
  const s=notificationText("RA-20261008-ABCDEF12",normalize(good()));
  assert.match(s,/Contact request only/);
  assert.doesNotMatch(s,/<html>|attachment/);
});
