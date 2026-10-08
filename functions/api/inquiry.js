// RETALLY production inquiry intake. Fail closed unless every release gate is configured.
// No secrets, documents, third-party destinations, or raw IP addresses are logged.
const ALLOWED = new Set([
  "fullName", "workEmail", "companyName", "annualSpend", "modes",
  "monthlyShipments", "invoiceHistory", "majorCarriers", "records",
  "suspectedIssues", "issueNotes", "campaign", "turnstileToken",
  "idempotencyKey", "website"
]);
const SPENDS = new Set(["Under $250k", "$250k–$1M", "$1M–$5M", "$5M–$20M", "$20M+"]);
const MODES = new Set(["Parcel", "LTL", "FTL", "Intermodal", "Ocean / air", "Other"]);
const SHIPMENTS = new Set(["", "Under 50", "50–249", "250–999", "1,000+"]);
const HISTORY = new Set(["", "Less than 3 months", "3–5 months", "6–12 months", "13–24 months", "More than 24 months"]);
const ISSUES = new Set(["", "Yes", "No", "Not sure"]);
const RECORDS = new Set(["Invoice export", "Rate agreements", "Shipment records", "Payment or credit evidence"]);
const CAMPAIGN = new Set(["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]);
const HOSTS = new Set(["www.retallyrecovery.com", "retallyrecovery.com"]);
const MAX_BODY_BYTES = 8192;
const SENSITIVE = /\b(?:password|passcode|api[\s_-]?key|access[\s_-]?token|bank[\s_-]?account|routing[\s_-]?number|card[\s_-]?number|cvv|iban|swift[\s_-]?code)\b/i;

function answer(code, body) {
  return new Response(JSON.stringify(body), {
    status: code,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store, private",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer"
    }
  });
}
function invalid(message = "Please review the form details and try again.") {
  return answer(400, { ok: false, error: message });
}
function cleanString(x, limit, required = false) {
  if (typeof x !== "string" || x.length > limit * 3) return null;
  const v = x.trim().replace(/\s+/g, " ");
  return (!v && required) || v.length > limit || /[\x00-\x08\x0B-\x1F\x7F]/.test(v) ? null : v;
}
function checkedChoice(x, allowed, required = false) {
  const v = cleanString(x, 80, required);
  return v !== null && allowed.has(v) ? v : null;
}
function checkedList(x, allowed, required = false) {
  if (!Array.isArray(x) || x.length > allowed.size || (required && x.length === 0)) return null;
  if (x.some(v => typeof v !== "string" || !allowed.has(v))) return null;
  return [...new Set(x)].sort();
}
function validEmail(x) {
  return x && x.length <= 160 && /^[a-zA-Z0-9][a-zA-Z0-9._%+\-]{0,62}@[a-zA-Z0-9](?:[a-zA-Z0-9.\-]{0,190}[a-zA-Z0-9])?\.[a-zA-Z]{2,24}$/.test(x) &&
    !x.includes("..");
}
export function normalize(body) {
  if (!body || typeof body !== "object" || Array.isArray(body)) return null;
  if (Object.keys(body).some(k => !ALLOWED.has(k))) return null;
  if (body.website !== undefined && body.website !== "") return null; // honeypot
  const fullName = cleanString(body.fullName, 100, true);
  const workEmail = cleanString(body.workEmail, 160, true)?.toLowerCase();
  const companyName = cleanString(body.companyName, 140, true);
  const annualSpend = checkedChoice(body.annualSpend, SPENDS, true);
  const modes = checkedList(body.modes, MODES, true);
  const monthlyShipments = checkedChoice(body.monthlyShipments ?? "", SHIPMENTS);
  const invoiceHistory = checkedChoice(body.invoiceHistory ?? "", HISTORY);
  const suspectedIssues = checkedChoice(body.suspectedIssues ?? "", ISSUES);
  const records = checkedList(body.records ?? [], RECORDS);
  const majorCarriers = cleanString(body.majorCarriers ?? "", 180);
  const issueNotes = cleanString(body.issueNotes ?? "", 500);
  const idempotencyKey = body.idempotencyKey;
  const turnstileToken = body.turnstileToken;
  if (!fullName || !companyName || !validEmail(workEmail) || !annualSpend || !modes ||
    monthlyShipments === null || invoiceHistory === null || suspectedIssues === null ||
    records === null || majorCarriers === null || issueNotes === null ||
    SENSITIVE.test(majorCarriers) || SENSITIVE.test(issueNotes) ||
    typeof idempotencyKey !== "string" || !/^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(idempotencyKey) ||
    typeof turnstileToken !== "string" || !turnstileToken || turnstileToken.length > 2048) return null;
  const campaign = body.campaign ?? {};
  if (typeof campaign !== "object" || !campaign || Array.isArray(campaign) ||
      Object.keys(campaign).some(k => !CAMPAIGN.has(k))) return null;
  const sources = {};
  for (const [k, v] of Object.entries(campaign)) {
    const s = cleanString(v, 120);
    if (s === null) return null;
    if (s) sources[k] = s;
  }
  return {
    fullName, workEmail, companyName, annualSpend, modes,
    monthlyShipments, invoiceHistory, suspectedIssues, records,
    majorCarriers, issueNotes, campaign: sources, idempotencyKey, turnstileToken
  };
}
export function validOrigin(request) {
  const url = new URL(request.url);
  const origin = request.headers.get("Origin");
  if (!HOSTS.has(url.hostname) || url.protocol !== "https:" || !origin) return false;
  try {
    const o = new URL(origin);
    return o.protocol === "https:" && o.host === url.host && o.pathname === "/";
  } catch {
    return false;
  }
}
async function boundedJson(request) {
  const size = Number(request.headers.get("Content-Length") || 0);
  if (size > MAX_BODY_BYTES) throw new Error("too_large");
  const stream = request.body;
  if (!stream) throw new Error("missing_body");
  const reader = stream.getReader();
  const chunks = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_BODY_BYTES) {
        await reader.cancel();
        throw new Error("too_large");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(total);
  let pos = 0;
  for (const part of chunks) { bytes.set(part, pos); pos += part.byteLength; }
  return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
}
async function digest(s) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(bytes)].map(c => c.toString(16).padStart(2, "0")).join("");
}
function canonical(p) {
  const { idempotencyKey, turnstileToken, ...stored } = p;
  return JSON.stringify(stored);
}
function validEnv(env) {
  return env.FREIGHT_INQUIRY_ENABLED === "1" &&
    env.FREIGHT_INQUIRY_MAILBOX_VERIFIED === "1" &&
    env.INQUIRY_DB?.prepare &&
    env.TURNSTILE_SECRET && env.TURNSTILE_SITEKEY &&
    env.INQUIRY_RATE_SECRET &&
    env.CLOUDFLARE_EMAIL_API_TOKEN &&
    env.CLOUDFLARE_ACCOUNT_ID &&
    env.INQUIRY_NOTIFY_TO === "jay@retallyrecovery.com" &&
    typeof env.INQUIRY_NOTIFY_FROM === "string" &&
    /^[a-z0-9._+-]+@retallyrecovery\.com$/.test(env.INQUIRY_NOTIFY_FROM);
}
async function limitRequest(env, ip) {
  if (!ip) return false;
  const hour = Math.floor(Date.now() / 3600000);
  const day = Math.floor(Date.now() / 86400000);
  for (const [period, bucket, max, expire] of [
    ["h", hour, 5, (hour + 1) * 3600],
    ["d", day, 20, (day + 1) * 86400]
  ]) {
    const key = await digest(env.INQUIRY_RATE_SECRET + ":" + period + ":" + bucket + ":" + ip);
    const result = await env.INQUIRY_DB.prepare(
      "INSERT INTO inquiry_limits(bucket,hits,expires_at) VALUES(?,1,?) " +
      "ON CONFLICT(bucket) DO UPDATE SET hits=hits+1,expires_at=excluded.expires_at RETURNING hits"
    ).bind(key, expire).first();
    if (!result || result.hits > max) return false;
  }
  return true;
}
async function verifyTurnstile(p, request, env) {
  const form = new FormData();
  form.set("secret", env.TURNSTILE_SECRET);
  form.set("response", p.turnstileToken);
  form.set("remoteip", request.headers.get("CF-Connecting-IP") || "");
  form.set("idempotency_key", p.idempotencyKey);
  const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
    method: "POST", body: form, signal: AbortSignal.timeout(7000)
  });
  if (!response.ok) return false;
  const r = await response.json();
  return r.success === true && r.action === "retally_audit" && HOSTS.has(r.hostname);
}
export function notificationText(reference, p) {
  const lines = [
    "RETALLY | Free Recovery Audit", "Reference: " + reference, "",
    "Name: " + p.fullName, "Work email: " + p.workEmail, "Company: " + p.companyName,
    "Annual freight spend: " + p.annualSpend, "Freight modes: " + p.modes.join(", "),
    "Monthly shipments: " + (p.monthlyShipments || "Not provided"),
    "History: " + (p.invoiceHistory || "Not provided"),
    "Major carriers: " + (p.majorCarriers || "Not provided"),
    "Available records: " + (p.records.join(", ") || "Not provided"),
    "Suspected issues: " + (p.suspectedIssues || "Not provided"),
    "Reason: " + (p.issueNotes || "Not provided"),
    "Campaign: " + (Object.entries(p.campaign).map(([k,v]) => k + "=" + v).join(", ") || "Direct"),
    "", "Contact request only. No files, billing documents, access rights or collection authority have been received."
  ];
  return lines.join("\n");
}
async function notify(env, reference, p) {
  const res = await fetch(
    "https://api.cloudflare.com/client/v4/accounts/" + encodeURIComponent(env.CLOUDFLARE_ACCOUNT_ID) + "/email/sending/send",
    {
      method: "POST",
      headers: { "Authorization": "Bearer " + env.CLOUDFLARE_EMAIL_API_TOKEN, "Content-Type": "application/json" },
      body: JSON.stringify({
        from: env.INQUIRY_NOTIFY_FROM,
        to: [env.INQUIRY_NOTIFY_TO],
        reply_to: p.workEmail,
        subject: "RETALLY Free Audit | " + reference,
        text: notificationText(reference, p)
      }),
      signal: AbortSignal.timeout(9000)
    }
  );
  if (!res.ok) return false;
  const json = await res.json();
  // API-level success is not evidence that our intended recipient was accepted.
  // In particular, a suppressed recipient can yield success:true.
  // Treat queued as provider-accepted, not as delivered to the actual inbox.
  if (json?.success !== true || !json.result) return false;
  const target = env.INQUIRY_NOTIFY_TO.toLowerCase();
  const delivered = Array.isArray(json.result.delivered) ? json.result.delivered : [];
  const queued = Array.isArray(json.result.queued) ? json.result.queued : [];
  const suppressed = Array.isArray(json.result.suppressed_recipients) ? json.result.suppressed_recipients : [];
  const bounced = Array.isArray(json.result.permanent_bounces) ? json.result.permanent_bounces : [];
  const hasTarget = values => values.some(v => typeof v === "string" && v.toLowerCase() === target);
  return !hasTarget(suppressed) && !hasTarget(bounced) && (hasTarget(delivered) || hasTarget(queued));
}
export async function onRequestPost({ request, env }) {
  // A backend deployment alone does not enable this service for the public.
  if (!validEnv(env)) return answer(503, { ok: false, error: "Online submission is not available. Please use the email contact option." });
  if (!validOrigin(request)) return answer(403, { ok: false, error: "Request origin was not accepted." });
  if (!/^application\/json(?:\s*;.*)?$/i.test(request.headers.get("content-type") || "")) {
    return answer(415, { ok: false, error: "Only the secure form is supported. No file attachments are accepted." });
  }
  let p;
  try { p = normalize(await boundedJson(request)); }
  catch (e) { return e.message === "too_large" ? answer(413, { ok: false, error: "Request is too large. Do not include documents." }) : invalid(); }
  if (!p) return invalid("Please correct the form. Do not include account numbers, credentials or attachments.");
  const payload = canonical(p);
  const fingerprint = await digest(payload);
  try {
    const db = env.INQUIRY_DB;
    const existing = await db.prepare(
      "SELECT reference, fingerprint FROM inquiries WHERE idempotency_key=?"
    ).bind(p.idempotencyKey).first();
    if (existing) return existing.fingerprint === fingerprint
      ? answer(202, { ok: true, reference: existing.reference, received: true, duplicate: true })
      : answer(409, { ok: false, error: "This request identifier was already used. Restart the form." });
    if (!await limitRequest(env, request.headers.get("CF-Connecting-IP"))) {
      return answer(429, { ok: false, error: "Please try again later or contact RETALLY by email." });
    }
    if (!await verifyTurnstile(p, request, env)) {
      return invalid("Verification expired or failed. Refresh the verification and try again.");
    }
    const reference = "RA-" + new Date().toISOString().slice(0,10).replaceAll("-","") +
      "-" + crypto.randomUUID().slice(0,8).toUpperCase();
    const now = Math.floor(Date.now() / 1000);
    const inserted = await db.prepare(
      "INSERT INTO inquiries(reference,idempotency_key,fingerprint,full_name,work_email,company_name,annual_spend,modes_json,details_json,accepted_at,notification_status) " +
      "VALUES(?,?,?,?,?,?,?,?,?,?,'pending') ON CONFLICT(idempotency_key) DO NOTHING"
    ).bind(reference,p.idempotencyKey,fingerprint,p.fullName,p.workEmail,p.companyName,p.annualSpend,
      JSON.stringify(p.modes), JSON.stringify({
        monthlyShipments:p.monthlyShipments,invoiceHistory:p.invoiceHistory,suspectedIssues:p.suspectedIssues,
        records:p.records,majorCarriers:p.majorCarriers,issueNotes:p.issueNotes,campaign:p.campaign
      }),now).run();
    if (!inserted.success) throw new Error("db_insert_failed");
    if (inserted.meta?.changes === 0) {
      const duplicate = await db.prepare("SELECT reference,fingerprint FROM inquiries WHERE idempotency_key=?")
        .bind(p.idempotencyKey).first();
      return duplicate?.fingerprint === fingerprint
        ? answer(202, { ok: true, reference:duplicate.reference, received:true,duplicate:true })
        : answer(409,{ok:false,error:"This request identifier was already used."});
    }
    // Durable acceptance is committed above. Notification is a separate, tracked state.
    let notified = false;
    try { notified = await notify(env,reference,p); } catch (_) { /* pending for operator reconciliation */ }
    if (notified) {
      try {
        await db.prepare("UPDATE inquiries SET notification_status='provider_accepted',notified_at=? WHERE reference=?")
          .bind(Math.floor(Date.now()/1000),reference).run();
      } catch (_) { /* durable inquiry is intact; reconciliation required */ }
    }
    // Incoming inquiries must never be purged as a side effect of accepting
    // another request. Notification status alone is not evidence of human
    // follow-up, closure, absence of a legal hold, or authority to delete.
    // Leave inquiry retention/erasure to a separately reviewed operator flow.
    // Only expired non-identifying rate-limit buckets are cleaned here.
    try {
      await db.prepare("DELETE FROM inquiry_limits WHERE expires_at < ?")
        .bind(now).run();
    } catch (_) { /* cleanup errors cannot roll back the saved inquiry */ }
    return answer(202, { ok: true, received: true, reference });
  } catch (_) {
    // Never expose raw input, infrastructure details, tokens or stack traces.
    return answer(503, { ok: false, error: "We could not confirm receipt. Please use the email contact option." });
  }
}
export function onRequestGet({ env }) {
  if (!validEnv(env)) return answer(503, { online: false });
  return answer(200, { online: true, siteKey: env.TURNSTILE_SITEKEY });
}
