import test from "node:test";
import assert from "node:assert/strict";
import { onRequestGet, onRequestPost, onRequestOptions } from "../../functions/api/group-inquiry.js";
import { onRequestPost as freightPost, validOrigin as freightOrigin } from "../../functions/api/inquiry.js";

const GROUP = "https://group.retallyrecovery.com";
const WWW = "https://www.retallyrecovery.com";
const APEX = "https://retallyrecovery.com";
const API = WWW + "/api/group-inquiry";
const payload = {
  business: "recoveryworks", fullName: "Synthetic Test", workEmail: "qa@example.org",
  companyName: "Example Research", message: "Please clarify your current service scope.",
  consent: true, idempotencyKey: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee", turnstileToken: "synthetic-token"
};
function makeRequest({ method = "POST", origin = GROUP, url = API, headers = {}, data = payload } = {}) {
  const h = new Headers(headers);
  if (origin !== null) h.set("Origin", origin);
  if (method === "POST") {
    if (!h.has("Content-Type")) h.set("Content-Type", "application/json");
    h.set("CF-Connecting-IP", "198.51.100.4");
  }
  return new Request(url, { method, headers: h, body: method === "POST" ? JSON.stringify(data) : undefined });
}
function environment(db) {
  return {
    FREIGHT_INQUIRY_ENABLED: "1", FREIGHT_INQUIRY_MAILBOX_VERIFIED: "1",
    TURNSTILE_SITEKEY: "synthetic-sitekey", TURNSTILE_SECRET: "synthetic-secret",
    INQUIRY_RATE_SECRET: "synthetic-salt", RESEND_API_KEY: "re_synthetic_test_key",
    INQUIRY_NOTIFY_TO: "jay@retallyrecovery.com", INQUIRY_DB: db
  };
}
function guardedDb() {
  const calls = [];
  return { calls, prepare(sql) { calls.push(sql); throw Error("Unexpected database access"); } };
}
function beforeReceiptDb() {
  const calls = [], writes = [];
  return { calls, writes, prepare(sql) {
    calls.push(sql);
    return { bind() { return {
      async first() {
        if (sql.startsWith("SELECT reference")) return null;
        if (sql.startsWith("INSERT INTO inquiry_limits")) return { hits: 1 };
        throw Error("Unexpected SQL lookup");
      },
      async run() { writes.push(sql); throw Error("Unexpected durable write"); }
    }; } };
  } };
}
function cors(response, expected = GROUP, preflight = false) {
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), expected);
  assert.equal(response.headers.get("Access-Control-Allow-Credentials"), null);
  const vary = response.headers.get("Vary").toLowerCase().split(/,\s*/);
  assert.ok(vary.includes("origin"));
  if (preflight) {
    assert.ok(vary.includes("access-control-request-method"));
    assert.ok(vary.includes("access-control-request-headers"));
  }
  assert.equal(response.headers.get("Cache-Control"), "no-store, private");
  return response;
}
const handlers = { GET: onRequestGet, POST: onRequestPost, OPTIONS: onRequestOptions };
function preflightHeaders(extra = {}) {
  return { "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type", ...extra };
}
async function withoutNetwork(fn) {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls++; throw Error("Unexpected provider request"); };
  try { await fn(); assert.equal(calls, 0); } finally { globalThis.fetch = original; }
}

test("Group preflight grants only the exact origin, requested approved method and Content-Type", async () => {
  await withoutNetwork(async () => {
    const db = guardedDb();
    const response = cors(await onRequestOptions({
      request: makeRequest({ method: "OPTIONS", headers: preflightHeaders({ "Access-Control-Request-Headers": "Content-Type" }) }),
      env: environment(db)
    }), GROUP, true);
    assert.equal(response.status, 204);
    assert.equal(await response.text(), "");
    assert.equal(response.headers.get("Access-Control-Allow-Methods"), "POST");
    assert.equal(response.headers.get("Access-Control-Allow-Headers"), "Content-Type");
    assert.deepEqual(db.calls, []);
    const get = cors(await onRequestOptions({ request: makeRequest({
      method: "OPTIONS", headers: { "Access-Control-Request-Method": "GET" }
    }) }), GROUP, true);
    assert.equal(get.status, 204);
    assert.equal(get.headers.get("Access-Control-Allow-Methods"), "GET");
    assert.equal(get.headers.get("Access-Control-Allow-Headers"), null);
  });
});

