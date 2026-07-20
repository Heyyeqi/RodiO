'use strict';
/*
 * run_pipeline.js — per-pixel proof that the REAL water_params_reference.js
 * deriveWaterParams() runs on a downloaded ocean-color grid.
 *
 * Loads grid_inputs.json (produced by prep_grid.py from a real satellite
 * NetCDF), calls deriveWaterParams() for every valid pixel, and writes:
 *   colorfield.json  — per-pixel baseColorDeep [r,g,b] 0..1
 *   proof_stats.json — coverage + range stats
 */
const fs = require('fs');
const path = require('path');
const { deriveWaterParams } = require('/Users/rw-mac/Projects/RodiO/docs/roadmap/source_appendix/water_params_reference.js');

const grid = JSON.parse(fs.readFileSync(path.join(__dirname, 'grid_inputs.json'), 'utf8'));
const { W, H, chl, spm, kd490, n_valid } = grid;

const rgb = [];          // flat per-pixel baseColorDeep [r,g,b]
let processed = 0;
const hueHist = {};      // bucket hue 0..360 by 15deg
let clearN = 0, turbidN = 0;
let hueMin = 999, hueMax = -999;

for (let i = 0; i < H; i++) {
  rgb[i] = [];
  for (let j = 0; j < W; j++) {
    const c = chl[i][j], k = kd490[i][j];
    if (c == null || k == null) { rgb[i][j] = null; continue; }
    const s = (spm[i][j] != null) ? spm[i][j] : 0.1;
    const p = deriveWaterParams({ chl: c, spm: s, kd490: k, wind: 5 });
    rgb[i][j] = p.baseColorDeep;
    processed++;
    const h = p._meta.hueDeg;
    hueMin = Math.min(hueMin, h); hueMax = Math.max(hueMax, h);
    const bucket = Math.floor(h / 15) * 15;
    hueHist[bucket] = (hueHist[bucket] || 0) + 1;
    if (p.clarity > 0.6) clearN++; else if (p.turbidity > 0.3) turbidN++;
  }
}

fs.writeFileSync(path.join(__dirname, 'colorfield.json'),
  JSON.stringify({ W, H, rgb, lat0: grid.lat0, lat1: grid.lat1, lon0: grid.lon0, lon1: grid.lon1 }));

const stats = {
  W, H, n_valid, processed,
  hueRange: { min: Math.round(hueMin * 10) / 10, max: Math.round(hueMax * 10) / 10 },
  clearPixels: clearN, turbidPixels: turbidN,
  hueHist,
  source: grid.source,
  provenance: grid.provenance,
};
fs.writeFileSync(path.join(__dirname, 'proof_stats.json'), JSON.stringify(stats, null, 2));

console.log(`PER-PIXEL RUN COMPLETE`);
console.log(`  grid            : ${W} x ${H}`);
console.log(`  valid pixels    : ${n_valid}`);
console.log(`  deriveWaterParams calls: ${processed}`);
console.log(`  hue range (deg) : ${stats.hueRange.min} .. ${stats.hueRange.max}`);
console.log(`  clear/clarity>0.6 : ${clearN}   turbid>0.3 : ${turbidN}`);
console.log(`  wrote colorfield.json + proof_stats.json`);
