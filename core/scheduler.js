const cron = require('node-cron')
const context = require('./context')
const claude = require('./claude')

let wsClients = []
let todayCount = 0
let resolveQueueFn = null
let appendToQueueFn = null

function setWsClients(clients) {
  wsClients = clients
}

function setResolveQueue(fn) {
  resolveQueueFn = fn
}

function setAppendToQueue(fn) {
  appendToQueueFn = fn
}

function broadcast(data) {
  const msg = JSON.stringify(data)
  wsClients.forEach(ws => {
    if (ws.readyState === 1) ws.send(msg)
  })
}

function getTodayCount() { return todayCount }
function incrementCount() { todayCount++ }

// 七曜零点交接仪式台词：索引 = new Date().getDay()（今天当值、即将隐退的曜日）。
// 前句"X隐去/离去"是退场，后句"Y接手/升起/流转/沉定/落地/复升"是明曜进场，
// 保持"三字退 + 三字进"的对称节奏。
const SHICHIYOU_CEREMONY_LINES = [
  '子时。日离去，月接手。',   // 0 周日→周一
  '子时。月隐去，火升起。',   // 1 周一→周二
  '子时。火隐去，水流转。',   // 2 周二→周三
  '子时。水散去，木沉定。',   // 3 周三→周四
  '子时。木退去，金浮现。',   // 4 周四→周五
  '子时。金隐去，土落地。',   // 5 周五→周六
  '子时。土归寂，日复升。',   // 6 周六→周日
]

// 07:00 晨间播报
cron.schedule('0 7 * * *', async () => {
  try {
    const ctx = await context.buildContext('早安，今天适合听什么？')
    const result = await claude.askClaude(ctx)
    broadcast({ type: 'morning', ...result })
    incrementCount()
  } catch (e) {
    console.error('[scheduler] 晨间播报失败:', e.message)
  }
})

// 整点情绪检查（9:00 - 22:00）
cron.schedule('0 9-22 * * *', async () => {
  const h = new Date().getHours()
  const prompts = {
    9: '开始工作了，来一首有节奏感的',
    12: '午休时间，轻松一点',
    15: '下午了，给点能量',
    18: '下班了，放松一下',
    21: '深夜模式，治愈系',
  }
  const input = prompts[h] || '现在适合听什么'
  try {
    const ctx = await context.buildContext(input)
    const result = await claude.askClaude(ctx)
    let queue = []
    if (resolveQueueFn && Array.isArray(result.play) && result.play.length > 0) {
      queue = await resolveQueueFn(result.play)
    }
    if (appendToQueueFn && queue.length > 0) {
      queue = await appendToQueueFn(queue)
    }
    broadcast({ type: 'scheduled', hour: h, ...result, queue })
    incrementCount()
  } catch (e) {
    console.error('[scheduler] 整点检查失败:', e.message)
  }
})

// 23:58 七曜零点交接仪式播报（前端 rimGlow 呼吸过渡同步进行）
cron.schedule('58 23 * * *', () => {
  try {
    const today = new Date().getDay() // 当前曜日（即将隐退）
    broadcast({
      type: 'shichiyou',
      say: SHICHIYOU_CEREMONY_LINES[today],
      play: [],
      replace_pool: false,
      reason: '七曜零点交接',
      segue: '',
    })
  } catch (e) {
    console.error('[scheduler] 七曜交接播报失败:', e.message)
  }
})

module.exports = {
  setWsClients,
  setResolveQueue,
  setAppendToQueue,
  broadcast,
  getTodayCount,
  incrementCount,
}
