const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.goto('http://127.0.0.1:8099/pwa/index.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(5000);
  const info = await page.evaluate(() => {
    const all = document.querySelectorAll('*');
    const found = [];
    all.forEach((el) => {
      if (el.children.length === 0 && el.textContent && el.textContent.includes('SyntaxError')) {
        found.push({ tag: el.tagName, id: el.id, cls: el.className, text: el.textContent.slice(0, 100) });
      }
    });
    return { count: found.length, items: found.slice(0, 5), hostname: window.location.hostname, isLocal: (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') };
  });
  console.log(JSON.stringify(info, null, 2));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
