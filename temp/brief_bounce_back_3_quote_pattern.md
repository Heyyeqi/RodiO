# 第三轮小修复:原声带正则不匹配连续双引号 `""`

## 问题

`cleanDisplayTitle` 里的 `ostPatterns`（`pwa/index.html` 里 `cleanDisplayTitle` 函数内，大概在 `// 4. 原声带后缀` 注释下面）用的是 `"[^"]*"`（单个引号），但曲库里这类标题的真实数据（已经用 `hex()` 查过数据库确认，不是CSV转义误差）里引号是连续两个字符 `""`，不是一个。这3条测试用例目前会保留原样、清理不掉：

```
Danger Zone - From ""Top Gun"" Original Soundtrack
赤道和北极 - ""夏日里的春天"" 电视剧原声带
Go Solo (From the Original Soundtrack ""Honig im Kopf"")
```

## 修复

把这几个正则里所有的 `"[^"]*"` 改成 `"+[^"]*"+`（引号部分从"恰好一个双引号"改成"一个或多个双引号"），这样单引号 `"X"` 和双写引号 `""X""` 都能匹配。具体位置是 `ostPatterns` 数组里的所有条目，不止一处，请全部检查并改。

## 验证

再跑一遍完整33条测试用例（brief `temp/brief_title_display_cleanup.md` 里那份，加上之前失败的这3条），贴出完整的逐条实际输出，确认这次是 33/33，且之前已经通过的30条不能因为这次改动又变回失败。
