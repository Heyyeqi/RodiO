# Brief:Phase 2 第一步 —— Scene Interpreter (Mood Intent JSON) Shadow Mode

## 背景

这是选歌模块Phase 2重架的第一个具体步骤,严格遵守方案文档(`RodiO_选歌模块_实施方案_v2.md`第十六节)的执行安全边界:**只做shadow mode,完全不影响真实播放**,后续接管真实队列是独立的、需要单独验收的步骤,这次不做。

现状核实过(不是猜测):
- `server.js:1184` `queueManager.setRefillHandler(...)`是所有静默补货的唯一真实汇合点,现有两个影子调用(`runShadowRecall`/`logShadowRerank`,约1201/1204行)都挂在这里,fire-and-forget、`.catch(()=>{})`吞掉异常。本次新增的第三个影子调用也挂在同一处,**在这两行之后**追加。
- `core/claude.js`的`askClaude(context)`是为真实选曲定制的(`{say, play, replace_pool, reason, segue}`形状),不要复用它的client实例或prompt结构——新建独立的DeepSeek调用。它的`extractFirstJson(text)`(第9行)JSON修复逻辑可以照抄写法(不是import复用,是抄一份逻辑到新模块,保持职责独立)。
- `core/context.js`的`getEnvironmentSnapshot()`是现成的环境快照(天气/农历/节气/月相/氛围情绪推断),直接复用,不用重新组装。
- `/api/explain`(`server.js`约1473-1521行)里内联了调性引擎的三张映射表(`SHICHIYOU_TONALITY`/`WEATHER_TONALITY`/`SEASON_TONALITY`)和intensity/warmth混合公式,这次要把它搬到新模块里(新增一份,**不改动`/api/explain`原有代码**,那边保持原样)。

## 任务1:新建 `core/mood-intent.js`

跟`core/shadow-recall.js`/`core/candidate-rerank.js`一样的写法(模块级`try/catch`、fire-and-forget、中文注释说明"纯观测,不影响真实选曲"的契约)。

### `computeTonalityVector(envSnapshot)`

把`/api/explain`里那三张映射表(`SHICHIYOU_TONALITY`/`WEATHER_TONALITY`/`SEASON_TONALITY`)和混合公式原样搬一份到这个新函数里,输入`envSnapshot`(结构和`/api/explain`里用的一致),输出`{ intensity, warmth }`。逻辑和`/api/explain`现有代码完全一致,只是挪了个位置、多了一份,不要改变任何权重或映射值。

### `buildMoodIntentPrompt(envSnapshot, currentQueue, reason, tonality)`

