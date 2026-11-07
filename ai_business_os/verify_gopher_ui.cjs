// Start the upstream pilot and React UI first. Run from the upstream gocrm-ui directory.
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const { chromium } = require(path.resolve('node_modules/playwright'));

async function main() {
  const [loginFile, email, reference] = process.argv.slice(2);
  if (!loginFile || !email?.endsWith('.invalid') || !reference?.startsWith('retally:synthetic:')) {
    throw Error('Expected login.json path, fixture email and synthetic inquiry reference');
  }
  const options = { headless: true };
  if (process.env.RETALLY_CHROMIUM_HELPER) {
    const { default: helper } = await import(process.env.RETALLY_CHROMIUM_HELPER);
    options.executablePath = await helper.executablePath();
    options.args = [...helper.args, '--disable-background-networking'];
  }
  const browser = await chromium.launch(options);
  try {
    const page = await browser.newPage();
    let nonLoopback = 0;
    await page.route('**/*', route => {
      if (new URL(route.request().url()).hostname === '127.0.0.1') return route.continue();
      nonLoopback++;
      return route.abort();
    });
    const login = JSON.parse(fs.readFileSync(loginFile));
    await page.goto('http://127.0.0.1:19824/login');
    await page.locator('#email').fill(login.email);
    await page.locator('#password').fill(login.password);
    await page.getByRole('button', { name: /^sign in$/i }).click();
    await page.waitForURL(url => !url.pathname.endsWith('/login'));
    await page.goto('http://127.0.0.1:19824/leads');
    await page.getByText(email, { exact: true }).first().waitFor();
    await page.goto('http://127.0.0.1:19824/tasks');
    const marker = createHash('sha256').update(reference).digest('hex');
    await page.getByText('Qualify inquiry [RETALLY-' + marker + ']', { exact: true }).first().waitFor();
    if (nonLoopback) throw Error('Blocked external requests detected');
    console.log(JSON.stringify({ freshLogin: true, fixtureLeadVisible: true, linkedTaskVisible: true,
                                 nonLoopbackPageRequests: nonLoopback }));
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
