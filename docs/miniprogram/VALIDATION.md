# 本地验证记录 · 2026-10-30

后续四页UI迭代新增记录见 [UI_VALIDATION.md](UI_VALIDATION.md)：当前客户端15项通过，官方编译和模拟器新版交互通过。以下保留首版本验证范围，勿将旧测试号验收当作正式登录验收。

## 已验证

- Python 3.12 隔离虚拟环境，安装项目 `backend/requirements.txt` 的 FastAPI 0.115.6 / Uvicorn 0.34.0，另装 pytest。
- 后端 20 项测试通过：会话/过期/生产登录配置、微信交换模拟、用户任务隔离、未完成任务禁止导出/删除、全文导出和删除、原子额度/去重、队列恢复、后台线程、请求频控、URL协议/内网/DNS/重定向/文件大小校验。
- 真实 RSS 适配与转写子进程调用链测试通过；上游 RSS、音频与模型进程均为受控模拟，不证明外部网络或真实语音识别可用。
- 小程序 8 项 Node 测试通过：并发登录复用、401 刷新、网络错误、导出错误、正式包禁止开发配置、离页停止轮询、确认弹窗、模式同步（部分断言合并在同一测试项）。
- 小程序 JS 语法与 JSON 配置解析通过。
- 现有 PodcastSearcher / AudioDownloader / SmartTranscriber 在隔离环境中可导入。
- 本机 ffprobe 可用；隔离环境已安装 FunASR，SenseVoiceSmall 与 VAD 权重已缓存到被 Git 忽略的 `data/miniprogram-model-cache/`。

- 实际监听 `127.0.0.1:8010` 的 HTTP 演示端到端验证通过：登录→搜索→单集→持久后台 worker→全文→TXT。启动和访问回环端口需要沙箱外权限，已通过工具审批执行。

## 开发者工具安装与官方编译检查

2026-10-30 经用户授权安装微信开发者工具 Apple Silicon 版 2.02.2609240，位置 `/Applications/wechatwebdevtools.app`。

- 安装包来自腾讯 `dldir1.qq.com/WechatWebDev/release/`；SHA-256 为 `16f1f876792bf5aa277fdd8dfc42edbc857277865741b18075c2e3a498027e6a`，与 Homebrew 官方目录记录一致。
- macOS `codesign --verify --deep --strict` 通过；签名主体 Tencent Technology (Shanghai) Company Limited，TeamIdentifier `FN2V63AD2J`；Gatekeeper `accepted`。
- 官方 `wcc` 检出 WXML 条件表达式使用 HTML 转义实体的问题，已将四个页面的 `&amp;&amp;` 修正为 `&&`。
- 修正后四份 WXML、全局 WXSS 均通过官方 `wcc` / `wcsc` 编译。
- 新增 `scripts/check_miniprogram_compile.py`，可重复执行官方编译检查，无登录、联网、上传或发布行为。
- 修正后后端20项、客户端8项测试通过。
- 用户已完成工具登录及开启服务端口，CLI 已成功连接本机 IDE。
- 新版 IDE 的普通导入与自动化入口均拒绝 `touristappid`，错误为 AppID 不存在。安装包代码中也明确拒绝游客/空 AppID 自动化。已请用户通过工具内“测试号”入口取得本人可用的测试 AppID，尚未注册或发布正式小程序。
- 用户已使用本人测试号导入项目，自动化连接端口9421已建立。当前项目已写入用户选择的测试AppID，未配置正式AppSecret。
- 模拟器发现确认弹窗按钮“确认并生成”超过微信四字限制，导致 fail 回调被当作取消。已改为“确认生成”，并将弹窗失败显示为可读错误；新增两项回归测试。
- 完整模拟器流程通过：搜索输入/结果渲染→选择单集→实际确认弹窗→新建任务并等待该任务完成→正文→无匹配/匹配关键词筛选→鉴权 TXT 下载与文件内容核对→离页返回仍可查看任务。
- 没有模拟 wx.request 或下载内容；只使用后端显式演示数据。没有触发文件发送。
- 模拟器未捕获 JS exception 或 console error。官方自动化截图已保存到 `screenshots/`，原图640×1386；已目视检查五张图的标题、正文、按钮、示例标识、底部导航及换行，未发现主要内容截断或遮挡。
- `screenshots/validation.json` 保存最新自动化结果，`screenshots/overview.png` 为实际四页截图拼接概览。
- 使用开发者工具2.02.2609240，当前本机基础库3.17.5；模拟器截图是本地开发验收，不代表iOS/Android真机分享验收。

- 外网只读验证通过：免费iTunes搜索“知行小酒馆”返回1个节目，公网校验下载RSS后解析出269集；未下载实际音频，未调用付费搜索/转写服务。

## 真实目录及本地语音模型

- 模拟器已切换真实模式，实际搜索“知行小酒馆”并打开首批20集列表，分页标志正常，没有提交第三方节目音频；异常列表为空。报告 `screenshots/real-catalog-validation.json`，截图 `06-real-search.png`、`07-real-episodes.png`。
- 通过 macOS Tingting 合成自制中文样例，实际时长11.326秒；经原项目 SmartTranscriber 调用本地 SenseVoice，正文及“播客、文字、语音”关键词核对通过。首次运行329.82秒包含权重下载，不能用作推理性能基准。
- 模型报告 `data/miniprogram-model-check/validation.json`，正文 `transcript.txt`；上述目录被 Git 忽略，保留在本机。复现入口 `scripts/check_miniprogram_transcription.py`。
- 实际 API 任务链路检查通过：ffprobe、STT子进程、SenseVoice、用户任务存储、鉴权TXT导出、删除与临时文件清理；缓存就绪后本次耗时11.01秒。音频下载传输由本地夹具复制自制样例替代，未覆盖公网节目音频下载。报告 `data/miniprogram-model-check/pipeline-validation.json`；入口 `scripts/check_miniprogram_transcription_pipeline.py`。
- 前端从鉴权 `/mini/session` 获取后端实际模式，避免切换服务后误保留演示标识；客户端测试覆盖登录刷新后的模式同步。

## 待单独验收

- 经授权的真实节目音频下载与长音频全流程、其他语言模型路由；中文短音频本地模型、免费iTunes搜索和真实RSS访问已验证。
- iOS/Android不同屏幕尺寸、长篇正文与真机交互复核；当前单一模拟器尺寸已检查。
- 正式 AppID 微信登录（当前尚未注册）、iOS / Android 真机文字复制、TXT 分享、长文本与后台恢复。
- Docker 镜像构建、目标服务器性能、TLS/域名配置、生产备份恢复、备案和平台审核。

## 范围与已知边界

原网页和原后端入口未改动；新增小程序服务独立运行。另修改原项目 `.gitignore` 以忽略小程序部署密钥、开发工具私有配置及本地数据/模型缓存。

此版本适用于继续本地开发和演示流程，不标记为可正式上线。没有付费接口调用、没有购买云资源、没有提交审核或发布。
