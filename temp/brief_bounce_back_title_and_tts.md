# 打回:两处严重问题,均已复现,不能提交

已经用真实代码独立复现了两个bug,报告里的"33通过/0失败"和"回调先校验state.currentTrack key是否一致"都对不上实际代码。

## 问题1:`cleanDisplayTitle` 里 `kw.test is not a function`,几乎必现崩溃

`kw` 定义成了普通函数:
```js
const kw = (str) => { ... return true/false ... }
```
但调用的地方写成了正则对象的 `.test()` 用法:
```js
if (!/\b(with|feat\.?|featuring)\b/i.test(inner) && kw.test(inner)) {   // 第32行左右
...
if (kw.test(tail.trim())) {   // 第41行左右
```
`kw` 是个函数不是正则，没有 `.test` 方法，这两处只要执行到就会抛 `TypeError: kw.test is not a function`。

复现（直接跑，必炸）：
```js
cleanDisplayTitle('Kalimboid - Live')                       // 抛错
cleanDisplayTitle('Under Pressure (Remastered)')             // 抛错
cleanDisplayTitle('Danger Zone - From ""Top Gun"" Original Soundtrack')  // 抛错
```
凡是标题末尾带 ` - ` 或者括号的（这在11000+首曲库里是大多数），只要播放到就会让 `renderHero()` 整个函数崩溃——因为 `heroTitle.textContent = ... cleanDisplayTitle(...)` 这行本身会抛错。**这不是边界情况，是几乎必现的主路径bug。**

**修复：把两处 `kw.test(x)` 改成 `kw(x)`。**

**要求：修完之后，请你自己真的跑一遍 brief 里给的全部测试用例（不要跳过、不要挑着跑），把每一条的实际输出打印出来给我看，不要只报"全部通过"这四个字。之前报告说测试脚本 `temp/test_clean_title.js` 跑出"33通过/0失败"，但这个文件现在磁盘上根本不存在，也没有贴出任何一行实际测试输出——这次请把完整的逐条测试输出直接贴在你的报告里。**

## 问题2:`pendingAutoExplainTimer`/`pendingAutoExplainKey` 从未声明，也从未在 `maybeAutoExplain` 里被赋值或校验

`playSong()` 里加了：
```js
if (pendingAutoExplainTimer) {
  clearTimeout(pendingAutoExplainTimer)
  pendingAutoExplainTimer = null
  pendingAutoExplainKey = null
}
```
但整个文件里搜不到 `let pendingAutoExplainTimer` 或任何形式的声明——这是一个未声明变量的读取，会直接抛 `ReferenceError: pendingAutoExplainTimer is not defined`，**每次调用 `playSong()`（也就是每次切歌/开始播放）都会崩溃**。

而且 brief 要求的核心逻辑——`maybeAutoExplain` 里设置定时器前记录 `pendingAutoExplainKey`、`setTimeout` 返回值存进 `pendingAutoExplainTimer`、回调触发时先校验 `state.currentTrack` 是否还等于这个 key——**这部分代码根本没有写**。现在的 `maybeAutoExplain`（3063-3102行）只是把 `1200` 改成了 `5000`，防重复触发的保护完全没有实现。

**修复要求：**

1. 在模块顶层（其他类似的模块级变量声明附近，比如 `activeExplainToken` 声明的地方）添加：
   ```js
   let pendingAutoExplainTimer = null
   let pendingAutoExplainKey = null
   ```

2. `maybeAutoExplain(item)` 内部，`setTimeout` 调用前：
   ```js
   pendingAutoExplainKey = explainKey
   pendingAutoExplainTimer = setTimeout(() => {
     // 先校验：歌曲是否还是当前播放的这首
     const currentKey = state.currentTrack ? `${state.currentTrack.name}::${state.currentTrack.artist}` : ''
     if (currentKey !== pendingAutoExplainKey) return
     pendingAutoExplainTimer = null
     pendingAutoExplainKey = null
     // ...原有的 cached / explainTrack 逻辑...
   }, 5000)
   ```

3. `playSong()` 里已经加的那段 `clearTimeout` 逻辑保留，现在变量声明补上之后就不会报错了。

**要求：修完后请实际在浏览器里播放一首歌、在5秒延迟内快速切换到另一首，打开控制台确认没有任何 `ReferenceError`/`TypeError` 报错，并且没有为已经切走的歌触发讲解。把控制台截图或者错误信息（如果还有的话）如实报告，不要只说"验证通过"。**

## 通用要求

这两个问题都是运行时错误，`node --check`/语法检查这类静态检查完全测不出来（引用未声明变量、调用不存在的方法都是合法JS语法）。以后这类改动，请你在提交前至少真的把改动后的函数单独拿出来跑一遍相关的几个真实输入，看它是否抛错，而不是只做语法检查就说"验证通过"。
