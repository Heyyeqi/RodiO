// Phase 1 step 5 — 路径 B shadow mode 影子召回（纯观测）
//
// 在真实路径 B 补货（fillQueueFromSpotifyPlaylists）完成后，另起一个
// fire-and-forget 的异步调用，跑在 track_profile 数据上，计算一组"影子候选"，
// 记录候选数量与真实选中结果的重合度。
//
// 硬性约束：
//   - 绝不修改 fillQueueFromSpotifyPlaylists 的返回值或任何真实队列内容
//   - 调用方不得 await 本函数（fire-and-forget），且必须 .catch(()=>{}) 兜底
//   - 本模块内部整体包 try/catch，任何报错都不影响真实补货流程

const state = require('./state')
const { transitionCost } = require('./transition-cost')

// 归一化 key：与 filterQueueCandidates 中 recentPlays 比对保持一致
// recentPlays 用 `${song_name}::${artist}`.toLowerCase()
function recentPlayKey(play) {
  const name = String(play?.song_name || play?.name || '').trim().toLowerCase()
  const artist = String(play?.artist || '').trim().toLowerCase()
  return `${name}::${artist}`
}

// spotifyItems 中每首的 key：与 queueKeyFromItem 保持一致
function itemKey(item) {
  const name = String(item?.song_info?.name || '').trim().toLowerCase()
  const artist = String(item?.song_info?.artist || '').trim().toLowerCase()
  return `${name}::${artist}`
}

/**
 * 运行影子召回观测。
 * @param {string} reason 补货原因（透传自 setRefillHandler）
 * @param {Array}  spotifyItems 真实路径 B 选中的曲目（fillQueueFromSpotifyPlaylists 返回值）
 * @param {string|null} queueFirstTrackKey 当前队列第一首的 track_key（归一化 key），无则 null
 * @returns {Promise<void>} 仅写入 shadow_recall_log，不返回任何业务值
 */
async function runShadowRecall(reason, spotifyItems, queueFirstTrackKey) {
  try {
    // 1. 影子候选来源：track_profile 全部行
    const profiles = state.getAllTrackProfiles()
    if (!Array.isArray(profiles)) return

    // 2. 过滤条件 1：排除最近播放过的（getRecentPlays(50) 归一化比对）
    const recentPlays = state.getRecentPlays(50)
    const recentKeys = new Set(recentPlays.map(recentPlayKey).filter(Boolean))

    let candidates = profiles.filter(p => {
      const key = String(p.track_key || '').toLowerCase()
      return key && !recentKeys.has(key)
    })

    // 3. 过滤条件 2：transition_cost ≤ 0.35（以队列第一首为参照）
    if (queueFirstTrackKey) {
      const ref = state.getTrackProfile(queueFirstTrackKey)
      if (ref) {
        candidates = candidates.filter(c => {
          const cost = transitionCost(ref, c)
          // 任一字段缺失导致 cost 为 null 时，保留（不强行用 0 凑）
          if (cost === null) return true
          return cost <= 0.35
        })
      }
      // ref 不在 track_profile 里 → 跳过该过滤条件（保留全部候选）
    }
    // queueFirstTrackKey 为 null → 跳过该过滤条件

    const shadowCandidateCount = candidates.length

    // 4. 统计重合度：影子候选与真实 spotifyItems 选中曲目的归一化 key 比对
    const realKeys = new Set((Array.isArray(spotifyItems) ? spotifyItems : []).map(itemKey).filter(Boolean))
    const overlapCount = candidates.filter(c => realKeys.has(String(c.track_key || '').toLowerCase())).length

    const realCount = Array.isArray(spotifyItems) ? spotifyItems.length : 0

    // 5. 写入观测日志
    state.insertShadowRecallLog(reason, realCount, shadowCandidateCount, overlapCount)
  } catch (err) {
    // 任何内部错误都吞掉，绝不影响真实补货
    console.error('[shadow-recall] 观测计算异常（已忽略，不影响真实队列）:', err?.message || err)
  }
}

module.exports = { runShadowRecall }
