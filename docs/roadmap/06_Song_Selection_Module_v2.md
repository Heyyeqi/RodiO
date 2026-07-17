# RodiO 选歌模块实施方案 v2

> 基于 v1 方案 + RW 修正意见 + Evan 工程审查 + 多轮 AI 评估整合。
> 时间：2026-06-04 | 状态：拍板，可交付 Codex / Claude Code 执行
>
> **v2 相对 v1 的主要变化：**
> - LLM 精排改为先由工程层压缩至 40-60 首，不直接吃 120 首
> - track_profile 增加工程必要字段（track_key / duration_ms / play_count 等）
> - Phase 1 拆为抽样先行，不允许直接全库打标
> - 新增 MVP 边界、执行安全边界、标签词表、评测协议四节
> - Mood Intent 拆分硬约束 / 软偏好 / 叙事意图三层
> - 新增人文策展原则章节
> - Spotify Related Artists 降级为备选，不作为主路径

---

## 一、核心原则（不再讨论）

**RodiO 需要的不是更多模型，而是更清楚的模型职责。**

```
一个主模型（DeepSeek）
一个稳定标签体系（track_profile）
一个分层候选池
一个反馈闭环（skip / complete / replay）
一个连贯性控制器（transition_cost）
```

**运行时：单 LLM。离线：多 LLM 评测。工程层：规则与反馈主导稳定性。**

**RodiO 不以最低 skip_rate 为唯一目标。系统必须保留最低探索比例和审美张力。**

---

## 二、架构定义：统一流水线，多触发入口

```
触发入口（多个）
  ├── 主动消息（用户点歌、情绪描述、闲聊）
  ├── 天气变化
  ├── 定时 cron 播报
  └── 队列低水位补货（< 10 首）
          ↓
  ┌──────────────────────────────┐
  │      intent_router           │  ← 规则层
  │  direct_song / mood_request  │
  │  artist_request / chat_only  │
  │  weather_trigger / refill    │
  └──────────────────────────────┘
          ↓（非 direct_song）
  ┌──────────────────────────────┐
  │    Scene Interpreter         │  ← DeepSeek Prompt A
  │  输入：时间/天气/月相/用户输入 │
  │  输出：Mood Intent JSON       │
  └──────────────────────────────┘
          ↓
  ┌──────────────────────────────┐
  │    Candidate Recall          │  ← 工程层：分层召回 ~120 首
  └──────────────────────────────┘
          ↓
  ┌──────────────────────────────┐
  │    Hard Filter               │  ← 工程层：黑名单/冷却/重复
  └──────────────────────────────┘
          ↓
  ┌──────────────────────────────┐
  │    Candidate Scoring         │  ← 工程层：多维打分 → 压缩至 40-60 首
  └──────────────────────────────┘
          ↓
  ┌──────────────────────────────┐
  │    LLM Curation              │  ← DeepSeek Prompt B
  │  从 40-60 首精排出 10-15 首   │
  │  输出 reason_code / risk_code │
  └──────────────────────────────┘
          ↓
  ┌──────────────────────────────┐
  │    Queue Builder             │  ← 工程层：连贯性/queue_curve/去重
  └──────────────────────────────┘
          ↓
  ┌──────────────────────────────┐
  │    DJ Narration              │  ← DeepSeek Prompt C（不必每次触发）
  │  1-2 句克制串讲，不解释算法   │
  └──────────────────────────────┘
```

**关键原则：**
- 入口可以多，后端选歌逻辑统一
- `direct_song_request`（用户明确点歌）直接 resolve，不进入 Mood Intent 链路
- DeepSeek 使用三套独立 prompt，职责不混用

---

## 三、核心改造：LLM 职责重定义

### 当前问题链

```
LLM 直接生成歌名
→ 幻觉/不准确
→ Spotify/NCM 搜索失败
→ 入队不足
→ 多轮补货
→ 延迟增加
→ 质量飘
```

### 改造后：LLM 生成 Mood Intent JSON，不再生成歌名

Mood Intent 分三层：

