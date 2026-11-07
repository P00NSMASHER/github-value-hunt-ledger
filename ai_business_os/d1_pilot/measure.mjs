import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
import {readdirSync,readFileSync} from "node:fs";
import {resolve,join} from "node:path";
import {pathToFileURL,fileURLToPath} from "node:url";
import {Miniflare} from "miniflare";

const baseline=process.argv.includes("--without-feed");
const repo=resolve(process.argv.slice(2).find(a=>a!=="--without-feed") ?? fileURLToPath(new URL("../..",import.meta.url)));
const {onRequestPost: freight}=await import(pathToFileURL(join(repo,"functions/api/inquiry.js")));
const {onRequestPost: group}=await import(pathToFileURL(join(repo,"functions/api/group-inquiry.js")));
const mf=new Miniflare({modules:true, script:"export default {fetch(){return new Response('local only')}}",
    host:"127.0.0.1",port:0,inspectorPort:0,compatibilityDate:"2026-01-01",d1Databases:{DB:"fixture"},cf:false});
const originalFetch=globalThis.fetch;
try {
    const db=await mf.getD1Database("DB");
    const migrationDir=join(repo,"freight/site/migrations");
    const paths=[...readdirSync(migrationDir).filter(f=>f.endsWith(".sql")).sort().map(f=>join(migrationDir,f)),
        ...(baseline?[]:[join(repo,"ai_business_os/retally_inquiry_feed.sql")])];
    // D1.prepare takes single statements. sqlite3.complete_statement understands trigger bodies.
    const splitter=`import json,sqlite3,sys
stmts=[]
for path in sys.argv[1:]:
    buf=""
    for line in open(path):
        buf+=line
        if sqlite3.complete_statement(buf):
            stmts.append(buf)
            buf=""
    assert all(not s.strip() or s.lstrip().startswith("--") for s in buf.splitlines())
print(json.dumps(stmts))`;
    const statements=JSON.parse(execFileSync("python3",["-c",splitter,...paths],{encoding:"utf8"}));
    for (const sql of statements) await db.prepare(sql).run();
    let totals, mails=0;
    const results={};
    const measuredDB={prepare(sql){return {bind(...params){
        const run=async()=>{const res=await db.prepare(sql).bind(...params).all();
            const {rows_read,rows_written,served_by}=res.meta;
            assert.equal(served_by,"miniflare.db");
            assert.ok(Number.isSafeInteger(rows_read)&&Number.isSafeInteger(rows_written));
            totals.statements++; totals.rows_read+=rows_read;totals.rows_written+=rows_written;
            return res;};
        return {run,first:async()=>(await run()).results[0]??null};}};}};
    const env={FREIGHT_INQUIRY_ENABLED:"1",FREIGHT_INQUIRY_MAILBOX_VERIFIED:"1",
        TURNSTILE_SITEKEY:"local",TURNSTILE_SECRET:"local",INQUIRY_RATE_SECRET:"fixture",
        RESEND_API_KEY:"re_fixture_only",INQUIRY_NOTIFY_TO:"jay@retallyrecovery.com",INQUIRY_DB:measuredDB};
    globalThis.fetch=async(url,opts)=>{
        const u=new URL(url);
        if (u.hostname==="challenges.cloudflare.com") {
            const t=opts.body.get("response"), group=t==="local_group";
            return Response.json({success:t!=="invalid",action:group?"retally_group":"retally_audit",
                hostname:group?"group.retallyrecovery.com":"www.retallyrecovery.com"});
        }
        if (u.href==="https://api.resend.com/emails") { mails++;return Response.json({id:crypto.randomUUID()}); }
        if(u.hostname==="127.0.0.1")return originalFetch(url,opts);
        throw Error("unrecognized transport");
    };
    const common={fullName:"Pilot Fixture",workEmail:"pilot@example.invalid",companyName:"Fixture Distribution",
        idempotencyKey:crypto.randomUUID()};
    const freightBody={...common,annualSpend:"$1M–$5M",modes:["LTL"],turnstileToken:"local"};
    const groupBody={...common,business:"capturebrief",message:"Synthetic test",consent:true,
        idempotencyKey:crypto.randomUUID(),turnstileToken:"local_group"};
    async function request(body,kind="freight",ip="192.0.2.1"){
        const g=kind==="group",request=new Request("https://www.retallyrecovery.com/api/"+(g?"group-inquiry":"inquiry"),
            {method:"POST",headers:{Origin:"https://"+(g?"group":"www")+".retallyrecovery.com",
            "Content-Type":"application/json","CF-Connecting-IP":ip},body:JSON.stringify(body)});
        return (g?group:freight)({request,env});
    }
    async function measure(name,run){totals={statements:0,rows_read:0,rows_written:0};
        const value=await run();results[name]={...totals};return value;}
    for (const [kind,body,ip] of [["freight",freightBody,"192.0.2.1"],["group",groupBody,"192.0.2.2"]]){
        for(const [label,changes,status] of [["invalid",{website:"bot"},400],["rejected_turnstile",{turnstileToken:"invalid"},400],
                ["accepted",{},202],["replay",{},202],["key_conflict",{fullName:"Different Person"},409]]){
            const res=await measure(kind+"_"+label,()=>request({...body,...changes},kind,ip));
            assert.equal(res.status,status,kind+" "+label);
        }
    }
    const concurrent={...freightBody,idempotencyKey:crypto.randomUUID()};
    const pair=await measure("concurrent_freight_pair",()=>Promise.all([request(concurrent,"freight","192.0.2.3"),request(concurrent,"freight","192.0.2.3")]));
    assert.deepEqual(pair.map(r=>r.status),[202,202]);
    const pairReceipts=await Promise.all(pair.map(r=>r.json()));assert.equal(pairReceipts[0].reference,pairReceipts[1].reference);
    assert.deepEqual(pairReceipts.map(r=>r.duplicate).sort(),[false,true]);
    for (let i=0;i<5;i++) {
        const reject=()=>request({...freightBody,idempotencyKey:crypto.randomUUID(),turnstileToken:"invalid"},"freight","192.0.2.4");
        const res=i===0 ? await measure("rate_first_rejected",reject) : i===1 ? await measure("rate_second_rejected",reject) : await reject();
        assert.equal(res.status,400);
    }
    const capped=await measure("freight_rate_limited",()=>request({...freightBody,idempotencyKey:crypto.randomUUID(),
        turnstileToken:"invalid"},"freight","192.0.2.4"));assert.equal(capped.status,429);
    assert.equal(mails,3);
    let plan=[];
    if (!baseline) {
        const src=readFileSync(join(repo,"ai_business_os/retally_inquiry_sync.py"),"utf8");
        const query=src.match(/def source_page\([\s\S]+?source\.execute\("""([\s\S]+?)"""/)[1];
        const sample=(await db.prepare(query).bind(0,25).all());
        const empty=(await db.prepare(query).bind(3,25).all());
        plan=(await db.prepare("EXPLAIN QUERY PLAN "+query).bind(0,25).all()).results.map(r=>r.detail);
        assert.equal(sample.results.length,3);assert.equal(empty.results.length,0);
        for(const [label,r] of [["catchup_three",sample],["catchup_empty",empty]]){
            results[label]={statements:1,rows_read:r.meta.rows_read,rows_written:r.meta.rows_written};
        }
    }
    console.log(JSON.stringify({environment:"local Miniflare 4.20260730.0 / workerd 2026-07-30",feed_enabled:!baseline,measured:results,
        query_plan:plan,mail_captured:mails,external_sends:0,production_billing_measured:false},null,2));
} finally {globalThis.fetch=originalFetch;await mf.dispose();}
