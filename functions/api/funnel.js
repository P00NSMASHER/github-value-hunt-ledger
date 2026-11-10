// Privacy-minimal, aggregate-only marketing intent. Untrusted client events
// MUST NOT be called "human visitors", "inquiries", "qualified leads" or customers.
// The authoritative inquiry/QA registry remains the ONLY confirmed-lead source.
const HOSTS = new Set(["www.retallyrecovery.com", "retallyrecovery.com"]);
const EVENTS = new Set([
  "freight_landing_viewed",
  "freight_free_audit_cta_clicked",
  "freight_audit_form_started",
  "freight_audit_request_prepared"
]);
const CHANNELS = new Set(["direct", "organic_search", "referral", "campaign"]);
const OFFERS = new Set(["general", "founding", "second_look"]);
const AUTOMATION = /bot|crawler|spider|headless|playwright|puppeteer|selenium|python|curl|wget|monitor|audit\/|capturebrief-release|retally-public-release|lighthouse/i;

function respond(status, payload) {
  return new Response(payload === null ? null : JSON.stringify(payload), {
    status, headers: {"Cache-Control":"no-store, private", "X-Content-Type-Options":"nosniff",
      ...(payload===null?{}:{"Content-Type":"application/json; charset=utf-8"})}
  });
}
function validRequest(request) {
  const url = new URL(request.url);
  if (url.protocol !== "https:" || !HOSTS.has(url.hostname) ||
      url.pathname !== "/api/funnel" || request.method !== "POST") return false;
  const origin = request.headers.get("Origin") || "";
  if (origin !== url.origin || request.headers.get("Sec-Fetch-Site") !== "same-origin")
    return false;
  const mode = request.headers.get("Sec-Fetch-Mode");
  if (mode && mode !== "cors") return false;
  if (!/^application\/json(?:\s*;.*)?$/i.test(request.headers.get("Content-Type") || "")) return false;
  return true;
}
async function readSmallBody(request) {
  if (Number(request.headers.get("Content-Length")||"0") > 256 || !request.body)
    throw new Error("invalid_size");
  const reader = request.body.getReader();
  const parts = []; let total=0;
  try {
    while(true) {
      const {done,value} = await reader.read();
      if(done) break;
      total += value.byteLength;
      if(total > 256) { await reader.cancel(); throw new Error("invalid_size"); }
      parts.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes=new Uint8Array(total); let pos=0;
  for(const part of parts){bytes.set(part,pos);pos+=part.length;}
  return JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(bytes));
}
export async function onRequestPost({request, env}) {
  if (!validRequest(request)) return respond(403, {ok:false});
  if (AUTOMATION.test(request.headers.get("User-Agent")||"") ||
      request.cf?.botManagement?.score < 30) return respond(204, null);
  if (!env?.INQUIRY_DB?.prepare) return respond(503, {ok:false});
  let p;
  try {p=await readSmallBody(request);} catch {return respond(400, {ok:false});}
  if (!p || typeof p !== "object" || Array.isArray(p) ||
      Object.keys(p).sort().join(",") !== "channel,event,offer" ||
      !EVENTS.has(p.event) || !CHANNELS.has(p.channel) || !OFFERS.has(p.offer))
    return respond(400, {ok:false});
  try {
    const day=new Date().toISOString().slice(0,10);
    const saved=await env.INQUIRY_DB.prepare(
      "INSERT INTO marketing_funnel_daily(day_utc,event,channel,offer,interactions) VALUES(?,?,?,?,1) " +
      // Bound daily D1 *row writes* even if a client spoofs browser headers.
      // 4 events × 4 channels × 3 offers × 250 = at most 12,000 writes/day.
      "ON CONFLICT(day_utc,event,channel,offer) DO UPDATE SET interactions=interactions+1 " +
      "WHERE marketing_funnel_daily.interactions < 250"
    ).bind(day,p.event,p.channel,p.offer).run();
    return saved?.success === true ? respond(204, null) : respond(503, {ok:false});
  } catch {return respond(503, {ok:false});}
}
export async function onRequestGet() { return respond(405,{ok:false}); }