```json
{
  "hard_constraints": {
    "energy_range": [0.2, 0.45],
    "brightness_range": [0.15, 0.4],
    "exclude_negative_tags": ["edm_drop", "idol_polished", "over_sweet"],
    "max_transition_cost": 0.25,
    "max_recent_repeat_days": 14
  },
  "soft_preferences": {
    "target_mood": ["introspective", "misty", "restrained"],
    "preferred_textures": ["ambient_pad", "piano", "soft_synth"],
    "language_bias": {
      "instrumental": 0.35,
      "zh": 0.25,
      "ja": 0.2,
      "en": 0.2
    },
    "exploration_level": 0.1
  },
  "narrative_intent": {
    "scene": "深夜、新月、潮湿、内省",
    "sequence_shape": "fade_into_inner_space",
    "transition_strategy": "slowly darker, no sudden tempo jump"
  }
}
```

**字段说明：**
- `hard_constraints`：工程层必须执行，不可绕过
- `soft_preferences`：工程层尽量满足，LLM 精排时参考
- `narrative_intent`：供 LLM 精排和 DJ 串讲使用，机器不直接解析数值

**Mood Intent 失败处理：**
```
JSON 非法 → fallback 旧路径
hard_constraints 任一字段缺失 → fallback
energy_range 异常（min > max / 超出 0-1）→ fallback
exploration_level 超出范围 → 重置默认值 0.1
avoid 为空但 scene 复杂 → 警告，继续执行
```

---

## 四、track_profile 标签体系（地基）

### 完整字段定义

```json
{
  "track_key": "normalized_name::normalized_artist",
  "spotify_uri": "spotify:track:xxx",
  "ncm_id": "12345678",
  "canonical_title": "标准化歌名",
  "canonical_artist": "标准化艺人名",
  "album": "专辑名",
  "duration_ms": 245000,
  "source_playlist": ["playlist_id_1"],
  "first_seen_at": "2026-01-01T00:00:00Z",
  "last_played_at": "2026-06-01T23:00:00Z",
  "play_count": 12,
  "skip_count": 2,
  "complete_count": 9,
  "like_count": 1,
  "dislike_count": 0,
  "candidate_exposure_count": 18,
  "candidate_rejected_count": 6,
  "validated_playable": true,
  "playability_checked_at": "2026-06-01T00:00:00Z",

  "language": "zh | ja | en | instrumental",
  "era": 1998,
  "has_vocal": true,
  "vocal_gender_guess": "female | male | group | none",
  "instrumental_ratio": 0.2,
  "genre_family": "art_pop | lo_fi | ambient | rb | indie | electronic | classical | other",

  "energy": 0.32,
  "brightness": 0.28,
  "density": 0.41,
  "warmth": 0.55,
  "rhythmic_motion": 0.3,
  "vocal_presence": 0.55,
  "emotional_weight": 0.72,

  "mood_tags": ["introspective", "misty"],
  "texture_tags": ["piano", "ambient_pad"],
  "negative_tags": [],

  "scene_fit": {
    "morning_clear_light": 0.2,
    "morning_cloudy_slow": 0.35,
    "work_focus_low_vocal": 0.6,
    "afternoon_warm_idle": 0.45,
    "evening_city_walk": 0.5,
    "night_clear_lonely": 0.8,
    "night_rain_humid": 0.88,
    "deep_night_introspective": 0.92,
    "weekend_slow": 0.6,
    "user_requested_explore": 0.3
  },

  "memory_recall_eligible": false,
  "label_confidence": 0.85,
  "label_version": "v1",
  "label_source": "deepseek_batch_v1"
}
```

### 标签分层说明

| 层级 | 字段 | 特性 |
|---|---|---|
| 客观标签 | language / era / has_vocal / genre_family / duration_ms | 稳定，少受模型影响 |
| 声学/体感标签 | energy / brightness / density / warmth / vocal_presence / emotional_weight | 数值化，可计算 |
| 审美语义标签 | mood_tags / texture_tags | 最有 RodiO 气质，最易漂移 |
| 排斥标签 | negative_tags | 服务于 avoid 机制 |
| 场景适配 | scene_fit | 核心召回依据 |

---

## 五、标签词表（固定枚举，不允许自造词）

### mood_tags（情绪标签，最多选 3 个）
```
introspective   misty          restrained     lonely
warm            detached       melancholic    dreamy
sensual         clear          restless       urban
nostalgic       hopeful        unresolved     bittersweet
```

