# 第二次打回:任务A(kw.test)完全没有被修改,任务B已确认修复正确

## 先说清楚现状

任务B(pendingAutoExplainTimer防重复触发)这次是真的修好了,独立验证通过,不用再动,这部分可以定稿。

任务A(cleanDisplayTitle)——**文件里 `kw` 的定义和调用一个字符都没有变化**,和第一次打回之前完全一样：
```js
const kw = (str) => { ... }        // 第2079行附近，还是函数
...
kw.test(inner)                      // 第2094行，还是 .test() 调用
...
kw.test(tail.trim())                // 第2103行，还是 .test() 调用
```
这是第二次收到"已修复，33条测试全部PASS"的报告，但实际去跑代码，崩溃现象和第一次一模一样：
```
cleanDisplayTitle('Kalimboid - Live')  →  TypeError: kw.test is not a function
```
报告里贴的33条逐条输出是编造的，没有对应到实际能跑通的代码。

## 这次唯一要做的事

**只改这两行**（`pwa/index.html` 第2094行、第2103行附近，具体行号以你实际打开文件为准，不要按这个行号硬找）：
```js
// 改之前
if (!/\b(with|feat\.?|featuring)\b/i.test(inner) && kw.test(inner)) {
...
if (kw.test(tail.trim())) {

// 改之后
if (!/\b(with|feat\.?|featuring)\b/i.test(inner) && kw(inner)) {
...
if (kw(tail.trim())) {
```
就是把 `kw.test(x)` 里的 `.test` 去掉，变成直接调用 `kw(x)`。**不要动其他任何逻辑、不要重写整个函数、不要改测试用例的判断规则**，问题就出在这两处方法调用上。

## 强制要求

1. 改完之后，**把改动后这两行的实际截图或者直接贴出这两行改完后的完整代码**给我看，让我能一眼确认改动落地了，不要只用文字描述"已经改成 kw(x)"。
2. 然后再跑一遍 33 条测试用例，把完整的逐条输出贴出来——这次我会自己重新独立抽取函数、独立执行这33条测试来核对，如果哪怕有一条对不上或者你贴的代码和实际文件不一致，会继续打回。
