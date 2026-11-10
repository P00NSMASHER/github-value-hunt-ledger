import {verifyRetallyOwner,RetallyOwnerAuthDenied} from '../../../freight/site/retally_os_auth.mjs';
import {renderRetallyOsPage} from '../../../freight/site/retally_os_ui.mjs';

const PATH='/api/internal/retally-os';
const REF=/^RA-\d{8}-[A-F0-9]{8}$/;
const ID=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const CASE_STATUS=new Set(['reviewing','qualified','on_hold','closed']);
const CHANNELS=new Set(['facebook','instagram','linkedin','x']);
const TASK_STATUS=new Set(['open','done','cancelled']);
const head={
  'Cache-Control':'private, no-store, max-age=0','Referrer-Policy':'no-referrer',
  'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY',
  'Permissions-Policy':'camera=(),microphone=(),geolocation=(),payment=()',
  'Strict-Transport-Security':'max-age=31536000; includeSubDomains'
};
const reply=(status,obj)=>new Response(JSON.stringify(obj),{status,headers:{...head,'Content-Type':'application/json; charset=utf-8'}});
function routeOk(request){try{const u=new URL(request.url);return u.protocol==='https:'&&u.hostname==='retallyrecovery.com'&&u.port===''&&u.pathname===PATH&&!u.hash;}catch{return false;}}
function clean(value,max,required=false){if(typeof value!=='string'||value.length>max*3)return null;const s=value.trim();if(s.length>max||(required&&!s)||/[\x00-\x08\x0b-\x1f\x7f]/.test(s))return null;return s;}
function allowKeys(obj,keys){return obj&&typeof obj==='object'&&!Array.isArray(obj)&&Object.keys(obj).every(k=>keys.includes(k));}
function dateOk(x){if(x==='')return true;if(!/^20\d{2}-\d{2}-\d{2}$/.test(x))return false;const d=new Date(x+'T00:00:00.000Z');return !Number.isNaN(d.valueOf())&&d.toISOString().slice(0,10)===x;}
function versionOk(v){return Number.isSafeInteger(v)&&v>=0&&v<=1000000;}
async function readSmall(request){const stated=Number(request.headers.get('Content-Length')||0);if(!Number.isSafeInteger(stated)||stated>8192||stated<0||!request.body)throw Error('invalid');const reader=request.body.getReader();const chunks=[];let total=0;try{while(true){const {done,value}=await reader.read();if(done)break;total+=value.byteLength;if(total>8192)throw Error('invalid');chunks.push(value)}}finally{reader.releaseLock()};const out=new Uint8Array(total);let pos=0;for(const x of chunks){out.set(x,pos);pos+=x.length}return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(out));}
function normalize(body){if(!body||typeof body.action!=='string')throw Error('invalid');
  if(body.action==='save_case'){
    if(!allowKeys(body,['action','reference','expectedVersion','owner','dueOn','status','note'])||!REF.test(body.reference)||!versionOk(body.expectedVersion)||!CASE_STATUS.has(body.status)||typeof body.dueOn!=='string'||!dateOk(body.dueOn))throw Error('invalid');
    const owner=clean(body.owner,80,true),note=clean(body.note,1000);
    if(owner===null||note===null||(body.status==='closed'&&note.length<8))throw Error('invalid');
    return {...body,owner,note};
  }
  if(body.action==='save_task'){
    if(!allowKeys(body,['action','taskId','reference','expectedVersion','title','owner','dueOn','status','note']) ||
       !ID.test(body.taskId)||!REF.test(body.reference)||!versionOk(body.expectedVersion)||
       !TASK_STATUS.has(body.status)||typeof body.dueOn!=='string'||!dateOk(body.dueOn))throw Error('invalid');
    const title=clean(body.title,140,true),owner=clean(body.owner,80,true),note=clean(body.note,1000);
    if(title===null||owner===null||note===null||(body.status!=='open'&&note.length<8))throw Error('invalid');
    return {...body,taskId:body.taskId.toLowerCase(),title,owner,note};
  }
  if(body.action==='save_draft'){
    if(!allowKeys(body,['action','draftId','expectedVersion','title','body','channel'])||!ID.test(body.draftId)||!versionOk(body.expectedVersion)||!CHANNELS.has(body.channel))throw Error('invalid');
    const title=clean(body.title,100,true),content=clean(body.body,1800,true);
    if(title===null||content===null)return null;
    return {...body,draftId:body.draftId.toLowerCase(),title,body:content};
  }
  if(body.action==='review_draft'){
    if(!allowKeys(body,['action','draftId','expectedVersion'])||!ID.test(body.draftId)||!versionOk(body.expectedVersion)||body.expectedVersion===0)throw Error('invalid');
    return {...body,draftId:body.draftId.toLowerCase()};
  }
  throw Error('invalid');
}
async function cases(db){
 const r=await db.prepare(`SELECT i.reference,i.full_name,i.work_email,i.company_name,i.annual_spend,
 i.details_json,i.accepted_at,i.notification_status,q.reference AS qa_reference,
 c.owner,c.due_on,c.status,c.note,c.version
 FROM inquiries i LEFT JOIN inquiry_qa_registry q ON q.reference=i.reference
 LEFT JOIN retally_os_cases c ON c.reference=i.reference
 ORDER BY i.accepted_at DESC,i.reference DESC LIMIT 100`).all();
 return (r.results||[]).map(x=>{
  let d={};try{d=JSON.parse(x.details_json||'{}')}catch{};
  const service=d.inquiryKind==='group_contact'?(typeof d.business==='string'?d.business:'group'):'freight';
  const campaign={};for(const k of ['utm_source','utm_medium','utm_campaign'])if(typeof d.campaign?.[k]==='string')campaign[k]=d.campaign[k].slice(0,120);
  return {reference:x.reference,contact:x.full_name,email:x.work_email,company:x.company_name,
   service,acceptedAt:x.accepted_at,notification:x.notification_status,synthetic:!!x.qa_reference,
   campaign,owner:x.owner,dueOn:x.due_on,status:x.status,note:x.note,version:x.version||0};
 });
}
async function tasks(db){
 const r=await db.prepare(`SELECT t.task_id,t.reference,t.title,t.owner,t.due_on,t.status,t.note,
 t.version,t.created_at,t.updated_at,q.reference AS qa_reference
 FROM retally_os_tasks t JOIN inquiries i ON i.reference=t.reference
 LEFT JOIN inquiry_qa_registry q ON q.reference=t.reference
 ORDER BY CASE WHEN t.status='open' THEN 0 ELSE 1 END,
 CASE WHEN t.due_on='' THEN 1 ELSE 0 END,t.due_on ASC,t.updated_at DESC LIMIT 200`).all();
 return (r.results||[]).map(x=>({taskId:x.task_id,reference:x.reference,title:x.title,owner:x.owner,
  dueOn:x.due_on,status:x.status,note:x.note,version:x.version,
  createdAt:x.created_at,updatedAt:x.updated_at,synthetic:!!x.qa_reference}));
}
async function drafts(db){const r=await db.prepare('SELECT draft_id,title,body,channel,status,version,updated_at FROM retally_os_social_drafts ORDER BY updated_at DESC,draft_id DESC LIMIT 60').all();return (r.results||[]).map(x=>({draftId:x.draft_id,title:x.title,body:x.body,channel:x.channel,status:x.status,version:x.version,updatedAt:x.updated_at}));}
async function saveCase(db,actor,v){
 const ref=await db.prepare('SELECT reference FROM inquiries WHERE reference=?').bind(v.reference).first();if(!ref)return reply(404,{error:'inquiry_not_found'});
 const old=await db.prepare('SELECT version FROM retally_os_cases WHERE reference=?').bind(v.reference).first();if((old?.version||0)!==v.expectedVersion)return reply(409,{error:'case_version_changed'});
 const now=Math.floor(Date.now()/1000);
 const updated=await db.prepare(`INSERT INTO retally_os_cases(reference,owner,due_on,status,note,version,updated_by,updated_at)
 VALUES(?,?,?,?,?,1,?,?) ON CONFLICT(reference) DO UPDATE SET
 owner=excluded.owner,due_on=excluded.due_on,status=excluded.status,note=excluded.note,
 version=retally_os_cases.version+1,updated_by=excluded.updated_by,updated_at=excluded.updated_at
 WHERE retally_os_cases.version=? RETURNING version`).bind(v.reference,v.owner,v.dueOn,v.status,v.note,actor.sub,now,v.expectedVersion).first();
 if(!updated)return reply(409,{error:'case_version_changed'});
 return reply(200,{ok:true,reference:v.reference,version:updated.version,externalSends:0});
}
async function saveTask(db,actor,v){
 const source=await db.prepare('SELECT reference FROM inquiries WHERE reference=?').bind(v.reference).first();
 if(!source)return reply(404,{error:'inquiry_not_found'});
 const old=await db.prepare('SELECT version,reference FROM retally_os_tasks WHERE task_id=?').bind(v.taskId).first();
 if(old && old.reference!==v.reference)return reply(409,{error:'task_scope_changed'});
 if((old?.version||0)!==v.expectedVersion)return reply(409,{error:'task_version_changed'});
 const now=Math.floor(Date.now()/1000);
 const record=await db.prepare(`INSERT INTO retally_os_tasks(
   task_id,reference,title,owner,due_on,status,note,version,created_by,created_at,updated_by,updated_at)
   VALUES(?,?,?,?,?,?,?,1,?,?,?,?)
   ON CONFLICT(task_id) DO UPDATE SET
     title=excluded.title,owner=excluded.owner,due_on=excluded.due_on,
     status=excluded.status,note=excluded.note,version=retally_os_tasks.version+1,
     updated_by=excluded.updated_by,updated_at=excluded.updated_at
   WHERE retally_os_tasks.version=? AND retally_os_tasks.reference=excluded.reference
   RETURNING version`).bind(v.taskId,v.reference,v.title,v.owner,v.dueOn,v.status,
     v.note,actor.sub,now,actor.sub,now,v.expectedVersion).first();
 if(!record)return reply(409,{error:'task_version_changed'});
 return reply(200,{ok:true,taskId:v.taskId,reference:v.reference,version:record.version,externalSends:0});
}
async function saveDraft(db,actor,v){
 const old=await db.prepare('SELECT version FROM retally_os_social_drafts WHERE draft_id=?').bind(v.draftId).first();if((old?.version||0)!==v.expectedVersion)return reply(409,{error:'draft_version_changed'});
 const now=Math.floor(Date.now()/1000);
 const x=await db.prepare(`INSERT INTO retally_os_social_drafts(draft_id,title,body,channel,status,version,updated_by,updated_at)
 VALUES(?,?,?,?,'draft',1,?,?) ON CONFLICT(draft_id) DO UPDATE SET
 title=excluded.title,body=excluded.body,channel=excluded.channel,status='draft',
 version=retally_os_social_drafts.version+1,updated_by=excluded.updated_by,updated_at=excluded.updated_at
 WHERE retally_os_social_drafts.version=? RETURNING version`).bind(v.draftId,v.title,v.body,v.channel,actor.sub,now,v.expectedVersion).first();
 if(!x)return reply(409,{error:'draft_version_changed'});
 return reply(200,{ok:true,draftId:v.draftId,version:x.version,published:false});
}
async function reviewDraft(db,actor,v){
 const x=await db.prepare(`UPDATE retally_os_social_drafts SET status='reviewed',version=version+1,updated_by=?,updated_at=?
 WHERE draft_id=? AND version=? AND status='draft' RETURNING version`).bind(actor.sub,Math.floor(Date.now()/1000),v.draftId,v.expectedVersion).first();
 if(!x)return reply(409,{error:'draft_unavailable_or_version_changed'});
 return reply(200,{ok:true,draftId:v.draftId,version:x.version,published:false});
}
export async function handleRetallyOs({request,env},authenticate=verifyRetallyOwner){
 if(!routeOk(request))return reply(404,{error:'not_found'});
 if(request.method!=='GET'&&request.method!=='POST')return reply(405,{error:'method_not_allowed'});
 let actor;try{actor=await authenticate(request)}catch(error){
  // Coarse, non-sensitive denial classification. Never return a token, email, or JWT claim.
  // Authentication remains fail-closed; Cloudflare Access is independently required at the edge.
  const check=error instanceof RetallyOwnerAuthDenied?error.check:'unexpected';
  return reply(403,{error:'owner_access_denied',check});
 }
 if(!env?.INQUIRY_DB?.prepare)return reply(503,{error:'private_store_unavailable'});
 const u=new URL(request.url);
 if(request.method==='GET'){
  // Some authenticated iPhone entry points return with transient URL parameters.
  // Drop them from browser history with a fixed same-origin destination.
  // Never echo or forward query values, and never change the strict data route.
  if(u.search&&u.search!=='?view=data')return new Response(null,{status:303,headers:{
   ...head,Location:'https://retallyrecovery.com'+PATH
  }});
  if(u.search==='?view=data'){
    try{return reply(200,{observedAt:new Date().toISOString(),cases:await cases(env.INQUIRY_DB),tasks:await tasks(env.INQUIRY_DB),drafts:await drafts(env.INQUIRY_DB)})}
    catch{return reply(503,{error:'private_store_unavailable'})}
  }
  const rand=crypto.getRandomValues(new Uint8Array(18));const nonce=btoa(String.fromCharCode(...rand));
  return new Response(renderRetallyOsPage(nonce),{status:200,headers:{...head,'Content-Type':'text/html; charset=utf-8',
   'Content-Security-Policy':`default-src 'none'; script-src 'nonce-${nonce}'; style-src 'nonce-${nonce}'; connect-src 'self'; form-action 'none'; base-uri 'none'; frame-ancestors 'none'; object-src 'none'; upgrade-insecure-requests`}});
 }
 if(u.search)return reply(400,{error:'invalid_query'});
 if(request.headers.get('Origin')!==u.origin || request.headers.get('Content-Type')!=='application/json' ||
   (request.headers.get('Sec-Fetch-Site')&&!['same-origin','none'].includes(request.headers.get('Sec-Fetch-Site'))))return reply(403,{error:'origin_denied'});
 let action;try{action=normalize(await readSmall(request));if(!action)throw Error('invalid')}
 catch{return reply(400,{error:'invalid_action'})}
 try{
   if(action.action==='save_case')return await saveCase(env.INQUIRY_DB,actor,action);
   if(action.action==='save_task')return await saveTask(env.INQUIRY_DB,actor,action);
   if(action.action==='save_draft')return await saveDraft(env.INQUIRY_DB,actor,action);
   if(action.action==='review_draft')return await reviewDraft(env.INQUIRY_DB,actor,action);
 }catch{return reply(503,{error:'private_write_unavailable'})}
 return reply(400,{error:'invalid_action'});
}

export const onRequest=(context)=>handleRetallyOs(context);
