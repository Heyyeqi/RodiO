// 复刻 pwa/index.html 中 cleanDisplayTitle（修复后版本：kw.test -> kw()）
function cleanDisplayTitle(name) {
  if (!name || typeof name !== 'string') return name
  const original = name
  let s = name

  const bookMatch = s.match(/^《(.+?)》(.+)$/)
  if (bookMatch) {
    const inner = bookMatch[1]
    const suffix = bookMatch[2]
    if (inner && suffix && suffix.trim().length > 0) {
      s = inner
    }
  }

  const kw = (str) => {
    const t = str.trim()
    if (!t) return false
    if (/^(live|remaster(éd|ed|isé)?|纯享(版)?|现场版|伴奏|抖音版|acoustic|radio\s*edit|extended(\s*(mix|version))?|bonus\s*track|demo(\s*version)?|single\s*version|album\s*version|instrumental(\s*version)?)(\s.*)?$/i.test(t)) return true
    if (/^(.*\s)?(live|remaster(éd|ed|isé)?|纯享(版)?|现场版|伴奏|抖音版|acoustic|radio\s*edit|extended(\s*(mix|version))?|bonus\s*track|demo(\s*version)?|single\s*version|album\s*version|instrumental(\s*version)?)$/i.test(t)) return true
    return false
  }

  const parenMatch = s.match(/^(.*?)([\(\[])(.+?)[\)\]]\s*$/)
  if (parenMatch) {
    const inner = parenMatch[3].trim()
    if (!/\b(with|feat\.?|featuring)\b/i.test(inner) && kw(inner)) {
      s = parenMatch[1]
    }
  }

  const dashMatch = s.match(/(.*?)(?:\s[–—-]\s)(.+)$/)
  if (dashMatch) {
    const tail = dashMatch[2]
    if (kw(tail.trim())) {
      s = dashMatch[1]
    }
  }

  const ostPatterns = [
    /\s*[–—-]\s*From\s+"[^"]*"\s*Original\s*Soundtrack$/i,
    /\s*[–—-]\s*From\s+"[^"]*"\s*Soundtrack$/i,
    /\s*[–—-]\s*from\s+The\s+[^–—-]+?\s+Soundtrack$/i,
    /\s*[–—-]\s*"[^"]*"\s*(电视剧|电影)原声带$/,
    /\s*\(From\s+"[^"]*"\s*Soundtrack\)$/i,
    /\s*\(From\s+the\s+Original\s*Soundtrack\s+"[^"]*"\)\s*$/i,
  ]
  for (const p of ostPatterns) {
    if (p.test(s)) {
      s = s.replace(p, '')
      break
    }
  }

  s = s.trim()
  if (!s) return original
  return s
}

const testCases = [
  ['Kalimboid - Live', 'Kalimboid'],
  ['Adventure of a Lifetime - Live from Spotify London', 'Adventure of a Lifetime'],
  ['One Way Or Another - Remastered 2001', 'One Way Or Another'],
  ['Under Pressure (Remastered)', 'Under Pressure'],
  ['少女的祈禱 - Live', '少女的祈禱'],
  ['Hotel California - Live On MTV, 1994', 'Hotel California'],
  ['Mo Money Mo Problems (feat. Puff Daddy & Mase) - 2014 Remaster', 'Mo Money Mo Problems (feat. Puff Daddy & Mase)'],
  ['《云中加冕·序章》2.0纯享', '云中加冕·序章'],
  ['西湖水 (伴奏)', '西湖水'],
  ['Into1 - 纯享版', 'Into1'],
  ['Shallow [2023 Remaster]', 'Shallow'],
  ["You're The One That I Want (Remastered 2022)", "You're The One That I Want"],
  ['Valerie - Live At BBC Radio 1 Live Lounge, London / 2007', 'Valerie'],
  ['Comment te dire adieu (Remasterisé en 2016)', 'Comment te dire adieu'],
  ['Good Luck, Babe! (Acoustic)', 'Good Luck, Babe!'],
  ['Return To Innocence (Radio Edit)', 'Return To Innocence'],
  ['God Particle (Bonus Track)', 'God Particle'],
  ['Fade To Black (Instrumental Version)', 'Fade To Black'],
  ["Ain't No Mountain High Enough (Single Version)", "Ain't No Mountain High Enough"],
  ["'Cross the Breeze (Album Version)", "'Cross the Breeze"],
  ['Gold (Thomas Jack Radio Edit)', 'Gold'],
  ['Freaks (Extended Mix)', 'Freaks'],
  ['Danger Zone - From "Top Gun" Original Soundtrack', 'Danger Zone'],
  ['Ever Love (From "Hana-Bi" Soundtrack)', 'Ever Love'],
  ['City Of Stars (From "La La Land" Soundtrack)', 'City Of Stars'],
  ['Safe & Sound - from The Hunger Games Soundtrack', 'Safe & Sound'],
  ['赤道和北极 - "夏日里的春天" 电视剧原声带', '赤道和北极'],
  ['Go Solo (From the Original Soundtrack "Honig im Kopf")', 'Go Solo'],
  ['Turandot (2008 Remastered Version), Act III', 'Turandot (2008 Remastered Version), Act III'],
  ['LOSS DELUXE', 'LOSS DELUXE'],
  ['Symphony No. 3 in A Minor, Op. 56, MWV N 18 "Schottische": II. Scherzo. Vivace non troppo - Remastered 2024', 'Symphony No. 3 in A Minor, Op. 56, MWV N 18 "Schottische": II. Scherzo. Vivace non troppo'],
  ['GOOD CREDIT (with Kendrick Lamar)', 'GOOD CREDIT (with Kendrick Lamar)'],
  ['サクラ サクラ (Instrumental With 尺八・三味线)', 'サクラ サクラ (Instrumental With 尺八・三味线)'],
]

let pass = 0
let fail = 0
testCases.forEach(([input, expected], i) => {
  let actual
  let threw = null
  try {
    actual = cleanDisplayTitle(input)
  } catch (e) {
    threw = e.message
    actual = `[THREW] ${e.message}`
  }
  const ok = !threw && actual === expected
  if (ok) pass++; else fail++
  console.log(`#${String(i + 1).padStart(2, '0')} ${ok ? 'PASS' : 'FAIL'}`)
  console.log(`   输入:   ${JSON.stringify(input)}`)
  console.log(`   实际:   ${JSON.stringify(actual)}`)
  console.log(`   期望:   ${JSON.stringify(expected)}`)
  if (!ok) console.log(`   >>> 不匹配${threw ? ' (抛出异常)' : ''}`)
})
console.log(`\n=== 结果: ${pass} 通过 / ${fail} 失败 (共 ${testCases.length}) ===`)