### texture_tags（质感标签，最多选 4 个）
```
piano           ambient_pad    grainy         lofi_dust
soft_synth      cold_synth     acoustic       string
jazz_brush      field_recording reverb_heavy  minimal
cinematic       vocal_breath   electric_distant
```

### negative_tags（排斥标签，命中则过滤）
```
edm_drop        idol_polished  mainstream_anthem  over_sweet
over_dramatic   metal_screaming generic_radio_pop  bright_festival
generic_lofi    overly_cheerful
```

### scene_id（场景 ID，固定 10 个）
```
morning_clear_light      morning_cloudy_slow
work_focus_low_vocal     afternoon_warm_idle
evening_city_walk        night_clear_lonely
night_rain_humid         deep_night_introspective
weekend_slow             user_requested_explore
```

### sequence_shape（序列形状）
```
slow_opening             city_to_inner_room
rain_on_glass            afterglow_fading
soft_focus_work          late_night_descent
gentle_recovery          unfamiliar_but_safe
fade_into_inner_space
```

---

## 六、标签标注规范（防漂移）

```
1. 每批标注前置 10 首 few-shot 示例（艺人+歌名+正确标签）
2. 每个数值字段给出 3 个参考锚点，例如：
   energy 0.1 = 坂本龍一《Merry Christmas Mr. Lawrence》
   energy 0.5 = 王菲《红豆》
   energy 0.85 = （仅用于描述上限，不在库中）
3. 每批抽样复核：每 500 首抽 30 首人工检查
4. 多模型交叉抽检：抽取 300 首让第二个模型复核，冲突高的人工决定
5. 标签版本号（label_version）：词表或规范变化时升版，方便批量重标
6. 低置信度留空：label_confidence < 0.7 的字段可为 null，不强制填写
7. 禁止自造词：输出中出现词表外的词，视为标注失败，重新执行
```

---

## 七、候选召回层：分层召回

**取消"随机抽 50 首"，改为基于 track_profile 的分层召回，目标约 120 首。**

### 分层比例

| 层 | 数量 | 来源 | 召回依据 |
|---|---|---|---|
| 时段高匹配 | 40 首 | 本地库 | `scene_fit[当前 scene_id] > 0.6`，在 energy_range 内 |
| 相近气质 | 25 首 | 本地库 | 与当前播放曲 transition_cost < 0.2 |
| 历史高亲和未播 | 20 首 | 本地库 | like 记录关联，近 14 天未播放 |
| 发现候选 | 20 首 | discovery_candidates | 已验证可播放的新曲 |
| 低风险探索 | 10 首 | 本地库 | 低频播放、未被 skip、scene_fit > 0.4 |
| 反直觉备选 | 5 首 | 本地库 | 与当前场景有隐秘关联但不完全匹配 |

### 防"同批垄断"机制

```
1. 每层加入轻微分数扰动：score_with_jitter = base_score + random(-0.03, 0.03)
2. 同一 scene_id 下，candidate_exposure_count 近 7 天超过 3 次且未播放 → 降权 0.3
3. 同一艺人不超过 3 首进入同一批候选
4. 同一语言不超过候选总数的 60%
```

### 探索比例

```
普通时段：70% 已验证熟悉库 + 20% 久未播放旧收藏 + 10% 新发现
探索时段（user_requested_explore）：50% + 25% + 25%
```

---

## 八、Candidate Scoring 多维打分

工程层打分后，**压缩至 40-60 首**，再送入 LLM 精排。

### 打分公式（v1 默认权重）

```
final_score =
  taste_score      * 0.25   # mood_tags / texture_tags 与 soft_preferences 匹配
+ scene_score      * 0.25   # scene_fit[当前 scene_id]
+ freshness_score  * 0.20   # (当前日期 - last_played_at) 的对数归一化
+ continuity_score * 0.15   # 1 - transition_cost(当前曲, 候选曲)
+ feedback_score   * 0.10   # like_count * 2 - skip_count * 1.5（场景加权）
+ playability_score* 0.05   # validated_playable ? 1 : 0
```

> 注：初始权重为 v1 默认值，不要硬编码为常量。后续根据 skip_rate、completion_rate 实测调整。

