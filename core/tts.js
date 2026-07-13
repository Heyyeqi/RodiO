const fs = require('fs')
const path = require('path')
const crypto = require('crypto')

const CACHE_DIR = path.join(__dirname, '../cache/tts')
const FISH_URL = 'https://api.fish.audio/v1/tts'
const FISH_MODEL = 's2.1-pro-free'
const TTS_MIN_GAP_MS = 2000
let ttsQueue = Promise.resolve()
let lastTtsRequestAt = 0
let queueLength = 0

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function enqueueTtsTask(task) {
  queueLength += 1
  const wrappedTask = async () => {
    try {
      return await task()
    } finally {
      queueLength = Math.max(0, queueLength - 1)
    }
  }
  const next = ttsQueue.then(wrappedTask, wrappedTask)
  ttsQueue = next.then(() => undefined, () => undefined)
  return next
}

function normalizeTtsText(text) {
  const cleaned = String(text || '')
    .replace(/\r/g, '')
    .replace(/\n+/g, '，')
    .replace(/[“”"]/g, '')
    .replace(/……/g, '，')
    .replace(/—+/g, '，')
    .replace(/\s+/g, ' ')
    .trim()

  if (!cleaned) return ''
  return /[。！？.!?]$/.test(cleaned) ? cleaned : `${cleaned}。`
}

async function synthesizeWithOptions(text, options = {}) {
  const { speed = 0.96, suffix = '' } = options
  const normalizedText = normalizeTtsText(text)
  const hash = crypto.createHash('md5').update(normalizedText).digest('hex')
  const filename = `${hash}${suffix}.mp3`
  const cachePath = path.join(CACHE_DIR, filename)

  if (fs.existsSync(cachePath)) return `/cache/tts/${filename}`

  const apiKey = process.env.FISH_API_KEY
  if (!apiKey) throw new Error('FISH_API_KEY 未配置')
  const voiceId = process.env.FISH_VOICE_ID
  if (!voiceId) throw new Error('FISH_VOICE_ID 未配置')

  fs.mkdirSync(CACHE_DIR, { recursive: true })

  const requestBody = {
    text: normalizedText,
    reference_id: voiceId,
    format: 'mp3',
    prosody: { speed },
  }

  console.log('[fish-tts] request body:', JSON.stringify(requestBody))

  const wait = TTS_MIN_GAP_MS - (Date.now() - lastTtsRequestAt)
  if (wait > 0) {
    await delay(wait)
  }
  console.log('[tts-queue] starting request, queue length:', queueLength)
  lastTtsRequestAt = Date.now()

  const response = await fetch(FISH_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      model: FISH_MODEL,
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(requestBody),
  })

  console.log('[fish-tts] response status:', response.status)

  if (!response.ok) {
    const errText = await response.text().catch(() => '')
    throw new Error(`Fish Audio TTS 请求失败: ${response.status} ${errText.slice(0, 200)}`)
  }

  const audioBuffer = Buffer.from(await response.arrayBuffer())
  if (!audioBuffer.length) {
    throw new Error('Fish Audio TTS 未返回音频数据')
  }

  fs.writeFileSync(cachePath, audioBuffer)

  return `/cache/tts/${filename}`
}

async function synthesize(text) {
  return enqueueTtsTask(() => synthesizeWithOptions(text))
}

async function synthesizeSlow(text) {
  return enqueueTtsTask(() => synthesizeWithOptions(text, { speed: 0.84, suffix: '_slow' }))
}

module.exports = { synthesize, synthesizeSlow }
