/* Golden Goose 016: deterministic, synthetic-only Michigan hydrovac cash test.
 * Source: https://www.michigan.gov/dtmb/-/media/Project/Websites/dtmb/Procurement/Contracts/021/250000000902.pdf
 * This never proves a collectible receivable or user revenue.
 */
const MI_URL='https://www.michigan.gov/dtmb/-/media/Project/Websites/dtmb/Procurement/Contracts/021/250000000902.pdf';
function cashCents(x) {
  if(typeof x!=='string'||!/^(0|[1-9]\d*)\.\d{2}$/.test(x))return null;
  const n=Number(x.replace('.',''));return Number.isSafeInteger(n)?n:null;
}
function utcDay(x) {
  if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(x))return null;
  const n=Date.parse(x+'T00:00:00Z');
  return Number.isFinite(n)&&new Date(n).toISOString().slice(0,10)===x?n:null;
}
const usd=n=>(n/100).toFixed(2);
function classifyCash(r){
  const answer=(status,reason,gap,details={})=>({status,reason,
    apparent_difference_usd:gap===null?null:usd(gap),
    collectible_usd:null,verified_owner_revenue_usd:'0.00',
    scope:'SYNTHETIC_NOT_CUSTOMER_PROOF',...details});
  if(!r||r.contract_id!=='250000000902'||r.contract_url!==MI_URL)
    return answer('REVIEW','AUTHORITY_MISSING',null);
  const mandatory=['delivery_order','accepted_work','invoice_itemized',
    'disposal_manifest','full_payment_ledger','payment_cleared',
    'credits_offsets_accounted','disputes_resolved','amendments_checked',
    'waiver_checked','final_payment_state_known','final_payment_recorded'];
  if(mandatory.some(k=>r[k]!==true))return answer('REVIEW','EVIDENCE_INCOMPLETE',null);
  const amount=cashCents(r.invoice_usd),paid=cashCents(r.paid_usd),
    service=utcDay(r.service_date),receipt=utcDay(r.received_date),
    payment=utcDay(r.payment_date);
  if(amount===null||paid===null||amount<=0||service===null||receipt===null||payment===null||
     service<utcDay('2025-06-26')||service>=utcDay('2028-01-01')||
     receipt<service||payment<receipt||payment>utcDay('2026-10-29'))
    return answer('REVIEW','INVALID_TIMELINE_OR_AMOUNT',null);
  const days=(payment-receipt)/86400000;
  const early=days<=30, discount=Math.floor((amount+50)/100);
  const lowerBound=early?amount-discount:amount;
  const details={days_after_receipt:days,eligible_early_discount:early,
    allowed_discount_usd:early?usd(discount):'0.00',
    minimum_cash_target_usd:usd(lowerBound),after_net45:days>45};
  if(paid===amount)return answer('MATCHED_FULL','FULL_INVOICE_PAID',0,details);
  if(early&&paid===lowerBound)return answer('MATCHED_DISCOUNT','AUTHORIZED_ONE_PERCENT_DISCOUNT',0,details);
  return answer('REVIEW','APPARENT_VARIANCE_NOT_COLLECTIBLE',Math.max(0,lowerBound-paid),details);
}
function runMichiganCashHoldout(){
  const mk=()=>({contract_id:'250000000902',contract_url:MI_URL,
    invoice_usd:'10000.00',paid_usd:'9900.00',service_date:'2026-08-30',
    received_date:'2026-09-01',payment_date:'2026-09-30',
    delivery_order:true,accepted_work:true,invoice_itemized:true,
    disposal_manifest:true,full_payment_ledger:true,payment_cleared:true,
    credits_offsets_accounted:true,disputes_resolved:true,
    amendments_checked:true,waiver_checked:true,
    final_payment_state_known:true,final_payment_recorded:true});
  const cases=[
    ['day29_discount',r=>{},'MATCHED_DISCOUNT','0.00'],
    ['day30_discount',r=>{r.payment_date='2026-10-01'},'MATCHED_DISCOUNT','0.00'],
    ['day0_discount',r=>{r.payment_date='2026-09-01'},'MATCHED_DISCOUNT','0.00'],
    ['full_early',r=>{r.paid_usd='10000.00'},'MATCHED_FULL','0.00'],
    ['full_day31',r=>{r.paid_usd='10000.00';r.payment_date='2026-10-02'},'MATCHED_FULL','0.00'],
    ['full_day45',r=>{r.paid_usd='10000.00';r.payment_date='2026-10-16'},'MATCHED_FULL','0.00'],
    ['full_day46',r=>{r.paid_usd='10000.00';r.payment_date='2026-10-17'},'MATCHED_FULL','0.00'],
    ['discount_taken_day31',r=>{r.payment_date='2026-10-02'},'REVIEW','100.00'],
    ['discount_too_large',r=>{r.paid_usd='9800.00'},'REVIEW','100.00'],
    ['one_cent_short',r=>{r.paid_usd='9999.99';r.payment_date='2026-10-02'},'REVIEW','0.01'],
    ['overpayment',r=>{r.paid_usd='10100.00'},'REVIEW','0.00'],
    ['wrong_contract',r=>{r.contract_id='unknown'},'REVIEW',null],
    ['fake_source',r=>{r.contract_url='https://example.org/fake.pdf'},'REVIEW',null],
    ['no_delivery_order',r=>{r.delivery_order=false},'REVIEW',null],
    ['not_accepted',r=>{r.accepted_work=false},'REVIEW',null],
    ['no_itemization',r=>{r.invoice_itemized=false},'REVIEW',null],
    ['no_manifest',r=>{r.disposal_manifest=false},'REVIEW',null],
    ['partial_ledger',r=>{r.full_payment_ledger=false},'REVIEW',null],
    ['uncleared_cash',r=>{r.payment_cleared=false},'REVIEW',null],
    ['unknown_credit',r=>{r.credits_offsets_accounted=false},'REVIEW',null],
    ['open_dispute',r=>{r.disputes_resolved=false},'REVIEW',null],
    ['unknown_change',r=>{r.amendments_checked=false},'REVIEW',null],
    ['possible_waiver',r=>{r.waiver_checked=false},'REVIEW',null],
    ['unknown_final_state',r=>{r.final_payment_state_known=false},'REVIEW',null],
    ['partial_payment',r=>{r.final_payment_recorded=false},'REVIEW',null],
    ['missing_date',r=>{delete r.payment_date},'REVIEW',null],
    ['payment_predates_receipt',r=>{r.payment_date='2026-08-31'},'REVIEW',null],
    ['service_after_receipt',r=>{r.service_date='2026-09-02'},'REVIEW',null],
    ['precontract_service',r=>{r.service_date='2025-06-25'},'REVIEW',null],
    ['invalid_leap_date',r=>{r.received_date='2026-02-29'},'REVIEW',null],
    ['future_payment',r=>{r.payment_date='2026-10-30'},'REVIEW',null],
    ['no_payment_amount',r=>{delete r.paid_usd},'REVIEW',null],
    ['negative_amount',r=>{r.paid_usd='-1.00'},'REVIEW',null],
    ['noncents_amount',r=>{r.invoice_usd='10000'},'REVIEW',null],
    ['unsafe_number',r=>{r.invoice_usd='999999999999999999.99'},'REVIEW',null],
    ['string_bool',r=>{r.delivery_order='true'},'REVIEW',null]
  ];
  let pass=0, reviewed=0, matched=0;
  for(const [name,change,want,gap] of cases){
    const r=mk();change(r);const got=classifyCash(r);
    if(got.status!==want||got.apparent_difference_usd!==gap||got.collectible_usd!==null||
       got.verified_owner_revenue_usd!=='0.00'||got.scope!=='SYNTHETIC_NOT_CUSTOMER_PROOF')
      throw Error('FAILED '+name+' '+JSON.stringify(got));
    pass++;if(got.status==='REVIEW')reviewed++;else matched++;
  }
  return {passed:pass,total:cases.length,reviewed,matched,owner_revenue_usd:'0.00',
    customers:0,actual_receivables_verified:0};
}
if(typeof module!=='undefined'&&module.exports){
  module.exports={classifyCash,runMichiganCashHoldout};
  if(require.main===module)console.log(JSON.stringify(runMichiganCashHoldout()));
}
