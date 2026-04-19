const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('CONSOLE:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGEERROR:', err.toString()));
  page.on('requestfailed', req => console.log('REQUESTFAILED:', req.url(), req.failure()?.errorText));
  page.on('response', res => {
    if (res.status() >= 400) console.log('BADRESPONSE:', res.status(), res.url());
  });
  await page.goto('http://127.0.0.1:8000/dashboard', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'dashboard-test.png', fullPage: true });
  console.log('URL:', page.url());
  console.log('TITLE:', await page.title());
  console.log('CONTENT START:', (await page.content()).slice(0, 500));
  await browser.close();
})();
