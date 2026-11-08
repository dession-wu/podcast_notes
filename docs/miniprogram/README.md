# 播客文字 · 微信小程序本地开发交付

已确认范围：免费内测，搜索→单集→任务→阅读→TXT 导出，不公开全文库，不支付。

本地开发已实现独立 API 与原生小程序。**官方编译、测试号模拟器演示完整流程、真实播客搜索与单集列表、自制中文音频本地 SenseVoice 识别均已通过。正式微信登录、真机导出、真实节目下载与长音频全流程仍待验收。**

更新：正式 AppID 经公网 Windows API 的微信登录、搜索和单集列表已验证；Windows 独立环境的实际 SenseVoice 及自制音频任务/导出测试通过，用户报告手机可使用。详细进度以 [WINDOWS_TUNNEL.md](WINDOWS_TUNNEL.md) 为准。新增中文对话模式的句级时间、说话人和阅读布局见 [DIALOGUE_TRANSCRIPTION.md](DIALOGUE_TRANSCRIPTION.md)；Windows 新模型与双人音频质量尚待验收。

交付时本机8010端口已运行 `--real` 模式，开发者工具可直接搜索真实节目；重启命令见下文。

## 本机启动

当前会话创建了隔离环境 `/tmp/podcast-mini-venv`（重启/清理临时目录后可能消失）。在项目根目录运行：

```sh
/tmp/podcast-mini-venv/bin/python scripts/run_miniprogram_local.py
```

只监听本机 `127.0.0.1:8010`，默认演示模式。健康检查 `http://127.0.0.1:8010/mini/health`；开发 API 文档 `http://127.0.0.1:8010/docs`。演示搜索返回体验节目，文字中明确注明演示，不会下载真实音频或调用付费服务。

其他机器创建 Python 3.12 虚拟环境，安装 `backend/requirements.txt`、`pytest`；无需安装浏览器即可运行本地演示。原项目 `core` 包会导入 Playwright Python 包，但小程序服务不会启动浏览器。

## 导入微信开发者工具

1. 微信开发者工具已安装到 `/Applications/wechatwebdevtools.app`。先启动并按界面完成首次提示；需要扫码时请由本人完成。命令行联调需开启“设置 → 安全设置 → 服务端口”。
2. 导入 `miniprogram/` 文件夹，使用本人微信登录，在AppID字段附近选择“测试号”。本次已确认新版工具拒绝 `touristappid` 游客占位值，不能依靠此占位值运行自动化；当前项目已使用用户导入的测试号。
3. 本地开发设置中，**仅本机开发时**关闭合法域名、TLS 和 HTTPS 证书校验。共享项目配置保持校验开启；本机通过已被Git忽略的 `project.private.config.json` 关闭校验，以连接回环HTTP服务。正式环境必须使用HTTPS并核对合法域名。
4. 保留 `config.js` 中本机 API 地址与 `developmentLogin:true`。默认演示模式可搜索任意名字体验流程；`--real` 模式请输入真实播客名，仅对已获授权的节目确认并提交，在“我的文字”查看结果。
5. TXT 分享与剪贴板能力必须在实际微信客户端继续验证，开发者工具可能不完整支持。

`127.0.0.1` 指向运行客户端的机器；手机不能访问电脑的此地址。本机开发登录故意禁止局域网远程访问。后续真机联调用正式微信登录和测试 HTTPS 服务，不要把开发认证模式直接暴露公网。

## 切换真实搜索与转写

停止演示服务，再运行：

```sh
/tmp/podcast-mini-venv/bin/python scripts/run_miniprogram_local.py --real
```

真实模式和演示模式默认使用两个数据库目录，避免混淆。真实搜索使用现有 `PodcastSearcher`；RSS/音频下载使用单独的公网校验器，不接受客户端传入本机路径。搜索来源、RSS 和音频站点可能无法从当前网络访问，界面会显示错误。

实际转写要求 FFmpeg/ffprobe、适配的本地 Whisper/SenseVoice 依赖与模型。首次下载模型可能产生大量流量并占用磁盘；本阶段不接入付费转写；本地模型的安装与实际识别进度以 VALIDATION.md 为准。自动语言路由使用原项目 `SmartTranscriber`。模型缺失时任务明确失败，不生成伪结果。