test("unapproved or malformed preflight methods and headers never receive a permission grant", async () => {
  const cases = [
    {},
    ...["PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "post", "GET, POST", "*"].map(method => ({ "Access-Control-Request-Method": method })),
    ...["", "authorization", "cookie", "x-requested-with", "content-type, authorization", "content-type,", ",content-type", "content-type, Content-Type", "*"].map(headers => preflightHeaders({ "Access-Control-Request-Headers": headers }))
  ];
  await withoutNetwork(async () => {
    for (const headers of cases) {
      const response = cors(await onRequestOptions({ request: makeRequest({ method: "OPTIONS", headers }) }), GROUP, true);
      assert.equal(response.status, 403, JSON.stringify(headers));
      assert.equal(response.headers.get("Access-Control-Allow-Methods"), null);
      assert.equal(response.headers.get("Access-Control-Allow-Headers"), null);
    }
  });
});

test("origin spoofing, previews, credentials, ports and URL decorations fail for every Group method", async () => {
  const origins = [
    "null", "http://group.retallyrecovery.com", GROUP + ":443", GROUP + ":8443", GROUP + "/",
    GROUP + "/contact", GROUP + "?x=1", GROUP + "#x", GROUP + ".", GROUP + ".evil.example",
    "https://user:password@group.retallyrecovery.com", "https://group.retallyrecovery.com@evil.example",
    "https://evil.example@group.retallyrecovery.com", "https://preview.retally-group.pages.dev",
    "https://recoveryworks.retallyrecovery.com", "https://permitplate.retallyrecovery.com",
    "https://capturebrief.retallyrecovery.com", APEX, "https://GROUP.retallyrecovery.com",
    GROUP + ", " + WWW, GROUP + " " + WWW, "not-an-origin"
  ];
  await withoutNetwork(async () => {
    const db = guardedDb(), env = environment(db);
    for (const origin of origins) for (const [method, handler] of Object.entries(handlers)) {
      const response = cors(await handler({ request: makeRequest({ method, origin, headers: preflightHeaders() }), env }), null, method === "OPTIONS");
      assert.equal(response.status, 403, method + " " + origin);
    }
    for (const method of ["POST", "OPTIONS"]) {
      assert.equal(cors(await handlers[method]({ request: makeRequest({ method, origin: null, headers: preflightHeaders() }), env }), null, method === "OPTIONS").status, 403);
    }
    assert.deepEqual(db.calls, []);
  });
});

test("cross-origin Group can target only the exact www production endpoint", async () => {
  const urls = [
    "http://www.retallyrecovery.com/api/group-inquiry", WWW + ":8443/api/group-inquiry",
    APEX + "/api/group-inquiry", GROUP + "/api/group-inquiry", WWW + "/api/inquiry", API + "/",
    API + "?business=capturebrief", API + "#fragment", WWW + "/api/%67roup-inquiry",
    "https://preview.retally-freight.pages.dev/api/group-inquiry"
  ];
  await withoutNetwork(async () => {
    const db = guardedDb(), env = environment(db);
    for (const url of urls) for (const [method, handler] of Object.entries(handlers)) {
      const response = cors(await handler({ request: makeRequest({ method, url, headers: preflightHeaders() }), env }), null, method === "OPTIONS");
      assert.equal(response.status, 403, method + " " + url);
    }
    // Request constructors reject userinfo and normalize default ports. Also
    // reject either lexical form if an upstream runtime presents it unchanged.
    for (const url of ["https://user:password@www.retallyrecovery.com/api/group-inquiry", WWW + ":443/api/group-inquiry"]) {
      const request = { url, method: "GET", headers: new Headers({ Origin: GROUP }) };
      assert.equal(cors(await onRequestGet({ request, env }), null).status, 403);
    }
    assert.deepEqual(db.calls, []);
  });
});

test("credential-bearing requests are rejected even when their Group or legacy origin is approved", async () => {
  await withoutNetwork(async () => {
    const db = guardedDb(), env = environment(db);
    for (const origin of [GROUP, WWW, APEX]) for (const name of ["Cookie", "Authorization", "Proxy-Authorization"]) {
      const url = origin === APEX ? APEX + "/api/group-inquiry" : API;
      for (const [method, handler] of Object.entries(handlers)) {
        const response = cors(await handler({ request: makeRequest({ method, origin, url,
          headers: { ...preflightHeaders(), [name]: "synthetic-credential" } }), env }), origin, method === "OPTIONS");
        assert.equal(response.status, 403, method + " " + name);
        assert.equal(response.headers.get("Access-Control-Allow-Methods"), null);
      }
    }
    assert.equal(cors(await onRequestGet({ request: makeRequest({ method: "GET", origin: null, headers: { Cookie: "synthetic=1" } }), env }), null).status, 403);
    assert.deepEqual(db.calls, []);
  });
});

test("config is readable from Group and exact legacy origins, with no-Origin legacy GET compatibility", async () => {
  await withoutNetwork(async () => {
    const db = guardedDb(), env = environment(db);
    for (const origin of [GROUP, WWW, APEX]) {
      const url = origin === APEX ? APEX + "/api/group-inquiry" : API;
      const response = cors(await onRequestGet({ request: makeRequest({ method: "GET", origin, url }), env }), origin);
      assert.equal(response.status, 200);
      assert.deepEqual(await response.json(), { online: true, siteKey: env.TURNSTILE_SITEKEY });
    }
    for (const base of [WWW, APEX]) {
      const response = cors(await onRequestGet({ request: makeRequest({ method: "GET", origin: null, url: base + "/api/group-inquiry" }), env }), null);
      assert.equal(response.status, 200);
    }
    for (const url of [API + "?x=1", GROUP + "/api/group-inquiry", "https://preview.pages.dev/api/group-inquiry"]) {
      assert.equal(cors(await onRequestGet({ request: makeRequest({ method: "GET", origin: null, url }), env }), null).status, 403);
    }
    assert.deepEqual(db.calls, []);
  });
});

test("all existing activation gates retain readable fail-closed config and submission responses", async () => {
  const gates = [
    env => { env.FREIGHT_INQUIRY_ENABLED = "0"; },
    env => { env.FREIGHT_INQUIRY_MAILBOX_VERIFIED = "0"; },
    env => { delete env.INQUIRY_DB; },
    env => { env.INQUIRY_DB = {}; },
    env => { delete env.TURNSTILE_SECRET; },
    env => { delete env.TURNSTILE_SITEKEY; },
    env => { delete env.INQUIRY_RATE_SECRET; },
    env => { delete env.RESEND_API_KEY; },
    env => { env.RESEND_API_KEY = "incorrect-key-prefix"; },
    env => { env.RESEND_API_KEY = "re_short"; },
    env => { env.INQUIRY_NOTIFY_TO = "elsewhere@example.org"; }
  ];
  await withoutNetwork(async () => {
    for (const disable of gates) {
      const db = guardedDb(), env = environment(db);
      disable(env);
      const config = cors(await onRequestGet({ request: makeRequest({ method: "GET" }), env }));
      assert.equal(config.status, 503);
      assert.deepEqual(await config.json(), { online: false });
      assert.equal(cors(await onRequestPost({ request: makeRequest(), env })).status, 503);
      assert.deepEqual(db.calls, []);
    }
  });
});

test("wrong handler methods and malformed payloads return readable errors before storage", async () => {
  await withoutNetwork(async () => {
    const db = guardedDb(), env = environment(db);
    for (const [method, handler] of Object.entries(handlers)) {
      const wrong = method === "POST" ? "GET" : "POST";
      assert.equal(cors(await handler({ request: makeRequest({ method: wrong }), env }), GROUP, method === "OPTIONS").status, 405);
    }
    for (const data of [null, [], { ...payload, consent: false }, { ...payload, validOrigin: true },
      { ...payload, validTurnstileHostname: "group.retallyrecovery.com" }, { ...payload, business: "scopesignal" }]) {
      assert.equal(cors(await onRequestPost({ request: makeRequest({ data }), env })).status, 400);
    }
    const malformed = new Request(API, { method: "POST", headers: { Origin: GROUP, "Content-Type": "application/json" }, body: "{invalid" });
    assert.equal(cors(await onRequestPost({ request: malformed, env })).status, 400);
    assert.deepEqual(db.calls, []);
  });
});

test("Group Turnstile hostname is bound to the admitted origin, including legacy same-origin forms", async () => {
  const cases = [
    ...["www.retallyrecovery.com", "retallyrecovery.com", "group.retallyrecovery.com.evil.example",
      "group.retallyrecovery.com.", "GROUP.retallyrecovery.com", "group.retallyrecovery.com:443",
      "https://group.retallyrecovery.com", "preview.pages.dev", "", null].map(hostname => ({ origin: GROUP, hostname })),
    { origin: WWW, hostname: "group.retallyrecovery.com" },
    { origin: WWW, hostname: "retallyrecovery.com" },
    { origin: APEX, hostname: "group.retallyrecovery.com" },
    { origin: APEX, hostname: "www.retallyrecovery.com" }
  ];
  const original = globalThis.fetch;
  try {
    for (const { origin, hostname } of cases) {
      const db = beforeReceiptDb(), env = environment(db);
      let verifications = 0, otherRequests = 0;
      globalThis.fetch = async url => {
        if (String(url) !== "https://challenges.cloudflare.com/turnstile/v0/siteverify") {
          otherRequests++; throw Error("Unexpected provider request");
        }
        verifications++;
        return Response.json({ success: true, action: "retally_group", hostname });
      };
      const url = origin === APEX ? APEX + "/api/group-inquiry" : API;
      assert.equal(cors(await onRequestPost({ request: makeRequest({ origin, url }), env }), origin).status, 400, String(hostname));
      assert.equal(verifications, 1);
      assert.equal(otherRequests, 0);
      assert.deepEqual(db.writes, []);
    }
  } finally { globalThis.fetch = original; }
});

test("Group origin and hostname never authorize a freight submission", async () => {
  const data = { fullName: payload.fullName, workEmail: payload.workEmail, companyName: payload.companyName,
    annualSpend: "Under $250k", modes: ["LTL"], idempotencyKey: payload.idempotencyKey, turnstileToken: payload.turnstileToken };
  await withoutNetwork(async () => {
    const db = guardedDb(), request = makeRequest({ url: WWW + "/api/inquiry", data });
    assert.equal(freightOrigin(request), false);
    const response = await freightPost({ request, env: environment(db) });
    assert.equal(response.status, 403);
    assert.equal(response.headers.get("Access-Control-Allow-Origin"), null);
    assert.deepEqual(db.calls, []);
  });
  const db = beforeReceiptDb(), original = globalThis.fetch;
  let verifications = 0;
  globalThis.fetch = async url => {
    assert.equal(String(url), "https://challenges.cloudflare.com/turnstile/v0/siteverify");
    verifications++;
    return Response.json({ success: true, action: "retally_audit", hostname: "group.retallyrecovery.com" });
  };
  try {
    const response = await freightPost({ request: makeRequest({ origin: WWW, url: WWW + "/api/inquiry", data }), env: environment(db) });
    assert.equal(response.status, 400);
    assert.equal(response.headers.get("Access-Control-Allow-Origin"), null);
    assert.equal(verifications, 1);
    assert.deepEqual(db.writes, []);
  } finally { globalThis.fetch = original; }
});
