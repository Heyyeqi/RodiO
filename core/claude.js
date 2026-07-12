const OpenAI = require('openai')

const client = new OpenAI({
  apiKey: process.env.DEEPSEEK_API_KEY,
  baseURL: 'https://api.deepseek.com',
})

// 从可能包含多余文字的字符串中提取第一个完整 JSON 对象
function extractFirstJson(text) {
  const start = text.indexOf('{')
  if (start === -1) return null
  let depth = 0
  for (let i = start; i < text.length; i++) {
    if (text[i] === '{') depth++
    else if (text[i] === '}') {
      depth--
      if (depth === 0) return text.slice(start, i + 1)
    }
  }
  return null
}

async function askClaude(context) {
  const response = await client.chat.completions.create({
    model: 'deepseek-v4-flash',
    messages: [
      { role: 'system', content: context.system },
      ...context.messages,
    ],
    thinking: { type: 'disabled' },
  })

  const raw = response.choices[0]?.message?.content || '{}'

  // 先尝试直接解析
  try {
    return JSON.parse(raw)
  } catch {
    // 提取第一个完整 JSON 对象
    const fragment = extractFirstJson(raw)
    if (fragment) {
      try {
        return JSON.parse(fragment)
      } catch {
        // ignore
      }
    }
    return { say: raw, play: [], replace_pool: false, reason: 'JSON 解析失败', segue: '' }
  }
}

// 给定中文标题+艺人，猜测外语歌曲的原始语言标题（日文/罗马字/英文等）
// 返回 { candidates: string[], confidence: 'high'|'medium'|'low'|'unknown' }
// 解析失败/请求异常一律返回 { candidates: [], confidence: 'unknown' }，不抛异常
async function guessOriginalTitle(name, artist) {
  const fallback = { candidates: [], confidence: 'unknown' }
  if (!name) return fallback
  try {
    const response = await client.chat.completions.create({
      model: 'deepseek-v4-flash',
      messages: [
        {
          role: 'system',
          content:
            '你是一个音乐曲库助手。用户会给你一首歌的中文译名和艺人名。' +
            '如果这是外语歌曲（日文/韩文/英文等）的中文译名，请推测 1-3 个可能的原始语言标题（原文、罗马字或英文均可）。' +
            '如果判断不出来，或者本来就不是外语歌（如华语原创），请明确返回空候选。' +
            '只输出严格 JSON，不要任何额外文字，格式：' +
            '{"candidates": ["原标题1", "原标题2"], "confidence": "high" | "medium" | "low" | "unknown"}。' +
            'confidence 表示你对猜测的把握：明确知道原曲填 high，较有把握填 medium，只是猜测填 low，完全不知道填 unknown。',
        },
        {
          role: 'user',
          content: `歌名：${name}\n艺人：${artist || '未知'}`,
        },
      ],
      thinking: { type: 'disabled' },
    })

    const raw = response.choices[0]?.message?.content || '{}'
    let parsed = null
    try {
      parsed = JSON.parse(raw)
    } catch {
      const fragment = extractFirstJson(raw)
      if (fragment) {
        try { parsed = JSON.parse(fragment) } catch { parsed = null }
      }
    }
    if (!parsed || !Array.isArray(parsed.candidates)) return fallback
    const candidates = parsed.candidates
      .filter((c) => typeof c === 'string' && c.trim().length > 0)
      .map((c) => c.trim())
      .slice(0, 3)
    const confidence = ['high', 'medium', 'low', 'unknown'].includes(parsed.confidence)
      ? parsed.confidence
      : 'unknown'
    return { candidates, confidence }
  } catch {
    return fallback
  }
}

module.exports = { askClaude, guessOriginalTitle }
