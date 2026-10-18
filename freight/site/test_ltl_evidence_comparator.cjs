/* RETALLY LTL comparator: pure arithmetic and negative controls.
 * Runs offline using the source file. Never sends a request.
 */
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const calculator = require("./ltl-evidence-comparator.js");
const sample = () => ({
  count:1,
  original:{length:48,width:40,height:45,weight:450},
  carrier:{length:48,width:40,height:48,weight:500}
});
test("official NMFTA sample and a fictional carrier reweigh are computed exactly", () => {
  const result = calculator.compare(sample());
  assert.equal(result.original.volume, 50);
  assert.equal(result.original.density, 9);
  assert.ok(Math.abs(result.carrier.volume - 53.333333333333336) < 1e-10);
  assert.ok(Math.abs(result.carrier.density - 9.375) < 1e-10);
  assert.equal(result.change.weight, 50);
  assert.ok(Math.abs(result.change.density - 0.375) < 1e-10);
  assert.equal(Object.hasOwn(result, "freightClass"), false);
  assert.equal(Object.hasOwn(result, "refund"), false);
});
test("identical quantities scale weight and volume but not density", () => {
  const input=sample();input.count=3;
  const out=calculator.compare(input);
  assert.equal(out.original.volume,150);
  assert.equal(out.original.weight,1350);
  assert.equal(out.original.density,9);
  assert.equal(out.carrier.weight,1500);
});
test("same measurements return exactly zero deltas", () => {
  const input=sample();input.carrier={...input.original};
  const out=calculator.compare(input);
  assert.deepEqual(out.change,{weight:0,volume:0,density:0});
});
test("numeric validation blocks missing, zero, negative, malformed, overly large and fractional unit counts", () => {
  const cases=[
    ["count", "", null],["count", "0", null],["count", "-2", null],
    ["count", "1.5", null],["count", "1001", null],
    ["original", "length", 0],["carrier", "height", "N/A"],
    ["original", "width", 1201],["carrier", "weight", Infinity],
    ["original", "weight", -5]
  ];
  for(const [field,other,value] of cases){
    const input=sample();
    if(field==="count")input.count=other;
    else input[field][other]=value;
    assert.throws(()=>calculator.compare(input),RangeError);
  }
});
test("pure calculator never mutates the submitted object", () => {
  const input=sample(),original=JSON.stringify(input);
  calculator.compare(input);
  assert.equal(JSON.stringify(input),original);
});
test("calculator source cannot upload, track, persist, fetch, guess NMFC class or leak a shipment identifier", () => {
  const s=fs.readFileSync(path.join(__dirname,"ltl-evidence-comparator.js"),"utf8");
  for(const prohibited of ["fetch(", "XMLHttpRequest", "sendBeacon", "localStorage", "sessionStorage", "document.cookie", "classMap", "rateSchedule", "innerHTML"]){
    assert.ok(!s.includes(prohibited),prohibited);
  }
});
test("browser demo only populates fictional values; submit, reset and print are user gestures", () => {
  const s=fs.readFileSync(path.join(__dirname,"ltl-evidence-comparator.js"),"utf8");
  const events={},nodes=new Map(),printed=[];
  function node(id){
    if(!nodes.has(id))nodes.set(id,{
      value:"",textContent:"",hidden:id==="ltlCompareResults",
      addEventListener(name,fn){events[id+":"+name]=fn;},
      reset(){ for(const x of nodes.values())if("value" in x)x.value=""; }
    });
    return nodes.get(id);
  }
  const context={
    document:{getElementById:node},
    window:{print(){printed.push("ok");}},
    module:{exports:{}},
    RangeError,Number,Math,Object,String
  };
  vm.runInNewContext(s,context,{filename:"ltl-evidence-comparator.js"});
  events["ltlDemo:click"]();
  assert.equal(node("ltlOriginalDensity").textContent,"9.00");
  assert.equal(node("ltlCarrierDensity").textContent,"9.38");
  assert.equal(node("ltlDensityDifference").textContent,"+0.38");
  assert.equal(node("ltlCompareResults").hidden,false);
  events["ltlPrint:click"]();
  assert.equal(printed.length,1);
  events["ltlClear:click"]();
  assert.equal(node("ltlCompareResults").hidden,true);
  assert.equal(node("ltlOriginalLength").value,"");
});
