'use strict';
/*
 * water_params_reference.js
 * Horizon Mode 水质系统 v2 — 数据驱动参考实现（无依赖，CommonJS）
 *
 * 管线: (CHL, SPM, ZSD/KD490, CDM, wind)  ->  4项IOPs  ->  9维
 *   CHL  -> a_phy    (浮游植物吸收)
 *   SPM  -> b_bp     (颗粒后向散射) + a_det (碎屑吸收)
 *   CDM  -> a_cdom   (有色溶解有机物吸收)
 *   ZSD/KD490 -> clarity / depthColorFalloff
 *   wind -> surfaceRoughness / foamCoverage
 *   CHL异常/CDM -> colorTint (藻华/河流染色)
 *
 * 颜色维度统一经 OKLab: sRGB(设计值) -> linear -> OKLab; 深度渐变在 OKLab 内插值; 输出 OKLab -> linear -> sRGB
 */

// ── 纯水 IOPs (Pope & Fry 1997, 15C/35psu; 单位 m^-1) ──
const A_WATER = { 443: 0.0064, 490: 0.0085, 510: 0.0098, 555: 0.0134, 650: 0.0345 };
const BB_WATER = { 443: 0.0017, 490: 0.0014, 510: 0.0013, 555: 0.0011, 650: 0.0008 };
const WL = [443, 490, 510, 555, 650];
// RGB 波段近似
const RGB = { r: 650, g: 555, b: 490 };

