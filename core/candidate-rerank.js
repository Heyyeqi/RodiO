// Phase 1 step 6 — 候选打分模块（影子模式，纯观测）
//
// 对候选曲目计算 freshness / continuity / feedback / playability 四个维度，
// 加权混合成排序分 blended，仅写入 shadow_rerank_candidates 观测表，
// 绝不修改 fillQueueFromSpotifyPlaylists 的返回值或任何真实队列内容。
//
// 硬性约束：
//   - 绝不参与真实选曲决策
//   - 调用方必须 fire-and-forget 且 .catch(()=>{}) 兜底
//   - 本模块内部整体包 try/catch，任何报错都不影响真实补货流程

const state = require('./state')
const { transitionCost } = require('./transition-cost')
const { normalizeSongKey, normalizeArtistKey } = require('./search-utils')

// 与 READY_POOL_ROUND_SIZE 对齐，最多记录前 30 个候选
const MAX_LOG_CANDIDATES = 30

// 加权混合权重
const W_FRESHNESS = 0.40
const W_CONTINUITY = 0.30
const W_FEEDBACK = 0.20
const W_PLAYABILITY = 0.10

// 反馈分数归一化区间：raw_score ∈ [-3, 3] → score ∈ [0, 1]
const FEEDBACK_FLOOR = -3
const FEEDBACK_RANGE = 6

// freshness 对数归一化基准天数
const FRESHNESS_LOG_BASE_DAYS = 90

/**
 * 计算单个候选曲目的四维打分与混合分。
 * @param {Object} candidateSong 候选曲目对象，需含 name / artist 字段
 * @param {string|null} currentTrackKey 当前曲目归一化 track_key（作为 continuity 参照），无则 null
 * @returns {Object} 见任务定义结构
 */
function computeCandidateScore(candidateSong, currentTrackKey) {
  const name = candidateSong?.song_info?.name || candidateSong?.name
  const artist = candidateSong?.song_info?.artist || candidateSong?.artist

  // track_key 用 normalizeSongKey/normalizeArtistKey 拼接（与 play_events 表 key 匹配）
  const trackKey = `${normalizeSongKey(name)}::${normalizeArtistKey(artist)}`

  // ── freshness ──
  let freshnessRawDays = null
  let freshnessScore = 1
  const lastPlay = state.getLastPlayAt(trackKey)
  if (lastPlay) {
    const days = (Date.now() - new Date(lastPlay).getTime()) / (1000 * 60 * 60 * 24)
    freshnessRawDays = Math.max(0, days)
    freshnessScore = Math.min(1, Math.log(1 + freshnessRawDays) / Math.log(1 + FRESHNESS_LOG_BASE_DAYS))
  }

  // ── continuity ──
  let continuityRawCost = null
  let continuityScore = 0.5 // 中性值
  const candProfile = state.getTrackProfile(trackKey)
  const curProfile = currentTrackKey ? state.getTrackProfile(currentTrackKey) : null
  if (candProfile && curProfile) {
    const cost = transitionCost(candProfile, curProfile)
    if (cost !== null) {
      continuityRawCost = cost
      continuityScore = 1 - cost
    }
  }

  // ── feedback ──
  // 注意：用原始歌名/艺人名，getSongFeedbackScore 内部走自己的小写拼接方案
  const feedbackRawScore = state.getSongFeedbackScore({ name, artist })
  let feedbackExcluded = false
  let feedbackScore = 0
  if (feedbackRawScore <= FEEDBACK_FLOOR) {
    feedbackExcluded = true
    feedbackScore = 0
  } else {
    feedbackExcluded = false
    feedbackScore = Math.max(0, Math.min(1, (feedbackRawScore - FEEDBACK_FLOOR) / FEEDBACK_RANGE))
  }

  // ── playability ──
  const everPlayed = state.hasPlayEvent(trackKey)
  const playabilityScore = everPlayed ? 1 : 0

  // ── 加权混合 ──
  let blended = null
  let excluded = false
  if (feedbackExcluded) {
    blended = null
    excluded = true
  } else {
    blended =
      freshnessScore * W_FRESHNESS +
      continuityScore * W_CONTINUITY +
      feedbackScore * W_FEEDBACK +
      playabilityScore * W_PLAYABILITY
  }

  return {
    freshness: { raw_days: freshnessRawDays, score: freshnessScore },
    continuity: { raw_cost: continuityRawCost, score: continuityScore },
    feedback: { raw_score: feedbackRawScore, excluded: feedbackExcluded, score: feedbackScore },
    playability: { ever_played: everPlayed, score: playabilityScore },
    blended,
    excluded,
  }
}

/**
 * 影子日志：对候选列表逐首打分并写入 shadow_rerank_candidates。
 * @param {Array} candidates 候选曲目数组（含 name/artist 字段）
 * @param {string|null} currentTrackKey 当前曲目归一化 track_key
 * @param {string} reason 补货原因（透传自 setRefillHandler）
 * @returns {Promise<void>} 仅写入观测表，不返回任何业务值
 */
async function logShadowRerank(candidates, currentTrackKey, reason) {
  try {
    const list = Array.isArray(candidates) ? candidates : []
    const top = list.slice(0, MAX_LOG_CANDIDATES)
    for (const c of top) {
      const score = computeCandidateScore(c, currentTrackKey)
      const name = c?.song_info?.name || c?.name
      const artist = c?.song_info?.artist || c?.artist
      const trackKey = `${normalizeSongKey(name)}::${normalizeArtistKey(artist)}`
      state.insertShadowRerankCandidate({
        reason: reason || null,
        track_key: trackKey,
        freshness_raw_days: score.freshness.raw_days,
        continuity_raw_cost: score.continuity.raw_cost,
        feedback_raw_score: score.feedback.raw_score,
        feedback_excluded: score.feedback.excluded ? 1 : 0,
        playability_ever_played: score.playability.ever_played ? 1 : 0,
        blended_score: score.blended,
      })
    }
    console.log(`[candidate-rerank] shadow logged: ${top.length} candidates, reason=${reason || 'null'}`)
  } catch (err) {
    // 任何内部错误都吞掉，绝不影响真实补货
    console.error('[candidate-rerank] 观测计算异常（已忽略，不影响真实队列）:', err?.message || err)
  }
}

module.exports = { computeCandidateScore, logShadowRerank }
