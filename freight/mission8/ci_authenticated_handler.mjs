/* M11: authentic copied M8 TypeScript endpoint handlers, legitimate local
   synthetic JWT + membership, localhost HTTP, ephemeral real PostgreSQL.
   NO hosted Floot credential, actual customer, external provider or payment.
*/
import {createServer} from "node:http";
import {strict as assert} from "node:assert";
import {createHash} from "node:crypto";
import {readFileSync,writeFileSync} from "node:fs";
import {performance} from "node:perf_hooks";
import {SignJWT} from "jose";
import postgres from "postgres";
import superjson from "superjson";
import {handle as prepare} from "./floot/endpoints/recovery/payment_prepare_POST.ts";
import {handle as authorize} from "./floot/endpoints/recovery/payment_authorize_POST.ts";
import {handle as event} from "./floot/endpoints/recovery/payment_event_POST.ts";
import {handle as payments} from "./floot/endpoints/recovery/payments_GET.ts";
import {requireRecoveryTenant} from "./floot/helpers/recoveryTenant.tsx";

for(const n of ["FLOOT_DATABASE_URL","JWT_SECRET","RETALLY_TESTED_HEAD_SHA"]) assert(process.env[n],"Missing isolated CI variable: "+n);
assert(/localhost|127[.]0[.]0[.]1/.test(process.env.FLOOT_DATABASE_URL),"Ephemeral local DB only");
const db=postgres(process.env.FLOOT_DATABASE_URL,{max:3,prepare:false});
const routes={"/_api/recovery/payment_prepare":prepare,"/_api/recovery/payment_authorize":authorize,
 "/_api/recovery/payment_event":event,"/_api/recovery/payments":payments};
const tests=[];
const start=performance.now();
const server=createServer(async (incoming,outgoing)=>{
 const path=new URL(incoming.url||"/","http://localhost").pathname;
 try{
  const chunks=[];
  for await(const chunk of incoming) chunks.push(Buffer.from(chunk));
  const base="http://127.0.0.1:"+server.address().port;
  const response=await routes[path](new Request(base+path,{method:incoming.method,
   headers:incoming.headers,...(incoming.method==="POST"?{body:Buffer.concat(chunks)}:{})}));
  outgoing.writeHead(response.status,Object.fromEntries(response.headers.entries()));
  outgoing.end(Buffer.from(await response.arrayBuffer()));
 }catch(error){console.error("Local handler failure",String(error).slice(0,200));outgoing.writeHead(500);outgoing.end();}
});
const receipt={scope:"REAL_M8_TYPESCRIPT_HANDLERS_LOCALHOST_HTTP_EPHEMERAL_POSTGRES_NOT_HOSTED",
 tested_head_sha:process.env.RETALLY_TESTED_HEAD_SHA,hosted_floot_verified:false,
 real_customer_or_provider_data:false,production_modified:false,
 tests,source_sha256:{}};
