const { chromium } = require('playwright');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const logs = [];
  page.on('console', m => { const t=m.text(); if (t.includes('[MOTION')||t.includes('[BREATHE]')) logs.push(t); });
  await page.goto('http://localhost:8080/index.html?earthCandidate=cameraGrammarV1', { waitUntil: 'networkidle' });
  await sleep(4000);
  await page.evaluate(() => window.earth3d.transitionToComposition('homeGlobe', { duration: 3, envelope: 'easeInOutCubic' }));
  await sleep(4000);
  await page.evaluate(() => { window.__motionLog = 0; window.earth3d.setGramPrimitive('breathe'); });
  await sleep(2000);
  console.log('LOGS:', JSON.stringify(logs.slice(-10), null, 2));
  await browser.close();
})();
