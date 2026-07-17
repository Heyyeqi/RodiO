# Brief:歌曲名显示去除版本后缀(仅UI显示层,不改数据)

## 背景

用户反馈歌名太长,比如"云中加冕·序章 - 2.0纯享版"想只显示"云中加冕·序章"。查了下曲库(`track_profile.canonical_title`),这类带"Live/Remaster/纯享/伴奏"等版本后缀的歌名一共107首(约占已标注库的1%)。用户进一步要求也查一下原声带(OST)类和其他特殊情况——又额外查到15首"From 'X' Soundtrack"格式的原声带歌名，以及128首"Acoustic/Radio Edit/Extended/Bonus Track/Instrumental/Demo/Single Version/Album Version"等其他版本标记（这128首里有不少需要谨慎判断的边界情况，见下文"不要处理"部分）。格式都很杂。

## 范围(重要,请严格遵守)

**只改显示,不改数据。** 只修改 `pwa/index.html:2071` 这一行:
```js
heroTitle.textContent = state.currentTrack && state.currentTrack.name ? state.currentTrack.name : 'Waiting'
```
改成调用一个新的显示专用清理函数,例如:
```js
heroTitle.textContent = state.currentTrack && state.currentTrack.name ? cleanDisplayTitle(state.currentTrack.name) : 'Waiting'
```
**`state.currentTrack.name` 本身不能被修改**——这个字段还被搜索、黑名单排除(`disliked_tracks.json`的track_key)、MediaSession元数据等好几处逻辑用到原始值,只能加一层显示时的清理,不能改数据源头。

如果MediaSession的`title`(`pwa/index.html:2097`附近)显示上也想要一致的效果,可以一并用这个函数处理,但这不是强制项,你判断。

## 要实现的清理规则

新增函数 `cleanDisplayTitle(name)`,只处理"名字末尾的装饰性版本标记",规则如下,按顺序尝试:

1. 书名号格式:如果整个字符串匹配 `《标题》后缀` 这种形式(后缀不为空),只保留书名号内的内容。
   - 例:`《云中加冕·序章》2.0纯享` → `云中加冕·序章`

2. 尾部用 ` - ` 或 ` – ` 或 ` — ` 分隔、且分隔后内容匹配下列关键词(不区分大小写,关键词后面允许跟数字/年份/"from/at/on ..."等自由文本)的,整段尾缀去掉:
   - `Live`(包括 `Live from X`、`Live at X`、`Live On X, YYYY` 等所有以 Live 开头的尾缀)
   - `Remaster` / `Remastered` / `Remasterisé`(包括带年份如 `Remastered 2001`、`2014 Remaster`)
   - `纯享` / `纯享版`
   - `现场版`
   - `伴奏`
   - `抖音版`
   - `Acoustic`
   - `Radio Edit`(包括前面带人名/工作室的,如 `Thomas Jack Radio Edit`——即"XXX Radio Edit"这种整体也算)
   - `Extended`（`Extended Mix`、`Extended Version`）
   - `Bonus Track`
   - `Demo`（`Demo`、`Demo Version`）
   - `Single Version` / `Album Version`
   - `Instrumental Version`（注意：只匹配"Instrumental Version"或末尾单独一个"Instrumental"，不要匹配"Instrumental With XXX"这种——后面带具体乐器/编制说明的要保留，见下方"不要处理"部分的例子）

3. 尾部是单独一对括号 `(...)` 或方括号 `[...]`,且括号内内容匹配上面同一组关键词的(包括带年份,如 `(Remastered)`、`(2018 Remaster)`、`[2023 Remaster]`),整个括号一起去掉。

4. 原声带(Soundtrack/OST)后缀,这几种具体格式都要覆盖：
   - ` - From ""电影名"" Soundtrack` / ` - From ""电影名"" Original Soundtrack` → 去掉整个尾缀
   - `(From "电影名" Soundtrack)` → 去掉整个括号
   - ` - from The 电影名 Soundtrack`(注意小写from、无引号的情况也要匹配)
   - 中文格式： ` - ""剧名"" 电视剧原声带` / ` - ""剧名"" 电影原声带` → 去掉整个尾缀
   - `(From the Original Soundtrack ""电影名"")` → 这种"Soundtrack"在"From"和电影名之间的语序也要覆盖，去掉整个括号

## 明确不要处理的情况(避免误伤,务必仔细看)

