const { chromium } = require('playwright');

const BASE = 'http://localhost:8080/pwa/index.html';
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
  await sleep(3000); // let activation + initial transition settle

  // helper to read visual state
  const getVS = () => page.evaluate(() => {
    const vs = window.__rodioVisualState || {};
    return {
      rollDeg: vs._gramRollDeg,
      rollOffset: vs._gramRollOffset,
      latOffset: vs._gramLatOffset,
      lonOffset: vs._gramLonOffset,
    };
  });
  const getZ = () => page.evaluate(() => {
    // camera is inside closure; expose via e3d if available
    return window.__rodioCameraZ ?? null;
  });

  // We need camera.position.z. Try to grab from a global hook if present.
  const getCamZ = () => page.evaluate(() => {
    if (window.__e3d && window.__e3d._camera) return window.__e3d._camera.position.z;
    return null;
  });

  // ---- 1. deepSpace screenshot ----
  await page.evaluate(() => {
    const vs = window.__rodioVisualState;
    window.e3d && window.e3d.transitionToComposition && window.e3d.transitionToComposition('deepSpace', { duration: 3, envelope: 'easeInOutCubic' });
  });
  await sleep(4000); // transition done
  await page.screenshot({ path: OUT + '/roundD_deepSpace.png' });
  const dsZ = await getCamZ();
  console.log('deepSpace settled camera.position.z =', dsZ);

  // ---- 2. breathe: record z over time ----
  await page.evaluate(() => {
    window.e3d && window.e3d.transitionToComposition && window.e3d.transitionToComposition('homeGlobe', { duration: 3, envelope: 'easeInOutCubic' });
  });
  await sleep(4000);
  await page.evaluate(() => window.e3d && window.e3d.setGramPrimitive && window.e3d.setGramPrimitive('breathe'));
  const breatheSamples = [];
  for (let i = 0; i < 12; i++) {
    const z = await getCamZ();
    breatheSamples.push({ t: i * 2.5, z });
    await sleep(2500);
  }
  console.log('BREATHE z samples:', JSON.stringify(breatheSamples));

  // ---- 3. rollDrift homeGlobe (base 0) ----
  await page.evaluate(() => {
    window.e3d && window.e3d.transitionToComposition && window.e3d.transitionToComposition('homeGlobe', { duration: 3, envelope: 'easeInOutCubic' });
  });
  await sleep(4000);
  await page.evaluate(() => window.e3d && window.e3d.setGramPrimitive && window.e3d.setGramPrimitive('rollDrift'));
  const homeRoll = [];
  for (let i = 0; i < 8; i++) {
    const vs = await getVS();
    homeRoll.push({ t: i * 3, rollDeg: vs.rollDeg, rollOffset: vs.rollOffset, total: (vs.rollDeg||0)+(vs.rollOffset||0) });
    await sleep(3000);
  }
  console.log('ROLLDRIFT homeGlobe (base 0):', JSON.stringify(homeRoll));

  // ---- 4. rollDrift polarDiagonal (base 10) ----
  await page.evaluate(() => {
    window.e3d && window.e3d.transitionToComposition && window.e3d.transitionToComposition('polarDiagonal', { duration: 3, envelope: 'easeInOutCubic' });
  });
  await sleep(4000);
  await page.evaluate(() => window.e3d && window.e3d.setGramPrimitive && window.e3d.setGramPrimitive('rollDrift'));
  const polarRoll = [];
  for (let i = 0; i < 8; i++) {
    const vs = await getVS();
    polarRoll.push({ t: i * 3, rollDeg: vs.rollDeg, rollOffset: vs.rollOffset, total: (vs.rollDeg||0)+(vs.rollOffset||0) });
    await sleep(3000);
  }
  console.log('ROLLDRIFT polarDiagonal (base 10):', JSON.stringify(polarRoll));

  // ---- 5. breathe NOT active during transition ----
  // switch to a composition while breathe is the active primitive, sample z during transition
  await page.evaluate(() => {
    window.e3d && window.e3d.transitionToComposition && window.e3d.transitionToComposition('homeGlobe', { duration: 3, envelope: 'easeInOutCubic' });
  });
  await sleep(4000);
  await page.evaluate(() => window.e3d && window.e3d.setGramPrimitive && window.e3d.setGramPrimitive('breathe'));
  await sleep(2000); // let breathe settle
  // now trigger a transition and sample z rapidly during it
  await page.evaluate(() => {
    window.e3d && window.e3d.transitionToComposition && window.e3d.transitionToComposition('farOrbit', { duration: 4, envelope: 'easeInOutCubic' });
  });
  const transSamples = [];
  for (let i = 0; i < 10; i++) {
    const z = await getCamZ();
    transSamples.push({ t: i * 0.5, z });
    await sleep(500);
  }
  console.log('TRANSITION (breathe active) z samples:', JSON.stringify(transSamples));

  console.log('CONSOLE ERRORS:', JSON.stringify(errors));
  await browser.close();
})().catch(e => { console.error('SCRIPT ERROR:', e); process.exit(1); });
