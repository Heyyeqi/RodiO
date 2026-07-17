# 修复:瓦片加载中的占位内容跟正式内容色调不匹配 + 瓦片永久放弃后无法再自动恢复

本轮阶段:生成候选(直接修复)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件,尤其不要碰 Camera Grammar V1 相关代码

---

## 背景

上一轮已经修了 `loadTileAsync()`(`earth3d.js:1201`)缺少 `img.decode()` 等待的问题,但用户实测5次里仍有2次在近景构图(`horizonSkim`)下出现硬边色块/对角线瑕疵(截图确认,东海/台湾附近海域出现一块偏亮偏白、边界笔直的区域)。这次继续查,找到了另一个更可能是主因的机制,不是decode()能解决的范围。

## 根因(已读代码确认)

**机制一:LOD切换时的占位内容跟正式瓦片色调不匹配**

`requestVisibleTiles()`(`earth3d.js:1139-1152`)在检测到LOD等级变化时(比如切到`horizonSkim`/`limbHero`这类需要更高精度瓦片的近景构图),会调用`resetAtlas()`,进而调用`redrawAtlasBaseLayer()`(`earth3d.js:1126-1137`):

```js
redrawAtlasBaseLayer() {
  const width = this.atlasCanvas.width
  const height = this.atlasCanvas.height
  if (!width || !height || !this.atlasContext) return
  if (bootstrapDayAtlasImage && bootstrapDayAtlasState === 'ready') {
    this.atlasContext.drawImage(bootstrapDayAtlasImage, 0, 0, width, height)   // ← 问题在这里
  } else {
    this.atlasContext.fillStyle = '#020514'
    this.atlasContext.fillRect(0, 0, width, height)
  }
  this.atlasTexture.needsUpdate = true
}
```

页面运行一段时间后,`bootstrapDayAtlasState`几乎总是`'ready'`(开机很早就加载完了),所以这个函数几乎总是走**把一张低分辨率的全球8K底图拉伸铺满整个瓦片图集**这条分支。之后各个高精度区域瓦片再逐个异步加载、逐个画上去覆盖这块拉伸的低清占位内容。**在这个覆盖过程完成之前,已经加载好的高精度瓦片格子,跟旁边还没轮到、仍显示拉伸低清底图的格子,亮度/色调必然对不上**——这正是截图里"一块区域明显偏亮偏白、边界是笔直的格子边界"的成因。只有近景构图才会触发LOD切换、才会看到这个过程,平时同一精度等级内平移不会重绘占位层,所以不会遇到。

**机制二:瓦片连续失败4次后永久放弃,不会再自动恢复**

`loadTileAsync()`(`earth3d.js:1219-1238`)的失败回调:

```js
() => {
  this.loadingTiles.delete(key)
  const attempts = (this.tileRetryCount.get(key) || 0) + 1
  this.tileRetryCount.set(key, attempts)
  const maxRetries = 4
  if (attempts > maxRetries) {
    console.warn('[tile-stream] tile unavailable, giving up after', attempts - 1, 'retries:', key, url)
    return
  }
  ...
}
```

`tileRetryCount`这个计数器只在瓦片**成功**加载时才会被清除(`earth3d.js:1205`,`this.tileRetryCount.delete(key)`),放弃时不会重置。如果某个瓦片这次因为网络抖动/mapbox限流真的连续失败4次放弃了,即使之后camera再次移动导致这个瓦片重新进入可见范围、重新调用`loadTileAsync()`,只要这次还失败一次,计数器已经是超过4的历史值,会立刻再次放弃,不会真正给到完整的4次重试机会——相当于一旦放弃就是这个session里永久放弃,那个格子会一直停留在低清占位内容上。这可以解释为什么5次测试里有2次"复现"且没有自动恢复的迹象。

## 修复方式

### 1. 高精度LOD等级下,占位内容改用中性深色填充,不用拉伸的低清全球图

```js
redrawAtlasBaseLayer() {
  const width = this.atlasCanvas.width
  const height = this.atlasCanvas.height
  if (!width || !height || !this.atlasContext) return
  // 高精度(区域瓦片)LOD下，拉伸的低清全球底图跟即将逐个加载进来的高精度瓦片色调差异明显，
  // 反而比纯色占位更容易被误认成渲染错误——只在低精度(全球视角)LOD下使用底图占位。
  const useBootstrapImage = bootstrapDayAtlasImage
    && bootstrapDayAtlasState === 'ready'
    && this.lodConfig?.lod === 'global'   // 具体判断条件请你确认 lodConfig.lod 在低精度等级下的实际取值，可能不是叫'global'，照实际枚举值改
  if (useBootstrapImage) {
    this.atlasContext.drawImage(bootstrapDayAtlasImage, 0, 0, width, height)
  } else {
    this.atlasContext.fillStyle = '#020514'
    this.atlasContext.fillRect(0, 0, width, height)
  }
  this.atlasTexture.needsUpdate = true
}
```
**这个判断条件需要你先查一下`lodConfig.lod`在各个精度等级下实际的取值枚举**(比如是字符串`'4k'`/`'8k'`/`'16k'`,还是别的命名),不要直接照抄我写的`'global'`这个占位值,用实际代码里的判断方式区分"全球视角LOD"和"近景区域瓦片LOD"。

### 2. 瓦片放弃后,如果之后重新变为可见,给一次全新的重试机会

在`updateStreaming()`(`earth3d.js:1154`附近)缓存未命中、准备调用`loadTileAsync(tile)`之前,判断一下:如果这个key的重试计数已经超过上限(说明之前放弃过),先清掉计数器再重新尝试:

```js
} else {
  stats.misses += 1
  this.cacheMisses += 1
  const key2 = key  // 沿用上面已有的 key 变量，不要重复计算
  if ((this.tileRetryCount.get(key2) || 0) > 4) {
    this.tileRetryCount.delete(key2)   // 之前放弃过，这次重新进入可见范围，给一次全新的重试预算
  }
  this.loadTileAsync(tile)
}
```

## 严格边界

**只允许改动**:`redrawAtlasBaseLayer()`内部的占位内容选择逻辑、`updateStreaming()`缓存未命中分支加一行重试计数器重置。

**禁止改动**:`loadTileAsync()`/`drawTile()`的其余逻辑、上一轮已经加的`img.decode()`修复、Camera Grammar V1相关任何代码、瓦片URL/数据源配置。

## 完成后请提供

1. git diff
2. `lodConfig.lod`在近景/远景两种情况下的实际取值,确认判断条件写对了
3. `horizonSkim`/`limbHero`连续硬刷新10次(比上次多测几次,这个问题本身概率性),记录复现次数,对比上一轮的"5次里2次"
4. 如果这次测试中触发了`[tile-stream] tile unavailable, giving up`,记录一下具体是哪个瓦片、发生在哪次测试里,以及后续camera移动后这个瓦片有没有真的恢复正常(验证机制二的修复)

## 验证方式

1. `horizonSkim`/`limbHero`连续硬刷新10次,记录复现率是否比上一轮(2/5)明显下降
2. 如果偶尔还是能看到瓦片处于加载中的状态,确认这次占位内容是深色而不是刺眼的拼接色块(即使还没完全消除瑕疵,视觉冲击也应该明显减弱)
3. 确认远景构图(`homeGlobe`/`farOrbit`)不受影响(它们本来就应该走"全球视角LOD"这条占位分支,行为不变)
4. 控制台无新增报错
