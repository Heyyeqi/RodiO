const { chromium } = require('playwright');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('http://localhost:8080/index.html?earthCandidate=cameraGrammarV1', { waitUntil: 'networkidle' });
  await sleep(4000);
  const getDbg = () => page.evaluate(() => window.earth3d.getGramDebug());
  const getZ = () => page.evaluate(() => window.earth3d.getCameraZ());
  console.log('initial:', JSON.stringify(await getDbg()));
  await page.evaluate(() => window.earth3d.transitionToComposition('homeGlobe', { duration: 3, envelope: 'easeInOutCubic' }));
  await sleep(1000); console.log('t=1s (transitioning):', JSON.stringify(await getDbg()), 'z=', (await getZ()).toFixed(3));
  await sleep(3000); console.log('t=4s (settled):', JSON.stringify(await getDbg()), 'z=', (await getZ()).toFixed(3));
  await page.evaluate(() => window.earth3d.setGramPrimitive('breathe'));
  await sleep(2000); console.log('breathe set, t=6s:', JSON.stringify(await getDbg()), 'z=', (await getZ()).toFixed(3));
  await sleep(5000); console.log('breathe t=11s:', JSON.stringify(await getDbg()), 'z=', (await getZ()).toFixed(3));
  await browser.close();
})();
