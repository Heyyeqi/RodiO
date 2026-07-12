// 彩云天气（Caiyun Weather）实时天气数据源
//
// 作为 fetchWeatherByCoords 的主力数据源：返回实时 skycon（天气现象）、
// 温度等。日出日落由 astronomy 模块的天文计算提供，本模块不负责。
//
// 失败时（status !== 'ok' 或网络错误）一律 throw Error，由调用方降级到
// OpenWeatherMap。

const CAIYUN_BASE = 'https://api.caiyunapp.com/v2.6'

async function fetchCaiyunRealtime(lat, lon) {
  const key = process.env.CAIYUN_API_KEY
  if (!key) throw new Error('CAIYUN_API_KEY 未配置')
  const url = `${CAIYUN_BASE}/${key}/${lon},${lat}/realtime`
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 8000)
  let res
  try {
    res = await fetch(url, { signal: controller.signal })
  } catch (err) {
    clearTimeout(timer)
    throw new Error(`彩云请求失败: ${err.message}`)
  } finally {
    clearTimeout(timer)
  }
  const data = await res.json().catch(() => ({}))
  if (data?.status !== 'ok' || !data?.result?.realtime) {
    throw new Error(`彩云返回异常: status=${data?.status}, hasRealtime=${!!data?.result?.realtime}`)
  }
  return data
}

// 彩云 skycon → 与 OpenWeatherMap main 同套枚举（Clear/Clouds/Rain/Snow/Haze/Fog/Dust）
function mapSkyconToMain(skycon) {
  if (!skycon) return 'Clear'
  switch (skycon) {
    case 'CLEAR_DAY':
    case 'CLEAR_NIGHT':
      return 'Clear'
    case 'PARTLY_CLOUDY_DAY':
    case 'PARTLY_CLOUDY_NIGHT':
    case 'CLOUDY':
      return 'Clouds'
    case 'LIGHT_HAZE':
    case 'MODERATE_HAZE':
    case 'HEAVY_HAZE':
      return 'Haze'
    case 'LIGHT_RAIN':
    case 'MODERATE_RAIN':
    case 'HEAVY_RAIN':
    case 'STORM_RAIN':
      return 'Rain'
    case 'FOG':
      return 'Fog'
    case 'LIGHT_SNOW':
    case 'MODERATE_SNOW':
    case 'HEAVY_SNOW':
    case 'STORM_SNOW':
      return 'Snow'
    case 'DUST':
    case 'SAND':
      return 'Dust'
    case 'WIND':
      return 'Clear'
    default:
      return 'Clear'
  }
}

// 彩云 skycon → 中文描述
function mapSkyconToDescription(skycon) {
  if (!skycon) return '未知'
  switch (skycon) {
    case 'CLEAR_DAY':
    case 'CLEAR_NIGHT':
      return '晴'
    case 'PARTLY_CLOUDY_DAY':
    case 'PARTLY_CLOUDY_NIGHT':
      return '多云'
    case 'CLOUDY':
      return '阴'
    case 'LIGHT_HAZE':
      return '轻度霾'
    case 'MODERATE_HAZE':
      return '中度霾'
    case 'HEAVY_HAZE':
      return '重度霾'
    case 'LIGHT_RAIN':
      return '小雨'
    case 'MODERATE_RAIN':
      return '中雨'
    case 'HEAVY_RAIN':
      return '大雨'
    case 'STORM_RAIN':
      return '暴雨'
    case 'FOG':
      return '雾'
    case 'LIGHT_SNOW':
      return '小雪'
    case 'MODERATE_SNOW':
      return '中雪'
    case 'HEAVY_SNOW':
      return '大雪'
    case 'STORM_SNOW':
      return '暴雪'
    case 'DUST':
      return '浮尘'
    case 'SAND':
      return '沙尘暴'
    case 'WIND':
      return '大风'
    default:
      return '未知'
  }
}

module.exports = { fetchCaiyunRealtime, mapSkyconToMain, mapSkyconToDescription }
