"""Generate a single-file read-only RETALLY operator console and evidence bundle.

No network, database writes beyond temporary synthetic fixtures, or hosted app.
The UI is only as verified as its data: generated numbers are explicitly MOCKED.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import json
from dataclasses import asdict

from freight.lab_phase2_demo import build_demo
from freight.lab_phase3_simulated_pilot import simulated_cohort
from freight.lab_phase3_economics import fixed_default_contingency_bps
from freight.lab_operations_intelligence import LAB_CONSUMERS
from freight.lab_assurance import digest

LAB_NAMES={
 1:"Invoice rating",2:"Customer lifecycle",3:"Blind pilot accuracy",
 4:"Source integration",5:"Claims and settlement",6:"Security and identity",
 7:"Sales qualification",8:"Contingency economics",9:"Buyer procurement",
 10:"Freight research",11:"Reliability and restore",12:"Fraud controls",
 13:"Future savings",14:"Competitive evidence",
}


def control_snapshot() -> dict:
    prior,prior_report=build_demo()
    cohort=simulated_cohort()
    tasks=prior["financial"]["routed_lab_work"]["lab_work_items"]
    labs=[{"id":i,"name":name,"status":"ROUTED_NOT_EXECUTED",
           "routed_items":sum(x["lab"]==i for x in tasks)} for i,name in LAB_NAMES.items()]
    modeled=sum(x["economic_scenario"]["expected_net_margin_cents"] for x in cohort["cohort"])
    sample_finance=prior["financial"]["financial_proof"]["currency_totals"]["USD"]
    payload={"schema":1,"scope":"SYNTHETIC_RESEARCH_CONTROL_CENTER",
             "release_status":"RESEARCH_BLOCKED_NO_PRODUCTION_FINANCIAL_CERTIFICATION",
             "pilot":cohort,"labs":labs,"routed_tasks_not_executed":len(tasks),
             "historical_open_findings":26,
             "sample_financial_replay":sample_finance,
             "sample_financial_receipt":prior["financial"]["financial_proof"]["receipt_hash"],
             "recommended_default_contingency_bps":fixed_default_contingency_bps(),
             "aggregate_modeled_margin_cents":modeled,
             "actual_company_revenue_cents":0,"actual_customer_recovery_cents":0,
             "production_deployed":False,"hosted_staging_certified":False,
             "external_bank_carrier_and_buyer_authority_proven":False,
             "payment_replay_guard":"TESTED_IN_FLOOT_UNPUBLISHED_PREVIEW_ONLY",
             "next_actions":[
                "Review the four stacked research PRs as one integration candidate",
                "Provision independently controlled buyer and carrier evidence keys",
                "Create a genuinely segregated hosted RecoveryOS test tenancy/database",
                "Execute authenticated end-to-end settlement and replay in staging",
                "Connect remaining routed lab engines to actual domain adapters",
                "Calibrate audit labor, recovery, fee collection and dispute assumptions",
             ]}
    payload["receipt_sha256"]=digest(payload)
    return payload


def owner_markdown(payload: dict) -> str:
    finance=payload["sample_financial_replay"]
    lines=["# RETALLY | Laboratory Control Center", "", "> Fictional research-only evidence. This is not a recovered-cash or customer-revenue report.","",
        "## Reviewed checkpoint",
        f"- Historical findings open: **{payload['historical_open_findings']}**",
        f"- Routed 14-lab task items, not executed by this report: **{payload['routed_tasks_not_executed']}**",
        f"- Actual customer recovery and RETALLY revenue: **$0.00 each**",
        f"- Default working contingency: **{payload['recommended_default_contingency_bps']/100:.0f}%**, engagement terms control actual fees.","",
        "## Fictional accounting proof",
        f"- Net customer credit in the example: **${finance['recovered_cents']/100:.2f}**",
        f"- Fee earned under the example's *separate 20% fictional engagement*: **${finance['earned_fee_cents']/100:.2f}**",
        f"- Fee collected and retained: **${finance['collected_fee_cents']/100:.2f}**",
        f"- Research replay receipt: `{payload['sample_financial_receipt']}`", "",
        "## Simulated founding pilot (not real customers)",
        "| Fictional account | Outcome state | Modeled expected net | Real cash |",
        "|---|---|---:|---:|",]
    for c in payload["pilot"]["cohort"]:
        lines.append(f"| {c['synthetic_customer_id']} | {c['state']} | ${c['economic_scenario']['expected_net_margin_cents']/100:,.2f} | $0.00 |")
    lines.extend(["",f"Aggregate modeled margin (not actual revenue): **${payload['aggregate_modeled_margin_cents']/100:,.2f}**", "",
                  "## Next evidence gates", *[f"- {v}" for v in payload["next_actions"]], "",
                  "The accounting gate uses synthetic issuer signatures. A passing test does not certify hosted RecoveryOS, real tariffs, external remittance, or production tenant isolation.",
                  "",f"Packet SHA-256: `{payload['receipt_sha256']}`"])
    return "\n".join(lines)+"\n"


HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>RETALLY | Laboratory Control Center</title>
<style>
:root{color-scheme:light;--bg:#f5f7f6;--panel:#fff;--ink:#122825;--muted:#64736f;--green:#0a8b65;--border:#dce5e1;--red:#a33239;--amber:#a3610d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.container{max-width:1190px;margin:auto;padding:24px 20px 52px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;border-bottom:1px solid var(--border);padding-bottom:17px}
.brand{font-size:23px;font-weight:840;letter-spacing:.095em}.brand span{color:var(--green)}.subtitle{font-size:12px;color:var(--muted);letter-spacing:.01em}
.flag{background:#f7e8e4;border:1px solid #e9c7bd;color:#8c302d;padding:8px 13px;border-radius:24px;font-size:11px;font-weight:750;letter-spacing:.05em}
h1{font-size:clamp(27px,3.6vw,43px);letter-spacing:-.044em;line-height:1.13;margin:30px 0 10px}h2{font-size:19px;letter-spacing:-.02em;margin:0 0 13px}
.lede{color:var(--muted);max-width:780px;font-size:14px;margin:0 0 23px}.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:22px}
.stat,.panel{background:var(--panel);border:1px solid var(--border);border-radius:15px}.stat{padding:17px}.stat .number{font-weight:790;font-size:29px;letter-spacing:-.04em;font-variant-numeric:tabular-nums}.stat small{display:block;color:var(--muted);font-size:12px}.danger{color:var(--red)}.green{color:var(--green)}
.layout{display:grid;grid-template-columns:1.45fr 1fr;gap:14px}.panel{padding:20px;margin:0 0 14px}.muted{color:var(--muted)}.pill{font-size:10px;font-weight:800;border:1px solid #d2ded8;padding:4px 8px;border-radius:30px;background:#f4f7f6;white-space:nowrap}
.row{display:flex;justify-content:space-between;gap:10px;align-items:center;border-bottom:1px solid #ebf0ee;padding:12px 0}.row:last-child{border-bottom:none}.row strong{font-size:13px}.tiny{font-size:11px;color:var(--muted)}.metric{font-variant-numeric:tabular-nums;font-weight:700} .gridlabs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.lab{border:1px solid var(--border);border-radius:10px;padding:11px}.lab strong{font-size:12px;display:block}.lab small{font-size:11px;color:var(--muted)}.lab .number{font-size:11px;font-weight:800;color:var(--green)}
input,select{background:#fff;border:1px solid #ccd9d3;border-radius:8px;padding:8px 11px;color:var(--ink);font:inherit}.filter{display:flex;gap:8px;align-items:center;margin:6px 0 13px}.filter input{flex:1;min-width:0}
footer{color:var(--muted);font-size:11px;border-top:1px solid var(--border);padding-top:22px;margin-top:16px;overflow-wrap:anywhere}
@media(max-width:800px){.layout{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}}@media(max-width:480px){.container{padding:16px 13px 38px}.top{align-items:flex-start;flex-direction:column}.stat{padding:13px}.stat .number{font-size:25px}.gridlabs{grid-template-columns:1fr}.panel{padding:15px}}
</style></head><body><div class="container"><div class="top"><div><div class="brand">RETA<span>LL</span>Y</div><div class="subtitle">RESEARCH OPERATIONS / ASSURANCE</div></div><span class="flag">SIMULATED DATA · NOT CERTIFIED</span></div>
<h1>Laboratory intelligence</h1><p class="lede">Financial evidence, modelled operating decisions and unresolved engineering work. No real bank settlement, client revenue or production deployment is represented.</p>
<section class="stats"><div class="stat"><small>Open audit findings</small><div id="findings" class="number danger">26</div><small>Historical, unresolved</small></div><div class="stat"><small>Proposed lab tasks</small><div id="tasks" class="number">49</div><small>Routed, not executed here</small></div><div class="stat"><small>Real RETALLY revenue</small><div class="number">$0.00</div><small>Simulated pilot only</small></div><div class="stat"><small>Aggregate modeled margin</small><div id="margin" class="number danger"></div><small>Uncalibrated estimate</small></div></section>
<div class="layout"><main>
<section class="panel"><h2>Founding customer simulation</h2><div id="pilot"></div></section>
<section class="panel"><h2>Laboratory handoff</h2><p class="tiny">These are work-routing receipts. A routed item is not a worker execution.</p><div class="filter"><input id="labsearch" placeholder="Filter labs…" aria-label="Filter laboratories"/><select id="laborder" aria-label="Sort laboratories"><option value="id">Number</option><option value="items">Most routed tasks</option></select></div><div id="labs" class="gridlabs"></div></section>
</main><aside><section class="panel"><h2>Financial proof / synthetic</h2><div id="money"></div><p class="tiny">The sample engagement uses a 20% fictional signed rate; the commercial launch working default is 30%.</p></section>
<section class="panel"><h2>Recommended actions</h2><div id="actions"></div></section><section class="panel"><h2>Release boundary</h2><p class="muted">Research gates pass with synthetic attestations. Production financial assurance remains blocked until independent buyer, carrier and bank evidence plus actual hosted staging tests exist.</p><span class="pill">NO PUBLISH · NO MERGE</span></section></aside></div><footer id="receipt"></footer></div>
<script id="evidence" type="application/json">__DATA__</script><script>
const data=JSON.parse(document.getElementById('evidence').textContent);const $=s=>document.querySelector(s);const cents=x=>(x<0?'−':'')+'$'+(Math.abs(x)/100).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
const clean=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
$('#findings').textContent=data.historical_open_findings;$('#tasks').textContent=data.routed_tasks_not_executed;$('#margin').textContent=cents(data.aggregate_modeled_margin_cents);
$('#pilot').innerHTML=data.pilot.cohort.map(c=>'<div class="row"><div><strong>'+clean(c.synthetic_customer_id)+'</strong><div class="tiny">'+clean(c.state.replaceAll('_',' '))+'</div></div><div class="metric '+(c.economic_scenario.expected_net_margin_cents<0?'danger':'')+'">'+cents(c.economic_scenario.expected_net_margin_cents)+'</div></div>').join('');
const fin=data.sample_financial_replay;$('#money').innerHTML=[['Customer credit retained',fin.recovered_cents],['Earned fee',fin.earned_fee_cents],['Collected fee',fin.collected_fee_cents],['Open receivable',fin.fee_receivable_cents],['Refund liability',fin.fee_refund_due_cents]].map(a=>'<div class="row"><span>'+a[0]+'</span><strong class="metric">'+cents(a[1])+'</strong></div>').join('');
$('#actions').innerHTML=data.next_actions.map((x,i)=>'<div class="row"><span class="tiny">'+(i+1)+'.</span><span>'+clean(x)+'</span></div>').join('');
function renderLabs(){let ls=data.labs.filter(x=>x.name.toLowerCase().includes($('#labsearch').value.toLowerCase())||String(x.id).includes($('#labsearch').value));if($('#laborder').value==='items')ls.sort((a,b)=>b.routed_items-a.routed_items);$('#labs').innerHTML=ls.map(x=>'<div class="lab"><span class="number">LAB '+x.id.toString().padStart(2,'0')+'</span><strong>'+clean(x.name)+'</strong><small>'+x.routed_items+' proposed tasks · not executed</small></div>').join('');}
$('#labsearch').oninput=renderLabs;$('#laborder').onchange=renderLabs;renderLabs();$('#receipt').textContent='Research packet SHA-256 '+data.receipt_sha256+' · No external customer or banking evidence was read.';
</script></body></html>'''


def generate(directory: Path) -> dict:
    directory.mkdir(parents=True,exist_ok=True)
    payload=control_snapshot()
    (directory/"phase3_dashboard.json").write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    (directory/"phase3_executive_report.md").write_text(owner_markdown(payload))
    embed=json.dumps(payload,separators=(",",":"),sort_keys=True,ensure_ascii=False).replace("<","\\u003c").replace("&","\\u0026")
    (directory/"index.html").write_text(HTML.replace("__DATA__",embed))
    return payload


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("/tmp/retally-phase3-console"))
    args=p.parse_args()
    o=generate(args.output)
    print(json.dumps({"scope":o["scope"],"receipt":o["receipt_sha256"],
                      "routed_not_executed":o["routed_tasks_not_executed"],
                      "simulated_customer_count":o["pilot"]["simulated_customer_count"],
                      "real_revenue_cents":o["actual_company_revenue_cents"]},sort_keys=True))

if __name__=="__main__": main()
