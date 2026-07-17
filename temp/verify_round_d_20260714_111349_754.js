const { chromium } = require('playwright');

const BASE = 'http://localhost:8080/index.html';
const OUT = '/Users/rw-mac/Projects/RodiO/screenshots';
const fs = require('fs');
fs.mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));

  await page.goto(BASE + '?earthCandidate=cameraGrammarV1', { waitUntil: 'networkidle' });
  await sleep(3500);

  const getVS = () => page.evaluate(() => {
    const vs = window.__rodioVisualState || {};
    return { rollDeg: vs._gramRollDeg, rollOffset: vs._gramRollOffset, latOffset: vs._gramLatOffset, lonOffset: vs._gramLonOffset };
  });
  const getZ = () => page.evaluate(() => window.earth3d.getCameraZ());
  const setPrim = (k) => page.evaluate((kk) => window.earth3d.setGramPrimitive(kk), k);
  const transTo = (k) => page.evaluate((kk) => window.earth3d.transitionToComposition(kk, { duration: 3, envelope: 'easeInOutCubic' }), k);

  // ---- 1. deepSpace screenshot ----
  await transTo('deepSpace');
  await sleep(4000);
  await page.screenshot({ path: OUT + '/roundD_deepSpace.png' });
  console.log('deepSpace z =', await getZ());

  // ---- 2. breathe: z over time ----
  await transTo('homeGlobe');
  await sleep(4000);
  await setPrim('breathe');
  await sleep(2000);
  const breatheSamples = [];
  for (let i = 0; i < 14; i++) {
    breatheSamples.push({ t: +(i * 2.5).toFixed(1), z: +(await getZ()).toFixed(4) });
    await sleep(2500);
  }
  console.log('BREATHE z:', JSON.stringify(breatheSamples));
  for (let i = 0; i < 4; i++) { await page.screenshot({ path: OUT + `/roundD_breathe_${i}.png` }); await sleep(3000); }

  // ---- 3. rollDrift homeGlobe (base 0) ----
  await transTo('homeGlobe');
  await sleep(4000);
  await setPrim('rollDrift');
  const homeRoll = [];
  for (let i = 0; i < 8; i++) {
    const vs = await getVS();
    homeRoll.push({ t: i * 3, rollDeg: vs.rollDeg, rollOffset: +vs.rollOffset.toFixed(3), total: +((vs.rollDeg||0)+(vs.rollOffset||0)).toFixed(3) });
    await sleep(3000);
  }
  console.log('ROLLDRIFT homeGlobe (base 0):', JSON.stringify(homeRoll));

  // ---- 4. rollDrift polarDiagonal (base 10) ----
  await transTo('polarDiagonal');
  await sleep(4000);
  await setPrim('rollDrift');
  const polarRoll = [];
  for (let i = 0; i < 8; i++) {
    const vs = await getVS();
    polarRoll.push({ t: i * 3, rollDeg: vs.rollDeg, rollOffset: +vs.rollOffset.toFixed(3), total: +((vs.rollDeg||0)+(vs.rollOffset||0)).toFixed(3) });
    await sleep(3000);
  }
  console.log('ROLLDRIFT polarDiagonal (base 10):', JSON.stringify(polarRoll));

  // ---- 5. breathe NOT active during transition ----
  await setPrim('breathe');
  await sleep(2000);
  await transTo('farOrbit'); // 3s transition
  const transSamples = [];
  for (let i = 0; i < 8; i++) {
    const vs = await getVS();
    transSamples.push({ t: +(i * 0.5).toFixed(1), z: +(await getZ()).toFixed(4), rollOffset: vs.rollOffset });
    await sleep(500);
  }
  await page.screenshot({ path: OUT + '/roundD_transition_breathe.png' });
  console.log('TRANSITION (breathe active) z:', JSON.stringify(transSamples));

  console.log('CONSOLE ERRORS:', JSON.stringify(errors));
  await browser.close();
})().catch(e => { console.error('SCRIPT ERROR:', e); process.exit(1); });
