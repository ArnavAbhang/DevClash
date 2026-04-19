const { chromium } = require('playwright');
(async () => {
  const loginRes = await fetch('http://127.0.0.1:8000/api/auth/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ email: 'copilot-test@example.com', password: 'Password123' })
  });
  const data = await loginRes.json();
  console.log('LOGIN_RESPONSE:', JSON.stringify(data, null, 2));
  if (!(data && data.data && data.data.token)) {
    console.error('Login failed', data);
    process.exit(1);
  }
  console.log('LOGIN_USER:', data.data.user);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('CONSOLE:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGEERROR:', err.toString()));
  page.on('requestfailed', req => console.log('REQUESTFAILED:', req.url(), req.failure()?.errorText));
  page.on('response', res => { if (res.status() >= 400) console.log('BADRESPONSE:', res.status(), res.url()); });
  await page.addInitScript((token, user) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
  }, data.data.token, data.data.user);
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
  const preGotoLocalState = await page.evaluate(() => ({
    token: localStorage.getItem('token'),
    user: localStorage.getItem('user'),
  }));
  console.log('PRE_GOTO_LOCALSTATE:', preGotoLocalState);
  await page.goto('http://127.0.0.1:8000/dashboard', { waitUntil: 'networkidle' });
  const localState = await page.evaluate(() => ({
    token: localStorage.getItem('token'),
    user: localStorage.getItem('user'),
    path: window.location.pathname,
    html: document.body.innerHTML.slice(0, 200),
  }));
  console.log('LOCALSTATE:', localState);
  await page.screenshot({ path: 'dashboard-auth-test.png', fullPage: true });
  console.log('URL:', page.url());
  console.log('TITLE:', await page.title());
  console.log('CONTENT START:', (await page.content()).slice(0, 500));
  await browser.close();
})();