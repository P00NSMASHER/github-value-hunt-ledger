import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {generateKeyPairSync,createSign,createHash,webcrypto} from 'node:crypto';
import {verifyRetallyOwner,ACCESS_AUD,ACCESS_ISSUER} from './retally_os_auth.mjs';
import {handleRetallyOs,onRequest} from '../../functions/api/internal/retally-os.js';

if(!globalThis.crypto)globalThis.crypto=webcrypto;
const syntheticEmail='owner@local.example';
const {publicKey,privateKey}=generateKeyPairSync('rsa',{modulusLength:2048});
const jwk={...publicKey.export({format:'jwk'}),kid:'phase2-mocked-rsa',alg:'RS256',use:'sig'};
const now=()=>Math.floor(Date.now()/1000);
function token(payload={}){
 const h=Buffer.from(JSON.stringify({alg:'RS256',typ:'JWT',kid:'phase2-mocked-rsa'})).toString('base64url');
 const p=Buffer.from(JSON.stringify({sub:'owner-fixture',email:syntheticEmail,iss:ACCESS_ISSUER,aud:[ACCESS_AUD],iat:now()-30,exp:now()+900,...payload})).toString('base64url');
 const signer=createSign('RSA-SHA256');signer.update(h+'.'+p);signer.end();return h+'.'+p+'.'+signer.sign(privateKey).toString('base64url');
}
const digest=s=>createHash('sha256').update(s).digest('hex');
const certFetcher=async()=>Response.json({keys:[jwk]});
function req(method='GET',body,opts={}){
 const url=opts.url||'https://retallyrecovery.com/api/internal/retally-os';
 const headers={...opts.headers};if(opts.jwt)headers['Cf-Access-Jwt-Assertion']=opts.jwt;
 if(method==='POST'){headers['Content-Type']=opts.type||'application/json';if(opts.origin!==false)headers.Origin=opts.origin||'https://retallyrecovery.com';}
 return new Request(url,{method,headers,body:body===undefined?undefined:JSON.stringify(body)});
}
function db(){
 const db=new DatabaseSync(':memory:');db.exec(`CREATE TABLE inquiries(reference TEXT PRIMARY KEY, full_name TEXT NOT NULL,work_email TEXT NOT NULL,company_name TEXT NOT NULL,annual_spend TEXT,details_json TEXT NOT NULL,accepted_at INTEGER NOT NULL,notification_status TEXT NOT NULL);CREATE TABLE inquiry_qa_registry(reference TEXT PRIMARY KEY);`);
 db.exec(readFileSync(new URL('./migrations/20261108_retally_os_phase2.sql',import.meta.url),'utf8'));
 const now=Math.floor(Date.now()/1000);
 const insert=db.prepare('INSERT INTO inquiries VALUES(?,?,?,?,?,?,?,?)');
 insert.run('RA-20261108-AABBCCDD','Synthetic QA','qa@example.invalid','Test Carrier','Under $250k',JSON.stringify({inquiryKind:'freight',campaign:{utm_source:'test'}}),now-1,'delivery_verified');
 insert.run('RA-20261108-ABCDEF12','Real Customer','real@example.com','Sample Freight LLC','$1M–$5M',JSON.stringify({campaign:{utm_source:'linkedin',utm_medium:'organic_social'}}),now,'pending');
 db.prepare('INSERT INTO inquiry_qa_registry VALUES(?)').run('RA-20261108-AABBCCDD');
 const adapter={prepare(sql){const statement=db.prepare(sql);return {all:async()=>({results:statement.all()}), first:async()=>statement.get()||null, bind(...args){return {first:async()=>statement.get(...args)||null,all:async()=>({results:statement.all(...args)}),run:async()=>statement.run(...args)}}}}};
 return {adapter,raw:db};
}
const auth=async()=>({sub:'owner-fixture'});
const context=(r,d)=>({request:r,env:{INQUIRY_DB:d.adapter}});

