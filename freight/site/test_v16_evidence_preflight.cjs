"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs");
const tool=require("./v16-evidence-preflight.js");
test("all 4096 buyer-marked six-source permutations fail closed to human review",()=>{
 const ids=Object.keys(tool.FIELDS),states=Object.keys(tool.OPTIONS);
 assert.equal(ids.length,6);assert.equal(states.length,4);
 const all=[];
 for(let i=0;i<4096;i++){let t=i,inputs={};for(const key of ids){inputs[key]=states[t%4];t=Math.floor(t/4);}
   const result=tool.evaluate(inputs);all.push(result.state);
   assert.equal(result.located+result.missing+result.unchecked+result.conflict,6);
   assert.match(result.report,/BUYER-MARKED, UNVERIFIED/);
   assert.match(result.report,/NO ORIGINAL RECORDS WERE READ OR VERIFIED/);
   assert(!/CLAIM APPROVED|CASH CONFIRMED|VERIFIED OVERCHARGE|AUTOMATIC PAYMENT/.test(result.state));
   if(result.conflict)assert.match(result.state,/HOLD/);
   else if(result.missing)assert.match(result.state,/MISSING/);
   else if(result.unchecked)assert.match(result.state,/DOCUMENT REVIEW/);
   else assert.match(result.state,/PRIVATE HUMAN REVIEW/);
 }
 assert.equal(all.length,4096);
});
test("unsupported or malicious evidence states cannot be laundered into permission",()=>{
 assert.throws(()=>tool.evaluate({invoice:"verified"}),/Unsupported/);
 assert.throws(()=>tool.evaluate({rate:"approved"}),/Unsupported/);
 const full=tool.evaluate(Object.fromEntries(Object.keys(tool.FIELDS).map(x=>[x,"located"])));
 assert.equal(full.located,6);
 assert.match(full.report,/NO ORIGINAL RECORDS WERE READ OR VERIFIED/);
 assert.match(full.report,/fee entitlement or guaranteed outcome/);
});
test("local site script cannot store, send, fetch or claim a customer-approved recovery",()=>{
 const js=fs.readFileSync(__dirname+"/v16-evidence-preflight.js","utf8");
 const html=fs.readFileSync(__dirname+"/index.html","utf8");
 assert(html.includes('name="freight-product-version" content="16.0.0"'));
 assert(html.includes('id="evidence-preflight"'));
 assert(html.includes('data-v16-preflight hidden'));
 assert(html.includes('src="v16-evidence-preflight.js?v=1"'));
 assert(!/\b(?:fetch\s*\(|XMLHttpRequest|sendBeacon|localStorage|sessionStorage|indexedDB|document\.cookie)\b/.test(js));
 assert(!/\b(?:stripe|paymentIntent|subscribe|sendMail)\s*\(/i.test(js));
 assert(!js.includes("window.location.href"));
});
