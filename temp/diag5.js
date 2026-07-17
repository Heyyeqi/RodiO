const { chromium } = require('playwright');
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('http://localhost:8080/index.html?earthCandidate=cameraGrammarV1', { waitUntil: 'networkidle' });
  await sleep(4000);
  const pre = await page.evaluate(() => { const vs=window.__rodioVisualState||{}; return {preZ: vs._precomputeTargetZ, preFov: vs._precomputeTargetFov, preLon: vs._precomputeLonOffset}; });
  console.log('precompute state:', JSON.stringify(pre));
  await browser.close();
})();
