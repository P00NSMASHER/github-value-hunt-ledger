/* Golden Goose 017 | two-source public-price scope adversarial holdout
 * RESEARCH ONLY. No customer/real invoice input; no entitlement or receivable.
 * Michigan signed contract: https://www.michigan.gov/dtmb/-/media/Project/Websites/dtmb/Procurement/Contracts/021/250000000902.pdf
 * Worcester bid: https://www.worcesterma.gov/finance/purchasing-bids/bids/cr-8693-j6
 * Tender specifications: https://www.worcesterma.gov/sites/default/files/bids/CR-8693-J6-FORM-30B-Sealed-Bid-G-S-Vacuum-Excavation-Services-DPW.pdf
 * Published bid rate sheets: https://www.worcesterma.gov/sites/default/files/bids/CR-8693-J6%20-%20Bid%20Results%20%28Unit%20Pricing%20Pages%29.pdf
 */
'use strict';
const MI_SOURCE='https://www.michigan.gov/dtmb/-/media/Project/Websites/dtmb/Procurement/Contracts/021/250000000902.pdf';
const WO_SOURCE='https://www.worcesterma.gov/finance/purchasing-bids/bids/cr-8693-j6';
const WO_BID_PDF='https://www.worcesterma.gov/sites/default/files/bids/CR-8693-J6-FORM-30B-Sealed-Bid-G-S-Vacuum-Excavation-Services-DPW.pdf';
const WO_RATES_PDF='https://www.worcesterma.gov/sites/default/files/bids/CR-8693-J6%20-%20Bid%20Results%20%28Unit%20Pricing%20Pages%29.pdf';
const RATE_MI={regular_basin:6800,emergency_basin:25000,lane_closure_day:100000};
const RATE_WO={
  'Phoenix Communications, Inc.':[31500,31500,31500,36000,31500],
  'R.H. White Construction Co., Inc.':[31200,36700,36700,36700,31200]
};
function money(s) {
  if(typeof s!=='string'||!/^(?:0|[1-9][0-9]*)[.][0-9]{2}$/.test(s))return null;
  const n=Number(s.replace('.',''));
  return Number.isSafeInteger(n)?n:null;
}
function dateNumber(s) {
  if(typeof s!=='string'||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(s))return null;
  const n=Date.parse(s+'T00:00:00Z');
  return Number.isFinite(n)&&new Date(n).toISOString().slice(0,10)===s?n:null;
}
function result(status,reason,price=null) {
  return {status,reason,public_price_arithmetic_usd:price===null?null:(price/100).toFixed(2),
    verified_collectible_usd:null,verified_owner_revenue_usd:'0.00',
    customer_invoices_reviewed:0,scope:'PUBLIC_RULES_AND_SYNTHETIC_FIXTURES_ONLY'};
}
function publicScopeCheck(row) {
  if(!row||typeof row!=='object')return result('REVIEW','INVALID_ROW');
  const dt=dateNumber(row.service_date),now=dateNumber('2026-10-29');
  if(dt===null||dt>now)return result('REVIEW','BAD_OR_FUTURE_SERVICE_DATE');
  const invoice=money(row.invoice_usd);
  if(invoice===null)return result('REVIEW','INVALID_CURRENCY');
  if(row.mode==='MI') {
    if(row.contract_id!=='250000000902'||row.source_url!==MI_SOURCE)
      return result('REVIEW','WRONG_CONTRACT_AUTHORITY');
    if(dt<dateNumber('2025-06-26')||dt>=dateNumber('2028-01-01'))
      return result('REVIEW','OUTSIDE_CONTRACT_TERM');
    if(!['regular_basin','emergency_basin','lane_closure_day'].includes(row.item)||
       !Number.isSafeInteger(row.units)||row.units<1||row.units>1000)
      return result('REVIEW','UNKNOWN_UNIT_OR_ITEM');
    if(['delivery_order','accepted_work','itemized_invoice','disposal_manifest',
        'amendment_reviewed','credits_reviewed','waivers_reviewed'].some(k=>row[k]!==true))
      return result('REVIEW','MISSING_ITEM_EVIDENCE');
    if(row.item==='emergency_basin'&&row.emergency_authorized!==true)
      return result('REVIEW','EMERGENCY_NOT_AUTHORIZED');
    if(row.item==='lane_closure_day'&&row.lane_closure_authorized!==true)
      return result('REVIEW','LANE_CLOSURE_NOT_AUTHORIZED');
    if(['separate_disposal_usd','separate_water_usd','unlisted_fee_usd','sales_tax_usd']
       .some(k=>money(row[k])!==0))
      return result('REVIEW','UNSUPPORTED_SEPARATE_CHARGE');
    if(row.claimed_unit_rate_usd!==(RATE_MI[row.item]/100).toFixed(2))
      return result('REVIEW','WRONG_UNIT_PRICE');
    const expected=RATE_MI[row.item]*row.units;
    if(invoice!==expected)return result('REVIEW','INVOICE_DIFFERS_FROM_PUBLIC_PRICE');
    return result('PUBLIC_CONTRACT_ARITHMETIC_ONLY','NO_REAL_WORK_OR_ENTITLEMENT_ATTESTED',expected);
  }
  if(row.mode==='WO') {
    if(row.bid_id!=='CR-8693-J6'||row.source_url!==WO_SOURCE||
       row.spec_url!==WO_BID_PDF||row.rate_sheet_url!==WO_RATES_PDF)
      return result('REVIEW','WRONG_BID_AUTHORITY');
    if(dt<dateNumber('2026-07-01')||dt>dateNumber('2027-06-30'))
      return result('REVIEW','OUTSIDE_ADVERTISED_PERIOD');
    const rates=RATE_WO[row.bidder];
    if(!rates||!Number.isInteger(row.tier)||row.tier<0||row.tier>=5||
       !Number.isInteger(row.worked_hours)||row.worked_hours<1||row.worked_hours>24)
      return result('REVIEW','UNKNOWN_BIDDER_TIER_OR_HOURS');
    if(['separate_disposal_usd','separate_water_usd','unlisted_fee_usd','sales_tax_usd']
       .some(k=>money(row[k])!==0))
      return result('REVIEW','BID_SPEC_FORBIDS_EXTRA_DISPOSAL_WATER');
    if(row.amendments_checked!==true||row.signed_terms_verified!==false)
      return result('REVIEW','CONTRACT_TERMS_MUST_REMAIN_UNVERIFIED');
    if(row.claimed_unit_rate_usd!==(rates[row.tier]/100).toFixed(2))
      return result('REVIEW','WRONG_BID_HOURLY_RATE');
    const expected=rates[row.tier]*Math.max(4,row.worked_hours);
    if(invoice!==expected)return result('REVIEW','INVOICE_DIFFERS_FROM_BID_ARITHMETIC');
    return result('PUBLIC_BID_ARITHMETIC_ONLY','SIGNED_CONTRACT_NOT_OBTAINED',expected);
  }
  return result('REVIEW','UNSUPPORTED_CONTRACT_FAMILY');
}
function runScopeHoldout() {
  const mi=()=>({mode:'MI',contract_id:'250000000902',source_url:MI_SOURCE,
    service_date:'2026-09-01',item:'regular_basin',units:1,
    claimed_unit_rate_usd:'68.00',invoice_usd:'68.00',
    delivery_order:true,accepted_work:true,itemized_invoice:true,
    disposal_manifest:true,amendment_reviewed:true,credits_reviewed:true,
    waivers_reviewed:true,emergency_authorized:false,lane_closure_authorized:false,
    separate_disposal_usd:'0.00',separate_water_usd:'0.00',
    unlisted_fee_usd:'0.00',sales_tax_usd:'0.00'});
  const wo=()=>({mode:'WO',bid_id:'CR-8693-J6',source_url:WO_SOURCE,
    spec_url:WO_BID_PDF,rate_sheet_url:WO_RATES_PDF,service_date:'2026-09-01',
    bidder:'Phoenix Communications, Inc.',tier:4,worked_hours:1,
    claimed_unit_rate_usd:'315.00',invoice_usd:'1260.00',
    amendments_checked:true,signed_terms_verified:false,
    separate_disposal_usd:'0.00',separate_water_usd:'0.00',
    unlisted_fee_usd:'0.00',sales_tax_usd:'0.00'});
  const samples=[
    ['mi_one_basin',mi,()=>{},'PUBLIC_CONTRACT_ARITHMETIC_ONLY'],
    ['mi_two_basins',mi,r=>{r.units=2;r.invoice_usd='136.00'},'PUBLIC_CONTRACT_ARITHMETIC_ONLY'],
    ['mi_emergency_item',mi,r=>{r.item='emergency_basin';r.claimed_unit_rate_usd='250.00';r.invoice_usd='250.00';r.emergency_authorized=true},'PUBLIC_CONTRACT_ARITHMETIC_ONLY'],
    ['mi_lane_closure',mi,r=>{r.item='lane_closure_day';r.claimed_unit_rate_usd='1000.00';r.invoice_usd='1000.00';r.lane_closure_authorized=true},'PUBLIC_CONTRACT_ARITHMETIC_ONLY'],
    ['mi_unlisted_disposal_180',mi,r=>{r.separate_disposal_usd='180.00';r.invoice_usd='248.00'},'REVIEW'],
    ['mi_unlisted_water',mi,r=>{r.separate_water_usd='50.00';r.invoice_usd='118.00'},'REVIEW'],
    ['mi_cross_contract_hour_rate',mi,r=>{r.claimed_unit_rate_usd='315.00';r.invoice_usd='315.00'},'REVIEW'],
    ['mi_false_70_rate',mi,r=>{r.claimed_unit_rate_usd='70.00';r.invoice_usd='70.00'},'REVIEW'],
    ['mi_missing_delivery',mi,r=>{r.delivery_order=false},'REVIEW'],
    ['mi_unaccepted_work',mi,r=>{r.accepted_work=false},'REVIEW'],
    ['mi_no_manifest',mi,r=>{r.disposal_manifest=false},'REVIEW'],
    ['mi_unknown_amendment',mi,r=>{r.amendment_reviewed=false},'REVIEW'],
    ['mi_unreviewed_waiver',mi,r=>{r.waivers_reviewed=false},'REVIEW'],
    ['mi_unknown_credit',mi,r=>{r.credits_reviewed=false},'REVIEW'],
    ['mi_unapproved_emergency',mi,r=>{r.item='emergency_basin';r.invoice_usd='250.00';r.claimed_unit_rate_usd='250.00'},'REVIEW'],
    ['mi_unapproved_lane',mi,r=>{r.item='lane_closure_day';r.invoice_usd='1000.00';r.claimed_unit_rate_usd='1000.00'},'REVIEW'],
    ['mi_wrong_document',mi,r=>{r.source_url=WO_SOURCE},'REVIEW'],
    ['mi_wrong_contract',mi,r=>{r.contract_id='250000000903'},'REVIEW'],
    ['mi_prepurchase',mi,r=>{r.service_date='2025-06-25'},'REVIEW'],
    ['mi_invalid_date',mi,r=>{r.service_date='2026-02-29'},'REVIEW'],
    ['mi_future_job',mi,r=>{r.service_date='2026-10-30'},'REVIEW'],
    ['mi_invalid_money',mi,r=>{r.invoice_usd='68.001'},'REVIEW'],
    ['mi_ineligible_tax',mi,r=>{r.sales_tax_usd='4.08'},'REVIEW'],
    ['mi_unlisted_admin_fee',mi,r=>{r.unlisted_fee_usd='25.00'},'REVIEW'],
    ['mi_inconsistent_invoice',mi,r=>{r.invoice_usd='67.00'},'REVIEW'],
    ['wo_phoenix_1hr_min',wo,()=>{},'PUBLIC_BID_ARITHMETIC_ONLY'],
    ['wo_phoenix_4hr',wo,r=>{r.worked_hours=4},'PUBLIC_BID_ARITHMETIC_ONLY'],
    ['wo_rh_white_1hr',wo,r=>{r.bidder='R.H. White Construction Co., Inc.';r.claimed_unit_rate_usd='312.00';r.invoice_usd='1248.00'},'PUBLIC_BID_ARITHMETIC_ONLY'],
    ['wo_phoenix_weekend',wo,r=>{r.tier=3;r.claimed_unit_rate_usd='360.00';r.invoice_usd='1440.00'},'PUBLIC_BID_ARITHMETIC_ONLY'],
    ['wo_false_only_actual_hour',wo,r=>{r.invoice_usd='315.00'},'REVIEW'],
    ['wo_extra_disposal_fee',wo,r=>{r.separate_disposal_usd='180.00';r.invoice_usd='1440.00'},'REVIEW'],
    ['wo_extra_water_fee',wo,r=>{r.separate_water_usd='50.00';r.invoice_usd='1310.00'},'REVIEW'],
    ['wo_mi_unit_substitution',wo,r=>{r.claimed_unit_rate_usd='68.00';r.invoice_usd='272.00'},'REVIEW'],
    ['wo_wrong_bidder',wo,r=>{r.bidder='New England Vacuum Excavation'},'REVIEW'],
    ['wo_wrong_tier',wo,r=>{r.tier=5},'REVIEW'],
    ['wo_0hours',wo,r=>{r.worked_hours=0},'REVIEW'],
    ['wo_missing_spec',wo,r=>{r.spec_url='https://example.org/fake.pdf'},'REVIEW'],
    ['wo_source_mismatch',wo,r=>{r.source_url=MI_SOURCE},'REVIEW'],
    ['wo_fake_signed_terms',wo,r=>{r.signed_terms_verified=true},'REVIEW'],
    ['wo_unknown_amendment',wo,r=>{r.amendments_checked=false},'REVIEW'],
    ['wo_outside_period',wo,r=>{r.service_date='2026-06-30'},'REVIEW'],
    ['wo_sales_tax',wo,r=>{r.sales_tax_usd='75.60'},'REVIEW'],
    ['wo_unsupported_misc',wo,r=>{r.unlisted_fee_usd='50.00'},'REVIEW'],
    ['cross_without_mode',wo,r=>{r.mode='UNKNOWN'},'REVIEW']
  ];
  let passed=0,review=0,miMatched=0,woMatched=0;
  for(const [name,make,mutate,want] of samples){
    const row=make();mutate(row);const got=publicScopeCheck(row);
    if(got.status!==want||got.verified_collectible_usd!==null||
       got.verified_owner_revenue_usd!=='0.00'||got.customer_invoices_reviewed!==0||
       got.scope!=='PUBLIC_RULES_AND_SYNTHETIC_FIXTURES_ONLY'||
       ((want==='REVIEW')!==(got.public_price_arithmetic_usd===null)))
      throw Error(name+': expected '+want+' got '+JSON.stringify(got));
    passed++;if(got.status==='REVIEW')review++;
    else if(got.status==='PUBLIC_CONTRACT_ARITHMETIC_ONLY')miMatched++;
    else woMatched++;
  }
  return {passed,total:samples.length,review,mi_arithmetic_only:miMatched,
    wo_bid_arithmetic_only:woMatched,verified_owner_revenue_usd:'0.00',
    verified_collectible_usd:null,customer_invoices_reviewed:0};
}
if(typeof module!=='undefined'&&module.exports){
  module.exports={publicScopeCheck,runScopeHoldout};
  if(require.main===module)console.log(JSON.stringify(runScopeHoldout()));
}
