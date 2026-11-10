import test from "node:test";
import assert from "node:assert/strict";
import {onRequestPost,onRequestGet} from "../../functions/api/funnel.js";
const calls=[];
const env={INQUIRY_DB:{prepare(sql){return {bind(...args){return {async run(){calls.push({sql,args});return {success:true}}}}}}}};
function req(data, options={}) {
  const host=options.host||"www.retallyrecovery.com";
  return new Request("https://"+host+"/api/funnel",{
    method:"POST",
    headers:{"Origin":options.origin||"https://"+host,
      "Sec-Fetch-Site":options.fetchSite||"same-origin",
      "Sec-Fetch-Mode":"cors","Content-Type":"application/json",
      "User-Agent":options.ua||"Mozilla/5.0"},
    body:typeof data==="string"?data:JSON.stringify(data)
  });
}
const valid={event:"freight_audit_form_started",channel:"organic_search",offer:"founding"};
test("stores only aggregate dimensions and no personal data",async()=>{
  calls.length=0;
  assert.equal((await onRequestPost({request:req(valid),env})).status,204);
  assert.equal(calls.length,1);
  assert.match(calls[0].sql,/marketing_funnel_daily/);
  assert.equal(calls[0].args.length,4);
  assert.deepEqual(calls[0].args.slice(1),[valid.event,valid.channel,valid.offer]);
});
test("denies cross-origin, forged sec-fetch and arbitrary events",async()=>{
  calls.length=0;
  for(const request of [
    req(valid,{origin:"https://evil.example"}),
    req(valid,{fetchSite:"cross-site"}),
    req({...valid,email:"victim@example.com"}),
    req({...valid,event:"freight_qualified_lead"}),
    req({...valid,offer:"unexpected"}),
  ]) assert.notEqual((await onRequestPost({request,env})).status,204);
  assert.equal(calls.length,0);
});
test("bounds aggregate write amplification without creating identities",async()=>{
  calls.length=0;
  assert.equal((await onRequestPost({request:req(valid),env})).status,204);
  assert.match(calls[0].sql,/marketing_funnel_daily\\.interactions < 250/);
  assert.ok(!/ip|email|user_agent/i.test(calls[0].sql));
});
test("does not count known audits, automation or bad bot scores",async()=>{
  calls.length=0;
  for(const ua of ["RETALLY-Public-Release-Audit/1.0","HeadlessChrome/143","CaptureBrief-release-readonly/1.0"])
    assert.equal((await onRequestPost({request:req(valid,{ua}),env})).status,204);
  assert.equal((await onRequestPost({request:Object.assign(req(valid),{cf:{botManagement:{score:15}}}),env})).status,204);
  assert.equal(calls.length,0);
});
test("fails closed without DB; never tracks on GET",async()=>{
 assert.equal((await onRequestPost({request:req(valid),env:{}})).status,503);
 assert.equal((await onRequestGet()).status,405);
});
