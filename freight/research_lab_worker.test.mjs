import test from "node:test";
import assert from "node:assert/strict";
import scout, {ENGINES, canonicalCandidates, feedSpecs, fetchCatalog, permitplateCandidateInScope, selectCandidateWindow, persistSourceWindow, providerErrorCode, providerMetadataInScope, cycle} from "./research_lab_worker.mjs";

test("all four engines have bounded catalog-only probes", () => {
  assert.equal(ENGINES.length,4);
  for(const engine of ENGINES){
    const feeds=feedSpecs(engine);
    assert.ok(feeds.length>=3 && feeds.length<=4);
    for(const f of feeds){
      assert.match(f.url,/^https:\/\/(api.github.com|zenodo.org|api.us.socrata.com)\//);
      assert.ok(!/token=|apikey=|password=/i.test(f.url));
      assert.ok(["github","zenodo","socrata"].includes(f.provider));
    }
  }
});
test("source IDs, not arbitrary metadata or private source rows, enter discovery", ()=>{
  assert.deepEqual(canonicalCandidates("github",{items:[
    {html_url:"https://github.com/owner/source-data",name:"freight-invoice-data",description:"PERSON@PRIVATE.COM"},
    {html_url:"https://github.com/owner/repo?token=secret"},
    {html_url:"http://localhost/private"},
  ]},"freightrecovery"),["https://github.com/owner/source-data"]);
  assert.deepEqual(canonicalCandidates("zenodo",{hits:{hits:[
    {id:987654321,metadata:{title:"LTL freight tariff dataset"},files:[{key:"confidential-document.pdf"}]},
    {id:"../123"},
  ]}},"freightrecovery"),["https://zenodo.org/records/987654321"]);
  assert.deepEqual(canonicalCandidates("socrata",{results:[
    {resource:{id:"abcd-1234",name:"DOB NOW: Build – Approved Permits"}},
    {resource:{id:"../../passwd"}},
  ]},"permitplate"),["https://data.cityofnewyork.us/d/abcd-1234"]);
});
test("missing or malformed API responses fail closed", ()=>{
  for(const p of ["github","zenodo","socrata"]){
    assert.throws(()=>canonicalCandidates(p,{bad:[]},p==="socrata"?"permitplate":"freightrecovery"),/INVALID_ITEMS/);
  }
  assert.throws(()=>canonicalCandidates("wrong",{items:[]}, "freightrecovery"),/UNSUPPORTED_PROVIDER/);
  assert.throws(()=>feedSpecs("unknown"),/INVALID_ENGINE/);
});
test("public HTTP interface has read-only GET handlers only",async()=>{
  assert.equal(typeof scout.fetch,"function");
  assert.equal(typeof scout.scheduled,"function");
  const r=await scout.fetch(new Request("https://research.invalid/feed",{method:"POST"}),{});
  assert.equal(r.status,405);
  assert.deepEqual(await r.json(),{error:"READ_ONLY"});
});

test("Cloudflare-compatible manual redirect mode blocks all 3xx",async()=>{
  const original=globalThis.fetch;
  try {
    globalThis.fetch=async(url,options)=>{
      assert.equal(options.redirect,"manual");
      assert.ok(!options.headers.Authorization);
      return new Response("",{status:302,headers:{Location:"https://evil.invalid/private"}});
    };
    await assert.rejects(fetchCatalog(feedSpecs("recoveryos")[0]),/REDIRECT_BLOCKED/);
  }finally{globalThis.fetch=original;}
});
test("public metadata fetch parses bounded valid JSON",async()=>{
  const original=globalThis.fetch;
  try{
    globalThis.fetch=async(url,options)=>{
      assert.equal(options.redirect,"manual");
      return new Response(JSON.stringify({items:[{html_url:"https://github.com/test/example",name:"freight-invoice-data"}]}),
        {status:200,headers:{"content-type":"application/json"}});
    };
    assert.deepEqual(await fetchCatalog(feedSpecs("freightrecovery")[0]),
      ["https://github.com/test/example"]);
  }finally{globalThis.fetch=original;}
});

test("rotation reaches all bounded candidate windows without repeating only the first 24", () => {
  const input=Array.from({length:57},(_,i)=>"https://github.com/source/catalog-"+String(i).padStart(3,"0"));
  const batches=[0,1200000,2400000].map(t=>selectCandidateWindow([...input].reverse(),t));
  assert.deepEqual(batches.map(b=>b.length),[24,24,9]);
  assert.equal(new Set(batches.flat()).size,57);
  assert.deepEqual(batches[0],selectCandidateWindow([...input],0));
  assert.deepEqual(selectCandidateWindow(["a","a","b"],0),["a","b"]);
  assert.deepEqual(selectCandidateWindow([],0),[]);
  assert.throws(()=>selectCandidateWindow([],NaN),/INVALID_SCHEDULE_TIME/);
});


test("PermitPlate excludes restaurant inspection catalogs from its permit leads", () => {
  const q = feedSpecs("permitplate").map(s => new URL(s.url).searchParams.get("q") || "");
  assert.ok(q.every(x => !/restaurant|inspection/i.test(x)));
  assert.deepEqual(canonicalCandidates("socrata", {results: [
    {resource:{id:"abcd-1234",name:"DOHMH Restaurant Inspection"}},
    {resource:{id:"rbx6-tga4",name:"DOB NOW: Build – Approved Permits"}},
    {resource:{id:"ipu4-2q9a",name:"DOB Permit Issuance"}},
    {resource:{id:"w9ak-ipjd",name:"DOB NOW: Job Application Filings"}},
  ]},"permitplate"), [
    "https://data.cityofnewyork.us/d/ipu4-2q9a",
    "https://data.cityofnewyork.us/d/rbx6-tga4",
    "https://data.cityofnewyork.us/d/w9ak-ipjd",
  ]);
  assert.equal(permitplateCandidateInScope("https://github.com/owner/NYC-Restaurant-Inspection"), false);
  assert.equal(permitplateCandidateInScope("https://github.com/owner/NYC-DOB-Building-Permits"), true);
  for (const url of [
    "https://github.com/gcivil-nyu-org/dine-safe-ly",
    "https://data.cityofnewyork.us/d/43nn-pn8j",
    "https://data.cityofnewyork.us/d/pitm-atqc",
    "https://data.cityofnewyork.us/d/qcdj-rwhu",
    "https://data.cityofnewyork.us/d/fpeh-f7ci",
  ]) assert.equal(permitplateCandidateInScope(url), false, url);
});


test("bounded catalogs rotate query terms and pages without extra network budget",()=>{
  const start=Date.UTC(2026,9,23,0,0,0);
  const now=[];
  for(let lap=0;lap<15;lap++){
    const specs=feedSpecs("freightrecovery",start+lap*1200000);
    assert.equal(specs.length,3);
    assert.equal(specs.filter(x=>x.provider==="github").length,2);
    assert.equal(specs.filter(x=>x.provider==="zenodo").length,1);
    for(const spec of specs){
      const url=new URL(spec.url);
      assert.ok(url.hostname==="api.github.com"||url.hostname==="zenodo.org");
      assert.ok([1,2,3].includes(Number(url.searchParams.get("page"))));
      assert.ok(!/[?&](?:api_?key|token|auth)=/i.test(url.search));
    }
    now.push(specs.map(x=>x.url).join("|"));
  }
  assert.ok(new Set(now).size>=12);
  assert.ok(now.some(x=>x.includes("sort=updated")));
  assert.ok(now.some(x=>x.includes("page=3")));
  assert.notDeepEqual(feedSpecs("capturebrief",start),feedSpecs("capturebrief",start+100*1200000));
  assert.throws(()=>feedSpecs("recoveryos",Number.NaN),/INVALID_SCHEDULE_TIME/);
  assert.equal(feedSpecs("permitplate",start).filter(x=>x.provider==="socrata").length,1);
});

test("D1 source publication uses one bounded atomic batch with rights holds",async()=>{
  const batched=[];
  const db={
    prepare(sql){return {bind(...args){return {sql,args}}};},
    async batch(stmts){batched.push(stmts);return [{meta:{changes:2}},{meta:{changes:2}}];},
  };
  const before=Date.UTC(2026,9,23,12,0);
  const input=["https://github.com/example/source-two","https://zenodo.org/records/1001"];
  const out=await persistSourceWindow(db,"freightrecovery",input,before);
  assert.deepEqual(out,{newSources:2,attempted:2});
  assert.equal(batched.length,1);
  assert.equal(batched[0].length,2);
  assert.match(batched[0][0].sql,/INSERT OR IGNORE INTO sources/);
  assert.match(batched[0][0].sql,/UNVERIFIED_RIGHTS_HOLD/);
  assert.match(batched[0][0].sql,/UNVERIFIED_TRUTH_HOLD/);
  assert.match(batched[0][1].sql,/INSERT OR IGNORE INTO source_engines/);
  assert.equal(batched[0][0].args.length,6);
  assert.equal(batched[0][1].args.length,4);
  assert.ok(batched[0][0].args.includes("2026-10-23"));
  assert.equal(batched[0][0].sql.includes("source-two"),false);
  assert.deepEqual(await persistSourceWindow(db,"capturebrief",[],before),
                   {newSources:0,attempted:0});
  assert.equal(batched.length,1);
  await assert.rejects(persistSourceWindow(
    {prepare:db.prepare,batch:async()=>[{meta:{changes:99}},{meta:{changes:2}}]},
    "freightrecovery",input,before),/INVALID_STORAGE_RECEIPT/);
});

test("provider errors are fixed bounded telemetry codes with no source disclosure",()=>{
  assert.equal(providerErrorCode(new Error("HTTP_429")),"HTTP_429");
  assert.equal(providerErrorCode(new Error("HTTP_503")),"HTTP_503");
  assert.equal(providerErrorCode(new Error("REDIRECT_BLOCKED")),"REDIRECT_BLOCKED");
  assert.equal(providerErrorCode(new Error("token=sensitive@example.com http://private.invalid")),"SOURCE_UNAVAILABLE");
  const timeout=Object.assign(new Error("contains private customer info"),{name:"TimeoutError"});
  assert.equal(providerErrorCode(timeout),"TIMEOUT");
});

test("oversized public catalog streaming is bounded by byte count",async()=>{
  const original=globalThis.fetch;
  try{
    globalThis.fetch=async()=>new Response(new ReadableStream({
      start(controller){
        controller.enqueue(new Uint8Array(600001));
        controller.enqueue(new Uint8Array(600001));
        controller.close();
      },
    }),{status:200,headers:{"content-type":"application/json"}});
    // Streaming Response has no Content-Length header; the byte guard itself
    // must reject the oversized source rather than relying on metadata.
    await assert.rejects(fetchCatalog(feedSpecs("capturebrief")[0]),/RESPONSE_LIMIT/);
  }finally{globalThis.fetch=original;}
});

test("GitHub rate limit skips secondary request and writes a degraded receipt",async()=>{
  const original=globalThis.fetch;
  const seen=[],sql=[];
  const db={
    prepare(query){
      sql.push(query);
      return {
        first:async()=>({name:"freightrecovery"}),
        bind(...args){return {
          async run(){return {meta:{changes:1}};},
        };},
      };
    },
    batch:async()=>[{meta:{changes:1}},{meta:{changes:1}}],
  };
  try{
    globalThis.fetch=async url=>{
      seen.push(String(url));
      if(String(url).includes("api.github.com"))
        return new Response("",{status:429});
      return new Response(JSON.stringify({hits:{hits:[{id:12345,metadata:{title:"Freight invoice dataset"}}]}}),
        {status:200,headers:{"content-type":"application/json"}});
    };
    const result=await cycle({RESEARCH_DB:db},Date.UTC(2026,9,23,12,0));
    assert.equal(result.state,"DEGRADED");
    assert.equal(result.added,1);
    assert.equal(seen.filter(x=>x.includes("api.github.com")).length,1);
    assert.equal(seen.filter(x=>x.includes("zenodo.org")).length,1);
    assert.ok(sql.some(x=>x.includes("UPDATE runs SET status")));
  }finally{globalThis.fetch=original;}
});


test("read-only cursor paging preserves newest-first ordering and emits no D1 internal fields",async()=>{
  const rows=[
    {cursor_id:300,url:"https://github.com/example/newest-source",first_seen:"2026-10-23"},
    {cursor_id:200,url:"https://github.com/example/older-source",first_seen:"2026-10-22"},
    {cursor_id:100,url:"https://github.com/example/oldest-source",first_seen:"2026-10-21"},
  ];
  const calls=[];
  const db={
    prepare(sql){
      assert.ok(sql.includes("SELECT s.rowid AS cursor_id"));
      assert.ok(!/insert|update|delete/i.test(sql));
      return {bind(...args){calls.push({sql,args});return {
        async all(){
          const lane=args[0],hasCursor=args.length===3;
          const before=hasCursor?args[1]:Infinity;
          const lim=args.at(-1);
          assert.equal(lane,"freightrecovery");
          return {results:rows.filter(x=>x.cursor_id<before).slice(0,lim)};
        },
      }}};
    },
  };
  const root="https://research.invalid/feed?engine=freightrecovery&limit=2";
  const first=await (await scout.fetch(new Request(root),{RESEARCH_DB:db})).json();
  assert.equal(first.scope,"PUBLIC_SOURCE_POINTERS_NOT_APPROVED_TEST_DATA");
  assert.equal(first.next_cursor,"200");
  assert.equal(first.sources.length,2);
  assert.deepEqual(Object.keys(first.sources[0]).sort(),["first_seen","url"]);
  const second=await (await scout.fetch(new Request(root+"&before="+first.next_cursor),{RESEARCH_DB:db})).json();
  assert.equal(second.next_cursor,null);
  assert.equal(second.sources.length,1);
  assert.equal(new Set([...first.sources,...second.sources].map(x=>x.url)).size,3);
  assert.equal(calls.length,2);
  assert.equal(calls[0].args.length,2);
  assert.deepEqual(calls[1].args,["freightrecovery",200,2]);
});

test("malformed feed pagination inputs reject before querying D1",async()=>{
  for (const suffix of ["&before=-1","&before=0","&before=abc",
      "&before=1%20or%201%3D1","&before=1234567890123",
      "&limit=0","&limit=1000","&limit=2junk"]) {
    const db={prepare(){throw Error("UNAUTHORIZED_D1_READ")}};
    const result=await scout.fetch(
      new Request("https://research.invalid/feed?engine=recoveryos"+suffix),{RESEARCH_DB:db}
    );
    assert.equal(result.status,400,suffix);
  }
});


test("all four engine lanes reject obviously off-topic public metadata without storing text",()=>{
  const cases=[
    ["freightrecovery", "Freight invoice tariff dataset", "Baking and dining recipes"],
    ["permitplate", "NYC DOB NOW approved building permits", "NYC restaurant inspection permits"],
    ["capturebrief", "Federal solicitation contract awards", "Professional basketball boxscores"],
    ["recoveryos", "Accounts payable supplier invoice reconciliation", "Wildlife photography archive"],
  ];
  for(const [engine,good,bad] of cases){
    for(const provider of ["github","zenodo"]){
      const correct=provider==="github"?{name:"generic",description:good}:
        {metadata:{title:good}};
      const wrong=provider==="github"?{name:"generic",description:bad}:
        {metadata:{title:bad}};
      assert.equal(providerMetadataInScope(engine,provider,correct),true,engine+"/"+provider);
      assert.equal(providerMetadataInScope(engine,provider,wrong),false,engine+"/"+provider);
    }
    const output=canonicalCandidates("github",{items:[
      {html_url:"https://github.com/synthetic-fixture/public-evidence-1",
        name:"generic-source",description:good+" PRIVATE@TEST.INVALID"},
      {html_url:"https://github.com/synthetic-fixture/off-topic-2",
        name:"generic-source",description:bad},
      {html_url:"https://github.com/synthetic-fixture/unknown-3"},
    ]},engine);
    assert.deepEqual(output,["https://github.com/synthetic-fixture/public-evidence-1"]);
    assert.ok(!JSON.stringify(output).includes("PRIVATE@TEST.INVALID"));
  }
  assert.equal(providerMetadataInScope("recoveryos","zenodo",{metadata:{creators:["Private"]}}),false);
  assert.equal(providerMetadataInScope("recoveryos","github",{name:"",description:""}),false);
  assert.throws(()=>providerMetadataInScope("bogus","github",{name:"freight"}),/INVALID_ENGINE/);
  assert.throws(()=>providerMetadataInScope("freightrecovery","socrata",{}),/UNSUPPORTED_PROVIDER/);
});

test("Zenodo record IDs require bounded, engine-specific title evidence",()=>{
  const response={hits:{hits:[
    {id:55,metadata:{title:"Supplier payment invoice reconciliation"}},
    {id:56,metadata:{title:"Biology reference photographs"}},
    {id:57,metadata:{creators:["untrusted name"]}},
    {id:"../99",metadata:{title:"Supplier invoice dataset"}},
  ]}};
  assert.deepEqual(canonicalCandidates("zenodo",response,"recoveryos"),[
    "https://zenodo.org/records/55",
  ]);
});