- **字符串中间**的括号说明,只处理**末尾**的。例如 `Turandot (2008 Remastered Version), Act III` 末尾是 `, Act III`,不是版本关键词,这条**不应该被清理**,保持原样。
- 没有明显分隔符、关键词直接连在词里的,比如 `LOSS DELUXE`——`DELUXE`前面没有 ` - ` 或括号分隔，**不要处理**，保持原样，避免误伤专辑名/歌名里本来就有这类词的情况。
- **`(with 人名)` / `(feat. 人名)` / `(featuring 人名)` 这类是合作艺人credit,不是版本标记，绝对不要清理**。例如 `GOOD CREDIT (with Kendrick Lamar)` 必须保持原样，不能把 `(with Kendrick Lamar)` 当成版本后缀去掉。
- 括号内容如果是**具体的、有信息量的描述**而不是泛泛的版本标记词，不要清理。例如 `サクラ サクラ (Instrumental With 尺八・三味线)` 这个括号说明了具体用什么乐器演奏(尺八/三味线)，是有意义的信息，不是"这只是个器乐版"这种空洞标记，**不能清理**——判断标准是：如果"Instrumental"后面紧跟着"With/with + 具体名词"，说明这是描述性内容，不属于第2/3条要清理的范围。
- 多段混合、结构复杂的标题（比如同时有开头方括号标签 + 中间括号 + 结尾多个 - 分隔尾缀的），只要不确定清理是否安全，宁可保留原样或只清理最明确的一段，不用非要做到完美，不要为了处理这类复杂case过度设计规则。
- 清理后如果结果为空字符串或只剩标点，说明规则出错，应该保留原始值，不能显示空标题。

## 测试用例(务必逐条跑一遍,不要只测一两条就说完成)

清理后应该变化的（来自真实曲库数据）：
```
Kalimboid - Live                                          → Kalimboid
Adventure of a Lifetime - Live from Spotify London         → Adventure of a Lifetime
One Way Or Another - Remastered 2001                       → One Way Or Another
Under Pressure (Remastered)                                → Under Pressure
少女的祈禱 - Live                                           → 少女的祈禱
Hotel California - Live On MTV, 1994                       → Hotel California
Mo Money Mo Problems (feat. Puff Daddy & Mase) - 2014 Remaster → Mo Money Mo Problems (feat. Puff Daddy & Mase)
《云中加冕·序章》2.0纯享                                     → 云中加冕·序章
西湖水 (伴奏)                                                → 西湖水
Into1 - 纯享版                                              → Into1
Shallow [2023 Remaster]                                    → Shallow
You're The One That I Want (Remastered 2022)               → You're The One That I Want
Valerie - Live At BBC Radio 1 Live Lounge, London / 2007   → Valerie
Comment te dire adieu (Remasterisé en 2016)                → Comment te dire adieu
Good Luck, Babe! (Acoustic)                                → Good Luck, Babe!
Return To Innocence (Radio Edit)                           → Return To Innocence
God Particle (Bonus Track)                                 → God Particle
Fade To Black (Instrumental Version)                       → Fade To Black
Ain't No Mountain High Enough (Single Version)             → Ain't No Mountain High Enough
'Cross the Breeze (Album Version)                          → 'Cross the Breeze
Gold (Thomas Jack Radio Edit)                              → Gold
Freaks (Extended Mix)                                      → Freaks
Danger Zone - From ""Top Gun"" Original Soundtrack          → Danger Zone
Ever Love (From "Hana-Bi" Soundtrack)                      → Ever Love
City Of Stars (From "La La Land" Soundtrack)               → City Of Stars
Safe & Sound - from The Hunger Games Soundtrack            → Safe & Sound
赤道和北极 - ""夏日里的春天"" 电视剧原声带                    → 赤道和北极
Go Solo (From the Original Soundtrack ""Honig im Kopf"")   → Go Solo
```

清理后应该**保持不变**（验证不会误伤）：
```
Turandot (2008 Remastered Version), Act III   → 原样不变（版本说明不在末尾）
LOSS DELUXE                                    → 原样不变（无分隔符）
Symphony No. 3 in A Minor, Op. 56, MWV N 18 ""Schottische"": II. Scherzo. Vivace non troppo - Remastered 2024 → Symphony No. 3 in A Minor, Op. 56, MWV N 18 ""Schottische"": II. Scherzo. Vivace non troppo （只去掉末尾的 Remastered 2024，中间的移动说明保留）
GOOD CREDIT (with Kendrick Lamar)              → 原样不变（这是合作艺人credit，不是版本标记）
サクラ サクラ (Instrumental With 尺八・三味线)   → 原样不变（括号内是具体乐器说明，有信息量，不是空洞的版本标记）
```

以下这种复杂多段结构，不强求完美处理，能处理多少算多少，不要为了它过度设计规则：
```
[Theme Song] Wu Ji - Bibi Zhou Special Edition
Merry Christmas Mr. Lawrence (Heart of Asia) - Astro Heavenly Remix - Single Edit
```

## 验证方式

1. 写一小段独立的 Node 测试脚本（不用提交，跑完删掉即可，或者你判断要不要留），把上面所有测试用例跑一遍，逐条打印实际输出 vs 期望输出，全部匹配再提交
2. `node --check pwa/index.html` 不适用（这是HTML文件），改用浏览器里手动播放几首列表里的歌确认标题显示正常，普通没有后缀的歌名（比如就是"晴天"这种）显示完全不受影响
3. 确认 `state.currentTrack.name` 本身、MediaSession（如果你选择一并处理）之外的所有其他引用点（搜索、黑名单、track_key 生成）都还在用原始未清理的值
