// RETALLY Group contact-only route. Its exact-origin policy is confined to
// this route; freight retains its existing same-origin and Turnstile hosts.
// Durable receipts, release gates, rate limits and the fixed inbox are shared.
import { cleanString, validEmail, receiveInquiry, onRequestGet as inquiryConfig } from "./inquiry.js";

const GROUP_ORIGIN = "https://group.retallyrecovery.com";
const GROUP_API = "https://www.retallyrecovery.com/api/group-inquiry";
const LEGACY_ORIGINS = Object.freeze([
  "https://www.retallyrecovery.com", "https://retallyrecovery.com"
]);

function acceptedOrigin(request) {
  const origin = request.headers.get("Origin");
  // Compare serialized strings, not URL-normalized hostnames: credentials,
  // explicit ports, paths, queries, fragments and origin lookalikes fail closed.
  if (origin === GROUP_ORIGIN && request.url === GROUP_API) return origin;
  return LEGACY_ORIGINS.find(value => origin === value &&
    request.url === value + "/api/group-inquiry") || null;
}
function validGroupOrigin(request) {
  return acceptedOrigin(request) !== null && !hasCredentials(request);
}
function hasCredentials(request) {
  return ["Cookie", "Authorization", "Proxy-Authorization"].some(name => request.headers.has(name));
}
function groupAnswer(status, error) {
  return new Response(JSON.stringify({ ok: false, error }), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store, private",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      ...(status === 405 ? { Allow: "GET, POST, OPTIONS" } : {})
    }
  });
}
function admissionError(request, method, allowLegacyConfig = false) {
  // Same-origin fetch GETs ordinarily omit Origin. Preserve only that public
  // config lookup at the two exact production URLs, without any CORS grant.
  const legacyConfig = allowLegacyConfig && !request.headers.has("Origin") &&
    LEGACY_ORIGINS.some(origin => request.url === origin + "/api/group-inquiry");
  if ((!acceptedOrigin(request) && !legacyConfig) || hasCredentials(request)) {
    return groupAnswer(403, "Request origin or credentials were not accepted.");
  }
  return request.method === method ? null : groupAnswer(405, "Request method was not accepted.");
}
function withCors(request, response, preflight = false) {
  const headers = new Headers(response.headers);
  const vary = new Set((headers.get("Vary") || "").split(",").map(v => v.trim()).filter(Boolean));
  vary.add("Origin");
  if (preflight) {
    vary.add("Access-Control-Request-Method");
    vary.add("Access-Control-Request-Headers");
  }
  headers.set("Vary", [...vary].join(", "));
  headers.delete("Access-Control-Allow-Origin");
  headers.delete("Access-Control-Allow-Credentials");
  const origin = acceptedOrigin(request);
  if (origin) headers.set("Access-Control-Allow-Origin", origin);
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

export function onRequestGet(context) {
  const { request } = context;
  return withCors(request, admissionError(request, "GET", true) || inquiryConfig(context));
}
export function onRequestOptions({ request }) {
  const rejected = admissionError(request, "OPTIONS");
  if (rejected) return withCors(request, rejected, true);
  const method = request.headers.get("Access-Control-Request-Method");
  const requestedHeaders = request.headers.get("Access-Control-Request-Headers");
  const headers = requestedHeaders === null ? [] : requestedHeaders.split(",").map(v => v.trim().toLowerCase());
  if (!["GET", "POST"].includes(method) || headers.some(value => value !== "content-type") ||
      new Set(headers).size !== headers.length) {
    return withCors(request, groupAnswer(403, "Preflight was not accepted."), true);
  }
  return withCors(request, new Response(null, {
    status: 204,
    headers: {
      "Cache-Control": "no-store, private",
      "Access-Control-Allow-Methods": method,
      ...(headers.length ? { "Access-Control-Allow-Headers": "Content-Type" } : {})
    }
  }), true);
}

export const BUSINESSES = Object.freeze({
  general: "RETALLY Group",
  recovery: "RETALLY Freight Recovery",
  recoveryworks: "RETALLY RecoveryWorks",
  capturebrief: "CaptureBrief",
  permitplate: "PermitPlate"
});
const ALLOWED = new Set(["business","fullName","workEmail","companyName","message","consent",
  "turnstileToken","idempotencyKey","website"]);
const SENSITIVE = /\b(?:password|passcode|api[\s_-]?key|access[\s_-]?token|bank[\s_-]?account|routing[\s_-]?number|card[\s_-]?number|cvv|iban|swift[\s_-]?code|social[\s_-]?security|patient[\s_-]?record|classified|controlled[\s_-]?unclassified)\b/i;
export function normalize(body) {
  if (!body || typeof body !== "object" || Array.isArray(body) ||
      Object.keys(body).some(k=>!ALLOWED.has(k)) || body.consent !== true ||
      (body.website !== undefined && body.website !== "")) return null;
  const business = body.business;
  if (typeof business !== "string" || !Object.hasOwn(BUSINESSES,business)) return null;
  const fullName = cleanString(body.fullName,100,true);
  const workEmail = cleanString(body.workEmail,160,true)?.toLowerCase();
  const companyName = cleanString(body.companyName ?? "",140);
  const message = cleanString(body.message,800,true);
  const idempotencyKey = body.idempotencyKey, turnstileToken = body.turnstileToken;
  if (!fullName || !validEmail(workEmail) || companyName === null || !message ||
      SENSITIVE.test(message) || SENSITIVE.test(companyName) ||
      typeof idempotencyKey !== "string" || !/^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(idempotencyKey) ||
      typeof turnstileToken !== "string" || !turnstileToken || turnstileToken.length>2048) return null;
  return { inquiryKind:"group_contact",business,fullName,workEmail,companyName,message,
    consent:true,annualSpend:"",modes:[],idempotencyKey,turnstileToken };
}
export function notificationText(reference,p) {
  return ["RETALLY | Group inquiry","Reference: "+reference,"",
    "Business: "+BUSINESSES[p.business],"Name: "+p.fullName,"Email: "+p.workEmail,
    "Company: "+(p.companyName || "Not provided"),"Message: "+p.message,"",
    "Contact request only. No files, payment, customer authorization, service commitment or confidential records have been received."
  ].join("\n");
}
const GROUP_POLICY = Object.freeze({
  normalize, turnstileAction:"retally_group", subject:"RETALLY Group Inquiry", notificationText,
  validOrigin: validGroupOrigin,
  validTurnstileHostname: (hostname, request) => {
    const origin = acceptedOrigin(request);
    return origin !== null && hostname === new URL(origin).hostname;
  },
  details:p=>({inquiryKind:p.inquiryKind,business:p.business,message:p.message,consent:p.consent})
});
export async function onRequestPost(context) {
  const { request } = context;
  const rejected = admissionError(request, "POST");
  return withCors(request, rejected || await receiveInquiry(context,GROUP_POLICY));
}
