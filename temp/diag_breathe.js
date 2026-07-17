const { chromium } = require('playwright');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('http://localhost:8080/index.html?earthCandidate=cameraGrammarV1', { waitUntil: 'networkidle' });
  await sleep(4000);
  const getZ = () => page.evaluate(() => window.earth3d.getCameraZ());
  await page.evaluate(() => window.earth3d.transitionToComposition('homeGlobe', { duration: 3, envelope: 'easeInOutCubic' }));
  await sleep(4000);
  console.log('settled z =', (await getZ()).toFixed(4));
  await page.evaluate(() => window.earth3d.setGramPrimitive('breathe'));
  await sleep(1500);
  const samples = [];
  for (let i=0;i<16;i++){ samples.push(+(await getZ()).toFixed(4)); await sleep(2000); }
  console.log('breathe z samples (2s apart):', JSON.stringify(samples));
  const min=Math.min(...samples), max=Math.max(...samples);
  console.log('min=',min,'max=',max,'range=',(max-min).toFixed(4));
  await browser.close();
})();
