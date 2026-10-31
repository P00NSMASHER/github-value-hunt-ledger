/* Freight Recovery 16.0: buyer-marked evidence readiness. No IO, storage or actions. */
(function(root){
 "use strict";
 const FIELDS=Object.freeze({
   invoice:"Original carrier invoice",
   rate:"Effective signed tariff or contracted rate",
   shipment:"Shipment facts (BOL, POD or measurements)",
   payment:"What was actually paid or credited",
   incumbent:"Prior incumbent claims, adjustments or refunds",
   identity:"Invoice and shipment reference"
 });
 const OPTIONS=Object.freeze({
   unchecked:"Not checked",
   located:"Buyer reports an original source is available (NOT verified)",
   missing:"Evidence unavailable",
   conflict:"Sources or values conflict"
 });
 function evaluate(input){
   const values={};let located=0,missing=0,unchecked=0,conflict=0;
   for(const key of Object.keys(FIELDS)){
     const value=input?.[key]??"unchecked";
     if(!Object.prototype.hasOwnProperty.call(OPTIONS,value))throw Error("Unsupported evidence state");
     values[key]=value;
     if(value==="located")located++;
     else if(value==="missing")missing++;
     else if(value==="conflict")conflict++;
     else unchecked++;
   }
   const state=conflict?"HOLD — CONFLICTING ORIGINAL EVIDENCE":
     missing?"MISSING EVIDENCE — MANUAL SCOPE REVIEW":
     unchecked?"DOCUMENT REVIEW REQUIRED":"READY TO REQUEST PRIVATE HUMAN REVIEW";
   const explanation=conflict?"Original versions or amounts conflict. Preserve each original and reconcile independently before any financial claim.":
     missing?"At least one source is missing. A scoped audit may help identify safe next steps, but no result can be promised.":
     unchecked?"At least one source family is unchecked. Locate its original evidence before interpreting any suspected difference.":
     "You marked all six sources as available. No rate, billing error, adjustment, refund, or entitlement was verified.";
   const report=[
     "Freight Recovery 16.0 | BUYER-MARKED, UNVERIFIED EVIDENCE PREPARATION",
     "Status: "+state,"",
     ...Object.keys(FIELDS).map(key=>FIELDS[key]+": "+OPTIONS[values[key]]),"",
     "Buyer-marked available: "+located+" of 6",
     "Missing: "+missing+"; unchecked: "+unchecked+"; conflicting: "+conflict,"",
     explanation,"",
     "NO ORIGINAL RECORDS WERE READ OR VERIFIED. This report contains NO customer or carrier",
     "record, proven overcharge, verified recovery, bank-cleared cash, authorized dispute,",
     "fee entitlement or guaranteed outcome. Independent human review is required."
   ].join("\n");
   return Object.freeze({values,located,missing,unchecked,conflict,state,explanation,report});
 }
 if(typeof module==="object"&&module.exports)module.exports={evaluate,FIELDS,OPTIONS};
 if(!root.document)return;
 const panel=root.document.querySelector("[data-v16-preflight]");if(!panel)return;
 const selects=[...panel.querySelectorAll("[data-v16-field]")];
 const title=panel.querySelector("[data-v16-state]"),detail=panel.querySelector("[data-v16-explanation]"),
   copy=panel.querySelector("[data-v16-copy]"),reset=panel.querySelector("[data-v16-reset]"),
   status=panel.querySelector("[data-v16-copy-status]"),fallback=panel.querySelector("[data-v16-fallback]"),
   manual=panel.querySelector("#v16-manual");
 if(selects.length!==6||![title,detail,copy,reset,status,fallback,manual].every(Boolean))return;
 let revision=0,output;
 function update(){
   revision++;fallback.hidden=true;manual.value="";status.textContent="";
   output=evaluate(Object.fromEntries(selects.map(field=>[field.dataset.v16Field,field.value])));
   title.textContent=output.state;detail.textContent=output.explanation;
 }
 for(const field of selects)field.addEventListener("change",update);
 copy.addEventListener("click",async()=>{
   const prior=revision,text=output.report;
   try{
     if(!root.navigator?.clipboard?.writeText)throw Error("Clipboard unavailable");
     await root.navigator.clipboard.writeText(text);
     status.textContent=prior===revision?"Unverified checklist copied. Nothing was sent or saved.":
       "Checklist changed during copying. Review the updated status and copy again.";
   }catch{
     if(prior!==revision){status.textContent="Checklist changed during copying. Copy again.";return;}
     fallback.hidden=false;manual.value=text;manual.focus();manual.select();
     status.textContent="Clipboard unavailable. Copy the complete text below manually. Nothing was sent.";
   }
 });
 reset.addEventListener("click",()=>{selects.forEach(field=>{field.value="unchecked"});update();});
 panel.hidden=false;update();
})(typeof window==="undefined"?globalThis:window);
