#!/usr/bin/env node
/**
 * backfill-sequence-shape.js
 *
 * 从 4 批标注 CSV 回填 sequence_shape 字段到 track_profile 表。
 *
 * 背景：
 *   track_profile 建表语句从 Phase 1 起遗漏了 sequence_shape 列（LLM 标注字段，
 *   取值如 circular / repetitive / linear / ...），4 批 CSV 中均含此列数据但
 *   写入 DB 时未落库。本脚本从 CSV 逐行解析，按 track_key 回填该列。
 *
 * 约束：
 *   - 不改 CSV 原文件、不改标注脚本
 *   - 不引入新 npm 依赖（csv-parse / better-sqlite3 / opencc-js 均为项目已有）
 *   - normalizeSongKey / normalizeArtistKey 原样复用 core/search-utils 实现
 *
 * 运行：
 *   node scripts/backfill-sequence-shape.js
 */

const fs = require('fs')
const path = require('path')
const Database = require('better-sqlite3')
const { parse } = require('csv-parse/sync')
const { normalizeSongKey, normalizeArtistKey } = require('../core/search-utils')

// ── 路径配置 ──────────────────────────────────────────────────────────────
const ROOT = path.join(__dirname, '..')
const DB_PATH = path.join(ROOT, 'db', 'state.db')
const OUTPUT_DIR = path.join(ROOT, 'output')

// 4 批 CSV。batch1 实际文件名为 track_label_review.csv（无 _batch1 后缀）。
const CSV_FILES = [
  'track_label_review.csv',          // batch1
  'track_label_review_batch2.csv',   // batch2
  'track_label_review_batch3.csv',   // batch3
  'track_label_review_batch4.csv',   // batch4
]

// 视为无效占位符、需跳过的 sequence_shape 值（大小写不敏感）
const INVALID_PLACEHOLDERS = new Set([
  '',
  'n/a',
  'na',
  'null',
  'none',
  '-',
  '--',
  'undefined',
])

// ── 打开 DB ───────────────────────────────────────────────────────────────
if (!fs.existsSync(DB_PATH)) {
  console.error(`[backfill] DB 不存在: ${DB_PATH}`)
  process.exit(1)
}
const db = new Database(DB_PATH)
db.pragma('journal_mode = WAL')

// 确保 sequence_shape 列存在（与 core/state.js 迁移逻辑一致，保证本脚本独立运行也能建列）
try {
  const tpCols = db.prepare('PRAGMA table_info(track_profile)').all().map((c) => c.name)
  if (!tpCols.includes('sequence_shape')) {
    db.prepare('ALTER TABLE track_profile ADD COLUMN sequence_shape TEXT').run()
    console.log('[backfill] 已新增 sequence_shape 列')
  }
} catch (e) {
  if (!/duplicate column/i.test(e.message)) throw e
}

// 预编译语句
const updateStmt = db.prepare(
  'UPDATE track_profile SET sequence_shape = ? WHERE track_key = ?'
)
const existsStmt = db.prepare(
  'SELECT 1 FROM track_profile WHERE track_key = ? LIMIT 1'
)

// ── 主流程 ────────────────────────────────────────────────────────────────
let grandTotalRead = 0
let grandTotalMatched = 0
let grandTotalUnmatched = 0
let grandTotalSkipped = 0

for (const fileName of CSV_FILES) {
  const filePath = path.join(OUTPUT_DIR, fileName)
  if (!fs.existsSync(filePath)) {
    console.log(`\n[${fileName}] 文件不存在，跳过`)
    continue
  }

  const raw = fs.readFileSync(filePath, 'utf8')
  let records
  try {
    records = parse(raw, {
      columns: true,
      skip_empty_lines: true,
      relax_quotes: true,
      relax_column_count: true,
    })
  } catch (e) {
    console.error(`[${fileName}] CSV 解析失败: ${e.message}`)
    continue
  }

  let read = 0
  let matched = 0
  let unmatched = 0
  let skipped = 0

  for (const row of records) {
    const name = row.name
    const artist = row.artist
    if (name == null || artist == null) continue

    const trackKey = `${normalizeSongKey(name)}::${normalizeArtistKey(artist)}`
    if (!trackKey) continue

    const shapeRaw = (row.sequence_shape ?? '').toString().trim()
    const shape = shapeRaw.toLowerCase()

    // 占位符 / 空值跳过
    if (INVALID_PLACEHOLDERS.has(shape)) {
      skipped++
      continue
    }

    read++

    const exists = existsStmt.get(trackKey)
    if (!exists) {
      unmatched++
      continue
    }

    const info = updateStmt.run(shapeRaw, trackKey)
    if (info.changes > 0) {
      matched++
    } else {
      unmatched++
    }
  }

  grandTotalRead += read
  grandTotalMatched += matched
  grandTotalUnmatched += unmatched
  grandTotalSkipped += skipped

  console.log(`\n[${fileName}]`)
  console.log(`  读取行数(不含表头, 有效 name+artist): ${read}`)
  console.log(`  匹配更新数:                           ${matched}`)
  console.log(`  未匹配数(track_key 不存在):           ${unmatched}`)
  console.log(`  占位符/无效值跳过数:                  ${skipped}`)
}

console.log(`\n========== 总计 ==========`)
console.log(`  读取行数(有效):   ${grandTotalRead}`)
console.log(`  匹配更新数:       ${grandTotalMatched}`)
console.log(`  未匹配数:         ${grandTotalUnmatched}`)
console.log(`  占位符跳过数:     ${grandTotalSkipped}`)

db.close()
