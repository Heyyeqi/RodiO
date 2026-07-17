const { chromium } = require('playwright');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const logs = [];
  page.on('console', m => logs.push('['+m.type()+'] '+m.text()));
  page.on('pageerror', e => logs.push('PAGEERROR: ' + e.message));
  await page.goto('http://localhost:8080/pwa/index.html?earthCandidate=cameraGrammarV1', { waitUntil: 'networkidle' });
  await sleep(4000);
  const hasEarth3d = await page.evaluate(() => typeof window.earth3d);
  const hasVS = await page.evaluate(() => typeof window.__rodioVisualState);
  const keys = await page.evaluate(() => window.earth3d ? Object.keys(window.earth3d).filter(k=>k.includes('Gram')||k.includes('Camera')||k==='getCameraZ') : null);
  console.log('typeof earth3d:', hasEarth3d);
  console.log('typeof __rodioVisualState:', hasVS);
  console.log('gram keys:', JSON.stringify(keys));
  console.log('LOGS:', JSON.stringify(logs.slice(0,30), null, 2));
  await browser.close();
})();
