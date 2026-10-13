"use strict";
/* RETALLY anonymous worksheet regression suite — zero network, zero dependencies. */
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const worksheet = require("./worksheet.js");

test("exact-cents arithmetic: sample yields a $125 candidate, NOT recovered money", () => {
  const output = worksheet.calculate({ billed: "1167.60", expected: "1042.60", credits: "0.00" });
  assert.equal(output.ok, true);
  assert.equal(output.positiveDifferenceCents, 12500);
  assert.equal(output.unresolvedCents, 12500);
  assert.equal(output.realizedRecoveryCents, null);
  assert.equal(output.verifiedOvercharge, false);
  assert.equal(output.authorizedClaim, false);
  assert.equal(output.state, "CANDIDATE_ONLY");
});

test("credits offset the candidate without creating imaginary money", () => {
  const x = worksheet.calculate({ billed:"100.00", expected:"75.00", credits:"10.01" });
  assert.equal(x.positiveDifferenceCents, 2500);
  assert.equal(x.reconciledCreditsCents, 1001);
  assert.equal(x.unresolvedCents, 1499);
});

test("all prior credits offset but do not verify a settlement", () => {
  const x = worksheet.calculate({ billed:"100.00", expected:"75.00", credits:"25.00" });
  assert.equal(x.state, "NO_UNRESOLVED_POSITIVE_DIFFERENCE");
  assert.equal(x.unresolvedCents, 0);
  assert.equal(x.realizedRecoveryCents, null);
});

test("more credits than a difference clamp to zero and flag review", () => {
  const x = worksheet.calculate({ billed:"100.00", expected:"75.00", credits:"50.00" });
  assert.equal(x.unresolvedCents, 0);
  assert.equal(x.reconciledCreditsCents, 2500);
  assert.equal(x.creditsExceedCandidate, true);
});

test("underbilling never creates a negative recovery estimate", () => {
  const x = worksheet.calculate({ billed:"80.00", expected:"100.00", credits:"0.00" });
  assert.equal(x.positiveDifferenceCents, 0);
  assert.equal(x.unresolvedCents, 0);
  assert.equal(x.state,"NO_POSITIVE_DIFFERENCE");
});

test("neutral exact input never implies error or money due", () => {
  const x = worksheet.calculate({ billed:"100.00", expected:"100.00", credits:"0.00" });
  assert.equal(x.state,"NO_POSITIVE_DIFFERENCE");
  assert.equal(x.unresolvedCents,0);
});

test("support cents exactly without floating point drift", () => {
  const x = worksheet.calculate({ billed:"0.30",expected:"0.10",credits:"0.10" });
  assert.equal(x.unresolvedCents,10);
  assert.equal(worksheet.dollars(x.unresolvedCents),"$0.10");
});

test("strictly reject exponent, negative, NaN, infinite, and fractional cents", () => {
  const invalid = ["-1","1e10","NaN","Infinity","0.001","$100","1,000","1.","01.00",".1","12abc","-0","-0.00"];
  for (const value of invalid) {
    assert.equal(worksheet.parseMoney(value).ok, false, value);
  }
});

test("reject numbers not strings; do not coerce untrusted inputs", () => {
  for (const x of [undefined,null,123,Infinity,[],{},false]) {
    assert.equal(worksheet.parseMoney(x).ok,false,String(x));
  }
});

test("validate blank and missing fields without silent zero imputation", () => {
  const x = worksheet.calculate({billed:"100",expected:"",credits:"0"});
  assert.equal(x.ok,false);assert.equal(x.field,"expected");
  const y = worksheet.calculate({billed:"100",expected:"90"});
  assert.equal(y.ok,false);assert.equal(y.field,"credits");
});

test("bound amounts to one billion dollars and safe integer cents", () => {
  assert.equal(worksheet.parseMoney("1000000000.00").ok,true);
  assert.equal(worksheet.parseMoney("1000000000.01").ok,false);
  assert.equal(worksheet.parseMoney("9999999999.99").ok,false);
  assert.throws(()=>worksheet.dollars(-1),RangeError);
  assert.throws(()=>worksheet.dollars(NaN),RangeError);
});

test("sample returns no contact identifiers or carrier invoice numbers", () => {
  assert.deepEqual(worksheet.SAMPLE,{billed:"1167.60",expected:"1042.60",credits:"0.00"});
  for (const value of Object.values(worksheet.SAMPLE)) assert.match(value,/^\d+\.\d{2}$/);
});

