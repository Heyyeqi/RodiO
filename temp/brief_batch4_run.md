# 指令:实际运行 batch4 标注 + 抽样,并提交

两个脚本都已经写好、语法检查通过(`scripts/label-track-sample-batch4.js` 和 `scripts/generate-batch4-human-check.js`),现在需要实际执行:

1. 运行主标注脚本(会真实调用 DeepSeek API,标注剩余约7800首,预计耗时较长,可后台跑):
   ```
   DEEPSEEK_API_KEY=sk-xxx node scripts/label-track-sample-batch4.js
   ```
2. 跑完后运行抽样脚本,生成人工复核文件:
   ```
   node scripts/generate-batch4-human-check.js
   ```
3. 两步都跑完后提交(`scripts/label-track-sample-batch4.js`、`scripts/generate-batch4-human-check.js`、`output/track_label_review_batch4.csv`、`output/track_label_review_batch4_human_check.csv`,以及 devlog.md 记录)

## 报告要求

跑完后请报告:
- 主脚本运行统计:候选池总数、成功写入数、跳过数(重复key)、失败数(API失败/校验失败被丢弃的)
- `track_profile` 里 `label_source='deepseek_sample_batch4'` 的行数(用于核对)
- commit hash

## 验证方式(我会独立核实,不接受纯文字总结)

- 直接查 DB:`SELECT COUNT(*) FROM track_profile WHERE label_source='deepseek_sample_batch4'`,核对是否约等于 (曲库总量 - 3943)
- `wc -l output/track_label_review_batch4_human_check.csv` 应为 241
- 随机抽查几行标签是否落在封闭词表内
