'use strict';
/*
 * run_pipeline_real.js — per-pixel proof on the REAL downloaded Copernicus grid.
 * Loads inputs.bin (float32 [H*W*4]: chl,spm,kd490,cdm; NaN=invalid) produced by
 * prep_copernicus.py, calls the REAL docs/roadmap/source_appendix/water_params_reference.js
 * deriveWaterParams() for every valid pixel, and writes:
 *   color_rgba.bin   uint8 [H*W*4] RGBA (A=255 valid, 0 invalid/land/cloud)
 *   pipeline_stats.json  coverage + hue range + validation-point samples
 */
const fs = require('fs');
const path = require('path');
const { deriveWaterParams } = require('/Users/rw-mac/Projects/RodiO/docs/roadmap/source_appendix/water_params_reference.js');

const DIR = '/Users/rw-mac/Projects/RodiO/temp/ocean_color_real';
const meta = JSON.parse(fs.readFileSync(path.join(DIR, 'grid_meta.json'), 'utf8'));
const { W, H } = meta;
const buf = fs.readFileSync(path.join(DIR, 'inputs.bin'));
const f32 = new Float32Array(buf.buffer, buf.byteOffset, buf.length / 4);

const rgba = new Uint8Array(H * W * 4);
let processed = 0;
let hueMin = 999, hueMax = -999;
const hueHist = {};
let clearN = 0, turbidN = 0;

const NAN = (x) => Number.isNaN(x);

for (let i = 0; i < H; i++) {
  for (let j = 0; j < W; j++) {
    const p = (i * W + j) * 4;
    const chl = f32[p], spm = f32[p + 1], kd = f32[p + 2], cdm = f32[p + 3];
    const out = (i * W + j) * 4;
    if (NAN(chl) || NAN(kd)) { rgba[out + 3] = 0; continue; }   // land/cloud/masked -> transparent
    const p0 = deriveWaterParams({ chl, spm, kd490: kd, cdm, wind: 5 });
    const c = p0.baseColorDeep;
    rgba[out]     = Math.round(Math.max(0, Math.min(1, c[0])) * 255);
    rgba[out + 1] = Math.round(Math.max(0, Math.min(1, c[1])) * 255);
    rgba[out + 2] = Math.round(Math.max(0, Math.min(1, c[2])) * 255);
    rgba[out + 3] = 255;
    processed++;
    const h = p0._meta.hueDeg;
    hueMin = Math.min(hueMin, h); hueMax = Math.max(hueMax, h);
    const bucket = Math.floor(h / 15) * 15;
    hueHist[bucket] = (hueHist[bucket] || 0) + 1;
    if (p0.clarity > 0.6) clearN++; else if (p0.turbidity > 0.3) turbidN++;
  }
}

fs.writeFileSync(path.join(DIR, 'color_rgba.bin'), Buffer.from(rgba.buffer));

// ---- validation point sampling (lat, lon -> pixel) ----
function sampleAt(lat, lon) {
  const j = Math.round((lon + 180) / 360 * W - 0.5);
  const i = Math.round((90 - lat) / 180 * H - 0.5);
  const p = (Math.max(0, Math.min(H - 1, i)) * W + Math.max(0, Math.min(W - 1, j))) * 4;
  const ok = rgba[p + 3] === 255;
  return ok ? { r: rgba[p], g: rgba[p + 1], b: rgba[p + 2],
                hex: '#' + [rgba[p], rgba[p + 1], rgba[p + 2]].map(x => x.toString(16).padStart(2, '0')).join('') }
           : { r: null, g: null, b: null, hex: null, note: 'invalid/masked' };
}
const points = {
  'South Pacific gyre (clear oligotrophic)':      [-25, -130],
  'Sargasso / N Atlantic gyre (clear)':           [28, -55],
  'Yangtze R. mouth (turbid estuary)':            [31.5, 122.5],
  'Amazon R. mouth (turbid estuary)':             [0, -49],
  'Benguela upwelling (productive, high CHL)':    [-25, 12],
};
const samples = {};
for (const [name, [lat, lon]] of Object.entries(points)) {
  samples[name] = { lat, lon, ...sampleAt(lat, lon) };
}

const stats = {
  W, H, n_core_valid: meta.n_core_valid, processed,
  hueRange: { min: Math.round(hueMin * 10) / 10, max: Math.round(hueMax * 10) / 10 },
  clearPixels: clearN, turbidPixels: turbidN,
  hueHist, samples, month: meta.month, sources: meta.sources,
};
fs.writeFileSync(path.join(DIR, 'pipeline_stats.json'), JSON.stringify(stats, null, 2));
console.log(`PER-PIXEL RUN COMPLETE (REAL data)`);
console.log(`  grid               : ${W} x ${H}`);
console.log(`  core valid pixels  : ${meta.n_core_valid}`);
console.log(`  deriveWaterParams  : ${processed}`);
console.log(`  hue range (deg)    : ${stats.hueRange.min} .. ${stats.hueRange.max}`);
console.log(`  clear/clarity>0.6  : ${clearN}   turbid>0.3 : ${turbidN}`);
console.log(`  wrote color_rgba.bin + pipeline_stats.json`);
