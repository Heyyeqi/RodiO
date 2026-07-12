// 共享 transition_cost 计算模块（Phase 1 step 4 / step 5 / candidate-rerank 共用）
//
// 五维度加权公式，权重和 = 1，故 sum(|差值| * 权重) 即为最终值。
// 输入为两个 track_profile 行对象（含 energy/brightness/density/
// vocal_presence/emotional_weight 五个字段）。任一对象缺失或字段缺失
// 时返回 null（调用方自行决定中性值，不强行用 0 凑）。

const WEIGHTS = {
  energy: 0.30,
  brightness: 0.20,
  density: 0.15,
  vocal_presence: 0.15,
  emotional_weight: 0.20,
}

const FIELDS = ['energy', 'brightness', 'density', 'vocal_presence', 'emotional_weight']

function transitionCost(a, b) {
  if (!a || !b) return null
  const allValid = FIELDS.every(
    f => a[f] !== null && a[f] !== undefined && b[f] !== null && b[f] !== undefined
  )
  if (!allValid) return null
  let sum = 0
  for (const f of FIELDS) {
    sum += Math.abs(a[f] - b[f]) * WEIGHTS[f]
  }
  return sum
}

module.exports = { transitionCost, WEIGHTS, FIELDS }
