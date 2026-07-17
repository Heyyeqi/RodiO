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
  console.log('before setPrim, motionLog=', await page.evaluate(()=>window.__motionLog||0));
  await page.evaluate(() => window.earth3d.setGramPrimitive('breathe'));
  for (let i=0;i<6;i++){
    await sleep(500);
    const s = await page.evaluate(() => ({ z: window.earth3d.getCameraZ(), ml: window.__motionLog||0, prim: window.earth3d.getGramDebug().activePrim }));
    console.log('t='+(i*0.5)+'s:', JSON.stringify(s));
  }
  console.log('LOGS count:', logs.length, 'last 5:', JSON.stringify(logs.slice(-5)));
  await browser.close();
})();