### 硬性过滤（打分前执行）

```
- Spotify URI 黑名单
- 近 120 首播放记录中已有
- 近期推荐冷却期（60 条键值）
- negative_tags 与 hard_constraints.exclude_negative_tags 有交集
- energy 与 hard_constraints.energy_range 完全不重叠
- dislike_count > 0
```

---

## 九、LLM Curation（Prompt B）

DeepSeek 从工程层压缩后的 **40-60 首**中精排出 **10-15 首**。

### 输入

```
- Mood Intent 完整 JSON
- 候选列表（每首：track_key / mood_tags / texture_tags / energy / scene_fit）
- 当前播放曲的 track_profile
- 近 10 首播放历史（track_key + scene_id）
- taste.md 核心段落
```

### 输出格式

```json
{
  "selected": [
    {
      "track_key": "空城::王菲",
      "rank": 1,
      "reason_code": ["scene_match", "texture_match", "good_transition"],
      "risk_code": ["slightly_too_vocal"]
    }
  ],
  "rejected_but_relevant": [
    {
      "track_key": "催眠::王菲",
      "reason": "too emotionally direct for this scene"
    }
  ],
  "sequence_note": "整体从内省缓慢下沉，第 7 首后可轻微上浮"
}
```

### reason_code 枚举

```
scene_match   taste_anchor   texture_match   energy_match
good_transition   fresh_but_safe   discovery_candidate
contrast_pick   language_balance   memory_recall
```

### risk_code 枚举

```
too_bright   too_sweet   too_dense   too_familiar
too_unfamiliar   weak_transition   possible_mainstream
possible_mismatch   slightly_too_vocal
```

---

## 十、连贯性控制：transition_cost + queue_curve

### 单曲过渡检查

```
transition_cost(a, b) =
  |energy_a - energy_b|                   * 0.30
+ |brightness_a - brightness_b|            * 0.20
+ |density_a - density_b|                  * 0.15
+ |vocal_presence_a - vocal_presence_b|    * 0.15
+ |emotional_weight_a - emotional_weight_b|* 0.20
```

| 场景 | 最大 transition_cost |
|---|---|
| deep_night / night_rain | 0.25 |
| work_focus | 0.30 |
| 普通时段 | 0.35 |
| 用户主动请求换风格 | 0.50 |
| 每 5-7 首允许一次反差曲 | 0.55（需 DJ 串讲解释） |

### 队列整体曲线（queue_curve）

根据 `sequence_shape` 设定整组歌的目标曲线方向：

| sequence_shape | energy | brightness | vocal_presence | emotional_weight |
|---|---|---|---|---|
| late_night_descent | 缓慢下降 | 下降 | 下降 | 上升 |
| soft_focus_work | 稳定 | 低位稳定 | 极低 | 中位稳定 |
| afterglow_fading | 轻微下降 | 缓慢下降 | 中低 | 缓慢上升 |
| unfamiliar_but_safe | 轻微波动 | 中低 | 低中 | 中位波动 |

Queue Builder 检查整组歌的曲线是否符合目标形状，不符合时从候选池插入修正曲。

---

## 十一、Skip 反馈闭环

### 事件记录格式

```json
{
  "event_type": "skip | complete | replay | like | dislike",
  "track_key": "曲名::艺人",
  "played_seconds": 18,
  "duration_seconds": 245,
  "played_ratio": 0.073,
  "user_active": true,
  "scene_id": "deep_night_introspective",
  "prev_track_key": "上一首::艺人",
  "context_snapshot": {
    "weather": "Rain",
    "solar_phase": "deep_night",
    "lunar_phase": "new"
  },
  "timestamp": "2026-06-04T23:41:00+08:00"
}
```

### 信号分层（秒数 + 比例双判断）

| 行为 | 条件 | 判断 | 权重 |
|---|---|---|---|
| 极速跳过 | < 20 秒 | 强负反馈 | -3 |
| 中途跳过 | 20-60 秒且 ratio < 30% | 中负反馈 | -2 |
| 听完大部分 | ratio > 70% 或 > 180 秒 | 弱正反馈 | +1 |
| 完整播放（用户活跃） | 100% + user_active=true | 正反馈 | +2 |
| 完整播放（无操作） | 100% + user_active=false | 弱正反馈 | +0.5 |
| 重播 / 收藏 | — | 强正反馈 | +4 |
| 用户手动点歌 | — | 场景强正样本 | +5 |
| TTS 后立刻跳过 | ratio < 5% | 单独记录，独立分析 | — |