// ── sRGB <-> linear ──
function s2l(c) { return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
function l2s(c) { return c <= 0.0031308 ? c * 12.92 : 1.055 * Math.pow(c, 1 / 2.4) - 0.055; }

// ── linear RGB <-> OKLab (Björn Ottosson) ──
function linToOKLab(r, g, b) {
  const l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b;
  const m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b;
  const s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b;
  const lc = Math.cbrt(l), mc = Math.cbrt(m), sc = Math.cbrt(s);
  return {
    L: 0.2104542553 * lc + 0.7936177850 * mc - 0.0040720468 * sc,
    a: 1.9779984951 * lc - 2.4285922050 * mc + 0.4505937099 * sc,
    b: 0.0259040371 * lc + 0.7827717662 * mc - 0.8086757660 * sc,
  };
}
function oklabToLin(L, a, b) {
  const lc = L + 0.3963377774 * a + 0.2158037573 * b;
  const mc = L - 0.1055613458 * a - 0.0638541728 * b;
  const sc = L - 0.0894841775 * a - 1.2914855480 * b;
  const l = lc * lc * lc, m = mc * mc * mc, s = sc * sc * sc;
  return {
    r: 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    g: -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    b: -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
  };
}
function oklch(L, C, hDeg) {
  const h = hDeg * Math.PI / 180;
  return oklabToLin(L, C * Math.cos(h), C * Math.sin(h));
}
function oklabToOklch(L, a, b) {
  const C = Math.sqrt(a * a + b * b);
  let h = Math.atan2(b, a) * 180 / Math.PI;
  if (h < 0) h += 360;
  return { L, C, h };
}

// ── 4项 IOPs ──
function computeIOPs(inp) {
  const chl = Math.max(inp.chl || 0, 1e-4);   // mg/m3
  const spm = Math.max(inp.spm || 0, 1e-4);   // g/m3
  const a = {}, bb = {};
  // 浮游植物吸收: Bricaud 1998: a_phy(443)=0.06*CHL^0.65
  const aPhy443 = 0.06 * Math.pow(chl, 0.65);
  // CDOM 吸收: 缺省从 CHL/SPM 经验估计; 若直接给 cdm(a_cdom@440) 则优先
  const aCdom440 = (inp.cdm != null) ? inp.cdm
    : 0.01 * Math.pow(chl, 0.5) + 0.01 * Math.pow(spm, 0.6);
  // 碎屑吸收: 随 SPM
  const aDet440 = 0.02 * Math.pow(spm, 0.7);
  // 颗粒后向散射: 随 SPM (Morel/Maritorena 量级)
  const bbP555 = 0.0025 * Math.pow(spm, 0.9);
  for (const wl of WL) {
    const aPhy = aPhy443 * Math.exp(-0.015 * (wl - 443));
    const aCdom = aCdom440 * Math.exp(-0.014 * (wl - 440));
    const aDet = aDet440 * Math.exp(-0.011 * (wl - 440));
    const bbP = bbP555 * Math.pow(555 / wl, 0.8);
    a[wl] = A_WATER[wl] + aPhy + aCdom + aDet;
    bb[wl] = BB_WATER[wl] + bbP;
  }
  return { a, bb, aPhy443, aCdom440, aDet440, bbP555 };
}

// 深水表观反射率 (Lee QAA: Rrs ≈ f*bb/(a+bb), f≈0.33)
function deepReflectance(iops) {
  const f = 0.33;
  return {
    r: f * iops.bb[RGB.r] / (iops.a[RGB.r] + iops.bb[RGB.r]),
    g: f * iops.bb[RGB.g] / (iops.a[RGB.g] + iops.bb[RGB.g]),
    b: f * iops.bb[RGB.b] / (iops.a[RGB.b] + iops.bb[RGB.b]),
  };
}

// ── 主入口 ──
function deriveWaterParams(inp) {
  const iops = computeIOPs(inp);
  const rr = deepReflectance(iops);
  // 归一化到 RGB chromaticity (linear)
  const mx = Math.max(rr.r, rr.g, rr.b, 1e-6);
  const lin = { r: rr.r / mx, g: rr.g / mx, b: rr.b / mx };
  const ok = linToOKLab(lin.r, lin.g, lin.b);
  const hue = oklabToOklch(ok.L, ok.a, ok.b); // 物理锚定的色相

  // 透明度: ZSD 优先, 否则由 KD490 反推 (ZSD≈1.7/KD490)
  let zsd = inp.zsd;
  if (zsd == null && inp.kd490 != null) zsd = 1.7 / Math.max(inp.kd490, 0.005);
  const clarity = clamp(zsd != null ? zsd / (zsd + 8) : 0.5, 0, 1);

  // 浑浊度: SPM 驱动
  const spm = Math.max(inp.spm || 0, 0);
  const turbidity = clamp(1 - Math.exp(-spm / 18), 0, 1);

  // 深度衰减: KD490 -> falloff
  const kd = inp.kd490 != null ? inp.kd490 : (zsd != null ? 1.7 / zsd : 0.1);
  const depthColorFalloff = clamp(0.4 + (kd - 0.02) * 2.4, 0.3, 2.5);

  // 风力 -> 粗糙度 / 泡沫
  const wind = inp.wind != null ? inp.wind : 5;
  const surfaceRoughness = clamp((wind - 2) / 16, 0, 1);
  const foamCoverage = clamp((wind - 7) / 13 * 0.42, 0, 0.42);

  // 深水色: 物理色相 + 艺术亮度曲线 (清晰->深饱和蓝; 浑浊->亮乳白)
  // 注意: 物理 Rrs 给出的是"反射率亮度"而非"感知水深色"; 感知深蓝色远大于反射率,
  // 故 L 用与 murk 解耦的曲线, 由常数锚定到真实视觉(清澈外海 L≈0.45 深蓝, 极浊 L≈0.72 乳白)
  const murk = 0.7 * turbidity + 0.3 * (1 - clarity);
  const Ldeep = clamp(0.45 + 0.27 * murk, 0.18, 0.82);
  const Cdeep = clamp(hue.C * 0.85 + 0.06, 0.04, 0.28);
  const deepLin = oklch(Ldeep, Cdeep, hue.h);
  const baseColorDeep = [l2s(clamp(deepLin.r, 0, 1)), l2s(clamp(deepLin.g, 0, 1)), l2s(clamp(deepLin.b, 0, 1))];

  // 浅水色: 深水色提亮 + 底质渗透
  const sub = inp.substrateColor
    ? inp.substrateColor
    : inferSubstrate(spm, clarity);
  const Lshallow = clamp(Ldeep + 0.22 + 0.18 * clarity, 0.2, 0.92);
  const shallowLin = oklch(Lshallow, Cdeep * 0.9 + 0.02, hue.h);
  let baseColorShallow = [l2s(clamp(shallowLin.r, 0, 1)), l2s(clamp(shallowLin.g, 0, 1)), l2s(clamp(shallowLin.b, 0, 1))];
  // 底质渗透: clarity 高时浅水区显底质色
  const subVis = clarity * 0.5;
  baseColorShallow = baseColorShallow.map((c, i) => clamp(c * (1 - subVis) + sub[i] * subVis, 0, 1));

  // colorTint: 藻华/河流染色
  const colorTint = computeTint(inp.chl || 0, iops.aCdom440, spm);

  return {
    clarity: round2(clarity),
    turbidity: round2(turbidity),
    baseColorDeep: r3(baseColorDeep),
    baseColorShallow: r3(baseColorShallow),
    substrateColor: r3(sub),
    depthColorFalloff: round2(depthColorFalloff),
    surfaceRoughness: round2(surfaceRoughness),
    foamCoverage: round2(foamCoverage),
    colorTint: r3(colorTint),
    _meta: { zsd: round2(zsd), kd490: round2(kd), hueDeg: round1(hue.h), hueChroma: round3(hue.C), wind },
  };
}

function computeTint(chl, aCdom440, spm) {
  let t = [1, 1, 1];
  const baseline = 0.3;
  // 只有"浮游植物主导"(spm 相对低)才判为藻华; 高 SPM 的河口褐变已编码在 baseColorDeep 里
  const phytoDominant = chl > 1 && spm < 10 * chl;
  if (phytoDominant) {
    const bloom = clamp((chl - baseline) / baseline, 0, 3);
    if (chl > 3) { // 强藻华: 绿推
      t = [1 - 0.03 * bloom, 1 + 0.10 * bloom, 1 - 0.05 * bloom];
    } else { // 轻藻华
      t = [1 - 0.01 * bloom, 1 + 0.06 * bloom, 1 - 0.02 * bloom];
    }
  } else if (aCdom440 > 0.5) { // 河流 CDOM 强染色(非浮游植物主导): 棕调
    const k = clamp((aCdom440 - 0.5) * 0.3, 0, 0.22);
    t = [1 + k, 1 - 0.04 * k, 1 - 0.14 * k];
  }
  return t.map(v => round3(clamp(v, 0.5, 1.5)));
}

function inferSubstrate(spm, clarity) {
  if (spm > 5) return [0.50, 0.42, 0.25];      // 淤泥/细沙
  if (clarity > 0.75) return [0.95, 0.88, 0.72]; // 白沙/珊瑚砂
  return [0.28, 0.32, 0.36];                    // 灰岩/砾石
}

function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }
function round1(x) { return Math.round(x * 10) / 10; }
function round2(x) { return Math.round(x * 100) / 100; }
function round3(x) { return Math.round(x * 1000) / 1000; }
function r3(a) { return a.map(round3); }