本机隔离环境已安装 FunASR 和 SenseVoice/VAD 权重，并通过约11秒自制中文语音验证；其他语言路由及长节目仍待验证。模型缓存位于被 Git 忽略的 `data/miniprogram-model-cache/`，启动脚本自动复用。

默认每用户每天 3 次、同时 1 个活动任务；全局最多 20 个活动任务，单 worker 串行转写。音频最多 150MB、实际时长最多 120 分钟，转写子进程最多 7200 秒。失败计入当日额度；删除不返还额度，避免绕过限制。上线前根据实测决定是否调整额度与资源。

## 数据与隔离

- 使用独立进程 `backend.mini.app:create_app --factory`，**不要将原 `backend.main` 直接作为小程序公网服务**。原网页 API、设置和全局文件库未开放到此服务。
- 开发身份由本机随机标识派生；这不是生产认证。正式环境仅使用微信 `code2Session` 返回的身份，客户端不可自报 openid。
- 会话 token 有效期 24 小时，数据库只存 token 摘要。AppSecret 和微信 session_key 不返回前端。
- 任务全文存入 SQLite，下载与模型临时文件完成/失败后删除，服务重启清理残留；模型输出目录也限制在任务临时目录，避免写入原网页全局文字库。
- 任务默认保留 7 天，定期清理；手动删除立即清除正文及标题，保留去内容的计数行直到保留期结束。目录保留节目元数据，不包含用户转写正文。
- SQLite/WAL、备份与导出文件仍应视为可能含有个人数据。删除不是磁盘取证级擦除；备份需独立制定到期删除策略。部署前确认隐私说明与实际策略一致。
- 重启后排队任务继续执行；运行中任务标记失败，用户可重新提交。此版本不支持多 worker/多副本，禁止将同一数据目录交给多个服务进程。

## 测试

项目根目录执行：

```sh
/tmp/podcast-mini-venv/bin/python -m pytest tests/test_miniprogram.py -q
node --test miniprogram/tests/client.test.cjs
python3 scripts/check_miniprogram_compile.py
node scripts/check_miniprogram_release.cjs
```

自动化验证与未完成项目详见 [TASKS.md](TASKS.md) 和 [VALIDATION.md](VALIDATION.md)。

发布预检在当前开发配置下应返回非零并显示阻止项；不要为了通过检查提前填写未部署的域名。后续计划及本轮UI优化见 [NEXT_STEPS.md](NEXT_STEPS.md)。

## 下一阶段

准备注册主体、AppID、实际内容来源与授权。需要付费资源时，先确认预算与部署方案；密钥只在服务器环境文件或密钥管理中配置，不发送到聊天、不复制进小程序。部署操作见 [DEPLOYMENT.md](DEPLOYMENT.md)，审核和隐私草稿见 [RELEASE_DRAFT.md](RELEASE_DRAFT.md)。

## 模拟器自动化与截图

本次已通过微信官方 `miniprogram-automator` 连接测试号模拟器，报告与截图位于 `docs/miniprogram/screenshots/`。可执行脚本 `scripts/check_miniprogram_simulator.cjs`，默认从临时目录 `/tmp/podcast-mini-qa/node_modules/miniprogram-automator` 加载SDK；也可通过 `MINI_AUTOMATOR_MODULE` 指向自己的安装路径。

前提：开发者工具已登录、服务端口已开启、测试号项目已导入，官方CLI以 `auto --auto-port 9421 --trust-project` 启动自动化，本机8010演示API已运行。脚本只连接本机演示，实际点击确认并新建任务，每次成功运行消耗一次演示用户当日额度；达到默认3次限制时会明确失败，不自动绕过额度。

脚本验证下载内容，不执行向他人发送文件。真机复制、分享与正式AppID登录仍需后续验证。

真实目录只读检查：`node scripts/check_miniprogram_real_catalog.cjs`，需要8010服务处于 `--real` 模式。只搜索和打开单集列表，不创建转写任务。实际模型与任务链路复现入口分别为 `scripts/check_miniprogram_transcription.py`、`scripts/check_miniprogram_transcription_pipeline.py`，使用自有短音频，参数见脚本 `--help`。
