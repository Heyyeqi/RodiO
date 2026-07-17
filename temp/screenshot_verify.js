const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  const consoleMsgs = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text());
    consoleMsgs.push(`[${msg.type()}] ${msg.text()}`);
  });
  page.on('pageerror', (err) => errors.push('PAGEERROR: ' + err.message));

  await page.goto('http://127.0.0.1:8099/pwa/index.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(5000);

  // 检查旧 UI 是否消失
  const checks = await page.evaluate(() => {
    const ids = ['theme-preview', 'rdl-zoom-control', 'earth-audit-control'];
    const result = {};
    ids.forEach((id) => {
      result[id] = document.getElementById(id) ? 'PRESENT' : 'ABSENT';
    });
    // Theme Tuner 检查
    result.themeTuner = document.querySelector('.theme-tuner, #theme-tuner, [class*="theme-tuner"]') ? 'PRESENT' : 'ABSENT';
    result.bodyText = document.body.innerText.slice(0, 200);
    return result;
  });

  await page.screenshot({ path: '/Users/rw-mac/Projects/RodiO/temp/page_full.png', fullPage: false });

  console.log('=== UI CHECKS ===');
  console.log(JSON.stringify(checks, null, 2));
  console.log('=== PAGE ERRORS (JS runtime) ===');
  console.log(errors.filter((e) => e.startsWith('PAGEERROR')).length ? errors.filter((e) => e.startsWith('PAGEERROR')).join('\n') : 'NONE');

  await browser.close();
})().catch((e) => {
  console.error('SCRIPT ERROR:', e);
  process.exit(1);
});