### 惩罚逻辑

```
skip_penalty = track_penalty
             + artist_penalty  * 0.3
             + tag_penalty     * 0.5
             + scene_penalty
```

跳过是场景惩罚 + 歌曲惩罚的组合，不能只做全局拉黑。

### 惩罚半衰期（防止越学越窄）

```
track_scene_penalty：14 天半衰
tag_scene_penalty：30 天半衰
artist_penalty：60 天半衰
```

### 注入方式

- **短期**：进入 24 小时冷却（按 track_key + scene_id 组合）
- **中期**：跳过的 tag 组合注入下次 Mood Intent 的 `exclude_negative_tags`
- **长期**：调整 `scene_fit[scene_id]` 权重

### 最小探索保留

```
普通时段：保留至少 5% discovery 比例
探索时段：保留至少 15% discovery 比例
```

---

## 十二、库扩张：discovery_candidates 流水线

### 三张表

```
library_tracks         主库（11,732 首），稳定主池
discovery_candidates   新发现候选池，待验证，不直接播放
validated_tracks       已验证可播放、已打标签，可进入播放
```

### 发现路径

**路径 1（主）：Last.fm**
- `track.getSimilar`：以高亲和曲为种子
- `artist.getSimilar`：track similar 为空时用艺人维度扩展
- 过滤：negative_tags 命中则丢弃

**路径 2：LLM 语义提名**
- 提名"气质相近但不显然"的曲目（每批约 2 首）
- 验证 Spotify/NCM 可播放性，失败直接丢弃

**路径 3：MusicBrainz 艺人关系图谱**
- 查询制作人、合作人、同厂牌艺人
- 每周离线运行一次

**路径 4（Phase 4 长期）：编辑策展源**
- Pitchfork / Resident Advisor / Bandcamp Daily RSS
- LLM 过滤符合 taste.md 的推荐

**关于 Spotify Related Artists：** 2024-11-27 公告已限制新应用访问。不作为主路径，若当前 App 已有 Extended Mode 且保留权限可作为备选。

### 新曲转正条件

```
转入 validated_tracks 的条件：
1. 至少播放 3 次
2. 至少 2 次 played_ratio > 70%
3. 无 played_seconds < 20 的早跳
4. 至少覆盖 2 个不同 scene_id（或单一 scene 下极高表现）
```

---

## 十三、模型职责边界

### 运行时：单 LLM（DeepSeek，三套独立 Prompt）

| Prompt | 职责 | 风格要求 |
|---|---|---|
| Prompt A：Scene Interpreter | 输出机器可执行 Mood Intent JSON | 精准，不写漂亮话 |
| Prompt B：LLM Curation | 从 40-60 首中排序，输出 reason_code / risk_code | 结构化 |
| Prompt C：DJ Narration | 1-2 句克制串讲 | 克制，不解释算法 |

### 离线：多 LLM 评测

```
曲库标签抽样复核：GPT / Gemini / Claude（抽 300 首）
新 prompt 评审：多模型审字段可执行性
新曲发现辅助：多模型提名取并集
异常推荐复盘：多模型分析失败案例
DeepSeek 替换验证：固定测试集多模型对比
```

**DJ 串讲不使用多模型轮流生成。**

### DJ 串讲克制规则

```
1. 不是每批歌都必须说话（见 silence_policy）
2. 每次 1-2 句，不超过 60 字
3. 不连续两次使用天气/月亮/夜晚
4. 不说"我懂你""我为你选了"等过度拟人句
5. 不直接评价用户情绪
6. 不解释算法逻辑
7. 不把情绪说破
8. reason_code 服务于内部调试，不出现在 say 文本中
```

### silence_policy（不说话的概率）

```json
{
  "deep_night_introspective": 0.75,
  "work_focus_low_vocal": 0.85,
  "night_rain_humid": 0.6,
  "morning_clear_light": 0.4,
  "user_chat_active": 0.2
}
```

