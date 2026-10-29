/* Golden Goose #021: deterministic 100-job Python -> posted-amount JS integration.
 * Run: node test_100_job_python_to_js_021.js
 * Requires local python3; no network/dependencies/customer records/outreach.
 * All source/jobs/sidecars are synthetic; arithmetic-only != collectible money.
 */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const {bridge}=require('./cohort_amount_bridge_019.js');
const fixturePath=path.join(__dirname,'synthetic_100_jobs.json');
const fixtures=JSON.parse(fs.readFileSync(fixturePath,'utf8'));
assert.equal(fixtures.synthetic_only,true,'Fixture must be explicitly synthetic');
assert.equal(fixtures.jobs.length,100,'Frozen cohort size changed');
const python=[
  'import json,sys',
  'sys.path.insert(0,sys.argv[1])',
  'from hydrovac_reconcile import summarize',
  "with open(sys.argv[2],encoding='utf-8') as f: jobs=json.load(f)['jobs']",
  "print(json.dumps(summarize(jobs,as_of='2026-10-29')))"
].join('\n');
const result=spawnSync(process.env.PYTHON||'python3',
  ['-c',python,__dirname,fixturePath],
  {encoding:'utf8',timeout:15000,maxBuffer:3*1024*1024});
if(result.error||result.status!==0)
  throw Error('Python quantity summary failed: '+(result.error||result.stderr));
const summary=JSON.parse(result.stdout);
assert.equal(summary.total_jobs,100);
assert.equal(summary.clear,70);
assert.equal(summary.candidate_discrepancies,12);
assert.equal(summary.review_only,18);
assert.equal(summary.illustrative_candidate_gross_usd,'4940.00');
assert.equal(summary.verified_collectible_usd,null);
assert.equal(summary.verified_customer_revenue_usd,0);
const money=n=>n.toFixed(2);
function postedProof(job){
  const id=job.job_id, index=Number(id.slice(-3));
  assert.equal(job.fixture_category,'clean');
  const qtyHours=Number(job.approved_billable_hours);
  const qtyDumps=Number(job.approved_dump_loads);
  const rate=Number(job.rate_card.hourly_rate),dump=Number(job.rate_card.dump_fee);
  const hoursAmount=qtyHours*rate, dumpsAmount=qtyDumps*dump;
  const row={legacy_quantity_status:'CLEAR_RECONCILED',job_id:id,
    signed_rate_reviewed:true,rate_versions_reviewed:true,
    full_ledger_verified:true,credits_reviewed:true,discounts_reviewed:true,
    waivers_reviewed:true,no_dispute:true,job_identity_reviewed:true,
    has_credit_memo:false,has_waiver:false,has_unapplied_cash:false,
    approved_hours:money(qtyHours),approved_dumps:money(qtyDumps),
    signed_hourly_usd:money(rate),signed_dump_usd:money(dump),
    ledger_total_usd:money(hoursAmount+dumpsAmount),
    posted:[{job_id:id,invoice_line_id:'POST-'+id,state:'ISSUED',
      hours_qty:money(qtyHours),dumps_qty:money(qtyDumps),
      hourly_unit_usd:money(rate),dump_unit_usd:money(dump),
      hours_extended_usd:money(hoursAmount),dump_extended_usd:money(dumpsAmount),
      line_total_usd:money(hoursAmount+dumpsAmount)}]};
  // Predeclared, mutually exclusive synthetic negative controls.
  if(index<=4){ // coherent extensions but WRONG contract unit rate
    row.posted[0].hourly_unit_usd='160.00';
    row.posted[0].hours_extended_usd='640.00';
    row.posted[0].line_total_usd='820.00';
    row.ledger_total_usd='820.00';
  }else if(index<=7){ // quantities/rates correct but ledger subtotal incorrect
    row.ledger_total_usd='879.99';
  }else if(index<=10){ // credit exists; no lawful net-balance inference
    row.has_credit_memo=true;
  }
  return row;
}
const sidecars=fixtures.jobs.filter(x=>x.fixture_category==='clean').map(postedProof);
assert.equal(sidecars.length,70);
const baseline=summary.rows.filter(r=>r.status==='CLEAR_RECONCILED').length;
const checked=bridge(summary,sidecars);
assert.equal(checked.arithmetic_only,60);
assert.equal(checked.needs_review,40);
assert.equal(checked.verified_collectible_usd,null);
assert.equal(checked.verified_owner_revenue_usd,'0.00');
assert.equal(checked.actual_customer_invoices_reviewed,0);
for(const r of checked.rows){
  const index=Number(r.job_id.slice(-3));
  const expected=index>10&&index<=70?'SYNTHETIC_ARITHMETIC_ONLY':'REVIEW';
  assert.equal(r.status,expected,r.job_id);
  assert.equal(r.collectible_usd,null);
}
// Each predeclared mutation must fail closed, not create money.
// An absent arithmetic-clean proof must decrease arithmetic clears; removing
// a deliberately poisoned proof must not change the clear count.
const missing=bridge(summary,sidecars.filter(r=>r.job_id!=='SYN-HV-011'));
assert.equal(missing.arithmetic_only,59);
assert.equal(missing.needs_review,41);
const missingAlreadyReviewed=bridge(summary,sidecars.slice(1));
assert.equal(missingAlreadyReviewed.arithmetic_only,60);
assert.equal(missingAlreadyReviewed.needs_review,40);
const duplicated=JSON.parse(JSON.stringify(sidecars));
duplicated[1].posted[0].invoice_line_id=duplicated[0].posted[0].invoice_line_id;
const collision=bridge(summary,duplicated);
assert.equal(collision.status,'REVIEW');
assert.equal(collision.arithmetic_only,0);
const tamperedSummary={...summary,clear:71};
assert.equal(bridge(tamperedSummary,sidecars).arithmetic_only,0);
const hidden=JSON.parse(JSON.stringify(summary));
hidden.rows[14].discount_usd='100.00';
assert.equal(bridge(hidden,sidecars).arithmetic_only,0);
console.log(JSON.stringify({test:'GG-021 Python->JS synthetic cohort',
  cases:100,quantity_only_clears:baseline,
  hidden_posted_issues:10,strict_arithmetic_only:checked.arithmetic_only,
  strict_needs_review:checked.needs_review,
  gross_candidate_fictional_usd:summary.illustrative_candidate_gross_usd,
  verified_collectible_usd:null,verified_owner_revenue_usd:'0.00',
  real_customer_invoices:0,
  cohort_mutation_checks:5,
  incumbent_vendor_comparison:'NOT_RUN',
  customer_willingness_to_pay:'UNKNOWN'}));
