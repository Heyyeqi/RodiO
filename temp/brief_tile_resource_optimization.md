# 瓦片资源优化:清理隐藏区域的无用预加载 + 过渡开始时预取终点瓦片

本轮阶段:生成候选(直接修复)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件,尤其不要碰 Camera Grammar V1/Auto 相关的任何逻辑
允许 commit:否,除非我后续明确批准

---

## 背景

线上(Railway)实测发现相机从远到近切换构图时,出现画面还没渲染到位的情况。排查中顺带发现另一个独立问题:有一套"84个命名区域"的高精度贴图叠加系统(日本/台湾/南美等),代码注释写着"预加载所有区域避免切换卡顿",**但这套系统在正式模式下被写死永远隐藏**(`updateRDLOverlays()`,`earth3d.js:3373`起的非inspect分支),导致每次打开页面都在白白下载这84个永远不会显示的区域贴图,还会跟真正会被渲染的瓦片系统抢并发下载连接数。这次一起修:

1. 84个区域改成真正需要时才下载
2. 相机过渡一开始就提前预取终点会用到的瓦片,不用等相机真的到了才开始下载

## 现状(已核实)

- `rdlMeshes = _RDL_REGIONS.map(...)`(`earth3d.js:3090`)构造时,`.map()`回调内部无条件调用`_loadRDLTile(0)`,84个区域页面初始化时全部立即开始下载
- `setRDLInspectRegion(regionId)`(`earth3dApi`导出块,`earth3d.js:6844`)是唯一的"选中区域进行inspect"入口,懒加载应该挂在这里
- `computeVisibleTileSet(cameraState)`(`earth3d.js:1074`)和`resolveEarthTextureLOD(lodManager, deviceCaps, cameraState)`(`earth3d.js:965`)都是纯函数,输入`{lon, lat, fovDegrees, distance}`这类值,不依赖真实相机对象——可以传入"终点构图"的数值算出终点需要哪些瓦片,不用等相机真的移动过去
- `FrontendTileStreamingManager.loadTileAsync()`(`earth3d.js:1201`)加载成功后**无条件**画进当前图集画布——如果直接用这个方法预取"终点"（可能是不同LOD等级、不同瓦片网格尺寸）的瓦片，会画到当前图集里错误的格子位置，污染正在显示的画面。**预取必须是只下载只存缓存、不画图集的静默模式**
- `addToCache(key, texture)`(`earth3d.js:1268`)只是Map操作，无渲染副作用，预取复用它是安全的

## 要做的事

### 1. 84个区域改成懒加载

```js
const rdlMeshes = _RDL_REGIONS.map((region) => {
  // ...现有mesh/material构造不变...
  const entry = { region, mat, mesh, loaded: false, loading: false, texture: null }
  // ...现有 _applyRDLTex / _tileCandidates 不变...
  const _loadRDLTile = (urlIndex = 0) => { /* 内容不变 */ }
  entry.startLoad = () => {
    if (entry.loaded || entry.loading) return
    entry.loading = true
    _loadRDLTile(0)
  }
  // 删掉原来这两行无条件调用:
  // entry.loading = true
  // _loadRDLTile(0)
  return entry
})
```

`setRDLInspectRegion(regionId)`里，设置`_rdlInspectRegion`之后补一行触发懒加载:
```js
setRDLInspectRegion(regionId) {
  _rdlInspectRegion = regionId || null
  if (_rdlInspectRegion) {
    const entry = rdlMeshes.find((e) => e.region.id === _rdlInspectRegion)
    if (entry) entry.startLoad()
  }
  refreshRDLTextureSampling()
  requestRenderUpdate()
  return _rdlInspectRegion
},
```

### 2. 过渡开始时静默预取终点瓦片

`FrontendTileStreamingManager`新增方法(成功回调只做缓存，不画图集，不触发render):
```js
prefetchTile(tile) {
  const key = this.tileKey(tile)
  if (this.tileCache.has(key) || this.loadingTiles.has(key)) return
  this.loadingTiles.add(key)
  const modeAtRequest = EARTH_MODE
  const generation = this.loadGeneration
  loader.load(
    this.tileUrl(tile),
    (texture) => {
      this.loadingTiles.delete(key)
      if (generation !== this.loadGeneration || modeAtRequest !== EARTH_MODE) { texture.dispose(); return }
      const img = texture.image
      const applyCache = () => { configureEarthTexture(texture); this.addToCache(key, texture) }
      if (img && typeof img.decode === 'function') {
        img.decode().then(applyCache).catch(applyCache)
      } else {
        applyCache()
      }
    },
    undefined,
    () => { this.loadingTiles.delete(key) }   // 预取失败静默放弃，不重试——真正需要时 updateStreaming() 自己的重试逻辑会接管
  )
}
```

新增模块级函数(放在`transitionToComposition()`附近):
```js
function prefetchTilesForCameraState(cameraState) {
  if (!tileManager) return
  const config = resolveEarthTextureLOD(tileManager.lodManager, renderer.capabilities, cameraState)
  const tiles = computeVisibleTileSet({ ...cameraState, lod: config.lod, tileCols: config.tileCols, tileRows: config.tileRows })
  tiles.forEach((tile) => tileManager.prefetchTile(tile))
}
```

`transitionToComposition()`内部，`targetZ`/`targetFov`都已经算出来之后（现有代码里就有这些变量，复用即可，不需要重新计算），加一行:
```js
prefetchTilesForCameraState({
  lat: comp.lat ?? (compositionKey === 'homeGlobe' ? CAMERA_PRESETS.globe.lat : 31.2304),
  lon: comp.lon ?? (compositionKey === 'homeGlobe' ? CAMERA_PRESETS.globe.lon : 121.4737),
  distance: targetZ,
  fovDegrees: targetFov,
})
```

## 严格边界

**只允许改动**:`rdlMeshes`构造逻辑(懒加载)、`setRDLInspectRegion()`加懒加载触发、`FrontendTileStreamingManager`新增`prefetchTile()`方法、新增`prefetchTilesForCameraState()`函数、`transitionToComposition()`里加一行预取调用。

**禁止改动**:`loadTileAsync()`/`drawTile()`/`updateStreaming()`/`computeVisibleTileSet()`/`resolveEarthTextureLOD()`本身的实现(只调用，不改)、Camera Grammar V1/Auto相关的任何逻辑、`_gramTransition`过渡的插值本身。

## 这一轮不做

不改变84个区域inspect模式本身的显示逻辑(sharpen/opacity/facing判断等)，只改下载触发时机；不给序列(`CAMERA_SEQUENCES`)的每一步单独加预取(序列内部调用的还是`transitionToComposition()`，自动继承这次的预取)。

## 完成后请提供

1. git diff
2. 硬刷新首页(不进inspect模式)的Network面板截图/记录，确认84个区域瓦片请求消失
3. 进入debug面板选中某个区域inspect的测试记录，确认懒加载正常工作、显示效果不变
4. 触发一次远景到近景的构图过渡，记录预取是否被触发(可以看Network面板里是否在过渡刚开始时就出现了目标瓦片的请求，不是等过渡完成后才出现)

## 验证方式

1. 硬刷新首页，Network面板确认不再有84个区域瓦片下载请求
2. debug面板选中区域inspect，确认这时候才开始下载，加载完成后正常显示
3. `?earthCandidate=cameraGrammarV1`或`cameraGrammarAuto`，触发`farOrbit`→`limbHero`这类远到近的过渡，观察Network面板确认预取在过渡开始时就已触发
4. 确认默认播放、其余候选、A-G轮已验证内容不受影响，控制台无新增报错