---

## 十四、RodiO 人文策展原则

**这是 RodiO 区别于任何普通播放器的核心所在。**

### 1. 时间不是时段，而是精神质地

RodiO 的时间是此刻的情绪状态，而不是几点钟：
```
清晨未完全醒来      午后开始失焦
傍晚城市变暗        深夜情绪沉底
雨天时间变慢        新月适合留白
```

每个 scene_id 对应一段 `time_poetics`：
```json
{
  "scene_id": "deep_night_introspective",
  "human_meaning": "一天的外部秩序退场，内在声音变得清楚",
  "music_direction": "低亮度、低密度、留白、轻微不安",
  "narration_rule": "不安慰，不解释，只轻轻打开空间"
}
```

### 2. 每一组歌应形成关系，而不是单曲堆叠

Queue Builder 负责让一组歌有"起承转合"：
```
同一质感的延展        情绪逐渐降温
从人声退到器乐        从城市感退到自然感
从明亮表层进入冷调内里
```

### 3. 推荐不是讨好，而是克制地判断此刻什么该出现

RodiO 不只知道你喜欢什么，还知道什么歌即使你喜欢，此刻也不该放。`rejected_but_relevant` 字段记录这种判断，不对用户展示，但用于系统学习。

### 4. 记忆不只是播放历史（Phase 3 长期）

`memory_moments` 轻量记录某首歌第一次出现的情境：
```json
{
  "moment_id": "2026-06-04-night-rain-001",
  "scene_id": "night_rain_humid",
  "track_key": "xxx::yyy",
  "emotional_color": ["humid", "restrained", "private"],
  "reuse_policy": "未来相似雨夜可低频召回"
}
```

召回时不直接告知用户，DJ 只轻轻说：
> 有些歌第二次出现时，反而更像第一次。

或者干脆不说。

**memory_recall 规则：**
```
每 20-30 首允许 1 首 memory recall
必须跨越至少 7 天
transition_cost 必须自然
用户早跳则降低该 moment 权重
```

### 5. 品味不是单一画像，而是多个子人格

```
work_self：低人声、低打扰、结构稳定
night_self：内省、冷调、留白、少量不安
city_self：都市、流动、节奏感、轻微疏离
explore_self：跨文化、新艺人、边缘风格
```

每个 scene_id 触发对应的 taste 子画像偏重。

### 6. 保留轻微不可预测性

```
90%：符合当前场景
7%：相邻但略陌生
3%：反直觉但有隐秘关联（跨语种但同气质）
```

完全准确会变无聊，完全随机会变愚蠢。RodiO 的目标是"低风险的不确定性"。

### 7. 留白是一种选择，不是失败

系统不必在每首歌之间都说话。沉默本身是 RodiO 气质的一部分。

### 8. 不可解释的部分是精华

用户感受到的应该是：一种恰好，一种轻微陌生，一种好像被理解但没有被冒犯的感觉。内部有 reason_code，但外部不暴露算法逻辑。

---

## 十五、MVP 实施边界

**Phase 1 只做五件事，目标是"可观测"，不是"重构播放"。**

### Phase 1 做

```
1. 建立 track_profile schema
2. 抽样 200 首打标，验证词表稳定性
3. 实现播放行为日志（skip / complete / replay）
4. 实现 transition_cost 计算（观测模式，不干预队列）
5. 改造路径 B shadow mode（不影响真实播放）
```

### Phase 1 不做

```
全库 11,732 首打标
DeepSeek 完整替换 Qwen
路径 A 改 Mood Intent
Last.fm / MusicBrainz / 编辑源接入
LLM Curation 正式控制真实队列
discovery_candidates 流水线
```

### 抽样打标顺序

```
1. 抽样 200 首（覆盖各主要艺人和时段）
2. 打标 + 人工检查直觉是否对
3. 调整词表（如有近义词混乱）
4. 扩展到 1,000 首
5. 多模型复核 300 首
6. 稳定后全库批量打标
```

---

## 十六、执行安全边界

**给 Codex / Claude Code 的硬性约束。**

