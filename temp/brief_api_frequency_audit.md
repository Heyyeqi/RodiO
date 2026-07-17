# Brief:API调用频率审查——除彩云外,确保及时又不浪费

## 已查到的现状(供参考,不用重新排查一遍,直接在这个基础上改)

后台常驻的定时/轮询机制一共这几处:

1. **彩云天气轮询**:`server.js:131` `WEATHER_POLL_INTERVAL = 5分钟`——本次不用管,已经确认过合理
2. **队列补货心跳**:`server.js:101` `QUEUE_HEARTBEAT_INTERVAL = 4分钟`——`server.js:1275`起,每4分钟检查一次`queueManager.size() < LOW_WATER_MARK`,满足才真正触发补货(还有个`HEARTBEAT_REPLENISH_COOLDOWN`防抖)。这个本身写得挺克制,注释里明确写着"后端独立补货心跳，不依赖前端在线"——是故意设计成不管有没有人在听都保持队列常满,方便你随时打开app都有歌。**这处不用动。**
3. **晨间播报**:`core/scheduler.js:46` `cron.schedule('0 7 * * *', ...)`——每天早上7点,固定调用一次`context.buildContext()`+`claude.askClaude()`(DeepSeek调用)+`broadcast()`。
4. **整点情绪检查**:`core/scheduler.js:58` `cron.schedule('0 9-22 * * *', ...)`——**每天9点到22点每个整点都触发一次**,一天14次,每次都是完整的`context.buildContext()`+`claude.askClaude()`(DeepSeek调用)+`broadcast()`,还会调用`appendToQueueFn`把结果塞进队列。
5. **七曜零点交接**:`core/scheduler.js:86` `cron.schedule('58 23 * * *', ...)`——每天23:58触发一次,这个不调用LLM,只是广播一句固定台词,成本可以忽略。
6. Spotify token刷新是按过期时间懒加载的(不是轮询),Spotify歌单缓存TTL是10分钟(`core/spotify.js:39`),这两处都合理,不用动。
7. 前端每秒轮询的`spotifyPlayer.getCurrentState()`(`pwa/index.html:1385`)读的是本地SDK内存状态,不打真实网络请求,不算浪费。

## 问题所在

第3、4两处(晨间播报+整点检查)**完全不检查有没有人连着**——`server.js`里维护的`wsClients`数组已经通过`scheduler.setWsClients(wsClients)`(`server.js:87`)传给了`core/scheduler.js`,但这两个cron job从来没检查过`wsClients`是不是空的。也就是说,就算你人不在、app也没开着,这两个定时任务照样每天固定跑14+1=15次完整的DeepSeek调用+构建上下文+广播——广播给零个客户端,纯粹浪费掉。

## 要做的改动

给`core/scheduler.js`里这两处cron(`0 7 * * *`和`0 9-22 * * *`)加一个前置检查:

- 如果`wsClients`里没有任何`readyState === 1`(在线连接)的客户端,**并且**队列长度已经不低于低水位线(不需要靠这次触发来补货保底),就跳过整个`context.buildContext()`+`claude.askClaude()`+`broadcast()`,只打一行日志说明跳过原因,直接return。
- 如果队列确实低于水位线(哪怕没人在线,也需要靠这次机会把队列填满,保持"随时打开都有歌"的体验),照常执行,不要因为没人在线就连队列填充这个副作用也一起跳过。

具体实现上,`core/scheduler.js`目前已经有`setResolveQueue`/`setAppendToQueue`这种"从server.js注入回调函数"的模式(`core/scheduler.js:13-19`),照着这个写法,新增一个`setQueueSizeGetter(fn)`,从`server.js`里把`() => queueManager.size()`和`LOW_WATER_MARK`这个值一起传进去(或者只传一个已经算好"是否需要保底"的布尔值获取函数,你自己判断哪种更干净),这样`scheduler.js`不用直接依赖`server.js`的内部变量。

## 不要做的事

- 不要动队列心跳(`server.js:1275`那段),那个已经是合理设计,"不依赖前端在线"是故意的
- 不要动彩云轮询、Spotify token刷新、Spotify歌单缓存TTL
- 不要改这两个cron本身的触发时间点(7点/9-22点整点),只加"是否值得触发"的前置判断,不改调度频率

## 验证方式

1. `node --check core/scheduler.js server.js`通过
2. 本地起服务,不打开任何浏览器标签页(模拟没有客户端连接),等到某个整点触发时刻,确认控制台打印"跳过"日志而不是真的调用DeepSeek(可以改本地系统时间测试,或者临时把cron表达式改成每分钟触发一次来快速验证,测完记得改回来)
3. 再测一次:不打开浏览器,但先把队列人为清空到低于水位线,确认这种情况下即使没人连着,cron照常执行、补货
4. 打开浏览器保持连接,确认正常触发不受影响
