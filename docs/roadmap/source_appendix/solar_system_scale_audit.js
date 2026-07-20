// 太阳系统一距离比例尺 —— 已审计确定，不是拍脑袋
// 约束依据：deepSpace相机距地心80.01单位，FOV 28°，半FOV14°，硬上限=80.01*tan(14°)=19.95单位
// 安全上限 = 硬上限*0.9 = 17.95单位（留边界，避免像HUD版本那样跑出视锥外）
// 输入：每个天体"典型地球距离"（内行星/外行星near-far几何平均，不是直接拿日心半长轴，
//       因为拿半长轴当地心距离会让水星显得比真实更近，这是审计时specifically排除的陷阱）

const MOON_DIST = 3              // 锚点，沿用#52已验证值（截图确认好看，不要改）
const SAFE_MAX_DIST = 17.95      // Pluto目标距离，= deepSpace视锥硬上限19.95的90%

const TYPICAL_EARTH_DIST_AU = {
  Moon: 0.00257,
  Venus: 0.6908797145583455,
  Mercury: 0.9220797145583455,
  Sun: 1.0,
  Mars: 1.1500330430035477,
  Jupiter: 5.105997356051019,
  Saturn: 9.484427710726674,
  Uranus: 19.16492841103248,
  Neptune: 30.052366978326347,
  Pluto: 39.4693339695516,
}

const logMoon = Math.log10(TYPICAL_EARTH_DIST_AU.Moon)
const logPluto = Math.log10(TYPICAL_EARTH_DIST_AU.Pluto)
const slope = (SAFE_MAX_DIST - MOON_DIST) / (logPluto - logMoon)

function compressToSceneDist(auDist) {
  return MOON_DIST + slope * (Math.log10(auDist) - logMoon)
}

// 验证：跑出来应该跟审计报告一致 —— Venus 11.68 / Mercury 12.13 / Sun 12.25 /
// Mars 12.47 / Jupiter 14.78 / Saturn 15.74 / Uranus 16.83 / Neptune 17.53 / Pluto 17.95
for (const [name, au] of Object.entries(TYPICAL_EARTH_DIST_AU)) {
  console.log(name, '→', compressToSceneDist(au).toFixed(2), '场景单位')
}

module.exports = { compressToSceneDist, TYPICAL_EARTH_DIST_AU, MOON_DIST, SAFE_MAX_DIST }