function check(label,condition,detail){
 tests.push({label,passed:!!condition,detail});
 assert(condition,label+": "+JSON.stringify(detail));
}
async function run(){
 for(const f of ["payment_prepare_POST.ts","payment_authorize_POST.ts","payment_event_POST.ts","payments_GET.ts"]){
  const s=readFileSync("freight/mission8/floot/endpoints/recovery/"+f);
  receipt.source_sha256[f]=createHash("sha256").update(s).digest("hex");
 }
 const who=await db.unsafe("SELECT u.id,m.tenant_id FROM users u JOIN recovery_tenant_memberships m ON m.user_id=u.id WHERE u.email='handler.owner@example.invalid' AND m.role='owner'");
 check("synthetic_user_member",who.length===1 && who[0].tenant_id==="handler_t",{memberships:who.length});
 const jwt=await new SignJWT({id:"m11-authenticated-session-local",createdAt:Date.now(),lastAccessed:Date.now()})
  .setProtectedHeader({alg:"HS256"}).setIssuedAt().setExpirationTime("4h")
  .sign(new TextEncoder().encode(process.env.JWT_SECRET));
 const cookie="floot_built_app_session="+jwt;
 await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
 const base="http://127.0.0.1:"+server.address().port;
 async function send(path,body,authenticated=true){
  const response=await fetch(base+path,{method:body?"POST":"GET",
   headers:{"Content-Type":"application/json",Origin:base,...(authenticated?{Cookie:cookie}:{})},
   ...(body?{body:superjson.stringify(body)}:{})});
  const text=await response.text();
  let data;
  try{data=superjson.parse(text)}catch{data={unparsed:text.slice(0,120)}}
  return{status:response.status,data};
 }
 const diagnosticReq=new Request(base+"/_api/recovery/payment_prepare",{method:"POST",headers:{Cookie:cookie,Origin:base}});
 const resolvedAccess=await requireRecoveryTenant(diagnosticReq);
 check("authenticated_tenant_identity_matches_fixture",resolvedAccess.tenantId==="handler_t" && Number(resolvedAccess.userId)===Number(who[0].id),{tenant:resolvedAccess.tenantId,user_id:resolvedAccess.userId});
 const bodyProbe={schema:1,tenant_id:resolvedAccess.tenantId,payer_id:"SIMULATED",payee_id:"SIMULATED",currency:"USD",amount_cents:10000,purpose:"Synthetic authenticated application acceptance",finding_ids:["handler_finding"],idempotency_key:"m11-local-handler-same-001"};
 const probeString=await db.unsafe("SELECT jsonb_typeof($1::jsonb) AS kind",[JSON.stringify(bodyProbe)]);
 check("original_JSON_string_double_encoded",probeString[0].kind==="string",probeString[0]);
 const probeObject=await db.unsafe("SELECT jsonb_typeof($1::jsonb) AS kind, $1::jsonb ->> 'tenant_id' AS tenant, $2::text AS expected",[bodyProbe,resolvedAccess.tenantId]);
 check("correct_JSON_object_parameter",probeObject[0].kind==="object" && probeObject[0].tenant===probeObject[0].expected,probeObject[0]);
 const basePayload={payerId:"SIMULATED",payeeId:"SIMULATED",currency:"USD",amountCents:10000,
 purpose:"Synthetic authenticated application acceptance",findingIds:["handler_finding"],
 idempotencyKey:"m11-local-handler-same-001"};
 const noauth=await send("/_api/recovery/payment_prepare",basePayload,false);
 check("no_auth_401",noauth.status===401,{status:noauth.status});
 const submissions=await Promise.all(Array.from({length:100},()=>send("/_api/recovery/payment_prepare",basePayload)));
 const positive=submissions.filter(x=>x.status===200), ids=positive.map(x=>x.data.instructionId);
 check("100_authenticated_preparation_calls",positive.length===100 && new Set(ids).size===1,
  {ok:positive.length,distinct_ids:new Set(ids).size,first_error:submissions.find(x=>x.status!==200)?.data?.error});
 const instruction=ids[0];
 const instructions=await db.unsafe("SELECT count(*)::int n,coalesce(sum(amount_cents),0)::bigint cents FROM recovery_payment_instructions WHERE tenant_id='handler_t'");
 const allocations=await db.unsafe("SELECT count(*)::int n,coalesce(sum(amount_cents),0)::bigint cents FROM recovery_value_allocations WHERE tenant_id='handler_t'");
 check("one_instruction_one_allocation",Number(instructions[0].n)===1 && Number(allocations[0].n)===1 &&
  Number(instructions[0].cents)===10000 && Number(allocations[0].cents)===10000,{instructions:instructions[0].n,allocations:allocations[0].n});
 const conflict=await send("/_api/recovery/payment_prepare",{...basePayload,amountCents:9000});
 check("altered_idempotency_rejected",conflict.status===400,{status:conflict.status,error:conflict.data.error});
 const currency=await send("/_api/recovery/payment_prepare",{...basePayload,currency:"EUR",idempotencyKey:"m11-local-cross-currency-002"});
 check("cross_currency_rejected",currency.status===400,{status:currency.status,error:currency.data.error});
 const oversized=await send("/_api/recovery/payment_prepare",{...basePayload,amountCents:100000,idempotencyKey:"m11-local-overcapacity-003"});
 check("duplicate_full_capacity_rejected",oversized.status===400,{status:oversized.status,error:oversized.data.error});
 const auths=await Promise.all(Array.from({length:100},()=>send("/_api/recovery/payment_authorize",
  {instructionId:instruction,reason:"Only fictional internal QA permission"})));
 const aok=auths.filter(x=>x.status===200), aids=aok.map(x=>x.data.authorizationId);
 check("100_authenticated_authorization_calls",aok.length===100 && new Set(aids).size===1,
  {ok:aok.length,distinct_ids:new Set(aids).size,error:auths.find(x=>x.status!==200)?.data?.error});
 const ap=await db.unsafe("SELECT count(*)::int n FROM recovery_payment_authorizations WHERE tenant_id='handler_t'");
 check("authorization_one_row",Number(ap[0].n)===1,{count:ap[0].n});
 const ep={instructionId:instruction,state:"SUBMITTED",provider:"SIM-ONLY",providerReference:"SIM-START",
  amountCents:10000,sourceHash:"e".repeat(64),occurredAt:"2026-10-08T12:00:00Z"};
 const callbacks=await Promise.all(Array.from({length:100},()=>send("/_api/recovery/payment_event",ep)));
 const ok=callbacks.filter(x=>x.status===200), eids=ok.map(x=>x.data.eventId);
 check("100_authenticated_event_calls",ok.length===100 && new Set(eids).size===1,
  {ok:ok.length,distinct_ids:new Set(eids).size,error:callbacks.find(x=>x.status!==200)?.data?.error});
 for(const [state,ref,time] of [["ACCEPTED","SIM-ACCEPT","2026-10-08T13:00:00Z"],
  ["SETTLED","SIM-SETTLE","2026-10-08T14:00:00Z"]]){
  const x=await send("/_api/recovery/payment_event",{...ep,state,providerReference:ref,occurredAt:time});
  check("lifecycle_"+state,x.status===200,{status:x.status,error:x.data.error});
 }
 const list=await send("/_api/recovery/payments");
 const row=list.data.payments?.find(x=>x.id===instruction);
 check("SETTLED_never_means_verified_cash",list.status===200 && row?.state==="SETTLED" &&
 row?.settlementVerification==="UNVERIFIED" && row?.verifiedRecoveredCents===0,
 {status:list.status,state:row?.state,cash:row?.verifiedRecoveredCents});
 const reversal=await send("/_api/recovery/payment_event",{...ep,state:"REVERSED",providerReference:"SIM-REVERSAL",occurredAt:"2026-10-08T15:00:00Z"});
 check("synthetic_reversal",reversal.status===200,{status:reversal.status,error:reversal.data.error});
 const final=await db.unsafe("SELECT count(*)::int n FROM recovery_payment_events WHERE tenant_id='handler_t'");
 check("append_only_four_states",Number(final[0].n)===4,{count:final[0].n});
}
try{await run();receipt.verdict="PASS"}
catch(e){receipt.verdict="FAIL";receipt.error=String(e).slice(0,400);process.exitCode=1}
finally{
 receipt.execution_seconds=Number(((performance.now()-start)/1000).toFixed(3));
 writeFileSync("freight/mission8/ci_authenticated_handler_receipt.json",JSON.stringify(receipt,null,2)+"\n");
 console.log("M11_HANDLER_ACCEPTANCE",JSON.stringify(receipt));
 await new Promise(resolve=>server.close(()=>resolve()));
 await db.end({timeout:3});
}
