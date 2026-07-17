const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const reqs = [];
  page.on('requestfailed', (r) => reqs.push(r.url() + ' :: ' + (r.failure() && r.failure().errorText)));
  await page.goto('http://127.0.0.1:8099/pwa/index.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(6000);
  const info = await page.evaluate(() => {
    return {
      hasRodio: typeof window.__rodio !== 'undefined',
      hasRodioVisualState: typeof window.__rodioVisualState !== 'undefined',
      lilGui: typeof window.lil !== 'undefined' || typeof window.GUI !== 'undefined',
      tunerScriptRan: document.querySelector('script') ? true : false,
      bodyHasTuner: document.body.innerHTML.includes('Theme Tuner') || document.body.innerHTML.includes('theme-tuner'),
    };
  });
  console.log('INFO:', JSON.stringify(info, null, 2));
  console.log('FAILED REQUESTS:', reqs.filter((r) => r.includes('lil') || r.includes('gui') || r.includes('cdn')).join('\n') || 'none cdn-related');
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
