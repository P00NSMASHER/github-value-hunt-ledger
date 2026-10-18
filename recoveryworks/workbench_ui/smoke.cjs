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
 await page.waitForFunction(()=>document.querySelectorAll('#case-list details').length===7);

 await page.getByRole('button',{name:'Operations',exact:true}).click();
 await page.getByRole('button',{name:'Verify backup and restore'}).click();
 await page.waitForFunction(()=>document.querySelector('#operation-result').textContent.includes('"restore_verified": true'));
 await page.getByRole('button',{name:'Lock workspace'}).click();
 await page.locator('#token').fill(tokens.reviewer);await page.getByRole('button',{name:'Open workspace'}).click();
 await page.getByRole('button',{name:'Evidence inbox'}).click();
 await page.getByRole('button',{name:'Read uploaded evidence'}).first().click();
 await page.waitForFunction(()=>[...document.querySelectorAll('#source-list pre')].some(e=>e.textContent.length>0));
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('button',{name:'Recovery cases'}).click();
 await page.locator('#case-list summary').first().click();
 await page.waitForTimeout(100);
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
 if(errors.length||overflow)throw Error(JSON.stringify({errors,overflow}));
 console.log(JSON.stringify({cases:7,desktop:'PASS',mobile:'PASS',backup_restore:'PASS',evidence_read:'PASS',javascript_errors:errors.length}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
