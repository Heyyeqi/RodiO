# Brief:补 track_profile.sequence_shape 字段 + 从4份CSV回填数据

## 背景

发现 `track_profile` 表建表语句(`core/state.js:46-108`)里,虽然注释明确写着"design doc Section 4 ... 无缺项无捏造"(见 `core/state.js:42-45`),但实际漏掉了 `sequence_shape` 这一列。4批标注脚本(batch1-4)里 LLM 都正常生成了这个字段、也过了封闭词表校验、也写进了各自的CSV,但 `INSERT OR REPLACE INTO track_profile` 语句里没带这一列,所以这11109条记录的 sequence_shape 数据目前只存在于CSV里,数据库里完全是空的。

这不是哪一批标注脚本的锅,是 `core/state.js` 建表语句本身从一开始就漏了这一列。现在要补上。

## 任务1:加列迁移

`core/state.js` 里已经有现成的迁移写法可以照抄,在 `core/state.js:142-153`(`play_events.transition_cost` 迁移)和 `core/state.js:155-169`(`song_feedback.score`/`score_updated_at` 迁移),都是"PRAGMA table_info 检查 + ALTER TABLE ADD COLUMN,包一层 try/catch 忽略 duplicate column 报错"的写法,保证重复启动不崩溃。

在这两段迁移代码后面,照同样的写法加一段:
```js
try {
  const tpCols = db.prepare('PRAGMA table_info(track_profile)').all().map(c => c.name)
  if (!tpCols.includes('sequence_shape')) {
    db.prepare('ALTER TABLE track_profile ADD COLUMN sequence_shape TEXT').run()
  }
} catch (e) {
  if (!/duplicate column/i.test(e.message)) throw e
}
```

同时把 `core/state.js:46-108` 的建表语句本身也补上这一列(放在 `negative_tags_json` 之后、`scene_fit_json` 之前比较合理,跟CSV/标注脚本里的字段顺序对应),这样全新初始化的数据库(比如未来换机器/重建db)也不会再漏这一列。**只加这一列,不要动其他任何字段或顺序。**

## 任务2:从4份CSV回填数据

新建 `scripts/backfill-sequence-shape.js`,独立脚本:

1. 依次读取这4份CSV(注意路径和列名,全部一致):
   - `output/track_label_review.csv`(batch1)
   - `output/track_label_review_batch2.csv`(batch2)
   - `output/track_label_review_batch3.csv`(batch3)
   - `output/track_label_review_batch4.csv`(batch4)
   
   每份CSV列结构:`name,artist,mood_tags,texture_tags,negative_tags,energy,brightness,density,warmth,rhythmic_motion,vocal_presence,emotional_weight,language,has_vocal,genre_family,scene_fit,sequence_shape,label_confidence,reason`

2. 对每一行,用现有的 `normalizeSongKey`/`normalizeArtistKey`(`core/search-utils.js`,batch3/batch4脚本里已经在用,直接复用同样的import)计算 `track_key = ${normalizeSongKey(name)}::${normalizeArtistKey(artist)}`

3. 用这个 track_key 去更新 `track_profile.sequence_shape`:
   ```js
   db.prepare('UPDATE track_profile SET sequence_shape = ? WHERE track_key = ?').run(sequenceShape, trackKey)
   ```

4. 用下面这个封闭词表额外校验一下(不是要拒绝写入,只是统计有没有意外的越界值,写日志即可,不要因为越界就跳过不写):
   ```js
   const SEQUENCE_VOCAB = new Set(['slow_opening','city_to_inner_room','rain_on_glass','afterglow_fading','soft_focus_work','late_night_descent','gentle_recovery','unfamiliar_but_safe','fade_into_inner_space'])
   ```

5. 跑完统计并打印:
   - 4份CSV总读取行数
   - 成功匹配到 track_key 并更新的行数
   - 没匹配到 track_key 的行数(如果有,打印前10条 name/artist 方便排查——理论上应该是0,因为这些track_key就是当初写入track_profile时用的同一套算法算出来的)
   - 词表越界的行数(理论上应该是0,前面已经在原CSV数据层面确认过没有越界)

## 不要做的事

- 不要改动4份CSV原文件
- 不要改动 batch1-4 的标注脚本
- 不要引入新依赖

## 验证方式(我会独立复核)

1. `PRAGMA table_info(track_profile)` 确认多了 `sequence_shape` 列
2. `SELECT COUNT(*) FROM track_profile WHERE sequence_shape IS NOT NULL AND sequence_shape != ''` 应该等于 11109(全部4批总数),或者你报告实际匹配数,我来对账
3. 随机抽几行核对 `sequence_shape` 值和对应CSV里的值是否一致
4. 提交时说明:改了哪些文件,回填统计数字
