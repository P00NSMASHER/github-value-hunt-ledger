const { chromium } = require('playwright');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.WORKBENCH_CHROMIUM?{executablePath:process.env.WORKBENCH_CHROMIUM}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const tokens=JSON.parse(fs.readFileSync(require('path').join(process.argv[2], 'credentials.json'),'utf8'));
 await page.goto('http://127.0.0.1:8765');
 await page.locator('#token').fill(tokens.operator);await page.getByRole('button',{name:'Open workspace'}).click();
 await page.locator('#workspace').waitFor({state:'visible'});
 await page.locator('#case-list details').nth(6).waitFor({state:'visible'});
 if(await page.locator('#case-list details').count()!==7)throw Error('Expected seven cases');

 await page.getByRole('button',{name:'Operations',exact:true}).click();
 await page.getByRole('button',{name:'Verify backup and restore'}).click();
 await page.locator('#operation-result').filter({hasText:'"restore_verified": true'}).waitFor({state:'visible'});
 await page.getByRole('button',{name:'Lock workspace'}).click();
 await page.locator('#token').fill(tokens.reviewer);await page.getByRole('button',{name:'Open workspace'}).click();
 await page.getByRole('button',{name:'Evidence inbox'}).click();
 await page.getByRole('button',{name:'Read uploaded evidence'}).first().click();
 await page.locator('#source-list pre').filter({hasText:/\S/}).first().waitFor({state:'visible'});
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('button',{name:'Recovery cases'}).click();
 await page.locator('#case-list summary').first().click();
 await page.waitForTimeout(100);
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
 if(errors.length||overflow)throw Error(JSON.stringify({errors,overflow}));
 // Synthetic API fixture verifies display grouping only; no exchange rate is inferred.
 await page.route('**/api/state',async route=>{
  const response=await route.fetch();const fixture=await response.json();
  fixture.cases=fixture.cases.slice(0,2).map((c,i)=>({...c,currency:i?'EUR':'USD',potential_cents:i?20000:10000,recovered_cents:0,fee_cents:0,remaining_cents:i?20000:10000}));
  await route.fulfill({response,json:fixture});
 });
 await page.locator('#refresh').click();
 await page.locator('#metrics strong').filter({hasText:'EUR'}).first().waitFor();
 const amounts=(await page.locator('#metrics strong').allTextContents()).map(t=>t.replace(/\s/g,''));
 if(!amounts.includes('EUR200.00')||!amounts.includes('USD100.00')||amounts.some(t=>t.includes('300.00')))throw Error('Mixed currencies were combined or mislabeled');
 if(await page.locator('#case-list details').count()!==2)throw Error('Currency fixture did not refresh');
 console.log(JSON.stringify({mixed_currency_display:'PASS',cases:7,desktop:'PASS',mobile:'PASS',backup_restore:'PASS',evidence_read:'PASS',javascript_errors:errors.length}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
