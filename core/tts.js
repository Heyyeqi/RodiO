const fs = require('fs')
const path = require('path')
const crypto = require('crypto')

const CACHE_DIR = path.join(__dirname, '../cache/tts')
const MINIMAX_URL = 'https://api.minimax.chat/v1/t2a_v2'
const MINIMAX_MIN_GAP_MS = 2000
let ttsQueue = Promise.resolve()
let lastMiniMaxRequestAt = 0
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

  const apiKey = process.env.MINIMAX_API_KEY
  if (!apiKey) {
    const err = new Error('MINIMAX_API_KEY 未配置')
    err.code = 'missing_key'
    throw err
  }

  fs.mkdirSync(CACHE_DIR, { recursive: true })

  const requestBody = {
    model: 'speech-01-turbo',
    text: normalizedText,
    stream: false,
    voice_setting: {
      voice_id: 'male-qn-jingying',
      speed,
      vol: 0.92,
      pitch: 0,
    },
    language_boost: 'auto',
    audio_setting: {
      audio_sample_rate: 32000,
      bitrate: 128000,
      format: 'mp3',
    },
  }

  console.log('[minimax-tts] request body:', JSON.stringify(requestBody))

  const wait = MINIMAX_MIN_GAP_MS - (Date.now() - lastMiniMaxRequestAt)
  if (wait > 0) {
    await delay(wait)
  }
  console.log('[tts-queue] starting request, queue length:', queueLength)
  lastMiniMaxRequestAt = Date.now()

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 15000)

  let response
  try {
    response = await fetch(MINIMAX_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(requestBody),
      signal: controller.signal,
    })
  } catch (e) {
    clearTimeout(timeoutId)
    const err = new Error(`MiniMax TTS 网络请求失败: ${e.message}`)
    err.code = e.name === 'AbortError' ? 'timeout' : 'network_error'
    throw err
  }
  clearTimeout(timeoutId)

  console.log('[minimax-tts] response status:', response.status)

  const rawText = await response.text()
  console.log('[minimax-tts] response preview:', rawText.slice(0, 500))

  const payload = rawText ? JSON.parse(rawText) : {}
  if (!response.ok) {
    const msg = payload?.base_resp?.status_msg || payload?.message || `MiniMax TTS 请求失败: ${response.status}`
    const err = new Error(msg)
    const code = payload?.base_resp?.status_code
    if (code === 1008) err.code = 'insufficient_balance'
    else if (code === 1000 || code === 1001) err.code = 'auth_failed'
    else if (code === 1004) err.code = 'rate_limited'
    else if (response.status === 429) err.code = 'rate_limited'
    else err.code = 'service_unavailable'
    throw err
  }

  const base64Audio = payload?.data?.audio
  if (!base64Audio) {
    const err = new Error('MiniMax TTS 未返回音频数据')
    err.code = 'no_audio'
    throw err
  }

  const isHexAudio = typeof base64Audio === 'string' && /^[0-9a-f]+$/i.test(base64Audio) && base64Audio.length % 2 === 0
  const audioBuffer = isHexAudio
    ? Buffer.from(base64Audio, 'hex')
    : Buffer.from(base64Audio, 'base64')

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
