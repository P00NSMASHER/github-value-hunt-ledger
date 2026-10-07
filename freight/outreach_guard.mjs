/**
 * Freight Recovery pre-send gate. No network or email transport.
 * State and prospect data MUST live privately outside the public checkout.
 * Callers must atomically persist the returned reservation BEFORE any send.
 * RESERVED/UNKNOWN reservations block retries until mailbox reconciliation.
 */
export const OPT_OUT = 'Reply "no thanks" and I won\'t follow up.';
const unresolved = /\{\{[\s\S]*?\}\}|\$\{[^}]*\}|<%[\s\S]*?%>|\[[^\]\n]*(?:required|placeholder|name|company|address|insert|todo|tbd)[^\]\n]*\]|<\s*(?:name|company|address|insert)[^>]*>|\b(?:TODO|TBD|PLACEHOLDER)\b/i;
const terminal = new Set(["OPT_OUT","NEGATIVE","HARD_BOUNCE","NO_FIT","CLOSED_NO_REPLY"]);
function norm(s) {
  return String(s || "").normalize("NFKC").replace(/[\u200B-\u200D\uFEFF]/g,"")
    .replace(/[“”]/g,'"').replace(/[‘’]/g,"'").replace(/\s+/g," ").trim().toLowerCase();
}
function visible(html) {
  return html.replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi,"")
    .replace(/<[^>]*>/g," ").replace(/&nbsp;|&#160;/gi," ")
    .replace(/&quot;|&#34;/gi,'"').replace(/&apos;|&#39;|&#x27;/gi,"'")
    .replace(/&amp;/gi,"&");
}
export function recipientKey(value) {
  if (typeof value !== "string" || !/^[^\s<>,;@]+@[^\s<>,;@]+\.[^\s<>,;@]+$/.test(value.trim()))
    throw new Error("SINGLE_RECIPIENT_REQUIRED");
  const [local,domain]=value.trim().toLowerCase().split("@");
  // Gmail aliases are the same mailbox. Do not strip plus/dots for corporate domains.
  if (domain==="gmail.com" || domain==="googlemail.com")
    return local.split("+")[0].replace(/\./g,"")+"@gmail.com";
  return local+"@"+domain;
}
export function reserveOutreach(message, state, sender, nowIso, reservationId) {
  const errors=[];
  const now=Date.parse(nowIso);
  if (!Number.isFinite(now)) throw new Error("INVALID_NOW");
  if (!state || state.schema_version!==1 || !Array.isArray(state.contacts) ||
      !Array.isArray(state.events)) throw new Error("PRIVATE_LEDGER_REQUIRED");
  const sync=Date.parse(state.mailbox_checked_at);
  if (!Number.isFinite(sync) || sync>now || now-sync>10*60*1000) errors.push("MAILBOX_RECHECK_REQUIRED");
  if (state.audit_hold!==false) errors.push("AUDIT_HOLD");
  if (!reservationId || state.events.some(e=>e.reservation_id===reservationId))
    errors.push("UNIQUE_RESERVATION_REQUIRED");
  let key;
  try { key=recipientKey(message.to); } catch { errors.push("SINGLE_RECIPIENT_REQUIRED"); }
  if (message.cc || message.bcc) errors.push("CC_BCC_NOT_ALLOWED");
  if (!message.account_id || unresolved.test(message.account_id)) errors.push("ACCOUNT_ID_REQUIRED");
  if (!message.subject?.trim()) errors.push("SUBJECT_REQUIRED");
  if (message.html && /<!--|\b(?:hidden|style)\s*=|<(?:script|style)\b/i.test(message.html)) errors.push("HTML_HIDDEN_CONTENT");
  const bodies=[message.text, ...(message.html===undefined?[]:[message.html])];
  if (!message.text?.trim()) errors.push("PLAIN_TEXT_REQUIRED");
  if (unresolved.test([message.subject,...bodies].join("\n"))) errors.push("UNRESOLVED_PLACEHOLDER");
  const postal=sender?.postal_lines;
  if (sender?.postal_approved!==true || !Array.isArray(postal) || postal.length<2 ||
      postal.some(s=>typeof s!=="string" || !s.trim() || unresolved.test(s)) ||
      !/\d/.test(postal?.[0]||"") || !/\b[A-Z]{2}\s+\d{5}(?:-\d{4})?\b/.test(postal?.slice(1).join(" ")||""))
    errors.push("APPROVED_SENDER_POSTAL_REQUIRED");
  bodies.forEach((body,index)=>{
    const readable=norm(index===1?visible(String(body||"")):body);
    if (!readable.includes(norm(OPT_OUT))) errors.push("OPT_OUT_MISSING_"+index);
    if (!readable.includes(norm(sender?.identity))) errors.push("SENDER_IDENTITY_MISSING_"+index);
    if (Array.isArray(postal) && postal.some(line=>!readable.includes(norm(line))))
      errors.push("SENDER_POSTAL_MISSING_"+index);
  });
  if (!sender?.identity?.trim() || unresolved.test(sender.identity)) errors.push("SENDER_IDENTITY_REQUIRED");
  const contact=state.contacts.find(c=>c.recipient_key===key && c.account_id===message.account_id);
  if (!contact) errors.push("RESEARCHED_CONTACT_REQUIRED");
  const matching=state.contacts.filter(c=>c.recipient_key===key || c.account_id===message.account_id);
  if (matching.some(c=>c.suppressed===true || terminal.has(c.status))) errors.push("SUPPRESSED");
  if (matching.some(c=>c.hold===true)) errors.push("CONTACT_HOLD");
  if (contact?.route_verified!==true) errors.push("OFFICIAL_ROUTE_REQUIRED");
  if (message.channel==="BUYER") {
    const q=contact?.qualification;
    if (!q || q.icp_version!=="ICP_V1" || q.approved!==true || !Number.isInteger(q.score) || q.score<65 || q.score>100 ||
        q.us_distributor_or_multisite_shipper!==true || q.target_scale_band!==true ||
        q.meaningful_ltl_or_parcel!==true || !Number.isFinite(q.history_months) || q.history_months<6 ||
        q.finance_owner_verified!==true || q.disqualified!==false ||
        !Array.isArray(q.evidence) || !q.evidence.length ||
        !q.evidence.every(u=>typeof u==="string" && /^https:\/\//.test(u)))
      errors.push("ICP_QUALIFICATION_REQUIRED");
    if (!["FIRST_LOOK","SECOND_LOOK"].includes(message.offer)) errors.push("OFFER_ROUTE_REQUIRED");
    if (q?.mature_controls===true && message.offer!=="SECOND_LOOK") errors.push("SECOND_LOOK_REQUIRED");
    if (!message.personalization?.trim() || unresolved.test(message.personalization) ||
        !norm(message.text).includes(norm(message.personalization))) errors.push("PERSONALIZATION_REQUIRED");
  } else if (!["REFERRAL","EDITORIAL","DIRECTORY"].includes(message.channel) ||
             contact?.channel_approved!==true) errors.push("CHANNEL_APPROVAL_REQUIRED");
  const past=state.events.filter(e=>e.recipient_key===key || e.account_id===message.account_id);
  if (past.some(e=>["RESERVED","UNKNOWN"].includes(e.delivery))) errors.push("UNRESOLVED_PRIOR_SEND");
  if (past.some(e=>!["SENT","CANCELLED","RESERVED","UNKNOWN","DRAFT"].includes(e.delivery)))
    errors.push("INVALID_DELIVERY_STATE");
  const sent=past.filter(e=>e.delivery==="SENT");
  if (sent.some(e=>!Number.isFinite(Date.parse(e.sent_at)) || Date.parse(e.sent_at)>now)) errors.push("INVALID_HISTORY");
  if (message.touch===1 && sent.length) errors.push("ALREADY_CONTACTED");
  if (![1,2,3].includes(message.touch)) errors.push("INVALID_TOUCH");
  if (message.touch>1) {
    if (message.channel!=="BUYER") errors.push("MANUAL_REPLY_REVIEW_REQUIRED");
    if (!message.reply_to_message_id || !sent.some(e=>e.message_id===message.reply_to_message_id && e.recipient_key===key))
      errors.push("PRIOR_THREAD_REQUIRED");
    if (matching.some(c=>c.status==="REPLIED" || c.status==="REFERRED")) errors.push("STOP_SEQUENCE_ON_REPLY");
    if (sent.length!==message.touch-1) errors.push("TOUCH_SEQUENCE_INVALID");
    const first=Math.min(...sent.map(e=>Date.parse(e.sent_at)));
    const last=Math.max(...sent.map(e=>Date.parse(e.sent_at)));
    const due=first+(message.touch===2?4:11)*24*60*60*1000;
    if (!Number.isFinite(first) || now<due || now-last<4*24*60*60*1000) errors.push("FOLLOW_UP_NOT_DUE");
  }
  if (errors.length) return {ok:false,errors:[...new Set(errors)]};
  const next=JSON.parse(JSON.stringify(state));
  next.events.push({reservation_id:reservationId,recipient_key:key,account_id:message.account_id,
    delivery:"RESERVED",reserved_at:nowIso,touch:message.touch,channel:message.channel});
  return {ok:true,errors:[],state:next,reservation_id:reservationId};
}