```
1. Shadow mode 优先
   新链路只生成候选和日志，不直接影响真实播放，直到验收通过。

2. 保留旧路径 fallback
   Mood Intent / 召回 / 精排任一失败 → fallback 到现有路径 B，记录原因。

3. 每次只改一个模块
   不允许同时改 context / queue / spotify resolve / TTS 四个链路。

4. 所有新文件只增不删
   不覆盖现有 playlist cache、history、blacklist、ncmIdMap。

5. Phase 1 不改真实播放行为
   不修改 resolveDjSelection / buildReadyPoolBatch 的真实链路。

6. 日志先行
   所有改动在能够观测之前不上线。

7. 新链路上线验收门槛（shadow mode 连续 7 天）：
   fallback_rate < 10%
   avg_transition_cost 低于旧链路 20%
   duplicate_rate 不高于旧链路
   candidate_empty_count = 0
```

### Fallback 日志格式

```json
{
  "fallback_reason": "mood_intent_invalid | candidate_recall_empty | llm_curation_failed | queue_builder_failed | playability_check_failed",
  "stage": "scene_interpreter | candidate_recall | candidate_scoring | llm_curation | queue_builder",
  "timestamp": "",
  "context_id": ""
}
```

---

## 十七、评测与验收协议

### 技术指标（每轮测试记录）

```
解析成功率   fallback_rate   avg_transition_cost
skip_rate    complete_rate   repeat_rate
新曲比例     同艺人集中度    语言比例
```

### 负面场景测试集

```
1. 天气 API 缺失
2. 月相数据异常
3. 用户输入极短："随便"
4. 用户输入矛盾："想安静但要兴奋一点"
5. 候选池不足（< 30 首可用）
6. 当前曲没有 track_profile
7. 新曲没有标签
8. Spotify 播放失败
9. NCM 回退失败
10. LLM 输出非法 JSON
```

### 主观审美验收表（每轮人工打分）

| 维度 | 分数 1-5 | 判断标准 |
|---|---|---|
| 此刻感 | — | 是否真的像此刻该出现 |
| 连贯性 | — | 前后是否自然，无突兀跳变 |
| 新鲜感 | — | 是否有轻微惊喜 |
| 不冒犯 | — | 是否没有突然土/俗/吵 |
| 人格稳定 | — | DJ 是否还像 RodiO |
| 串讲克制 | — | 是否没有油腻解释 |

> 技术指标只能告诉你系统没坏，主观验收才能判断它是不是 RodiO。

---

## 十八、实施路线图

### Phase 1：地基（立即开始）
```
1. track_profile schema
2. 抽样 200 首打标，验证词表
3. 播放行为日志
4. transition_cost 观测
5. 路径 B shadow mode
```

### Phase 2：核心架构改造
```
6. 路径 A → Mood Intent 生成模式
7. 路径 B → 基于 track_profile 的分层召回
8. 统一选歌流水线
9. LLM Curation 上线（先 shadow mode）
10. 验收通过后接管真实队列
```

### Phase 3：质量提升
```
11. Skip 反馈注入 Mood Intent
12. queue_curve 连贯性检查
13. discovery_candidates 流水线（Last.fm + LLM 提名）
14. DeepSeek 替换 Qwen 验证
15. memory_moments 轻量实现
```

### Phase 4：长期演化
```
16. 向量检索替代标签过滤
17. 动态品味画像（2% 探索比例）
18. 编辑策展源（Pitchfork / RA / Bandcamp Daily）
19. 简化 Bandit
20. time_poetics 全场景定义
```

---

## 十九、不做的事（已拍板）

| 方向 | 原因 |
|---|---|
| 声景实时合成 | 艺术性不可控，偏离核心诉求 |
| 共情监听器（摄像头/麦克风） | 隐私成本高，误判风险高 |
| 完整 RL 系统 | 个人样本量不足 |
| 运行时多 LLM 共同选歌 | 审美人格分裂，延迟高 |
| 腾讯/字节生态迁移 | 个人项目过重 |
| Spotify Related Artists 作为主路径 | 2024-11-27 起新应用已受限 |

---

*参考文档：《RodiO_选歌模块_多AI评估整合底稿.md》《RodiO_选歌模块技术披露.md》*
*本文档为 v2，可直接交付 Codex / Claude Code 执行 Phase 1 任务。*