function harness() {
  const controls = new Map();
  const ids = ["invoiceWorksheet","ws-billed","ws-expected","ws-credits","ws-difference",
  "ws-unresolved","ws-credit-applied","ws-status","ws-error","ws-sample","ws-clear",
  "ws-print","ws-copy","ws-copy-status"];
  let printed = 0, copied = "", focusCount = 0;
  let networkCount=0, localStorageCount=0;
  for (const id of ids) {
    controls.set(id,{id,value:"",textContent:"",dataset:{},listeners:{},
      addEventListener(type,fn){this.listeners[type]=fn;},
      fire(type){return this.listeners[type]?.({currentTarget:this});},
      focus(){focusCount++;}});
  }
  const printClasses = new Set();
  const listeners = {};
  const win = {print(){printed++;},
    addEventListener(type,fn){listeners[type]=fn;},
    navigator:{clipboard:{async writeText(value){copied=value;}}},
    fetch(){networkCount++;throw new Error("Unexpected network request")},
    localStorage:{setItem(){localStorageCount++;throw new Error("Unexpected persistence")}}
  };
  const doc = {getElementById(id){return controls.get(id)||null;},
    body:{classList:{add(x){printClasses.add(x)},remove(x){printClasses.delete(x)},contains(x){return printClasses.has(x)}}}};
  return {doc,win,controls,listeners,printClasses,states(){return {printed,copied,focusCount,networkCount,localStorageCount}}};
}

test("no markup means the script is inert on all other website pages", () => {
  const h = harness();
  h.controls.delete("invoiceWorksheet");
  assert.equal(worksheet.mount(h.doc,h.win),false);
  assert.equal(h.states().networkCount,0);
});

test("rendered sample stays sample-only and updates accessible totals", () => {
  const h = harness();
  assert.equal(worksheet.mount(h.doc,h.win),true);
  h.controls.get("ws-sample").fire("click");
  assert.equal(h.controls.get("ws-difference").textContent,"$125.00");
  assert.equal(h.controls.get("ws-unresolved").textContent,"$125.00");
  assert.match(h.controls.get("ws-status").textContent,/not a validated overcharge/i);
  assert.equal(h.controls.get("invoiceWorksheet").dataset.dataPolicy,"local-only-no-storage-or-upload");
  assert.equal(h.states().networkCount,0);
  assert.equal(h.states().localStorageCount,0);
});

test("live changes recalculate from current state without analytics", () => {
  const h=harness();worksheet.mount(h.doc,h.win);
  h.controls.get("ws-sample").fire("click");
  h.controls.get("ws-credits").value="100.00";
  h.controls.get("ws-credits").fire("input");
  assert.equal(h.controls.get("ws-unresolved").textContent,"$25.00");
  assert.equal(h.states().networkCount,0);
});

test("invalid fields hide old estimate and show descriptive error", () => {
  const h=harness();worksheet.mount(h.doc,h.win);
  h.controls.get("ws-sample").fire("click");
  h.controls.get("ws-billed").value="100abc";
  h.controls.get("ws-billed").fire("input");
  assert.equal(h.controls.get("ws-unresolved").textContent,"—");
  assert.match(h.controls.get("ws-error").textContent,/two decimals/);
});

test("clear button removes values and any stale candidate without sending data", () => {
  const h=harness();worksheet.mount(h.doc,h.win);
  h.controls.get("ws-sample").fire("click");
  h.controls.get("ws-clear").fire("click");
  for(const field of ["billed","expected","credits"])assert.equal(h.controls.get("ws-"+field).value,"");
  assert.equal(h.controls.get("ws-unresolved").textContent,"—");
  assert.ok(h.states().focusCount > 0);
  assert.equal(h.states().networkCount,0);
});

test("print class is scoped and cleaned up afterprint", () => {
  const h=harness();worksheet.mount(h.doc,h.win);
  h.controls.get("ws-print").fire("click");
  assert.equal(h.states().printed,1);
  assert.ok(h.printClasses.has("worksheet-print-mode"));
  h.listeners.afterprint();
  assert.ok(!h.printClasses.has("worksheet-print-mode"));
});

test("public-link copy never includes user-entered dollar amounts", async () => {
  const h=harness();worksheet.mount(h.doc,h.win);
  h.controls.get("ws-sample").fire("click");
  await h.controls.get("ws-copy").fire("click");
  const state=h.states();
  assert.equal(state.copied,"https://www.retallyrecovery.com/freight-invoice-audit-checklist#worksheet");
  assert.ok(!state.copied.includes("1167.60"));
  assert.match(h.controls.get("ws-copy-status").textContent,/no amounts were copied/i);
});

test("mount is idempotent; no duplicate listeners or double print", () => {
  const h=harness();
  assert.equal(worksheet.mount(h.doc,h.win),true);
  assert.equal(worksheet.mount(h.doc,h.win),true);
  h.controls.get("ws-print").fire("click");
  assert.equal(h.states().printed,1);
});

test("standalone JS has no credentials, tracking, network, or browser storage references", () => {
  const source=fs.readFileSync(path.join(__dirname,"worksheet.js"),"utf8");
  assert.ok(!/\b(?:fetch|XMLHttpRequest|sendBeacon|sessionStorage|indexedDB)\s*\(/.test(source));
  assert.ok(!/\b(?:localStorage|sessionStorage|indexedDB)\s*\.\s*(?:setItem|getItem)/.test(source));
  assert.ok(!/location\.search|utm_|dataLayer|gtag\(/i.test(source));
  assert.ok(!/mailto:|@retallyrecovery\.com|<form/i.test(source));
});
