import {verifyAccessJWT,hasRole} from "../../../freight/site/operator_access_auth.js";

// Server-only action route. Signed Cloudflare Access reviewer/approver roles
// and TWO explicit production opt-ins are required in verifyAccessJWT.
// Never reads lead content, sends emails, or deletes customer records.
const HOSTS=new Set(["www.retallyrecovery.com","retallyrecovery.com"]);
const ACTIONS=new Set(["RECORD_RESPONSE","VERIFY_RESPONSE","WAIVE_RESPONSE"]);
const REASONS=new Set(["SPAM","INVALID_CONTACT","WITHDRAWN","DO_NOT_CONTACT","OUT_OF_SCOPE"]);
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const REF=/^RA-[0-9]{8}-[A-F0-9]{8}$/;
const HASH=/^[a-f0-9]{64}$/i;
function response(status,body){
 return new Response(JSON.stringify(body),{status,headers:{
  "Content-Type":"application/json; charset=utf-8",
  "Cache-Control":"private, no-store","Referrer-Policy":"no-referrer",
  "X-Content-Type-Options":"nosniff"
 }});
}
function safeOrigin(req){
 try{
  const u=new URL(req.url),o=new URL(req.headers.get("Origin")||"");
  return u.protocol==="https:" && HOSTS.has(u.hostname) &&
   u.pathname==="/api/internal/inquiry-response" && !u.search && !u.hash &&
   o.origin===u.origin && o.pathname==="/" &&
   req.headers.get("Content-Type")==="application/json";
 }catch{return false;}
}
async function boundedBody(req){
 const n=Number(req.headers.get("Content-Length")||0);
 if(!Number.isSafeInteger(n)||n<0||n>4096||!req.body)throw Error("invalid");
 const reader=req.body.getReader(),parts=[];let size=0;
 try{
  while(true){
   const {done,value}=await reader.read();
   if(done)break;
   size+=value.length;
   if(size>4096)throw Error("invalid");
   parts.push(value);
  }
 }finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let i=0;
 for(const x of parts){bytes.set(x,i);i+=x.length;}
 return JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(bytes));
}
function input(raw){
 if(!raw||typeof raw!=="object"||Array.isArray(raw))throw Error("invalid");
 const keys=Object.keys(raw);
 if(keys.some(k=>!["action","reference","actionId","evidenceDigest","reason"].includes(k)))
  throw Error("invalid");
 if(!ACTIONS.has(raw.action)||!REF.test(raw.reference)||!UUID.test(raw.actionId)||
    !HASH.test(raw.evidenceDigest))throw Error("invalid");
 if(raw.action==="WAIVE_RESPONSE"){
  if(!REASONS.has(raw.reason))throw Error("invalid");
 }else if(raw.reason!==undefined)throw Error("invalid");
 return {action:raw.action,reference:raw.reference,
  actionId:raw.actionId.toLowerCase(),evidenceDigest:raw.evidenceDigest.toLowerCase(),
  reason:raw.reason||null};
}
function sqlFor(v,actor,now){
 const {reference,actionId,evidenceDigest,action,reason}=v;
 const audit=[actionId,action,actor.sub,evidenceDigest,now];
 if(action==="RECORD_RESPONSE")return {
  sql:`INSERT INTO inquiry_response_states(
    reference,response_state,responded_at,reported_by,response_evidence_digest,
    last_action_id,last_action,last_actor_sub,last_evidence_digest,last_action_at)
    SELECT reference,'REPORTED',?,?,?,?,?,?,?,?
    FROM inquiry_case_dispositions
    WHERE reference=? AND case_state='ACKNOWLEDGED'
      AND legal_hold=0 AND purge_approved_at IS NULL
    ON CONFLICT(reference) DO NOTHING RETURNING reference`,
  params:[now,actor.sub,evidenceDigest,...audit,reference]
 };
 if(action==="VERIFY_RESPONSE")return {
  sql:`UPDATE inquiry_response_states SET response_state='VERIFIED',
    verified_at=?,verified_by=?,verification_evidence_digest=?,
    last_action_id=?,last_action=?,last_actor_sub=?,last_evidence_digest=?,last_action_at=?
    WHERE reference=? AND response_state='REPORTED' AND reported_by<>?
      AND EXISTS(SELECT 1 FROM inquiry_case_dispositions d
         WHERE d.reference=? AND d.case_state='ACKNOWLEDGED' AND d.legal_hold=0)
    RETURNING reference`,
  params:[now,actor.sub,evidenceDigest,...audit,reference,actor.sub,reference]
 };
 if(action==="WAIVE_RESPONSE")return {
  sql:`INSERT INTO inquiry_response_states(
    reference,response_state,waived_at,waived_by,waiver_reason,waiver_evidence_digest,
    last_action_id,last_action,last_actor_sub,last_evidence_digest,last_action_at)
    SELECT reference,'WAIVED',?,?,?,?,?,?,?,?,?
    FROM inquiry_case_dispositions
    WHERE reference=? AND case_state='ACKNOWLEDGED'
      AND operator_id<>? AND purge_approved_at IS NULL
    ON CONFLICT(reference) DO NOTHING RETURNING reference`,
  params:[now,actor.sub,reason,evidenceDigest,...audit,reference,actor.sub]
 };
 throw Error("invalid");
}
export async function onRequestPost({request,env}){
 if(!safeOrigin(request))return response(403,{error:"operator_access_denied"});
 let identity;
 try{identity=await verifyAccessJWT(request,env);}
 catch{return response(403,{error:"operator_access_denied"});}
 let action;
 try{action=input(await boundedBody(request));}
 catch{return response(400,{error:"invalid_response_action"});}
 const role=action.action==="RECORD_RESPONSE"?"reviewer":"approver";
 if(!hasRole(identity,role))return response(403,{error:"operator_access_denied"});
 try{
  const {sql,params}=sqlFor(action,identity,Math.floor(Date.now()/1000));
  const changed=await env.INQUIRY_DB.prepare(sql).bind(...params).first();
  if(!changed||changed.reference!==action.reference)
   return response(409,{error:"response_action_not_permitted"});
  return response(200,{ok:true,reference:action.reference,
   action:action.action,actionId:action.actionId});
 }catch{
  return response(409,{error:"response_action_not_permitted"});
 }
}