// ── 验证: 已知真实站位 ──
const STATIONS = [
  { name: 'S1 远洋寡营养(南太平洋)', chl: 0.05, spm: 0.1, zsd: 30, kd490: 0.03, wind: 4, substrateColor: [0.12, 0.14, 0.18], v1: 'P2' },
  { name: 'S2 热带珊瑚礁(马尔代夫)', chl: 0.04, spm: 0.02, zsd: 35, kd490: 0.025, wind: 3, substrateColor: [0.95, 0.88, 0.72], v1: 'P1' },
  { name: 'S3 温带开阔(北大西洋)', chl: 0.2, spm: 0.3, zsd: 18, kd490: 0.08, wind: 8, substrateColor: [0.20, 0.24, 0.28], v1: 'P3' },
  { name: 'S4 长江口浑浊', chl: 5, spm: 200, zsd: 0.5, kd490: 2.5, wind: 6, substrateColor: [0.50, 0.42, 0.25], v1: 'P4' },
  { name: 'S5 波罗的海藻华', chl: 12, spm: 2, zsd: 3, kd490: 0.6, wind: 7, substrateColor: [0.38, 0.40, 0.28], v1: 'P7/P11' },
];

function runValidation() {
  const out = [];
  for (const s of STATIONS) {
    const p = deriveWaterParams(s);
    out.push({ station: s.name, v1_target: s.v1, params: p });
  }
  return out;
}

if (require.main === module) {
  const res = runValidation();
  for (const r of res) {
    const p = r.params;
    console.log(`\n=== ${r.station}  (对标 v1 ${r.v1_target}) ===`);
    console.log(`  clarity=${p.clarity}  turbidity=${p.turbidity}  falloff=${p.depthColorFalloff}  rough=${p.surfaceRoughness}  foam=${p.foamCoverage}`);
    console.log(`  baseColorDeep   = [${p.baseColorDeep}]   hue=${p._meta.hueDeg}°  C=${p._meta.hueChroma}`);
    console.log(`  baseColorShallow= [${p.baseColorShallow}]`);
    console.log(`  substrateColor  = [${p.substrateColor}]`);
    console.log(`  colorTint       = [${p.colorTint}]`);
  }
  require('fs').writeFileSync('/tmp/rodio_assets/water_validation.json', JSON.stringify(res, null, 2));
  console.log('\n[written] /tmp/rodio_assets/water_validation.json');
}

module.exports = { deriveWaterParams, computeIOPs, deepReflectance, linToOKLab, oklabToLin, runValidation };
