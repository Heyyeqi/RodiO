# Brief:移动端WebGL性能优化(4项,均在 pwa/earth3d.js)

背景:外部评审(Evan)反馈RodiO在手机上加载/渲染较重。已确认代码里已有一个粗糙的移动端判定 `isLowSpecularDevice()`(`earth3d.js:1052-1056`,视口最短边≤820 或 `matchMedia('(pointer: coarse)')` 命中),目前只用来选海洋高光贴图分辨率。本次要把这个判定复用/升级,驱动另外3个真实的性能开关。

**范围严格限定为下面4项,不要顺带重构其他渲染逻辑或引入新的依赖库(如 postprocessing、stats.js 等)。**

---

## 1. 移动端 pixelRatio 降级为 1.5

`earth3d.js:305` 现在是:
```js
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
```
改为:移动端(见第4项的判定函数)封顶 1.5,桌面端维持封顶 2 不变。

## 2. 移动端球体精度/抗锯齿降级

以下几处 `SphereGeometry` 目前精度都是 128×128,在移动端GPU上偏重:
- `earth3d.js:1744`(earthGeometry,主地球)
- `earth3d.js:1825` 和 `1851`(两个大气/云层球体)
- `earth3d.js:2737`(RDL瓦片球)
- `earth3d.js:3365`(另一层球体,注意确认这个具体是什么图层再改,不要盲目改)

移动端上把这些降到 64×64(桌面端不变,仍是128×128)。`earth3d.js:1863` 的 skyGeometry(32×32)和 `earth3d.js:2580` 的小球(16×16)已经很低精度,不用动。

另外 `earth3d.js:304` 的 `antialias: true` 在移动端也建议关闭(`antialias: !isMobile`),桌面端保持开启。

## 3. GPU能力诊断日志

目前完全没有GPU诊断日志。新增一段初始化时输出到 console 的诊断信息(默认只在第4项的 `?debugWebGL=1` 打开时才打印,避免污染生产环境的正常控制台):
- `renderer.capabilities.maxTextureSize`
- `devicePixelRatio`
- 是否命中移动端判定(第4项的判定结果)
- 通过 `WEBGL_debug_renderer_info` 扩展读取的GPU vendor/renderer字符串(如果拿不到就打印"unavailable",不要抛错)

## 4. 判定函数 + 调试参数

新增一个共享判定函数(建议命名 `isMobileDevice()`,与现有 `isLowSpecularDevice()` 并列或复用其内部逻辑,自行判断哪种更合适但不要重复造轮子),供上面1、2、3项统一调用。这个函数要能被两个URL参数覆盖:
- `?lite=1`:强制判定为移动端/低配模式(即使实际是桌面浏览器),用于人工测试降级效果
- `?debugWebGL=1`:开启第3项的GPU诊断日志打印(不影响1、2项的降级逻辑,只控制日志是否输出)

两个参数从 `window.location.search` 读取即可,不需要持久化。

---

## 验证方式(提交前请自行确认,提交后我会独立复核)

1. `git diff` 只涉及 `pwa/earth3d.js`,不要出现 `package.json`/`package-lock.json` 变化
2. 本地起服务后,分别访问不带参数 / 带 `?lite=1` / 带 `?debugWebGL=1` 的地址,确认:
   - 不带参数:桌面浏览器窗口下行为与现在完全一致(pixelRatio=2,球体128精度,无诊断日志)
   - `?lite=1`:控制台或肉眼可见球体精度变化,pixelRatio变化(可以在 `renderer.getPixelRatio()` 里打印确认)
   - `?debugWebGL=1`:控制台打印出GPU诊断信息
3. 提交信息里注明这4项分别改了哪几行,方便我逐条核对
