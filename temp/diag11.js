const { chromium } = require('playwright');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const logs = [];
  page.on('console', m => logs.push('['+m.type()+'] '+m.text()));
  page.on('pageerror', e => logs.push('PAGEERROR: ' + e.message));
  await page.goto('http://localhost:8080/index.html?earthCandidate=cameraGrammarV1', { waitUntil: 'networkidle' });
  await sleep(4000);
  await page.evaluate(() => window.earth3d.transitionToComposition('homeGlobe', { duration: 3, envelope: 'easeInOutCubic' }));
  await sleep(4000);
  const ret = await page.evaluate(() => window.earth3d.setGramPrimitive('breathe'));
  console.log('setPrim returned:', ret);
  await sleep(2000);
  console.log('ALL LOGS after setPrim:', JSON.stringify(logs.filter(l=>!l.includes('[log]')).slice(-15), null, 2));
  await browser.close();
})();
