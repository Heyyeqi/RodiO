// Manual Spotify Recommendations API probe.
// Run with:
// SPOTIFY_CLIENT_ID=... SPOTIFY_CLIENT_SECRET=... SPOTIFY_REFRESH_TOKEN=... node scripts/check-spotify-recommendations.js

const CLIENT_ID = process.env.SPOTIFY_CLIENT_ID
const CLIENT_SECRET = process.env.SPOTIFY_CLIENT_SECRET
const REFRESH_TOKEN = process.env.SPOTIFY_REFRESH_TOKEN

async function refreshAccessToken() {
  const res = await fetch('https://accounts.spotify.com/api/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      Authorization: 'Basic ' + Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString('base64'),
    },
    body: new URLSearchParams({
      grant_type: 'refresh_token',
      refresh_token: REFRESH_TOKEN,
    }),
  })
  const data = await res.json()
  if (!data.access_token) throw new Error('Token刷新失败: ' + JSON.stringify(data))
  return data.access_token
}

async function main() {
  console.log('刷新 token...')
  const token = await refreshAccessToken()

  // 用坂本龙一 Merry Christmas Mr. Lawrence 作为 seed
  const seedTrack = '4NFIUZzAAJ5cvw6WurI9Kl'

  console.log('调用 Recommendations API...')
  const res = await fetch(
    `https://api.spotify.com/v1/recommendations?seed_tracks=${seedTrack}&limit=5&target_energy=0.3&target_valence=0.3`,
    { headers: { Authorization: `Bearer ${token}` } }
  )
  const data = await res.json()
  console.log('HTTP 状态:', res.status)
  if (res.ok) {
    console.log('✓ 可用，返回曲目:')
    data.tracks?.forEach((track) => console.log(`  ${track.name} / ${track.artists[0]?.name}`))
  } else {
    console.log('✗ 失败:', JSON.stringify(data.error))
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
