/* Golden Goose #015. All public-source bid rates / scenarios; no actual invoices. */
function testPublicBidChecker(source,verify) {
  const valid=JSON.parse(JSON.stringify(source));
  const result=verify(valid);
  if(result.line_checks!==20||result.published_bid_totals_checked!==4||
     result.fictional_scenarios_checked!==4||result.illustrative_difference_usd!=='3335.00'||
     result.owner_revenue_usd!=='0.00')throw Error('Positive-case arithmetic failed');
  const attacks=[
    d=>d.source.pdf='https://example.invalid/altered.pdf',
    d=>d.rate_categories[0].id='wrong_category',
    d=>d.bidder_prices[0].name='Not The Actual Bidder',
    d=>d.minimum_call_hours=1,
    d=>d.bidder_prices[0].unit_hourly_usd[0]='300.00',
    d=>d.verified_owner_revenue_usd='100.00',
    d=>d.rate_categories[4].annual_estimated_hours=999,
    d=>d.bidder_prices[1].listed_awardee=false,
    d=>d.bidder_prices[3].published_total_usd='9999999.00',
    d=>d.scenarios[0].bidder=2,
  ];
  let caught=0;
  for(const attack of attacks) {
    const altered=JSON.parse(JSON.stringify(source));attack(altered);
    try {verify(altered);}catch(e){caught++;}
  }
  if(caught!==attacks.length)throw Error('Failed to reject '+(attacks.length-caught)+' source tampering cases');
  return {line_prices:20,grand_totals:4,fictional_scenarios:4,tampered_cases_rejected:caught,passed:true,customer_receipts_usd:'0.00'};
}
if(typeof module!=='undefined'&&module.exports){
  module.exports={testPublicBidChecker};
  if(require.main===module){
    const d=require('./worcester_bid_rates_2026.json');
    const f=require('./worcester_public_rate_audit.js').verifyPublicBidRates;
    console.log(JSON.stringify(testPublicBidChecker(d,f)));
  }
}
