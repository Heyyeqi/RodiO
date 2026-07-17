# Brief:标注扩容 batch4 —— 标完剩余全部曲库(约7800首)

## 背景

Phase 1 已完成 batch1(200)+batch2(796)+batch3(2947) = 3943首标注,现在要把剩下没标注的全部曲库(约7800首)一次性标完,不再是抽样。

**新建 `scripts/label-track-sample-batch4.js`,复制 `scripts/label-track-sample-batch3.js` 的结构,只改动下面列出的几处,其余(SYSTEM_PROMPT、5个封闭词表 MOOD_VOCAB/TEXTURE_VOCAB/NEGATIVE_VOCAB/SCENE_VOCAB/SEQUENCE_VOCAB、validateLabels 校验逻辑、DeepSeek 调用参数、DB 字段写入)原样复用,一个字都不要改。**

## 与 batch3 的差异(仅这几点)

1. **不再抽样,处理全部剩余曲库**:删掉 `SAMPLE_SIZE`/`sampleWithArtistLimit` 逻辑,直接对排除后的候选池全量遍历。
2. **排除已标注的方式改为直接查 DB,不再解析 CSV**:
   ```js
   const existingKeys = new Set(
     db.prepare('SELECT track_key FROM track_profile').all().map(r => r.track_key)
   )
   const poolFiltered = pool.filter(song => {
     const tk = `${normalizeSongKey(song.name)}::${normalizeArtistKey(song.artist)}`
     return !existingKeys.has(tk)
   })
   ```
   这样天然支持断点续跑——如果中途失败重跑,已经写入 track_profile 的曲目会被自动跳过,不需要额外的 checkpoint 机制。
3. **不再有每艺人配额上限(MAX_PER_ARTIST)**:这次是穷举剩余曲库,不是抽样,配额概念不适用,直接去掉。
4. **常量改名**:`LABEL_SOURCE = 'deepseek_sample_batch4'`,`REVIEW_CSV` 改成 `output/track_label_review_batch4.csv`,console.log 里的 batch3 字样改成 batch4。`LABEL_VERSION` 维持 `v2_2026-07-13` 不变(prompt没变)。
5. **人工复核CSV抽样量**:从全量 batch4 结果里随机抽 **240首**(30组×8首,和之前的分组格式一致,方便我复用同样的看法说明),而不是像 batch3 那样抽 180——量大了适当多抽一点。

## 不要做的事

- 不要引入新依赖(csv-parse 已经在用,不需要新库;这次也不再需要 csv-parse,因为排除逻辑改成查DB了——如果确认不再需要 csv-parse 就不用管它,不用刻意删除已有依赖)
- 不要改动 batch1/batch2/batch3 的脚本或它们生成过的CSV
- 不要改动 SYSTEM_PROMPT 或任何词表内容

## 运行方式

```
DEEPSEEK_API_KEY=sk-xxx node scripts/label-track-sample-batch4.js
```
预计耗时较长(约7800首,concurrency=3),可以后台跑,跑完直接报告结果统计(成功数/失败数/跳过数)和 `output/track_label_review_batch4.csv` 的路径。

## 验证方式(提交前自查,提交后我会独立复核)

1. `git status --short`:只应该看到 `scripts/label-track-sample-batch4.js`(新增)和 `output/track_label_review_batch4.csv`(新增),不应该有 package.json/package-lock.json 变化
2. 跑完后 `track_profile` 里 `label_source='deepseek_sample_batch4'` 的行数,应该约等于 (曲库总量 - 3943),而不是某个抽样数字
3. 随机抽几行核对 `mood_tags`/`texture_tags`/`negative_tags` 是否都在词表范围内(不要相信自己复算的"0-2处越界"这种总结,我会直接跑校验脚本核对)
