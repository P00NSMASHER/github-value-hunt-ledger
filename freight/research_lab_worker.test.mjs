import test from "node:test";
import assert from "node:assert/strict";
import scout, {ENGINES, canonicalCandidates, feedSpecs, fetchCatalog} from "./research_lab_worker.mjs";

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
    {resource:{id:"abcd-1234",name:"Private Name"}},
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
