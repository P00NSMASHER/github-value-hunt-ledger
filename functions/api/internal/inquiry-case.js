import {verifyAccessJWT,hasRole} from "./inquiry_auth.js";
// Disabled by default. Only signed Cloudflare Access actor identities authorize changes.
// No endpoint for raw inquiry reads or actual deletions.
const CODES=new Set(["ACKNOWLEDGE","CLOSE","SET_HOLD","RELEASE_HOLD","APPROVE_PURGE"]);
const HOSTS=new Set(["www.retallyrecovery.com","retallyrecovery.com"]);
function reply(status,body) {
  return new Response(JSON.stringify(body),{status,headers:{
    "Content-Type":"application/json; charset=utf-8","Cache-Control":"private, no-store",
    "Referrer-Policy":"no-referrer","X-Content-Type-Options":"nosniff"
  }});
}
function validRequest(request) {
  let url,origin;
  try{url=new URL(request.url);origin=new URL(request.headers.get("Origin")||"");}catch{return false;}
  return url.protocol==="https:" && HOSTS.has(url.hostname) &&
    url.pathname==="/api/internal/inquiry-case" && !url.search && !url.hash &&
    origin.origin===url.origin && origin.pathname==="/" &&
    request.headers.get("Content-Type")==="application/json";
}
async function readSmall(request) {
  const declared=Number(request.headers.get("Content-Length")||0);
  if(!Number.isSafeInteger(declared)||declared>4096||declared<0)throw Error("invalid_body");
  let text="";
  if(!request.body)throw Error("invalid_body");
  const reader=request.body.getReader();
  try{
    const chunks=[];
    let length=0;
    while(true){
      const {done,value}=await reader.read();
      if(done)break;
      length+=value.byteLength;
      if(length>4096)throw Error("invalid_body");
      chunks.push(value);
    }
    const buffer=new Uint8Array(length);let offset=0;
    for(const v of chunks){buffer.set(v,offset);offset+=v.length;}
    text=new TextDecoder("utf-8",{fatal:true}).decode(buffer);
    return JSON.parse(text);
  }finally{reader.releaseLock();}
}
function validatedAction(raw) {
  if(!raw||typeof raw!=="object"||Array.isArray(raw))throw Error("invalid_action");
  const keys=Object.keys(raw).sort();
  if(keys.some(k=>!["action","actionId","evidenceDigest","holdReason","reference"].includes(k)))throw Error("invalid_action");
  if(!CODES.has(raw.action) ||
     typeof raw.reference!=="string" ||
     !/^RA-[0-9]{8}-[A-F0-9]{8}$/.test(raw.reference) ||
     typeof raw.actionId!=="string" ||
     !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(raw.actionId) ||
     typeof raw.evidenceDigest!=="string" ||
     !/^[a-f0-9]{64}$/i.test(raw.evidenceDigest))throw Error("invalid_action");
  if(raw.action==="SET_HOLD") {
    if(!["LEGAL","DISPUTE","COMPLIANCE","CUSTOMER_REQUEST","SECURITY_INCIDENT"].includes(raw.holdReason))throw Error("invalid_action");
  }else if(raw.holdReason!==undefined)throw Error("invalid_action");
  return {action:raw.action,reference:raw.reference,
    actionId:raw.actionId.toLowerCase(),evidenceDigest:raw.evidenceDigest.toLowerCase(),
    holdReason:raw.holdReason||null};
}
function statement(input,actor,now) {
  const {reference,actionId,evidenceDigest,holdReason,action}=input;
  const shared=[actionId,action,actor.sub,evidenceDigest,now];
  if(action==="ACKNOWLEDGE")return {
    sql:`INSERT INTO inquiry_case_dispositions
      (reference,case_state,operator_id,acknowledged_at,legal_hold,
       last_action_id,last_action,last_actor_sub,last_evidence_digest,last_action_at)
      SELECT reference,'ACKNOWLEDGED',?, ?,0,?,?,?,?,?
      FROM inquiries WHERE reference=?
      ON CONFLICT(reference) DO NOTHING RETURNING reference`,
    params:[actor.sub,now,...shared,reference]
  };
  if(action==="CLOSE")return {
    sql:`UPDATE inquiry_case_dispositions SET case_state='CLOSED',
      closed_at=?,closed_by=?,retention_until=
        (SELECT accepted_at+90*86400 FROM inquiries WHERE reference=?),
      last_action_id=?,last_action=?,last_actor_sub=?,
      last_evidence_digest=?,last_action_at=?
      WHERE reference=? AND case_state='ACKNOWLEDGED'
        AND closed_at IS NULL AND purge_approved_at IS NULL
      RETURNING reference`,
    params:[now,actor.sub,reference,...shared,reference]
  };
  if(action==="SET_HOLD")return {
    sql:`UPDATE inquiry_case_dispositions SET legal_hold=1,hold_reason=?,hold_by=?,
      last_action_id=?,last_action=?,last_actor_sub=?,
      last_evidence_digest=?,last_action_at=?
      WHERE reference=? AND legal_hold=0 AND purge_approved_at IS NULL
      RETURNING reference`,
    params:[holdReason,actor.sub,...shared,reference]
  };
  if(action==="RELEASE_HOLD")return {
    sql:`UPDATE inquiry_case_dispositions SET legal_hold=0,
      hold_reason=NULL,hold_by=NULL,
      last_action_id=?,last_action=?,last_actor_sub=?,
      last_evidence_digest=?,last_action_at=?
      WHERE reference=? AND legal_hold=1 AND hold_by<>?
        AND purge_approved_at IS NULL RETURNING reference`,
    params:[...shared,reference,actor.sub]
  };
  if(action==="APPROVE_PURGE")return {
    sql:`UPDATE inquiry_case_dispositions SET purge_approved_at=?,purge_approved_by=?,
      last_action_id=?,last_action=?,last_actor_sub=?,
      last_evidence_digest=?,last_action_at=?
      WHERE reference=? AND case_state='CLOSED'
        AND closed_at IS NOT NULL AND closed_at<=?
        AND legal_hold=0 AND operator_id<>? AND closed_by<>?
        AND purge_approved_at IS NULL
        AND retention_until IS NOT NULL AND retention_until<=?
        AND EXISTS(SELECT 1 FROM inquiries WHERE reference=?
          AND accepted_at<=?-90*86400)
      RETURNING reference`,
    params:[now,actor.sub,...shared,reference,now,actor.sub,actor.sub,now,reference,now]
  };
  throw Error("invalid_action");
}
export async function onRequestPost({request,env}) {
  // No activation via code deployment alone. Failing policy or token returns 403.
  if(!validRequest(request))return reply(403,{error:"operator_access_denied"});
  let identity;
  try{identity=await verifyAccessJWT(request,env);}catch{return reply(403,{error:"operator_access_denied"});}
  let action;
  try{action=validatedAction(await readSmall(request));}
  catch{return reply(400,{error:"invalid_case_action"});}
  const role=["RELEASE_HOLD","APPROVE_PURGE"].includes(action.action)?"approver":"reviewer";
  if(!hasRole(identity,role))return reply(403,{error:"operator_access_denied"});
  try {
    const now=Math.floor(Date.now()/1000);
    const {sql,params}=statement(action,identity,now);
    // A single atomic database statement updates one case; a trigger records
    // the authenticated actor's statement context in immutable action history.
    const found=await env.INQUIRY_DB.prepare(sql).bind(...params).first();
    if(!found || found.reference!==action.reference) return reply(409,{error:"case_action_not_permitted"});
    return reply(200,{ok:true,reference:action.reference,
      action:action.action,actionId:action.actionId});
  }catch{
    return reply(409,{error:"case_action_not_permitted"});
  }
}
