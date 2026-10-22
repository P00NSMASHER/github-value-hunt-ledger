// RETALLY Group contact-only route. Reuses the verified same-origin,
// Turnstile, durable receipt, rate-limit, idempotency and fixed-inbox transport.
import { cleanString, validEmail, receiveInquiry, onRequestGet } from "./inquiry.js";
export { onRequestGet };

export const BUSINESSES = Object.freeze({
  general: "RETALLY Group",
  recovery: "RETALLY Recovery",
  capturebrief: "CaptureBrief",
  permitplate: "PermitPlate NYC",
  rehabsignal: "RehabSignal",
  sheetharbor: "SheetHarbor",
  "app-factory": "App Factory",
  "data-services": "RETALLY Data Services",
  scopesignal: "ScopeSignal",
  "contractor-quote-recovery": "Contractor Quote Recovery",
  resonance: "Resonance",
  "market-surveillance": "Market Surveillance Research"
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
  details:p=>({inquiryKind:p.inquiryKind,business:p.business,message:p.message,consent:p.consent})
});
export function onRequestPost(context) {
  return receiveInquiry(context,GROUP_POLICY);
}