// Every auth negative should reject before JWKS key lookup if possible.
test('Owner requires valid RS256 signature, exact audience, issuer, expiration and exact identity',async()=>{
 const hash=digest(syntheticEmail);
 const yes=await verifyRetallyOwner(req('GET',undefined,{jwt:token()}),certFetcher,hash);assert.deepEqual(yes,{sub:'owner-fixture'});
 const cases=[token({email:'intruder@example.com'}),token({aud:['wrong']}),token({iss:'https://evil.example'}),token({exp:now()-1}),token({iat:now()+900}),token({sub:''})];
 for(const bad of cases)await assert.rejects(()=>verifyRetallyOwner(req('GET',undefined,{jwt:bad}),certFetcher,hash),/owner_access_denied/);
 const valid=token();const altered=valid.slice(0,-2)+(valid.at(-2)==='A'?'B':'A')+valid.at(-1);
 await assert.rejects(()=>verifyRetallyOwner(req('GET',undefined,{jwt:altered}),certFetcher,hash));
 await assert.rejects(()=>verifyRetallyOwner(req('GET',undefined,{jwt:valid}),async()=>Response.json({keys:[]} ),hash));
 await assert.rejects(()=>verifyRetallyOwner(req('GET'),certFetcher,hash));
});
test('Production entry denies missing Access token and nonproduction host before touching data',async()=>{
 const d=db();const missing=await onRequest(context(req(),d));assert.equal(missing.status,403);
 const wrong=await onRequest(context(req('GET',undefined,{url:'https://staging.pages.dev/api/internal/retally-os'}),d));assert.equal(wrong.status,404);
 const method=await handleRetallyOs(context(req('DELETE'),d),auth);assert.equal(method.status,405);
 const query=await handleRetallyOs(context(req('GET',undefined,{url:'https://retallyrecovery.com/api/internal/retally-os?debug=true'}),d),auth);assert.equal(query.status,400);
});
test('Owner GET reads live source, labels QA, excludes it from true customer claims',async()=>{
 const d=db();const r=await handleRetallyOs(context(req('GET',undefined,{url:'https://retallyrecovery.com/api/internal/retally-os?view=data'}),d),auth);
 assert.equal(r.status,200);const data=await r.json();assert.equal(data.cases.length,2);assert.equal(data.cases[0].company,'Sample Freight LLC');assert.equal(data.cases[0].synthetic,false);assert.equal(data.cases[1].synthetic,true);assert.equal(data.cases[0].campaign.utm_source,'linkedin');assert.equal(data.drafts.length,0);
 const html=await handleRetallyOs(context(req(),d),auth);assert.equal(html.status,200);
 assert.match(html.headers.get('Content-Security-Policy'),/script-src 'nonce-/);const htmlText=await html.text();assert.match(htmlText,/RETALLY OS/);assert.doesNotMatch(htmlText,/real@example\.com/);assert.doesNotMatch(htmlText,/qa@example\.invalid/);
});
test('Private task saves use optimistic versions and append atomic audit triggers',async()=>{
 const d=db();const v={action:'save_case',reference:'RA-20261108-ABCDEF12',expectedVersion:0,owner:'Owner',dueOn:'2026-11-19',status:'reviewing',note:'Review intake evidence'};
 let r=await handleRetallyOs(context(req('POST',v),d),auth);assert.equal(r.status,200);assert.equal((await r.json()).version,1);
 r=await handleRetallyOs(context(req('POST',v),d),auth);assert.equal(r.status,409);
 r=await handleRetallyOs(context(req('POST',{...v,expectedVersion:1,status:'qualified'}),d),auth);assert.equal(r.status,200);assert.equal((await r.json()).version,2);
 assert.equal(d.raw.prepare('SELECT COUNT(*) AS n FROM retally_os_case_events').get().n,2);
 assert.equal(d.raw.prepare('SELECT status FROM retally_os_cases WHERE reference=?').get(v.reference).status,'qualified');
});
test('No client can forge a customer, send a message, report cash, or invent an action',async()=>{
 const d=db();const base={action:'save_case',reference:'RA-20261108-ABCDEF12',expectedVersion:0,owner:'Owner',dueOn:'',status:'reviewing',note:'Review'};
 const invalid=[{...base,reference:'RA-20991231-FFFFFFFF'}, {...base,action:'pay_invoice'}, {...base,externalSends:1},{...base,status:'recovered'}, {...base,status:'closed',note:'x'}, {...base,dueOn:'2026-02-31'}];
 for(const v of invalid){const r=await handleRetallyOs(context(req('POST',v),d),auth);assert.ok([400,404].includes(r.status),JSON.stringify(v))}
 assert.equal(d.raw.prepare('SELECT COUNT(*) AS n FROM retally_os_cases').get().n,0);
 for(const opts of [{origin:'https://evil.example'}, {origin:false},{type:'text/plain'}]){
   const r=await handleRetallyOs(context(req('POST',base,opts),d),auth);assert.equal(r.status,403);
 }
});
test('Draft save, edit and review persist but have no publishing path',async()=>{
 const d=db();const id='aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee';const v={action:'save_draft',draftId:id,expectedVersion:0,title:'Audit before paying',body:'A freight invoice may contain duplicate accessorial fees.',channel:'linkedin'};
 let r=await handleRetallyOs(context(req('POST',v),d),auth);assert.equal(r.status,200);assert.equal((await r.json()).published,false);
 r=await handleRetallyOs(context(req('POST',{action:'review_draft',draftId:id,expectedVersion:1}),d),auth);assert.equal(r.status,200);assert.equal((await r.json()).published,false);
 r=await handleRetallyOs(context(req('POST',{...v,expectedVersion:2,body:'Revision: check signed rate agreements first.'}),d),auth);assert.equal(r.status,200);
 assert.equal(d.raw.prepare('SELECT status FROM retally_os_social_drafts').get().status,'draft');
 assert.equal(d.raw.prepare('SELECT COUNT(*) AS n FROM retally_os_social_events').get().n,3);
 r=await handleRetallyOs(context(req('POST',{action:'review_draft',draftId:id,expectedVersion:2}),d),auth);assert.equal(r.status,409);
});
