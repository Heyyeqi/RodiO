const { chromium } = require('playwright');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('http://localhost:8080/index.html?earthCandidate=cameraGrammarV1', { waitUntil: 'networkidle' });
  await sleep(4000);
  const getVS = () => page.evaluate(() => { const vs = window.__rodioVisualState||{}; return {rollOffset: vs._gramRollOffset, latOffset: vs._gramLatOffset, activePrim: window.earth3d.getDebugState ? 'x':'?'}; });
  // transition to homeGlobe
  await page.evaluate(() => window.earth3d.transitionToComposition('homeGlobe', { duration: 3, envelope: 'easeInOutCubic' }));
  await sleep(4000);
  console.log('after homeGlobe trans:', JSON.stringify(await getVS()));
  const ret = await page.evaluate(() => window.earth3d.setGramPrimitive('rollDrift'));
  console.log('setPrim returned:', ret);
  for (let i=0;i<5;i++){ await sleep(2000); console.log('t='+(i*2)+'s:', JSON.stringify(await getVS())); }
  await browser.close();
})();
