// RETALLY Inquiry Operations | independent read-only D1 reconciliation.
// No customer content, name, email, IP, query params, or secret value is printed.
// Safe to run while the live inquiry endpoint is disabled.
const STATES = ["pending", "provider_accepted", "delivery_verified"];
const DAY = 86400;
const MAX = Number.MAX_SAFE_INTEGER;
const safeCount = (value, label) => {
  if ((typeof value !== "number" && typeof value !== "string") ||
      !/^\d+$/.test(String(value)) || !Number.isSafeInteger(Number(value)) ||
      Number(value) < 0) throw new Error("Invalid aggregate: " + label);
  return Number(value);
};
const isoSeconds = value => {
  if (value === undefined) return Math.floor(Date.now()/1000);
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(value)) {
    throw new Error("Use an ISO-8601 UTC timestamp ending in Z");
  }
  const n = Date.parse(value);
  if (!Number.isFinite(n) || new Date(n).toISOString().replace(".000Z","Z") !== value) {
    throw new Error("Invalid UTC timestamp");
  }
  return Math.floor(n / 1000);
};
export function readOnlyQueries(asOf) {
  if (!Number.isSafeInteger(asOf) || asOf < DAY * 90 || asOf > MAX - DAY * 90) {
    throw new Error("Invalid audit timestamp");
  }
  const hour = asOf - 3600, day = asOf - DAY, retention = asOf - DAY*90;
  return [
    { name:"notification_aging", sql:
      "SELECT notification_status, COUNT(*) AS total, MIN(accepted_at) AS oldest_at, "+
      "SUM(CASE WHEN accepted_at <= "+hour+" THEN 1 ELSE 0 END) AS aged_hour, "+
      "SUM(CASE WHEN accepted_at <= "+day+" THEN 1 ELSE 0 END) AS aged_day "+
      "FROM inquiries GROUP BY notification_status ORDER BY notification_status" },
    { name:"retention_review", sql:
      "SELECT COUNT(*) AS aged_total, "+
      "COALESCE(SUM(CASE WHEN notification_status='pending' THEN 1 ELSE 0 END),0) AS aged_pending, "+
      "COALESCE(SUM(CASE WHEN notification_status='provider_accepted' THEN 1 ELSE 0 END),0) AS aged_provider, "+
      "COALESCE(SUM(CASE WHEN notification_status='delivery_verified' THEN 1 ELSE 0 END),0) AS aged_delivered "+
      "FROM inquiries WHERE accepted_at < "+retention },
    { name:"case_lifecycle", sql:
      "SELECT COUNT(*) AS total, "+
      "COALESCE(SUM(CASE WHEN d.reference IS NULL THEN 1 ELSE 0 END),0) AS unacknowledged, "+
      "COALESCE(SUM(CASE WHEN d.case_state='ACKNOWLEDGED' THEN 1 ELSE 0 END),0) AS acknowledged, "+
      "COALESCE(SUM(CASE WHEN d.case_state='CLOSED' THEN 1 ELSE 0 END),0) AS closed, "+
      "COALESCE(SUM(CASE WHEN r.response_state='REPORTED' THEN 1 ELSE 0 END),0) AS reported, "+
      "COALESCE(SUM(CASE WHEN r.response_state='VERIFIED' THEN 1 ELSE 0 END),0) AS verified, "+
      "COALESCE(SUM(CASE WHEN r.response_state='WAIVED' THEN 1 ELSE 0 END),0) AS waived, "+
      "COALESCE(SUM(CASE WHEN d.legal_hold=1 THEN 1 ELSE 0 END),0) AS held, "+
      "COALESCE(SUM(CASE WHEN d.case_state='CLOSED' AND (r.reference IS NULL OR r.response_state NOT IN ('VERIFIED','WAIVED')) THEN 1 ELSE 0 END),0) AS closed_unverified, "+
      "COALESCE(SUM(CASE WHEN d.reference IS NULL AND i.accepted_at <= "+(asOf-4*3600)+" THEN 1 ELSE 0 END),0) AS aged_unacknowledged, "+
      "COALESCE(SUM(CASE WHEN d.case_state='ACKNOWLEDGED' AND (r.reference IS NULL OR r.response_state='REPORTED') AND i.accepted_at <= "+day+" THEN 1 ELSE 0 END),0) AS aged_response_incomplete, "+
      "COALESCE(SUM(CASE WHEN i.accepted_at < "+retention+" AND (d.case_state IS NULL OR d.case_state<>'CLOSED') THEN 1 ELSE 0 END),0) AS expired_unresolved, "+
      "COALESCE(SUM(CASE WHEN i.accepted_at < "+retention+" AND d.case_state='CLOSED' AND d.purge_approved_at IS NULL THEN 1 ELSE 0 END),0) AS expired_closed_unapproved "+
      "FROM inquiries i LEFT JOIN inquiry_case_dispositions d ON d.reference=i.reference "+
      "LEFT JOIN inquiry_response_states r ON r.reference=i.reference" },
    { name:"rate_limits", sql:
      "SELECT COUNT(*) AS expired_total FROM inquiry_limits WHERE expires_at < "+asOf }
  ];
}
function onlyKeys(row, expected, label) {
  if (!row || typeof row !== "object" || Array.isArray(row) ||
      Object.keys(row).some(k => !expected.includes(k)) ||
      expected.some(k => !Object.hasOwn(row,k))) {
    throw new Error("Unexpected D1 aggregate shape: " + label);
  }
}
export function reconcile(asOf, parts) {
  const queries=readOnlyQueries(asOf);
  if (!parts || typeof parts !== "object" || Array.isArray(parts) ||
      Object.keys(parts).sort().join("|") !== queries.map(q=>q.name).sort().join("|")) {
    throw new Error("Incomplete aggregate set; do not interpret as zero activity");
  }
  const rows=parts.notification_aging;
  if (!Array.isArray(rows) || rows.length > STATES.length) throw new Error("Malformed notification aggregates");
  const counts=Object.fromEntries(STATES.map(s => [s,{total:0,aged_hour:0,aged_day:0,oldest_at:null}]));
  const seen=new Set();
  for(const row of rows){
    onlyKeys(row,["notification_status","total","oldest_at","aged_hour","aged_day"],"notification");
    const s=row.notification_status;
    if(!STATES.includes(s) || seen.has(s)) throw new Error("Unknown or duplicate notification state");
    seen.add(s);
    const n=safeCount(row.total,"total"), h=safeCount(row.aged_hour,"aged_hour"),
      d=safeCount(row.aged_day,"aged_day");
    if(h>n || d>h || n===0) throw new Error("Inconsistent aging aggregates");
    const oldest=safeCount(row.oldest_at,"oldest_at");
    if(oldest>asOf) throw new Error("Future-dated inquiry in aggregate");
    counts[s]={total:n,aged_hour:h,aged_day:d,oldest_at:oldest};
  }
  if(!Array.isArray(parts.retention_review) || parts.retention_review.length!==1) throw new Error("Missing retention aggregate");
  if(!Array.isArray(parts.rate_limits) || parts.rate_limits.length!==1) throw new Error("Missing rate-limit aggregate");
  const rr=parts.retention_review[0], rl=parts.rate_limits[0];
  onlyKeys(rr,["aged_total","aged_pending","aged_provider","aged_delivered"],"retention");
  onlyKeys(rl,["expired_total"],"rate limits");
  const aged_total=safeCount(rr.aged_total,"aged_total"),
    aged_pending=safeCount(rr.aged_pending,"aged_pending"),
    aged_provider=safeCount(rr.aged_provider,"aged_provider"),
    aged_delivered=safeCount(rr.aged_delivered,"aged_delivered"),
    expired_total=safeCount(rl.expired_total,"expired_total");
  if(aged_total!==aged_pending+aged_provider+aged_delivered ||
    aged_pending>counts.pending.total || aged_provider>counts.provider_accepted.total ||
    aged_delivered>counts.delivery_verified.total) {
    throw new Error("Retention counts fail conservation");
  }
  if(!Array.isArray(parts.case_lifecycle) || parts.case_lifecycle.length!==1)
    throw new Error("Missing lifecycle aggregate; never infer a zero lead queue");
  const cl=parts.case_lifecycle[0];
  const cols=["total","unacknowledged","acknowledged","closed","reported","verified",
    "waived","held","closed_unverified","aged_unacknowledged",
    "aged_response_incomplete","expired_unresolved","expired_closed_unapproved"];
  onlyKeys(cl,cols,"case lifecycle");
  const cases=Object.fromEntries(cols.map(k=>[k,safeCount(cl[k],k)]));
  const notifications=STATES.reduce((n,s)=>n+counts[s].total,0);
  if(cases.total!==notifications ||
     cases.unacknowledged+cases.acknowledged+cases.closed!==cases.total ||
     cases.reported+cases.verified+cases.waived>cases.acknowledged+cases.closed ||
     cases.held>cases.total ||
     cases.aged_unacknowledged>cases.unacknowledged ||
     cases.aged_response_incomplete>cases.acknowledged ||
     cases.expired_unresolved>aged_total ||
     cases.expired_closed_unapproved>aged_total ||
     cases.closed_unverified>cases.closed) {
    throw new Error("Lead lifecycle aggregate inconsistent with notifications or retained cases");
  }
  const alerts=[];
  if(cases.unacknowledged>0)alerts.push({
    priority:cases.aged_unacknowledged>0?"P0":"P1",code:"UNACKNOWLEDGED_LEADS",
    count:cases.unacknowledged,action:"Assign signed, accountable reviewer; verify matching Zoho inbox reference; do not confuse message delivery with staff acknowledgment."});
  if(cases.acknowledged>0)alerts.push({
    priority:cases.aged_response_incomplete>0?"P0":"P1",code:"OPEN_LEADS_REQUIRE_VERIFIED_RESPONSE",
    count:cases.acknowledged,action:"Record the actual Zoho sent-message evidence, obtain independent verified response or approved no-contact waiver, and log disposition."});
  if(cases.reported>0)alerts.push({
    priority:cases.aged_response_incomplete>0?"P0":"P1",code:"REPORTED_RESPONSE_UNVERIFIED",
    count:cases.reported,action:"Another authorized operator must inspect independent source evidence before treating the first response as verified."});
  if(cases.closed_unverified>0)alerts.push({
    priority:"P0",code:"IMPOSSIBLE_CLOSED_CASE",count:cases.closed_unverified,
    action:"Investigate privileged D1 bypass or data corruption; no purge is permitted."});
  if(cases.expired_unresolved>0 || cases.expired_closed_unapproved>0)alerts.push({
    priority:"P0",code:"RETENTION_EXCEPTION_OR_APPROVAL_REQUIRED",
    count:cases.expired_unresolved+cases.expired_closed_unapproved,
    action:"Unresolved and unapproved aged cases are on hold for documented operator review; no blanket deletion."});
  if(counts.pending.total>0) alerts.push({priority:counts.pending.aged_hour>0?"P0":"P1",
    code:"UNDELIVERED_NOTIFICATION",count:counts.pending.total,
    action:"Reconcile each pending reference in restricted D1; independently verify recipient inbox, never infer delivery from HTTP 202."});
  if(counts.provider_accepted.total>0) alerts.push({priority:counts.provider_accepted.aged_day>0?"P0":"P1",
    code:"PROVIDER_NOT_INBOX_PROOF",count:counts.provider_accepted.total,
    action:"Confirm each reference in actual mailbox; provider queued/delivered field is not human follow-up."});
  if(aged_total>0) alerts.push({priority:aged_pending+aged_provider>0?"P0":"P1",
    code:"RETENTION_DECISION_REQUIRED",count:aged_total,
    action:"No automatic deletion. Independently verify human disposition, legal hold and data-retention authority before targeted purge."});
  if(expired_total>0) alerts.push({priority:"P2",code:"EXPIRED_RATE_BUCKETS",
    count:expired_total,action:"Clean up expired rate-limit buckets through a separately authorized operator change."});
  // Source-ledger structure can be verified; the actual human identity and Zoho
  // reply proof still require independently checked Access and mailbox evidence.
  if(cases.total===0)alerts.push({priority:"P2",code:"NO_LEADS_DOES_NOT_PROVE_RESPONSE_OPERATIONS",
    count:0,action:"Demonstrate a controlled signed response and retention review before enabling broad production intake."});
  return {
    as_of:new Date(asOf*1000).toISOString(),source:"read-only D1 aggregates",
    inquiry_total:notifications,
    status_counts:counts,
    case_lifecycle:cases,
    retention:{over_90_days:aged_total,pending:aged_pending,provider_accepted:aged_provider,delivery_verified:aged_delivered},
    rate_limit:{expired_buckets:expired_total},
    operational_acceptance:"CASE_ENFORCEMENT_CONFIGURED_ACTUAL_HUMAN_REVIEW_NOT_PROVEN",alerts
  };
}
async function queryD1({accountId,databaseId,token},sql,fetcher) {
  const url="https://api.cloudflare.com/client/v4/accounts/"+encodeURIComponent(accountId)+
    "/d1/database/"+encodeURIComponent(databaseId)+"/query";
  const response=await fetcher(url,{method:"POST",headers:{
    Authorization:"Bearer "+token,"Content-Type":"application/json"
  },body:JSON.stringify({sql}),signal:AbortSignal.timeout(10000)});
  if(!response.ok) throw new Error("Cloudflare aggregate query failed: HTTP "+response.status);
  const j=await response.json();
  if(j?.success!==true || !Array.isArray(j.result) || j.result.length!==1 ||
    !Array.isArray(j.result[0]?.results)) {
    throw new Error("D1 aggregate unavailable; fail closed");
  }
  return j.result[0].results;
}
export async function collect(asOf, credentials, fetcher=fetch) {
  if(!credentials || ![credentials.accountId,credentials.databaseId,credentials.token].every(v=>typeof v==="string" && v.length>0)) {
    throw new Error("Missing scoped operator credentials");
  }
  const parts={};
  for(const q of readOnlyQueries(asOf)){
    parts[q.name]=await queryD1(credentials,q.sql,fetcher);
  }
  return reconcile(asOf,parts);
}
export function dryRun(utc) {
  const asOf=isoSeconds(utc);
  return {as_of:new Date(asOf*1000).toISOString(),method:"POST",url_template:"/accounts/{accountId}/d1/database/{databaseId}/query",
    statements:readOnlyQueries(asOf),warning:"SELECT only. Never interpret provider acceptance as Zoho receipt; no deletion is authorized."};
}
const isEntry=typeof process!=="undefined" && process.argv?.[1]?.endsWith("/reconcile.mjs");
if(isEntry) {
  try{
    const args=process.argv.slice(2),mode=args[0]||"--dry-run",
      timestamp=args.find(s=>s.startsWith("--as-of="))?.slice(8),
      now=isoSeconds(timestamp);
    if(mode==="--dry-run") console.log(JSON.stringify(dryRun(timestamp),null,2));
    else if(mode==="--live") {
      const result=await collect(now,{
        accountId:process.env.CLOUDFLARE_ACCOUNT_ID,
        databaseId:process.env.CLOUDFLARE_D1_DATABASE_ID,
        token:process.env.CLOUDFLARE_API_TOKEN
      });
      console.log(JSON.stringify(result,null,2));
      if(result.alerts.some(a=>a.priority==="P0")) process.exitCode=2;
    }else throw new Error("Use --dry-run or --live; optional --as-of=YYYY-MM-DDTHH:MM:SSZ");
  } catch(err) {
    console.error("FAIL_CLOSED: "+(err instanceof Error?err.message:"Unknown operator error"));
    process.exitCode=1;
  }
}
