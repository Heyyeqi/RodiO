# Brief:补充 batch4 人工复核抽样脚本(新脚本,不是改batch3)

## 背景澄清

上一轮brief里我搞错了一件事:以为 batch3 的"30组×6首,240人工复核CSV"抽样逻辑是写在 `label-track-sample-batch3.js` 里的,让你照着改。实际核实后发现:
- `output/track_label_review_batch3.csv`(2947行)是 batch3 脚本直接全量写出的,没有抽样
- `output/track_label_review_batch3_human_check.csv`(180行,30组×6首)是另一次性生成的,生成它的脚本当时没有提交进仓库,只提交了结果文件

所以这不是"改batch3已有逻辑",是要新写一个独立脚本。你之前如实指出这个矛盾是对的,没有瞎编,这点没问题。

## 任务

新建 `scripts/generate-batch4-human-check.js`,独立脚本,逻辑:

1. 读取 `output/track_label_review_batch4.csv`(batch4主脚本跑完后的全量输出,列为:`name,artist,mood_tags,texture_tags,negative_tags,energy,brightness,density,warmth,rhythmic_motion,vocal_presence,emotional_weight,language,has_vocal,genre_family,scene_fit,sequence_shape,label_confidence,reason`)
2. 随机抽取 240 行(不放回抽样)
3. 按 30 组、每组 8 首 分组,组内顺序即抽取顺序即可,不需要额外排序
4. 输出 `output/track_label_review_batch4_human_check.csv`,列结构必须与 `output/track_label_review_batch3_human_check.csv` 完全一致:
   ```
   group,seq_in_group,track_key_name,track_key_artist,name,artist,label(mood_tags),genre_family,label_confidence
   ```
   其中:
   - `group`:1-30
   - `seq_in_group`:1-8(组内序号)
   - `track_key_name`/`track_key_artist`:直接用该行的 `name`/`artist` 原样填入(参照 batch3_human_check.csv 里这两列和 name/artist 列内容相同的实际情况)
   - `label(mood_tags)`:取自全量CSV的 `mood_tags` 列,原样填入(注意这一列在原CSV里是用分号分隔的字符串,不用重新格式化,照抄即可)
   - `genre_family`/`label_confidence`:原样填入

## 运行方式

```
node scripts/generate-batch4-human-check.js
```
不需要 API key,纯本地文件处理,跑完直接报告输出文件行数确认是241行(240数据行+1表头)。

## 验证方式

1. `git status --short` 只应看到 `scripts/generate-batch4-human-check.js`(新增)和 `output/track_label_review_batch4_human_check.csv`(新增)
2. `wc -l output/track_label_review_batch4_human_check.csv` 应为 241
3. 抽查几行,确认 `group`/`seq_in_group` 编号连续且不重复(1-30 × 1-8)
