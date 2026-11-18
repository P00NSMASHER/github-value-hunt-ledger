import test from "node:test";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";
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
  INQUIRY_RATE_SECRET:"salt",RESEND_API_KEY:"re_synthetic_test_key",
  INQUIRY_NOTIFY_TO:"jay@retallyrecovery.com",INQUIRY_DB:db
};}
function mockDb({failInsert=false,failNotificationUpdate=false}={}) {
  const inquiries=new Map(),limits=new Map(),sqlCalls=[],limitWrites=[];
  return {inquiries,limits,sqlCalls,limitWrites,
    prepare(sql) {sqlCalls.push(sql);return { bind(...params) {return {
      async first() {
        if(sql.startsWith("SELECT reference")) return inquiries.get(params[0]) || null;
        if(sql.startsWith("INSERT INTO inquiry_limits")) {
          const hits=(limits.get(params[0]) || 0)+1;
          if (hits > params[2]) return null; // no SQLite RETURNING row, no write on cap
          limits.set(params[0],hits);
          limitWrites.push({bucket:params[0],hits});
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
  return new Request("https://"+host+"/api/inquiry",{
    method:"POST",headers:{"Origin":origin,"Content-Type":contentType,"CF-Connecting-IP":"198.51.100.4"},
    body:JSON.stringify(data)
  });
}
function mockRemote({captcha=true,notify=true,providerResponse=null,providerStatus=null,transportThrows=false}={}) {
  const real=globalThis.fetch;
  let verifications=0,notifications=0;
  const sent=[];
  globalThis.fetch=async (url, options={}) => {
    if(String(url).includes("siteverify")) {
      verifications++;
      return Response.json({success:captcha,action:"retally_audit",hostname:"www.retallyrecovery.com"});
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
    ["Resend API token was never installed", e => { delete e.RESEND_API_KEY; }],
    ["Resend API token has invalid shape", e => { e.RESEND_API_KEY = "test-token"; }],
    ["durable inquiry database is missing", e => { delete e.INQUIRY_DB; }],
    ["Turnstile secret is missing", e => { delete e.TURNSTILE_SECRET; }],
    ["rate limiter secret is missing", e => { delete e.INQUIRY_RATE_SECRET; }],
    ["business notification recipient does not match", e => { e.INQUIRY_NOTIFY_TO = "other@example.org"; }],
    ["notification recipient missing", e => { delete e.INQUIRY_NOTIFY_TO; }],
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
    assert.equal(body.notificationPending,false);
    assert.match(body.reference,/^RA-\d{8}-[A-F0-9]{8}$/);
    const again=await onRequestPost({request:request(),env:e});
    assert.equal(again.status,202);
    const duplicate=await again.json();
    assert.equal(duplicate.reference,body.reference);
    assert.equal(duplicate.notificationPending,false);
    assert.equal(e.INQUIRY_DB.inquiries.size,1);
    assert.equal([...e.INQUIRY_DB.inquiries.values()][0].notification_status,"provider_accepted");
    assert.equal(remote.verifications,1);
    assert.equal(remote.notifications,1);
    const sent=remote.sent[0];
    assert.equal(sent.url,"https://api.resend.com/emails");
    assert.equal(sent.method,"POST");
    assert.equal(sent.headers.Authorization,"Bearer re_synthetic_test_key");
    assert.equal(sent.headers["Idempotency-Key"],"retally-audit-"+body.reference);
    assert.equal(sent.body.from,"RETALLY Audit Notifications <audit@notify.retallyrecovery.com>");
    assert.deepEqual(sent.body.to,["jay@retallyrecovery.com"]);
    assert.equal(sent.body.reply_to,"qa@example.org");
    assert.equal(sent.body.subject,"RETALLY Free Audit | "+body.reference);
    assert.equal(sent.body.attachments,undefined,"the inquiry never uploads freight files");
  } finally {remote.restore();}
});
test("Resend API acceptance requires HTTP 200 with UUID; never assert mailbox delivery", async () => {
  const scenarios=[
    ["Resend accepted email with UUID", {}, "provider_accepted"],
    ["provider authentication failure", {notify:false,providerStatus:401}, "pending"],
    ["sender domain unverified", {notify:false,providerStatus:403}, "pending"],
    ["rate limit", {notify:false,providerStatus:429}, "pending"],
    ["provider outage", {notify:false,providerStatus:503}, "pending"],
    ["transport timeout", {transportThrows:true}, "pending"],
    ["unexpected HTTP 201", {providerStatus:201}, "pending"],
    ["missing email ID", {providerResponse:{}}, "pending"],
    ["null email ID", {providerResponse:{id:null}}, "pending"],
    ["invalid email ID", {providerResponse:{id:"message-123"}}, "pending"],
    ["Cloudflare provider response cannot impersonate Resend", {providerResponse:{success:true,result:{delivered:["jay@retallyrecovery.com"]}}}, "pending"],
    ["provider returned non-object", {providerResponse:[]}, "pending"],
    ["malformed provider JSON", {providerResponse:"invalid-json"}, "pending"],
  ];
  for(const [label,options,expected] of scenarios) {
    const remote=mockRemote(options);
    try {
      const db=mockDb();
      const e=env(db);
      const response=await onRequestPost({request:request(),env:e});
      assert.equal(response.status,202,label+": durable acceptance should not depend on email");
      const receipt=await response.json();
      assert.equal(receipt.received,true,label);
      assert.equal(receipt.notificationPending,expected!=="provider_accepted",label);
      assert.equal(db.inquiries.size,1,label);
      assert.equal([...db.inquiries.values()][0].notification_status,expected,label);
      assert.equal(remote.notifications,1,label);
      assert.equal(db.sqlCalls.filter(sql=>sql.startsWith("UPDATE inquiries")).length,
        expected==="provider_accepted"?1:0,label);
    } finally {remote.restore();}
  }
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
    assert.equal((await r.json()).notificationPending,true);
    assert.equal([...e.INQUIRY_DB.inquiries.values()][0].notification_status,"pending");
    const duplicate=await onRequestPost({request:request(),env:e});
    assert.equal((await duplicate.json()).notificationPending,true);
    assert.equal(remote.notifications,1,"a duplicate never resends an uncertain notification");
  } finally {remote.restore();}
});

test("an uncommitted provider-status update must not masquerade as a staff notification", async () => {
  const remote=mockRemote();
  try {
    const e=env(mockDb({failNotificationUpdate:true}));
    const r=await onRequestPost({request:request(),env:e});
    assert.equal(r.status,202);
    const receipt=await r.json();
    assert.equal(receipt.received,true);
    assert.equal(receipt.notificationPending,true);
    assert.equal([...e.INQUIRY_DB.inquiries.values()][0].notification_status,"pending");
    const duplicate=await onRequestPost({request:request(),env:e});
    assert.equal((await duplicate.json()).notificationPending,true);
    assert.equal(remote.notifications,1,"never automatically resend after an ambiguous first attempt");
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

function runMarketingNavigationFixture(pageUrl, hrefs) {
  const links = hrefs.map(({href, download = false}) => ({
    href,
    download,
    getAttribute(name) {return name === "href" ? this.href : null;},
    setAttribute(name, value) {if (name === "href") this.href = value;},
    hasAttribute(name) {return name === "download" && this.download;}
  }));
  const dispatches = [], dataLayer = [];
  const browser = {
    location: new URL(pageUrl), dataLayer,
    dispatchEvent(event) {dispatches.push(event.detail);}
  };
  const document = {
    getElementById() {return null;},
    querySelectorAll(selector) {return selector === "a[href]" ? links : [];},
    body: {classList: {contains() {return false;}}}
  };
  const script = readFileSync(new URL("./site.js", import.meta.url), "utf8");
  runInNewContext(script, {
    URL, URLSearchParams, window: browser, document,
    CustomEvent: class {constructor(_type, options) {this.detail = options.detail;}}
  }, {filename: "site.js", timeout: 2000});
  return {links, dataLayer, dispatches};
}

test("retally campaign navigation keeps UTM tags through internal CTA without leaking offsite", () => {
  const campaign = "utm_source=facebook&utm_medium=organic_social&utm_campaign=retally_oct2026_launch&utm_content=oct14_evidence";
  const hrefs = [
    {href: "./#start-audit"},
    {href: "freight-audit-pricing.html?view=details#pricing"},
    {href: "https://www.retallyrecovery.com/about?utm_source=prior"},
    {href: "#methodology"},
    {href: "mailto:jay@retallyrecovery.com"},
    {href: "https://example.com/audit"},
    {href: "//evil.example/audit"},
    {href: "assets/synthetic-pilot-demo.zip"},
    {href: "private.csv", download: true},
    {href: "javascript:void(0)"}
  ];
  const {links, dataLayer, dispatches} = runMarketingNavigationFixture(
    "https://www.retallyrecovery.com/freight-audit-methodology?" + campaign, hrefs
  );
  const audit = new URL(links[0].href);
  assert.equal(audit.pathname, "/");
  assert.equal(audit.hash, "#start-audit");
  assert.equal(audit.searchParams.get("utm_source"), "facebook");
  assert.equal(audit.searchParams.get("utm_medium"), "organic_social");
  assert.equal(audit.searchParams.get("utm_campaign"), "retally_oct2026_launch");
  assert.equal(audit.searchParams.get("utm_content"), "oct14_evidence");
  const pricing = new URL(links[1].href);
  assert.equal(pricing.searchParams.get("view"), "details");
  assert.equal(pricing.hash, "#pricing");
  assert.equal(pricing.searchParams.get("utm_content"), "oct14_evidence");
  const existing = new URL(links[2].href);
  assert.equal(existing.searchParams.get("utm_source"), "prior");
  assert.equal(existing.searchParams.get("utm_campaign"), "retally_oct2026_launch");
  for (let i = 3; i < links.length; i++) {
    assert.equal(links[i].href, hrefs[i].href, "Must not rewrite nonpage/offsite link " + i);
  }
  assert.equal(dataLayer[0].event, "freight_landing_page_viewed");
  assert.equal(dataLayer[0].utm_content, "oct14_evidence");
  assert.equal(dispatches[0].properties.utm_source, "facebook");
});

test("retally campaign navigation leaves direct and untagged traffic unchanged", () => {
  const original = "./#start-audit";
  const {links, dataLayer} = runMarketingNavigationFixture(
    "https://www.retallyrecovery.com/freight-audit-pricing", [{href: original}]
  );
  assert.equal(links[0].href, original);
  assert.equal(dataLayer[0].utm_source, undefined);
});

test("online form waits for sequential Turnstile and Resend before declaring the receipt uncertain", () => {
  const front = readFileSync(new URL("./site.js", import.meta.url), "utf8");
  const backend = readFileSync(new URL("../../functions/api/inquiry.js", import.meta.url), "utf8");
  const clientTimeouts = [...front.matchAll(/window\.setTimeout\(\(\) => controller\.abort\(\), (\d+)\)/g)]
    .map(match => Number(match[1]));
  assert.ok(clientTimeouts.length >= 2, "Both online-availability and POST requests need bounded deadlines");
  assert.ok(clientTimeouts.some(value => value <= 5000),
    "The GET availability probe must not block the visitor for the full submission budget");
  const submissionTimeout = Math.max(...clientTimeouts);
  const providerTimeouts = [...backend.matchAll(/AbortSignal\.timeout\((\d+)\)/g)]
    .map(x => Number(x[1]));
  assert.deepEqual(providerTimeouts.sort((a,b) => a-b), [7000,9000],
    "Review the client budget if upstream deadlines change");
  assert.ok(submissionTimeout >= providerTimeouts.reduce((x,y) => x+y,0)+8000,
    "Wait for sequential provider deadlines plus database and transport margin");
  assert.match(front, /error\?\.name === "AbortError"/);
  assert.match(front, /Your request may already be saved/);
  assert.match(front, /retry this same form to retrieve/);
  assert.match(front, /pendingRequestKey \|\|= window\.crypto\?\.randomUUID\?\.\(\)/);
  assert.match(backend,/SELECT reference, fingerprint, notification_status FROM inquiries WHERE idempotency_key=\?/);
  assert.match(backend,/notificationPending/);
});

test("exhausted per-IP buckets stop writing without permitting further requests", async () => {
  const db=mockDb(),remote=mockRemote({captcha:false});
  try {
    for (let i=0; i<50; i++) {
      const result=await onRequestPost({request:request(),env:env(db)});
      assert.equal(result.status,i<5?400:429);
    }
    assert.equal(remote.verifications,5,"only five attempts reach Turnstile");
    assert.equal(remote.notifications,0);
    assert.equal(db.inquiries.size,0);
    assert.equal(db.limits.size,2,"hour and day buckets persist");
    assert.equal(db.limitWrites.length,10,"no additional writes after the fifth attempt");
    assert.deepEqual([...db.limits.values()].sort((a,b)=>a-b),[5,5]);
  } finally {remote.restore();}
});

// Browser-source contract: an availability GET is not a customer submission.
test("secure-intake availability GET never displays a submission receipt", async () => {
  const front = readFileSync(new URL("./site.js", import.meta.url), "utf8");
  const start = front.indexOf("const checkSecureIntake = async");
  const finish = front.indexOf("      checkSecureIntake();", start);
  assert.ok(start >= 0 && finish > start, "Availability probe must exist");
  const hint = {textContent: "Opens an email draft. Review it and press Send."};
  const submitButton = {textContent: "Open My Free Audit Request"};
  const calls = [];
  const context = {
    window: {setTimeout: () => 1, clearTimeout() {}},
    document: {
      createElement: () => ({dataset: {}, addEventListener() {}}),
      head: {appendChild() {}}
    },
    fetch: async (url, options = {}) => {
      calls.push({url, method: options.method || "GET"});
      return {ok: true, json: async () => ({online: true, siteKey: "syntheticSiteKey12345"})};
    },
    AbortController, serverReady: false,
    fallbackLink: {hidden: true}, submitButton, submitHint: hint,
    formError: {before() {}}
  };
  const probe = front.slice(start, finish);
  const ready = await runInNewContext(
    "(async () => {" + probe + "\nawait checkSecureIntake(); return serverReady;})()",
    context, {timeout: 2000}
  );
  assert.equal(ready, true);
  assert.deepEqual(calls, [{url: "/api/inquiry", method: "GET"}]);
  assert.equal(submitButton.textContent, "Submit My Free Audit Request");
  assert.match(hint.textContent, /form available/i);
  assert.match(hint.textContent, /nothing has been sent yet/i);
  assert.doesNotMatch(hint.textContent, /submitted securely|request received|receipt confirmed/i);
});

test("email-draft copy fallback preserves prepared text when clipboard is denied or absent", async () => {
  const js = readFileSync(new URL("./site.js", import.meta.url), "utf8");
  const html = readFileSync(new URL("./index.html", import.meta.url), "utf8");
  assert.match(html, /id="auditCopyFallback"[^>]*hidden/);
  assert.match(html, /<textarea id="auditManualSummary"[^>]*readonly/);
  const start = js.indexOf('    byId("copyAuditSummary")?.addEventListener("click",');
  const end = js.indexOf('    byId("copyAuditEmail")?.addEventListener("click",', start);
  assert.ok(start >= 0 && end > start, "Actual copy handler must be available");
  const prepared = "Synthetic private request only — reference QA-123";
  const run = async (clipboard) => {
    let click;
    let focused = 0;
    let selected = 0;
    let writes = 0;
    const elements = {
      copyAuditSummary: {addEventListener(type, cb) {assert.equal(type, "click"); click = cb;}},
      copyStatus: {textContent: ""},
      auditCopyFallback: {hidden: true},
      auditManualSummary: {
        value: "",
        focus() {focused++;},
        select() {selected++;}
      }
    };
    runInNewContext(js.slice(start, end), {
      byId: (id) => elements[id] || null,
      navigator: {clipboard: clipboard && {writeText: async (value) => {
        writes++;
        assert.equal(value, prepared);
        if (clipboard === "denied") throw Error("Synthetic clipboard denied");
      }}},
      preparedSummary: prepared
    }, {filename: "site.js:copyAuditSummary", timeout: 2000});
    assert.equal(typeof click, "function");
    await click();
    return {elements, focused, selected, writes};
  };
  const success = await run("allowed");
  assert.equal(success.elements.copyStatus.textContent, "Request details copied.");
  assert.equal(success.elements.auditCopyFallback.hidden, true);
  assert.equal(success.writes, 1);
  for (const mode of ["denied", null]) {
    const fail = await run(mode);
    assert.equal(fail.elements.auditCopyFallback.hidden, false);
    assert.equal(fail.elements.auditManualSummary.value, prepared);
    assert.equal(fail.focused, 1);
    assert.equal(fail.selected, 1);
    assert.match(fail.elements.copyStatus.textContent, /does not send an email/i);
  }
  assert.match(js, /if \(manual\) manual\.value = "";/, "Edit must clear stale personal text");
  assert.match(js, /if \(fallback\) fallback\.hidden = true;/, "Edit must hide stale text");
});

test("required freight mode validation moves keyboard focus to the first choice", () => {
  const js = readFileSync(new URL("./site.js", import.meta.url), "utf8");
  const html = readFileSync(new URL("./index.html", import.meta.url), "utf8");
  assert.match(html, /Freight types used <span>Choose at least one<\/span>/);
  const start = js.indexOf("    const validate = () => {");
  const finish = js.indexOf('    for (const field of all("input,select,textarea", auditForm))', start);
  assert.ok(start >= 0 && finish > start, "Exercise the real client validator");
  const validator = js.slice(start, finish);
  const check = (modeSelected) => {
    let focusCount = 0, error = "", scrollCount = 0;
    const firstMode = {focus() {focusCount++;}};
    const modesGroup = {
      querySelector: () => firstMode,
      scrollIntoView() {scrollCount++;}
    };
    const requiredField = {removeAttribute() {}, checkValidity: () => true};
    const accepted = runInNewContext(
      "(() => {" + validator + "\nreturn validate();})()",
      {
        auditForm: {querySelector: () => modeSelected ? firstMode : null},
        all: () => [requiredField],
        setError(message) {error = message;},
        byId: (id) => id === "modesGroup" ? modesGroup : null
      },
      {filename: "site.js:validate-modes", timeout: 2000}
    );
    return {accepted, focusCount, error, scrollCount};
  };
  const missing = check(false);
  assert.equal(missing.accepted, false);
  assert.equal(missing.focusCount, 1, "A missing required mode must receive keyboard focus");
  assert.match(missing.error, /choose at least one freight type/i);
  const valid = check(true);
  assert.equal(valid.accepted, true);
  assert.equal(valid.focusCount, 0, "Valid mode choices must not steal focus");
  assert.equal(valid.error, "");
});

test("email fallback cannot prepare a second request while secure intake is pending", () => {
  const front = readFileSync(new URL("./site.js", import.meta.url), "utf8");
  const start = front.indexOf('    fallbackLink?.addEventListener("click",');
  const end = front.indexOf('    const staticEmailLink = byId("auditStaticFallback")?.querySelector("a[data-contact-link]");', start);
  assert.ok(start >= 0 && end > start, "Run the actual fallback click handler");
  const handlerSource = front.slice(start, end);
  const run = (sending) => {
    let listener, prevented = 0, validated = 0, prepared = 0;
    runInNewContext(handlerSource, {
      sending,
      fallbackLink: {addEventListener(type, fn) {
        assert.equal(type, "click");
        listener = fn;
      }},
      validate() {validated++; return true;},
      prepareEmailDraft() {prepared++;}
    }, {filename:"site.js:email-fallback", timeout:2000});
    assert.equal(typeof listener, "function");
    listener({preventDefault() {prevented++;}});
    return {prevented, validated, prepared};
  };
  assert.deepEqual(run(false), {prevented:1, validated:1, prepared:1},
    "The manual email option must remain usable while no POST is active");
  assert.deepEqual(run(true), {prevented:1, validated:0, prepared:0},
    "An in-flight POST must not also prepare an email draft");
});

test("static direct-email escape cannot start a duplicate request during secure POST", () => {
  const html = readFileSync(new URL("./index.html", import.meta.url), "utf8");
  const front = readFileSync(new URL("./site.js", import.meta.url), "utf8");
  assert.match(html, /id="auditStaticFallback"[^>]*>[\s\S]*?data-contact-link/);
  const start = front.indexOf('    const staticEmailLink = byId("auditStaticFallback")?.querySelector("a[data-contact-link]");');
  const finish = front.indexOf('    auditForm.addEventListener("submit"', start);
  assert.ok(start >= 0 && finish > start, "The static direct-email anchor needs its own click guard");
  const listener = front.slice(start, finish);
  const exercise = (sending) => {
    let click;
    const link = {addEventListener(type, fn) {assert.equal(type, "click"); click = fn;}};
    runInNewContext(listener, {sending, byId(id) {
      assert.equal(id, "auditStaticFallback");
      return {querySelector(selector) {
        assert.equal(selector, "a[data-contact-link]");
        return link;
      }};
    }}, {filename: "site.js:static-email-fallback", timeout: 2000});
    assert.equal(typeof click, "function");
    let prevented = 0;
    click({preventDefault() {prevented++;}});
    return prevented;
  };
  assert.equal(exercise(false), 0, "Email must remain usable when no POST is active");
  assert.equal(exercise(true), 1, "A pending secure POST must block concurrent email handoff");
});

test("in-flight POST freezes request edits and retains its retry identity", () => {
  const front = readFileSync(new URL("./site.js", import.meta.url), "utf8");
  const html = readFileSync(new URL("./index.html", import.meta.url), "utf8");
  assert.match(html, /<fieldset class="form-step form-step-simple" data-form-step="1">/);
  assert.match(front, /const entryFieldset = auditForm\.querySelector\('fieldset\[data-form-step="1"\]'\)/);
  const begin = front.indexOf('    for (const field of all("input,select,textarea", auditForm))');
  const end = front.indexOf('    const issueNotes = byId("issueNotes");', begin);
  assert.ok(begin >= 0 && end > begin);
  const fieldHandler = front.slice(begin, end);
  const edit = (sending) => {
    let listener;
    const field = {
      addEventListener(type, fn) { assert.equal(type, "input"); listener = fn; },
      checkValidity() { return true; },
      removeAttribute() {}
    };
    return runInNewContext(
      "(() => { let pendingRequestKey = 'synthetic-stable-key';" + fieldHandler +
      "\nfireInput(); return pendingRequestKey; })()",
      {
        sending, auditForm: {}, all: () => [field], setError() {},
        fireInput() { assert.equal(typeof listener, "function"); listener(); }
      }, {filename:"site.js:pending-input", timeout:2000}
    );
  };
  assert.equal(edit(true), "synthetic-stable-key");
  assert.equal(edit(false), null);
  const start = front.indexOf("      sending = true;", end);
  const afterLock = front.indexOf("      const controller = new AbortController();", start);
  const cleanup = front.indexOf("        window.clearTimeout(timeout);", afterLock);
  const afterCleanup = front.indexOf("      }\n    });", cleanup);
  assert.ok(start > end && afterLock > start && cleanup > afterLock && afterCleanup > cleanup);
  const state = runInNewContext(
    "(() => { let sending = false;\n" + front.slice(start, afterLock) +
    "\nconst locked = entryFieldset.disabled && submitButton.disabled && sending;\n" +
    front.slice(cleanup, afterCleanup) +
    "\nreturn {locked, released: !entryFieldset.disabled && !submitButton.disabled && !sending}; })()",
    {
      entryFieldset: {disabled: false},
      submitButton: {disabled: false, textContent: "Submit"},
      window: {clearTimeout() {}}, timeout: 1
    }, {filename:"site.js:pending-lock", timeout:2000}
  );
  assert.equal(state.locked, true);
  assert.equal(state.released, true);
});
