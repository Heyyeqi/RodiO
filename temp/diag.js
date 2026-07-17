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
  const diag = await page.evaluate(() => {
    const vs = window.__rodioVisualState || {};
    return {
      hasEarth3d: typeof window.earth3d,
      gramEnabled: vs._gramMotionEnabled,
      activePrim: window.earth3d ? window.earth3d.getDebugState ? 'hasGetDebugState' : 'no' : null,
      vsKeys: Object.keys(vs),
      latOffset: vs._gramLatOffset,
      lonOffset: vs._gramLonOffset,
      rollOffset: vs._gramRollOffset,
    };
  });
  console.log('DIAG:', JSON.stringify(diag, null, 2));
  // try setGramPrimitive and check return
  const ret = await page.evaluate(() => window.earth3d.setGramPrimitive('rollDrift'));
  console.log('setGramPrimitive rollDrift returned:', ret);
  await sleep(2000);
  const after = await page.evaluate(() => {
    const vs = window.__rodioVisualState || {};
    return { rollOffset: vs._gramRollOffset, latOffset: vs._gramLatOffset };
  });
  console.log('after 2s:', JSON.stringify(after));
  console.log('LOGS:', JSON.stringify(logs.slice(0,20)));
  await browser.close();
})();
