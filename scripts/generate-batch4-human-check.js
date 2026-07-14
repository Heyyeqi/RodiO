#!/usr/bin/env node
'use strict';

// 独立脚本：从 batch4 全量标注 CSV 中随机抽取 240 行（30 组 × 8 首）
// 生成人工复核文件。纯本地文件处理，不依赖 API key，不引入新 npm 依赖。

const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const SRC_CSV = path.join(PROJECT_ROOT, 'output', 'track_label_review_batch4.csv');
const OUT_CSV = path.join(PROJECT_ROOT, 'output', 'track_label_review_batch4_human_check.csv');

const GROUPS = 30;
const PER_GROUP = 8;
const TOTAL = GROUPS * PER_GROUP; // 240

// 标准 CSV 转义（与 batch3_human_check.csv 的 dialect 一致）：
// 字段含逗号/双引号/换行时整体用双引号包裹，内部每个 " 转义为 ""。
function csvEscape(value) {
  const s = value === null || value === undefined ? '' : String(value);
  if (/[",\n\r]/.test(s)) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

// 解析一行 CSV（支持标准引号转义），返回字段数组。
function parseCsvLine(line) {
  const fields = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        cur += ch;
      }
    } else {
      if (ch === '"') {
        inQuotes = true;
      } else if (ch === ',') {
        fields.push(cur);
        cur = '';
      } else {
        cur += ch;
      }
    }
  }
  fields.push(cur);
  return fields;
}

function main() {
  // 1. 读取全量 CSV
  if (!fs.existsSync(SRC_CSV)) {
    console.error(`[ERROR] 源文件不存在: ${SRC_CSV}`);
    console.error('请先运行 batch4 主脚本生成 output/track_label_review_batch4.csv');
    process.exit(1);
  }

  const raw = fs.readFileSync(SRC_CSV, 'utf8');
  // 按行分割，容忍末尾换行
  const lines = raw.split(/\r?\n/).filter((l) => l.length > 0);
  if (lines.length < 2) {
    console.error(`[ERROR] 源文件无数据行: ${SRC_CSV}`);
    process.exit(1);
  }

  const header = parseCsvLine(lines[0]);
  const dataLines = lines.slice(1);

  if (dataLines.length < TOTAL) {
    console.error(
      `[ERROR] 源文件数据行不足 ${TOTAL} 行（实际 ${dataLines.length} 行），无法抽取 ${TOTAL} 行。`
    );
    process.exit(1);
  }

  // 列索引
  const idx = {};
  header.forEach((h, i) => {
    idx[h.trim()] = i;
  });
  const need = ['name', 'artist', 'mood_tags', 'genre_family', 'label_confidence'];
  const missing = need.filter((c) => idx[c] === undefined);
  if (missing.length > 0) {
    console.error(`[ERROR] 源文件缺少必要列: ${missing.join(', ')}`);
    console.error(`实际列: ${header.join(', ')}`);
    process.exit(1);
  }

  // 2. 不放回随机抽样 240 行
  const pool = dataLines.map((_, i) => i);
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  const sampled = pool.slice(0, TOTAL).map((i) => dataLines[i]);

  // 3. 按 30 组 × 8 首分组，组内顺序即抽取顺序
  const outHeader = [
    'group',
    'seq_in_group',
    'track_key_name',
    'track_key_artist',
    'name',
    'artist',
    'label(mood_tags)',
    'genre_family',
    'label_confidence',
  ];

  const outRows = [outHeader.map(csvEscape).join(',')];

  for (let g = 0; g < GROUPS; g++) {
    for (let s = 0; s < PER_GROUP; s++) {
      const row = parseCsvLine(sampled[g * PER_GROUP + s]);
      const name = row[idx['name']] || '';
      const artist = row[idx['artist']] || '';
      const moodTags = row[idx['mood_tags']] || '';
      const genreFamily = row[idx['genre_family']] || '';
      const labelConfidence = row[idx['label_confidence']] || '';

      const out = [
        String(g + 1),
        String(s + 1),
        name, // track_key_name 原样
        artist, // track_key_artist 原样
        name,
        artist,
        moodTags, // label(mood_tags) 原样照抄
        genreFamily,
        labelConfidence,
      ];
      outRows.push(out.map(csvEscape).join(','));
    }
  }

  fs.writeFileSync(OUT_CSV, outRows.join('\n') + '\n', 'utf8');

  console.log(`[OK] 已抽取 ${TOTAL} 行（${GROUPS} 组 × ${PER_GROUP} 首）`);
  console.log(`输出: ${OUT_CSV}`);
  console.log(`源文件数据行: ${dataLines.length}`);
}

main();
