import test from "node:test";
import assert from "node:assert/strict";
import scout, {ENGINES, canonicalCandidates, feedSpecs, fetchCatalog, permitplateCandidateInScope, selectCandidateWindow} from "./research_lab_worker.mjs";

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
    {html_url:"https://github.com/owner/source-data",description:"PERSON@PRIVATE.COM"},
    {html_url:"https://github.com/owner/repo?token=secret"},
    {html_url:"http://localhost/private"},
  ]}),["https://github.com/owner/source-data"]);
  assert.deepEqual(canonicalCandidates("zenodo",{hits:{hits:[
    {id:987654321,files:[{key:"confidential-document.pdf"}]},
    {id:"../123"},
  ]}}),["https://zenodo.org/records/987654321"]);
  assert.deepEqual(canonicalCandidates("socrata",{results:[
    {resource:{id:"abcd-1234",name:"DOB NOW: Build – Approved Permits"}},
    {resource:{id:"../../passwd"}},
  ]}),["https://data.cityofnewyork.us/d/abcd-1234"]);
});
test("missing or malformed API responses fail closed", ()=>{
  for(const p of ["github","zenodo","socrata"]){
    assert.throws(()=>canonicalCandidates(p,{bad:[]}),/INVALID_ITEMS/);
  }
  assert.throws(()=>canonicalCandidates("wrong",{items:[]}),/UNSUPPORTED_PROVIDER/);
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
      return new Response(JSON.stringify({items:[{html_url:"https://github.com/test/example"}]}),
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
  ]}), [
    "https://data.cityofnewyork.us/d/ipu4-2q9a",
    "https://data.cityofnewyork.us/d/rbx6-tga4",
    "https://data.cityofnewyork.us/d/w9ak-ipjd",
  ]);
  assert.equal(permitplateCandidateInScope("https://github.com/owner/NYC-Restaurant-Inspection"), false);
  assert.equal(permitplateCandidateInScope("https://github.com/owner/NYC-DOB-Building-Permits"), true);
});
