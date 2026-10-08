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
  const inquiries=new Map(),limits=new Map(),sqlCalls=[];
  return {inquiries,limits,sqlCalls,
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
          if(failInsert) throw Error("Simulated durable-store failure");
          if(inquiries.has(params[1])) return {success:true,meta:{changes:0}};
          inquiries.set(params[1],{reference:params[0],fingerprint:params[2],notification_status:"pending"});
          return {success:true,meta:{changes:1}};
        }
        if(sql.startsWith("UPDATE inquiries")) {
          for(const r of inquiries.values()) if(r.reference===params[1])r.notification_status="provider_accepted";
          return {success:true};
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
  return new Request("https://"+host+"/api/inquiry",{
    method:"POST",headers:{"Origin":origin,"Content-Type":contentType,"CF-Connecting-IP":"198.51.100.4"},
    body:JSON.stringify(data)
  });
}
function mockRemote({captcha=true,notify=true}={}) {
  const real=globalThis.fetch;
  let verifications=0,notifications=0;
  globalThis.fetch=async (url) => {
    if(String(url).includes("siteverify")) {
      verifications++;
      return Response.json({success:captcha,action:"retally_audit",hostname:"www.retallyrecovery.com"});
    }
    if(String(url).includes("email/sending/send")) {
      notifications++;
      return Response.json({success:notify},{status:notify?200:503});
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
test("all independent online-intake activation gates fail closed", async () => {
  const cases = [
    ["owner has not enabled the service", e => { e.FREIGHT_INQUIRY_ENABLED = "0"; }],
    ["business mailbox has not been independently verified", e => { e.FREIGHT_INQUIRY_MAILBOX_VERIFIED = "0"; }],
    ["email-sending API token was never installed", e => { delete e.CLOUDFLARE_EMAIL_API_TOKEN; }],
    ["durable inquiry database is missing", e => { delete e.INQUIRY_DB; }],
    ["Turnstile secret is missing", e => { delete e.TURNSTILE_SECRET; }],
    ["rate limiter secret is missing", e => { delete e.INQUIRY_RATE_SECRET; }],
    ["business notification recipient does not match", e => { e.INQUIRY_NOTIFY_TO = "other@example.org"; }],
    ["notification sender does not use the business domain", e => { e.INQUIRY_NOTIFY_FROM = "other@example.org"; }],
  ];
  for (const [reason, disable] of cases) {
    const db = mockDb();
    const e = env(db);
    disable(e);
    const status = await onRequestGet({env:e});
    assert.equal(status.status, 503, reason);
    assert.deepEqual(await status.json(), {online:false}, reason);
    const attemptedPost = await onRequestPost({request:request(),env:e});
    assert.equal(attemptedPost.status, 503, reason);
    assert.equal((await attemptedPost.json()).ok, false, reason);
    assert.equal(db.inquiries.size, 0, reason);
  }
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
test("a new inquiry never deletes older pending, provider-only or acknowledged-by-mail inquiries", async () => {
  const remote=mockRemote({notify:false});
  try {
    const db=mockDb();
    const old=Math.floor(Date.now()/1000)-91*86400;
    const historical=["pending","provider_accepted","delivery_verified"];
    for(const state of historical) db.inquiries.set("historical-"+state,{
      reference:"RA-20260701-"+state, fingerprint:"synthetic",
      notification_status:state,accepted_at:old
    });
    const response=await onRequestPost({request:request(),env:env(db)});
    assert.equal(response.status,202);
    assert.equal(db.inquiries.size,4);
    for(const state of historical) assert.ok(db.inquiries.has("historical-"+state));
    assert.equal(db.sqlCalls.filter(sql=>/^DELETE\s+FROM\s+inquiries\b/i.test(sql)).length,0);
    assert.ok(db.sqlCalls.some(sql=>/^DELETE\s+FROM\s+inquiry_limits\b/i.test(sql)));
  } finally {remote.restore();}
});
test("email notification is a plain-text contact summary, not an invoice package", () => {
  const s=notificationText("RA-20261008-ABCDEF12",normalize(good()));
  assert.match(s,/Contact request only/);
  assert.doesNotMatch(s,/<html>|attachment/);
});
