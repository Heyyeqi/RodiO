const { chromium } = require('playwright');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('http://localhost:8080/index.html?earthCandidate=cameraGrammarV1', { waitUntil: 'networkidle' });
  await sleep(4000);
  await page.evaluate(() => window.earth3d.transitionToComposition('homeGlobe', { duration: 3, envelope: 'easeInOutCubic' }));
  await sleep(4000);
  await page.evaluate(() => window.earth3d.setGramPrimitive('breathe'));
  await sleep(1500);
  for (let i=0;i<4;i++){
    const s = await page.evaluate(() => ({ z: window.earth3d.getCameraZ(), settled: window.__rodioVisualState._dbgSettledZRef, trans: window.__rodioVisualState._dbgTransRef }));
    console.log('t='+i+':', JSON.stringify(s));
    await sleep(1000);
  }
  await browser.close();
})();
