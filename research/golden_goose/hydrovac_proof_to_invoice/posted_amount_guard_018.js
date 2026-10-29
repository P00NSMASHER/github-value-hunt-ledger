/* Golden Goose 018: read-only synthetic posted-amount bridge.
 * The earlier Python quantity reconciler lacks posted unit prices/extended amounts.
 * This independent guard must NEVER infer collectible receivables or paid demand.
 * FAR 32.905 invoice itemization is a federal-process comparator, not authority
 * over the Michigan state contract or Worcester municipal bid.
 * https://www.acquisition.gov/far/subpart-32.9
 */
'use strict';
function cents(v) {
  if (typeof v !== 'string' || !/^(?:0|[1-9][0-9]*)\.[0-9]{2}$/.test(v)) return null;
  const n = Number(v.replace('.', ''));
  return Number.isSafeInteger(n) && n >= 0 && n <= 1000000000000 ? n : null;
}
function qty100(v) {
  if (typeof v !== 'string' || !/^(?:0|[1-9][0-9]*)\.[0-9]{2}$/.test(v)) return null;
  const n = Number(v.replace('.', ''));
  return Number.isSafeInteger(n) && n >= 0 && n <= 100000 ? n : null;
}
function answer(status, reason) {
  return {status,reason,verified_collectible_usd:null,verified_owner_revenue_usd:'0.00',
    customer_invoices_reviewed:0,scope:'SYNTHETIC_POSTED_AMOUNT_PROOF_ONLY'};
}
function postedAmountGuard(r) {
  const review = reason => answer('REVIEW',reason);
  if (!r || typeof r !== 'object' || Array.isArray(r) ||
    r.legacy_quantity_status !== 'CLEAR_RECONCILED') return review('NO_PRIOR_QUANTITY_RECONCILIATION');
  const required = ['signed_rate_reviewed','rate_versions_reviewed','full_ledger_verified',
    'credits_reviewed','discounts_reviewed','waivers_reviewed','no_dispute','job_identity_reviewed'];
  if (required.some(k => r[k] !== true) ||
      r.has_credit_memo !== false || r.has_waiver !== false ||
      r.has_unapplied_cash !== false) return review('UNCLEARED_AUTHORITY_OR_ADJUSTMENT');
  if (typeof r.job_id !== 'string' || !r.job_id.trim()) return review('JOB_IDENTITY_MISSING');
  const hours = qty100(r.approved_hours), dumps=qty100(r.approved_dumps),
    hourRate=cents(r.signed_hourly_usd), dumpRate=cents(r.signed_dump_usd);
  if ([hours,dumps,hourRate,dumpRate].some(x=>x===null)) return review('BAD_SIGNED_RATE_OR_QUANTITY');
  if (hours*hourRate>Number.MAX_SAFE_INTEGER || dumps*dumpRate>Number.MAX_SAFE_INTEGER)
    return review('UNSAFE_AMOUNT');
  const expectedNumer = hours*hourRate+dumps*dumpRate;
  if (expectedNumer%100) return review('NONCENT_EXPECTED_EXTENSION');
  const expected = expectedNumer/100;
  if (!Array.isArray(r.posted) || !r.posted.length) return review('MISSING_POSTED_AMOUNT_LEDGER');
  const seen = new Set(); let billed=0,billedHours=0,billedDumps=0;
  for (const l of r.posted) {
    if (!l || typeof l!=='object' || Array.isArray(l) ||
        l.state!=='ISSUED' || l.job_id!==r.job_id ||
        typeof l.invoice_line_id!=='string' || !l.invoice_line_id.trim())
      return review('INVALID_POSTED_LINE');
    const id=l.invoice_line_id.trim().toLowerCase();
    if (seen.has(id)) return review('DUPLICATE_POSTED_LINE');
    seen.add(id);
    const h=qty100(l.hours_qty),d=qty100(l.dumps_qty),
      hr=cents(l.hourly_unit_usd),dr=cents(l.dump_unit_usd),
      hx=cents(l.hours_extended_usd),dx=cents(l.dump_extended_usd),total=cents(l.line_total_usd);
    if ([h,d,hr,dr,hx,dx,total].some(x=>x===null)) return review('MISSING_OR_MALFORMED_MONEY');
    if (hr!==hourRate || dr!==dumpRate) return review('POSTED_UNIT_RATE_DIFFERS_FROM_SIGNED');
    const he=h*hr,de=d*dr;
    if (!Number.isSafeInteger(he)||!Number.isSafeInteger(de)||he%100||de%100 ||
        hx!==he/100 || dx!==de/100 || hx+dx!==total)
      return review('POSTED_EXTENSIONS_DO_NOT_FOOT');
    billed+=total;billedHours+=h;billedDumps+=d;
    if (!Number.isSafeInteger(billed)) return review('UNSAFE_TOTAL');
  }
  if (billedHours!==hours || billedDumps!==dumps) return review('POSTED_QUANTITIES_DO_NOT_FOOT');
  if (billed!==expected) return review('POSTED_TOTAL_DIFFERS_FROM_SIGNED');
  if (cents(r.ledger_total_usd)!==billed) return review('POSTED_LEDGER_TOTAL_NOT_VERIFIED');
  return answer('SYNTHETIC_ARITHMETIC_ONLY','NOT_A_RECEIVABLE_OR_REAL_INVOICE');
}
function runHoldout() {
  const base=()=>({legacy_quantity_status:'CLEAR_RECONCILED',job_id:'SYN-1',
    signed_rate_reviewed:true,rate_versions_reviewed:true,full_ledger_verified:true,
    credits_reviewed:true,discounts_reviewed:true,waivers_reviewed:true,
    no_dispute:true,job_identity_reviewed:true,has_credit_memo:false,
    has_waiver:false,has_unapplied_cash:false,
    approved_hours:'4.00',approved_dumps:'1.00',
    signed_hourly_usd:'175.00',signed_dump_usd:'180.00',ledger_total_usd:'880.00',
    posted:[{job_id:'SYN-1',invoice_line_id:'INV-1',state:'ISSUED',
      hours_qty:'4.00',dumps_qty:'1.00',hourly_unit_usd:'175.00',dump_unit_usd:'180.00',
      hours_extended_usd:'700.00',dump_extended_usd:'180.00',line_total_usd:'880.00'}]});
  const mutations=[
    ['valid',()=>{},'SYNTHETIC_ARITHMETIC_ONLY'],
    ['valid_split',r=>{r.posted[0].hours_qty='2.00';r.posted[0].dumps_qty='0.00';r.posted[0].hours_extended_usd='350.00';r.posted[0].dump_extended_usd='0.00';r.posted[0].line_total_usd='350.00';r.posted.push({...r.posted[0],invoice_line_id:'INV-2',hours_qty:'2.00',dumps_qty:'1.00',hours_extended_usd:'350.00',dump_extended_usd:'180.00',line_total_usd:'530.00'});},'SYNTHETIC_ARITHMETIC_ONLY'],
    ['valid_quarter',r=>{r.approved_hours='0.25';r.approved_dumps='0.00';r.ledger_total_usd='43.75';Object.assign(r.posted[0],{hours_qty:'0.25',dumps_qty:'0.00',hours_extended_usd:'43.75',dump_extended_usd:'0.00',line_total_usd:'43.75'});},'SYNTHETIC_ARITHMETIC_ONLY'],
    ['bad_rate_160',r=>{r.posted[0].hourly_unit_usd='160.00';r.posted[0].hours_extended_usd='640.00';r.posted[0].line_total_usd='820.00';r.ledger_total_usd='820.00'},'REVIEW'],
    ['bad_dump_rate_150',r=>{r.posted[0].dump_unit_usd='150.00';r.posted[0].dump_extended_usd='150.00';r.posted[0].line_total_usd='850.00';r.ledger_total_usd='850.00'},'REVIEW'],
    ['missing_amount',r=>{delete r.posted[0].line_total_usd},'REVIEW'],
    ['missing_hour_extension',r=>{delete r.posted[0].hours_extended_usd},'REVIEW'],
    ['partial_ledger',r=>{r.full_ledger_verified=false},'REVIEW'],
    ['unreviewed_discount',r=>{r.discounts_reviewed=false},'REVIEW'],
    ['credited_invoice',r=>{r.has_credit_memo=true},'REVIEW'],
    ['waived_claim',r=>{r.has_waiver=true},'REVIEW'],
    ['unapplied_cash',r=>{r.has_unapplied_cash=true},'REVIEW'],
    ['rate_change_unresolved',r=>{r.rate_versions_reviewed=false},'REVIEW'],
    ['unsigned',r=>{r.signed_rate_reviewed=false},'REVIEW'],
    ['duplicate_line',r=>{r.posted.push({...r.posted[0]})},'REVIEW'],
    ['wrong_job',r=>{r.posted[0].job_id='OTHER'},'REVIEW'],
    ['draft_line',r=>{r.posted[0].state='DRAFT'},'REVIEW'],
    ['quantity_short',r=>{r.posted[0].hours_qty='3.00';r.posted[0].hours_extended_usd='525.00';r.posted[0].line_total_usd='705.00';r.ledger_total_usd='705.00'},'REVIEW'],
    ['extension_mismatch',r=>{r.posted[0].hours_extended_usd='699.00'},'REVIEW'],
    ['ledger_off',r=>{r.ledger_total_usd='879.99'},'REVIEW'],
    ['price_extra',r=>{r.posted[0].line_total_usd='1060.00';r.ledger_total_usd='1060.00'},'REVIEW'],
    ['invalid_currency',r=>{r.ledger_total_usd='Infinity'},'REVIEW'],
    ['incorrect_original_status',r=>{r.legacy_quantity_status='POTENTIAL_HOURS_GAP'},'REVIEW'],
    ['string_proof',r=>{r.credits_reviewed='true'},'REVIEW'],
    ['unsafe_money',r=>{r.signed_hourly_usd='99999999999999.99'},'REVIEW']
  ];
  let pass=0,review=0,arithmetic=0;
  for(const [name,mutate,want] of mutations){
    const row=base();mutate(row);const got=postedAmountGuard(row);
    if(got.status!==want || got.verified_collectible_usd!==null ||
       got.verified_owner_revenue_usd!=='0.00' || got.customer_invoices_reviewed!==0)
      throw Error(name+' expected '+want+' got '+JSON.stringify(got));
    pass++;if(got.status==='REVIEW')review++;else arithmetic++;
  }
  return {passed:pass,total:mutations.length,review,arithmetic_only:arithmetic,
    real_invoices:0,verified_owner_revenue_usd:'0.00'};
}
if(typeof module!=='undefined' && module.exports){
  module.exports={postedAmountGuard,runHoldout};
  if(require.main===module)console.log(JSON.stringify(runHoldout()));
}
