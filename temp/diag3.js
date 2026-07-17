const { chromium } = require('playwright');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('http://localhost:8080/index.html?earthCandidate=cameraGrammarV1', { waitUntil: 'networkidle' });
  await sleep(4000);
  const getZ = () => page.evaluate(() => window.earth3d.getCameraZ());
  const getVS = () => page.evaluate(() => { const vs=window.__rodioVisualState||{}; return {settledZ: vs._gramSettledZ, rollOffset: vs._gramRollOffset}; });
  await page.evaluate(() => window.earth3d.transitionToComposition('homeGlobe', { duration: 3, envelope: 'easeInOutCubic' }));
  await sleep(4000);
  console.log('after homeGlobe:', 'z=', await getZ(), JSON.stringify(await getVS()));
  const ret = await page.evaluate(() => window.earth3d.setGramPrimitive('breathe'));
  console.log('setPrim breathe returned:', ret);
  await sleep(2000);
  for (let i=0;i<10;i++){ await sleep(2000); console.log('t='+(i*2)+'s z=', (await getZ()).toFixed(4), JSON.stringify(await getVS())); }
  await browser.close();
})();
