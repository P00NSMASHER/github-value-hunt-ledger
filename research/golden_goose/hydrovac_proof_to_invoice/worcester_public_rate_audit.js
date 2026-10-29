/* Source-bound public-bid arithmetic; not an invoice audit or money entitlement. */
function verifyPublicBidRates(data) {
  function cents(s) {
    if (typeof s !== 'string' || !/^[0-9]+[.][0-9]{2}$/.test(s)) throw Error('Invalid money amount');
    const n=Number(s.replace('.',''));
    if(!Number.isSafeInteger(n)) throw Error('Unsafe cents');
    return n;
  }
  if(data.minimum_call_hours!==4||data.bidder_prices.length!==4||data.rate_categories.length!==5) throw Error('Wrong cohort');
  const expectedNames=['Phoenix Communications, Inc.','R.H. White Construction Co., Inc.','New England Vacuum Excavation','Champion Environmental Services'];
  const expectedTiers=['urgent_weekday_day','urgent_weekday_evening','urgent_weekday_overnight','urgent_weekend_holiday','standard_weekday_day'];
  if(data.source?.official_page!=='https://www.worcesterma.gov/finance/purchasing-bids/bids/cr-8693-j6'||
     data.source?.pdf!=='https://www.worcesterma.gov/sites/default/files/bids/CR-8693-J6%20-%20Bid%20Results%20%28Unit%20Pricing%20Pages%29.pdf'||
     data.source?.bid!=='CR-8693-J6')throw Error('Unverified primary source identity');
  for(let i=0;i<5;i++)if(data.rate_categories[i].id!==expectedTiers[i])throw Error('Pricing tier identity changed');
  const totals=[37530000,37549600,45210000,285049200], qty=[100,40,24,24,1000];
  const names=new Set();let lineChecks=0,bidChecks=0;
  for(const [i,b] of data.bidder_prices.entries()){
    if(b.name!==expectedNames[i]||names.has(b.name)||b.pdf_page!==i+1||b.listed_awardee!==(i<2)||b.unit_hourly_usd.length!==5)throw Error('Bidders/awardees/pages mismatch');
    names.add(b.name);let computed=0;
    for(let j=0;j<5;j++){
      if(data.rate_categories[j].annual_estimated_hours!==qty[j])throw Error('Incorrect quantities');
      computed+=qty[j]*cents(b.unit_hourly_usd[j]);lineChecks++;
    }
    if(computed!==totals[i]||computed!==cents(b.published_total_usd))throw Error('Published bid mismatch');
    bidChecks++;
  }
  let gapCents=0,scenarioChecks=0;
  const illustrative=[];
  for(const c of data.scenarios){
    const b=data.bidder_prices[c.bidder];
    if(!b?.listed_awardee||!Number.isInteger(c.tier)||c.tier<0||c.tier>=5||
       !Number.isInteger(c.worked_hours)||c.worked_hours<1||c.worked_hours>=4)throw Error('Bad illustrative call');
    const p=cents(b.unit_hourly_usd[c.tier]);
    const gap=(4-c.worked_hours)*p;gapCents+=gap;scenarioChecks++;
    illustrative.push({bidder:b.name,rate_category:data.rate_categories[c.tier].id,worked_hours:c.worked_hours,minimum_hour_charge_usd:(4*p/100).toFixed(2),actual_only_usd:(c.worked_hours*p/100).toFixed(2),synthetic_difference_usd:(gap/100).toFixed(2),collectible_usd:null});
  }
  if(scenarioChecks!==4||gapCents!==333500)throw Error('Scenario mismatch');
  if(data.verified_owner_revenue_usd!=='0.00'||data.actual_customers!==0||data.verified_collectible_usd!==null)throw Error('Revenue misrepresentation');
  return {line_checks:lineChecks,published_bid_totals_checked:bidChecks,fictional_scenarios_checked:scenarioChecks,illustrative_difference_usd:(gapCents/100).toFixed(2),owner_revenue_usd:'0.00',illustrative};
}
if (typeof module!=='undefined'&&module.exports) module.exports={verifyPublicBidRates};
