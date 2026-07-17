# 修复:RDL瓦片加载缺少图片解码等待,导致近景构图出现硬边色块/对角线渲染缝隙

本轮阶段:生成候选(直接修复,风险低,复用已验证过的既有模式)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件,尤其是不要碰 Camera Grammar V1 相关代码(这是完全独立的另一个bug)
允许 commit:否,除非我后续明确批准

---

## 背景

用户反馈:在近景构图下(`limbHero`/`horizonSkim`这类),地球表面偶发出现硬边的矩形/对角线色块——一侧过曝发白,边界不跟随任何真实地理特征(海岸线/云层),是一条笔直的分割线。用户明确说这个问题"一直没解决",跨了多个session。

## 根因(已读代码确认,不是猜测)

`loadTileAsync()`(`earth3d.js:1201-1216`)里,`THREE.TextureLoader`的`onLoad`回调一触发,立刻调用`configureEarthTexture(texture)`和`this.drawTile(tile, texture)`:

```js
loader.load(
  url,
  (texture) => {
    this.loadingTiles.delete(key)
    this.tileRetryCount.delete(key)
    if (generation !== this.loadGeneration || modeAtRequest !== EARTH_MODE || key !== this.tileKey(tile)) {
      texture.dispose()
      return
    }
    configureEarthTexture(texture)
    this.addToCache(key, texture)
    this.drawTile(tile, texture)          // ← 问题在这里
    this.activeTiles.set(key, tile)
    if (!permanentlyUnavailable && isReady) {
      renderer.render(scene, camera)
    }
  },
  ...
)
```

`drawTile()`(`earth3d.js:1265-1279`)对`texture.image`直接做`this.atlasContext.drawImage(image, ...)`。**浏览器`<img>`的`onload`事件触发,不等于图片数据已经完全解码可以安全绘制**——这是真实存在的浏览器行为,在系统压力较大时更容易出现,会导致`drawImage`画出部分解码的、扁平过曝的色块,边界是硬边(不是渐变),这跟用户截图里的现象完全吻合。

**这个代码库里已经为另一张图片修过一模一样的问题**:开机时加载的8K基础日间贴图(`earth3d.js:895-923`,`bootstrapDayAtlasImage`)明确用了`img.decode().then(...)`等待真正解码完成后才标记为ready、才触发绘制,解码失败就兜底当作已完成(避免永久卡住):

```js
img.onload = () => {
  img.decode().then(() => {
    bootstrapDayAtlasImage = img
    bootstrapDayAtlasState = 'ready'
    if (tileManager?.redrawAtlasBaseLayer) {
      tileManager.redrawAtlasBaseLayer()
      requestRenderUpdate()
    }
  }).catch(() => {
    // decode() 失败兜底：按已解码对待，避免永久卡在 loading 态。
    bootstrapDayAtlasImage = img
    bootstrapDayAtlasState = 'ready'
    if (tileManager?.redrawAtlasBaseLayer) {
      tileManager.redrawAtlasBaseLayer()
      requestRenderUpdate()
    }
  })
}
```

但 RDL 瓦片流式加载这条路径(`loadTileAsync()`)当时没有一起改,是漏掉的另一处同类问题。只有近景构图才明显看得到,是因为近景下每块瓦片在屏幕上占比很大,解码不完整的瑕疵被放大;远景下同样的瑕疵因为瓦片本身很小,肉眼看不出来。

## 修复方式

照抄`earth3d.js:899-916`已经验证过的模式,给`loadTileAsync()`的`onLoad`回调加同样的`decode()`等待:

```js
loader.load(
  url,
  (texture) => {
    this.loadingTiles.delete(key)
    this.tileRetryCount.delete(key)
    if (generation !== this.loadGeneration || modeAtRequest !== EARTH_MODE || key !== this.tileKey(tile)) {
      texture.dispose()
      return
    }
    const applyTile = () => {
      configureEarthTexture(texture)
      this.addToCache(key, texture)
      this.drawTile(tile, texture)
      this.activeTiles.set(key, tile)
      if (!permanentlyUnavailable && isReady) {
        renderer.render(scene, camera)
      }
    }
    const img = texture.image
    if (img && typeof img.decode === 'function') {
      img.decode().then(applyTile).catch(applyTile)   // 解码失败兜底：仍按已加载处理，避免卡死（跟bootstrap atlas同一套处理）
    } else {
      applyTile()
    }
  },
  undefined,
  () => { /* 现有错误处理不变 */ }
)
```

**关键点**:
- `decode()`失败(`.catch`)也要执行`applyTile()`兜底,不能让瓦片永久卡在"已经从网络拿到但从来没画出来"的状态——这跟bootstrap atlas那次修复的兜底逻辑保持一致
- 不要改动`configureEarthTexture()`/`drawTile()`/`addToCache()`内部逻辑本身,只是把调用这几个函数的时机往后推迟到`decode()`完成之后
- 不要改动这次以外的任何RDL瓦片管理逻辑(重试/缓存/LOD切换等)

## 严格边界

**只允许改动**:`loadTileAsync()`(`earth3d.js:1201-1216`)的`onLoad`回调内部,加`decode()`等待。

**禁止改动**:`drawTile()`/`configureEarthTexture()`/`addToCache()`函数本身、瓦片重试/LOD/缓存逻辑、Camera Grammar V1相关的任何代码(这是完全独立的两个问题,不要在同一个改动里混在一起)。

## 完成后请提供

1. git diff
2. 在`limbHero`/`horizonSkim`这类近景构图下多次测试(建议连续刷新5-10次页面,因为这是一个时序竞争问题,不一定每次都触发),确认硬边色块/对角线瑕疵消失
3. 确认瓦片加载失败时的重试机制(现有的4次重试逻辑)没有被这次改动影响
4. 确认默认播放和其他所有主题/构图未受影响

## 验证方式

1. `limbHero`/`horizonSkim`,连续硬刷新页面5-10次,每次都截图观察地表是否有硬边色块/对角线瑕疵——因为是时序竞争问题,单次测试可能凑巧没触发,需要多测几次才能有信心确认修复生效
2. 确认瓦片加载失败(可以临时改一下tile URL制造404测试)时,4次重试机制仍然正常工作,不会因为加了`decode()`等待而被破坏
3. 确认远景构图(`homeGlobe`/`farOrbit`)和默认播放不受影响
4. 控制台无新增报错
