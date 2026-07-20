'use strict';
/*
 * verify_pipeline.js — 可行性验证：把真实海洋水色栅格逐像素喂给
 * docs/roadmap/source_appendix/water_params_reference.js 的 deriveWaterParams()，
 * 产出一张 "水质颜色" 纹理（Plate Carrée，可直接球面映射）。
 * 输入：sample_inputs.json  {W,H, chl:[[..]], kd490:[[..]]}  （null = 填充/陆地）
 * 输出：water_color_texture.png + water_color_stats.json
 */
const fs = require('fs');
const zlib = require('zlib');
const { deriveWaterParams } = require('/Users/rw-mac/Projects/RodiO/docs/roadmap/source_appendix/water_params_reference.js');

const inp = JSON.parse(fs.readFileSync('sample_inputs.json', 'utf8'));
const { W, H, chl, kd490 } = inp;

// ── 最小 PNG 编码器 (RGBA, 8-bit, 无过滤) ──
function crc32(buf) {
  let c, table = [];
  for (let n = 0; n < 256; n++) { c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; table[n] = c >>> 0; }
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < buf.length; i++) crc = table[(crc ^ buf[i]) & 0xFF] ^ (crc >>> 8);
  return (crc ^ 0xFFFFFFFF) >>> 0;
}
function chunk(type, data) {
  const len = Buffer.alloc(4); len.writeUInt32BE(data.length, 0);
  const t = Buffer.from(type, 'ascii');
  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(Buffer.concat([t, data])), 0);
  return Buffer.concat([len, t, data, crc]);
}
function writePNG(path, w, h, rgba) {
  const sig = Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0; // 8-bit RGBA
  const raw = Buffer.alloc((w * 4 + 1) * h);
  for (let y = 0; y < h; y++) { raw[y * (w * 4 + 1)] = 0; rgba.copy(raw, y * (w * 4 + 1) + 1, y * w * 4, (y + 1) * w * 4); }
  const idat = zlib.deflateSync(raw);
  fs.writeFileSync(path, Buffer.concat([sig, chunk('IHDR', ihdr), chunk('IDAT', idat), chunk('IEND', Buffer.alloc(0))]));
}

// ── 逐像素跑 deriveWaterParams ──
const rgba = Buffer.alloc(W * H * 4);
const stats = { nValid: 0, clarity: [], hueDeg: [], turbidity: [], depthColorFalloff: [], baseColorDeep: [] };
let nValid = 0;
for (let y = 0; y < H; y++) {
  for (let x = 0; x < W; x++) {
    const c = chl[y][x], k = kd490[y][x];
    const o = (y * W + x) * 4;
    if (c == null || k == null || !isFinite(c) || c <= 0) { rgba[o + 3] = 0; continue; } // 透明（陆地/填充）
    const p = deriveWaterParams({ chl: c, kd490: k, wind: 5 });
    const dc = p.baseColorDeep;
    rgba[o] = Math.round(dc[0] * 255);
    rgba[o + 1] = Math.round(dc[1] * 255);
    rgba[o + 2] = Math.round(dc[2] * 255);
    rgba[o + 3] = 255;
    nValid++;
    if (nValid <= 200000) { stats.clarity.push(p.clarity); stats.hueDeg.push(p._meta.hueDeg); stats.turbidity.push(p.turbidity); stats.depthColorFalloff.push(p.depthColorFalloff); stats.baseColorDeep.push(dc); }
  }
}
function q(arr) { if (!arr.length) return null; const s = arr.reduce((a, b) => a + b, 0); return { min: Math.min(...arr), max: Math.max(...arr), mean: s / arr.length }; }
const summary = {
  grid: { W, H }, nValid,
  clarity: q(stats.clarity), hueDeg: q(stats.hueDeg), turbidity: q(stats.turbidity), depthColorFalloff: q(stats.depthColorFalloff),
  provenance: 'real satellite-derived CHL (MODIS-Aqua, Zenodo 7971187) + Case-1 Kd490 (Morel & Maritorena 2001); water_params_reference.js deriveWaterParams() run per-pixel'
};
writePNG('water_color_texture.png', W, H, rgba);
fs.writeFileSync('water_color_stats.json', JSON.stringify(summary, null, 2));
console.log('[ok] valid pixels:', nValid, '/', W * H);
console.log(JSON.stringify(summary, null, 2));
