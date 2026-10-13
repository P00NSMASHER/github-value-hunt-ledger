"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");

const p=path.resolve(__dirname,"../brand/social/performance/retally-worksheet-social-drafts-20261013.json");
const pack=JSON.parse(fs.readFileSync(p,"utf8"));
const posts=pack.posts;
const byNetwork=network=>posts.filter(x=>x.network===network);

test("20 social drafts cover 8 topics and 3 networks with zero publishing mutations",()=>{
 assert.equal(posts.length,20);
 assert.equal(byNetwork("facebook").length,8);
 assert.equal(byNetwork("instagram").length,8);
 assert.equal(byNetwork("linkedin").length,4);
 assert.equal(pack.existing_calendar_unchanged,true);
 assert.equal(pack.public_page_state,"NEW_WORKSHEET_DRAFT_NOT_DEPLOYED");
 assert.equal(new Set(posts.map(x=>x.topic)).size,8);
});
test("all postings intentionally disabled and creative rights held",()=>{
 for(const row of posts){
  assert.equal(row.autoPublish,false);
  assert.equal(row.draft,true);
  assert.equal(row.requires_worksheet_release,true);
  assert.equal(row.requires_visual_review,true);
  assert.equal(row.media_status,"NOT_RENDERED_OR_APPROVED");
  assert.ok(["REVIEW_ONLY_NOT_SCHEDULED","RESTRICTED_ACCOUNT_DRAFT"].includes(row.status));
  assert.ok(row.visual_brief.length>=80);
  assert.ok(row.headline.length>=14 && row.headline.length<70);
 }
});
test("Facebook links have unique exact-host CTA and campaign attribution",()=>{
 const contents=new Set();
 for(const row of byNetwork("facebook")){
  const matches=row.copy.match(/https:\/\/[^\s]+/g)||[];
  assert.equal(matches.length,1,row.id);
  const url=new URL(matches[0]);
  assert.equal(url.origin,"https://www.retallyrecovery.com");
  assert.equal(url.pathname,"/freight-invoice-audit-checklist");
  assert.equal(url.hash,"#worksheet");
  assert.equal(url.searchParams.get("utm_source"),"facebook");
  assert.equal(url.searchParams.get("utm_medium"),"organic_social");
  assert.equal(url.searchParams.get("utm_campaign"),"retally_worksheet_education_2026");
  const marker=url.searchParams.get("utm_content");
  assert.ok(marker && !contents.has(marker));
  contents.add(marker);
 }
});
test("LinkedIn company drafts remain restricted pending account authorization",()=>{
 for(const row of byNetwork("linkedin")){
  assert.equal(row.requires_account_authorization,true);
  assert.equal(row.status,"RESTRICTED_ACCOUNT_DRAFT");
  const matches=row.copy.match(/https:\/\/[^\s]+/g)||[];
  assert.equal(matches.length,1);
  const url=new URL(matches[0]);
  assert.equal(url.searchParams.get("utm_source"),"linkedin");
  assert.equal(url.hash,"#worksheet");
 }
});
test("Instagram captions avoid nonclickable URL and unverified profile-link route",()=>{
 for(const row of byNetwork("instagram")){
  assert.equal(row.educational_link,null);
  assert.equal(row.requires_profile_link_review,true);
  assert.ok(!/https?:\/\//i.test(row.copy));
  assert.ok(!/link in (our |the )?bio/i.test(row.copy));
  assert.ok(row.copy.includes("#RETALLY"));
 }
});
test("no made-up customer outcomes or false recovery guarantees",()=>{
 for(const row of posts){
  assert.ok(!/(?:our customers saved|we recovered \$|guaranteed refund|verified customer case|guarantee your savings)/i.test(row.copy),row.id);
  assert.ok(!/(?:send us your invoices|upload your contract here|share bank account)/i.test(row.copy),row.id);
  assert.ok(!/https:\/\/(?:retallyrecovery\.com)\/api\/inquiry/i.test(row.copy));
 }
});
test("all detention sample versions clearly disclose illustrative scenario",()=>{
 const rows=posts.filter(x=>x.topic==="detention_sample");
 assert.equal(rows.length,2);
 for(const row of rows){
  assert.ok(/ILLUSTRATIVE/i.test(row.copy));
  assert.ok(/NOT A CUSTOMER RESULT/i.test(row.copy));
  assert.ok(row.copy.includes("08:30") && row.copy.includes("11:00"));
  assert.ok(row.copy.includes("120"));
  assert.ok(row.copy.includes("30"));
  assert.ok(row.copy.includes("60"));
 }
});
test("no unaudited media URL or social platform credentials in draft pack",()=>{
 const text=JSON.stringify(pack);
 assert.ok(!/static\.metricool\.com|linkedin\.com\/company\/|access_token|Bearer\s+/i.test(text));
 assert.equal(pack.human_rights_and_creative_acceptance_required,true);
 assert.ok(!posts.some(row=>row.scheduledDate||row.uuid||row.providerPostId));
});
test("unique outlines avoid exact copy crossposting",()=>{
 assert.equal(new Set(posts.map(x=>x.copy)).size,20);
 assert.ok(posts.every(x=>x.copy.length>180 && x.copy.length<2400));
});