纯函数,组装system+user消息,要求LLM严格按下面这个JSON schema输出(不能有markdown、不能有多余文字):

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
    "language_bias": { "instrumental": 0.35, "zh": 0.25, "ja": 0.2, "en": 0.2 },
    "exploration_level": 0.1
  },
  "narrative_intent": {
    "scene": "深夜、新月、潮湿、内省",
    "sequence_shape": "fade_into_inner_space",
    "transition_strategy": "slowly darker, no sudden tempo jump"
  }
}
```

`negative_tags`必须从这个封闭词表里选(不允许自造词):
```
edm_drop        idol_polished  mainstream_anthem  over_sweet
over_dramatic   metal_screaming generic_radio_pop  bright_festival
generic_lofi    overly_cheerful
```
`target_mood`必须从这个封闭词表里选(最多3个):
```
introspective   misty          restrained     lonely
warm            detached       melancholic    dreamy
sensual         clear          restless       urban
nostalgic       hopeful        unresolved     bittersweet
```
`preferred_textures`必须从这个封闭词表里选(最多4个):
```
piano           ambient_pad    grainy         lofi_dust
soft_synth      cold_synth     acoustic       string
jazz_brush      field_recording reverb_heavy  minimal
cinematic       vocal_breath   electric_distant
```
`sequence_shape`必须从这个封闭词表里选:
```
slow_opening             city_to_inner_room
rain_on_glass            afterglow_fading
soft_focus_work          late_night_descent
gentle_recovery          unfamiliar_but_safe
fade_into_inner_space
```

system prompt要求:精准、不写漂亮话、职责单一(这是"场景解读器"不是"DJ",不要有播报腔调);把`envSnapshot`里的天气/农历/节气/月相信息和`tonality`(intensity/warmth)作为上下文提供给LLM参考,帮它决定`narrative_intent.scene`怎么写、`hard_constraints.energy_range`大致该往哪个方向偏——但不要要求LLM自己输出tonality数值(这个由代码在校验通过后直接塞进最终JSON,见下面校验部分)。

user message里带上:当前时间、`envSnapshot`里的天气文本/节气/月相信息、`currentQueue`里最近几首歌的track_key(供LLM判断"最近在放什么调性,别突然跳变")、`reason`(这次补货触发原因,仅供参考)。

### `callSceneInterpreter(prompt)`

新建独立的DeepSeek client(`new OpenAI({apiKey: process.env.DEEPSEEK_API_KEY, baseURL: 'https://api.deepseek.com'})`,不要import或复用`core/claude.js`导出的实例),model用`deepseek-v4-flash`,`thinking: {type: 'disabled'}`,照抄`extractFirstJson`的JSON修复逻辑处理返回内容。

### `validateMoodIntent(raw)`

纯函数,严格实现下面的失败处理规则,返回`{valid: true, intent}`或`{valid: false, fallback_reason}`,**永不抛出异常**:

- `raw`不是对象或解析失败 → `fallback_reason: 'mood_intent_invalid_json'`
- `hard_constraints`缺失,或缺少`energy_range`/`brightness_range`/`exclude_negative_tags`/`max_transition_cost`/`max_recent_repeat_days`任一字段 → `'missing_hard_constraints'`
- `energy_range`不是长度为2的数组、任一值不在[0,1]、或min>max → `'energy_range_invalid'`
- `brightness_range`同样规则 → `'brightness_range_invalid'`
- `soft_preferences.exploration_level`不是[0,1]范围内的数字 → **这条不算失败**,直接把它重置为0.1,继续往下走(方案原文明确写着这条是"重置默认值"不是"拒绝",跟其他字段处理方式不一样,请务必按这个来,不要把它也归到失败分支)

校验通过后,把`computeTonalityVector`算出来的`{intensity, warmth}`直接写进最终返回的`intent.narrative_intent.tonality_vector`字段里——**这两个数值是代码算出来直接塞进去的,不依赖LLM自己在JSON里回传**,这样保证只要`valid=true`,`tonality_vector`一定存在且和调用时刻的环境完全对应。最终结构:

```json
"narrative_intent": {
  "scene": "...(LLM生成)",
  "sequence_shape": "...(LLM生成，来自封闭词表)",
  "transition_strategy": "...(LLM生成)",
  "tonality_vector": { "intensity": 0.38, "warmth": 0.42 }
}
```

### `generateShadowMoodIntent(reason, currentQueue, meta)`

导出的编排函数,整体包一层try/catch,永不抛出。流程:调用`context.getEnvironmentSnapshot()` → `computeTonalityVector` → `buildMoodIntentPrompt` → `callSceneInterpreter`(这一步如果抛错/超时,单独捕获,记`fallback_reason: 'llm_call_failed'`,和"LLM有响应但内容不合法"的`mood_intent_invalid_json`区分开)→ `validateMoodIntent` → 无论成功失败都调用`state.insertShadowMoodIntentLog(...)`记录一行,并记录本次调用耗时(`latency_ms`)。

## 任务2:`core/state.js`新增表和函数

加进顶层`db.exec`块,紧跟`shadow_recall_log`那段(全新表,不需要ALTER TABLE迁移,不要动任何现有表):

```sql
CREATE TABLE IF NOT EXISTS shadow_mood_intent_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reason TEXT,
  valid INTEGER NOT NULL,
  fallback_reason TEXT,
  intent_json TEXT,
  raw_response TEXT,
  tonality_intensity REAL,
  tonality_warmth REAL,
  latency_ms INTEGER,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
```

新增`insertShadowMoodIntentLog(row)`(参照`insertShadowRecallLog`同样的防御性默认值写法,`row`里各字段缺失时用`null`兜底)和`getRecentShadowMoodIntentLogs(limit = 50)`两个函数,从`module.exports`导出。

## 任务3:接入点 `server.js:1184`附近

在现有两行影子调用(`runShadowRecall(...)`/`logShadowRerank(...)`)**之后**追加第三行,同样fire-and-forget:
```js
generateShadowMoodIntent(reason, currentQueue, meta).catch(() => {})
```
文件顶部`require('./core/mood-intent')`引入。**只加这一行调用,不要动这附近任何其他代码**。

## 严格不要做的事

- 不要接入`/api/chat`(`resolveDjSelection`)或天气变化触发路径(`checkWeatherChange`)——这次只接静默补货这一个触发点,其他触发点是以后独立的接入步骤
- 不要改`/api/explain`路由里现有的调性引擎代码,新模块里的`computeTonalityVector`是新增的独立一份,不是重构
- 不要改`core/candidate-rerank.js`的打分公式或权重
- 不要改任何真实选曲/播放函数(`resolveDjSelection`/`buildReadyPoolBatch`/`fillQueueFromSpotifyPlaylists`本体逻辑一个字都不要动)
- 不要给Mood Intent加`scene_id`枚举字段(这次`narrative_intent.scene`就是自由文本,不是方案第五节的10个封闭scene_id值,这个是以后的缺口,这次不用管)
- 不要引入新的npm依赖(`openai`包已经在用了)

## 验证方式(我会独立核实,不接受纯文字总结)

1. `git status --short`确认只新增了`core/mood-intent.js`一个文件,`core/state.js`和`server.js`是修改(增量),没有其他文件被动
2. `node --check`所有改动文件
3. 本地起服务跑一段时间(建议至少触发几次真实静默补货),`SELECT COUNT(*) FROM shadow_mood_intent_log`确认有新记录落库
4. 贴几条真实的`intent_json`内容(不要编造,直接从DB里`SELECT`出来贴)供我核对schema和词表是否合规
5. 确认`shadow_recall_log`/`shadow_rerank_candidates`两张既有影子表的写入没有受影响(改动前后同样次数的触发应该产生同样次数的这两张表的新记录)
