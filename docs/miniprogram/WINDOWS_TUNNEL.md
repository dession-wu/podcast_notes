# 校园网 Windows 穿透联调

用户已选择内网穿透。目标 Windows 的 WLAN IPv4 为 10.197.209.65，网关 10.197.0.1；没有路由器管理权限。尚未安装穿透客户端、创建隧道或修改 DNS。

## 第一阶段：仅验证校园网能否连接隧道

采用 Cloudflare Quick Tunnel 进行临时连通测试。此阶段不要求 Cloudflare 账号或改动 podnotes.cloud 的 DNS。

1. Windows PowerShell：`winget install --id Cloudflare.cloudflared --exact`。完成后重新打开 PowerShell，执行 `cloudflared --version`。
2. 将 `scripts/windows_tunnel_probe.py` 复制到目标 Windows 下载目录，执行 `python "$env:USERPROFILE\Downloads\windows_tunnel_probe.py"`，保持窗口打开。它仅监听 127.0.0.1:18010，只提供 `/tunnel-check` 固定 JSON；不会列出文件或提供播客 API。
3. 在另一个 PowerShell 执行 `cloudflared tunnel --url http://127.0.0.1:18010`。保持窗口打开，将生成的 `https://….trycloudflare.com` 地址交给开发端验证。
4. 手机关闭 Wi-Fi、使用移动网络打开上述地址加 `/tunnel-check`，应看到 `service: podnotes-tunnel-probe`、`probe_only: true`、`backend_ready: false`。
5. 如遇超时，记录错误及连接日志，勿关闭整个系统防火墙或变更校园网络控制。校方限制需通过允许的接入方式解决。
6. 测试完成在两个窗口按 Ctrl+C 停止。临时地址停止后失效。

当前 Mac 已验证脚本可响应连通检查；尚未在 Windows 或校园网实测。Quick Tunnel 没有可用性保证，只适合开发测试。此阶段未发送播客内容到隧道。

## 第二阶段：自有域名与真实后端

- 成功验证校园网连接后，将 podnotes.cloud 添加到用户自己的 Cloudflare 账号。普通全区托管方案需要在注册商修改权威 DNS；切换前导出并核对所有现有 DNS 记录，向用户展示变更后再执行。域名注册商不需要更换。
- 在官方后台 Networking > Tunnels 创建命名隧道，Windows 使用后台生成的安装命令连接。隧道 token 仅在目标电脑输入，不发到聊天或提交 Git。
- 初次路由可配置 `api.podnotes.cloud` → `http://127.0.0.1:18010`，验证自有域名 HTTPS 和 `/tunnel-check`；此时仍未部署真实后端。
- 正式后端及微信登录配置、依赖和模型验收完成后，路由改到 `http://127.0.0.1:8010`。禁止暴露旧桌面管理服务或将当前开发登录后端直接发布。
- 验证 `python scripts/check_miniprogram_public.py` 后再切换小程序客户端配置；真机测试结果取决于微信合法域名、备案及调试条件，穿透本身不解决这些要求。
- 请求和响应会经过 Cloudflare；在提供真实用户服务前更新实际处理方说明。中国内地校园网与手机网络的可达性、延迟均需实测，不作稳定性承诺。

官方文档：
- https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
- https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/
- https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/

## 2026-11-01 外网验收

Windows 已安装 cloudflared 2026.10.7。复制脚本时出现 HTML 换行标记，随后用 PowerShell 重建最小探针，响应为 `podnotes-tunnel-ok`（不同于原 JSON 探针）。

用户日志显示已注册 tunnel connection；两个区域的 TCP / HTTP2 检查均通过，一处 UDP 检查失败，日志建议使用 HTTP2。没有要求修改校园防火墙。

开发端经公网 HTTPS 请求 `https://harold-letters-flux-concerns.trycloudflare.com/tunnel-check`，实际返回 HTTP 200，正文 `podnotes-tunnel-ok`。已验证校园 Windows 探针可经临时隧道访问，尚未验证手机移动网络、播客后端、微信登录或自有域名。临时地址可能随进程停止或重建失效。

下一项依赖：用户在自己的 Cloudflare 账号准备域名接入；先核对当前 DNS，再执行权威 DNS 变更、创建命名隧道及配置 api 子域名。尚未执行这些外部变更。

## 自有域名已连通

用户确认阿里云为实际注册商（此前腾讯云记录不准确），Cloudflare 名称服务器为 irena.ns.cloudflare.com 与 scott.ns.cloudflare.com。用户已完成命名隧道连接（界面 Healthy）和 api 子域名路由，手机移动网络访问成功。开发端独立请求 https://api.podnotes.cloud/tunnel-check 得到 HTTP 200 与 podnotes-tunnel-ok。

当前公开的是 18010 端口探针；还未部署 Windows 播客 API。准备了 scripts/run_miniprogram_server.py：固定正式 AppID、关闭开发 / 演示模式、回环 8010、隐藏输入 AppSecret、不自动保存密钥。后续启动需保持终端打开，尚无 API 后台自启动。微信登录及 Windows 模型转写尚未验收。

## 后端本机启动通过，等待切换路由

用户报告 Windows Python 3.12.3 / conda 25.7.0，完成部署步骤，本机 `/mini/health` 返回 status=ok、development=false、demo=false。此结果尚未证明微信 AppSecret 有效或模型已就绪。

Mac 端小程序 `miniprogram/config.js` 已配置 `https://api.podnotes.cloud` 与 developmentLogin=false。发布配置预检及官方 WXML/WXSS 编译通过。客户端测试原先隐式依赖开发配置，已将配置隔离为测试夹具，并补充正式 HTTPS 下传递 wx.login code 的检查，共 16 项通过；该测试使用模拟微信接口，不代替真实登录。

用户接下来将 Cloudflare 已发布应用路由由 127.0.0.1:18010 修改为 HTTP 127.0.0.1:8010。待公网健康检查后再验证微信域名配置、真实登录与转写模型。当前没有上传或发布小程序。

## 公网播客 API 健康检查

用户确认路由切换后手机访问 `/mini/health` 成功。开发端 curl 也返回 HTTP 200，JSON 为 status=ok、development=false、demo=false，HTTPS 已到达实际 API。Python urllib 检查单次收到 403，原因未确定，不能将全部客户端可达性视为已验收，也不应因此直接关闭 Cloudflare 防护。下一步检查微信合法域名配置与真实 wx.login；当前尚未确认 ICP 备案完成。转写模型仍未安装验收。

自动检查差异补充：使用 curl 模拟 Python-urllib/3.12 标识时返回 403 / Cloudflare 1010，普通 curl 正常。已为检查脚本增加 Podnotes-Deployment-Check/1.0 标识；本轮 Python 重测遇 TLS EOF，尚未得到通过结论，不能宣称自动检查完全通过。真实微信请求仍需验证，不要求全站关闭防护。

## 微信登录联调定位

用户确认 request/downloadFile 合法域名保存成功。发布配置预检通过。微信官方模拟器联调：独立 wx.login 返回 login:ok 且包含 code；将该新 code 发送至公网 /mini/login 得到 HTTP 401、通用微信登录失败，尚未拿到会话，因此搜索与 RSS 未通过，不是完整端到端成功。

为定位上游错误，backend/mini/app.py 新增仅输出整数微信 errcode 的失败提示和告警日志，不返回原始响应或密钥；部署 ZIP 同步更新。20 项后端测试通过。等待用户更新 Windows app.py 并重启后再检查，尚不能认定是 AppSecret 错误。

重启后再次诊断：wx.login 正常返回 code；后端 /mini/login 返回 HTTP 401、微信错误码 40125（invalid appsecret）。下一步由用户在正式小程序 wxcf1571f64e71f165 后台核对有效 AppSecret，清除当前 PowerShell 中可能残留的 WECHAT_APP_SECRET 后重新启动并隐藏输入。未取得或展示密钥，未重置微信密钥。搜索与真实转写仍未通过。

40125 输入排查补充：用户确认直接复制后台密钥，日志显示 Python getpass 提示后正常启动。检查 Python 3.12 win_getpass 实现和 CPython issue 81607 后发现 Ctrl+V 可能被当作 0x16 控制字符，而非实际粘贴；当前只是候选原因，尚未在用户电脑证实。改用 PowerShell Read-Host -AsSecureString 读取，经 NetworkCredential.Password 设置仅当前进程环境，再启动原 launcher，可避免该 getpass 输入路径。无需用户重下代码或重置密钥即可试验。新版 launcher 增加空白 / 控制 / 非 ASCII 字符检查，ZIP 已同步；源码语法通过，Windows 输入行为仍需实测。

用户改用 PowerShell Read-Host -AsSecureString 经进程环境传入密钥后重启，启动日志不再出现 getpass 提示，进程 24600。重新诊断 wx.login 成功取得 code，但公网登录请求自动化响应超时；完整页面重试提示网络连接失败，curl 公网 /mini/health 也在 15 秒内无响应。此次不能确认密钥已有效或 40125 已解决。需比对 Windows 本机健康接口、手机移动网络公网接口及服务器新请求日志，避免将开发端网络问题误判为校园隧道断开。

进程 6520 本机 curl 曾连接失败，但随后 Windows 确认该进程仍监听 8010；开发端公网健康接口恢复 HTTP 200。趁连通进行单次 wx.login / backend.login 诊断，再次得到 40125。不能将之前短暂不通确认为进程崩溃，也尚未证明 getpass 粘贴是根因。下一步仅核对实际传入密钥的格式元数据（存在、长度、32 位十六进制）与后台 AppID 对应关系，不要求重置密钥或展示密钥。

## 密钥输入修正后登录成功

用户在原 PowerShell 环境检查发现 WECHAT_APP_SECRET 存在但长度仅 1、hex32=false；随后按提示在 Read-Host 等待期间从微信后台复制，使用 Get-Clipboard 读取并启动。开发端重新测试，wx.login 成功，公网 /mini/login 返回 HTTP 200 且包含会话（未输出 token）。独立鉴权搜索返回 HTTP 200、1 个结果。

页面端完整流程尚未通过：出现通用请求失败和间歇性请求超时；已生成一次 search.png，但未取得单集列表验收截图。后续分阶段诊断也发生自动化响应超时。不能认定转写或端到端流程已完成。需要 Windows 后端同期 POST/GET 状态和 ERROR/Traceback，以区别后端异常、网络与自动化问题；不再反复要求更换密钥。

## Windows 部署包缺失模块修复

用户提供的日志.txt 明确显示：鉴权和搜索已成功，单集列表 GET 返回 500，AudioDownloader 导入 backend.config.download_settings 时抛出 ModuleNotFoundError。根因为此前 Windows ZIP 漏打包 backend/config，不是要求用户再配置可选搜索供应商密钥。

新增 scripts/build_miniprogram_server_bundle.py，采用源码目录白名单生成完整 ZIP，并额外生成仅包含 backend/config 三个 Python 文件的 podnotes-windows-config-fix.zip。补丁解压目标为现有 E:\podnotes\podnotes-server，保留 data 和用户环境。两个包均不包含密钥、数据库或模型。

scripts/check_miniprogram_server_bundle.py 在临时解压目录中使用隔离 Python 进程检查实际导入链，并以模拟 RSS 传输测试非演示单集接口，已通过。此结果不代替 Windows 实机、真实 RSS 或转写验收。用户尚需停止 API、解压补丁、原 PowerShell 重启；Cloudflare 路由无需修改。日志末尾 WinError 10054 单独保留，未确认与此前间歇性超时的因果关系。

## 补丁重启后真实链路通过（2026-11-02）

用户确认 Windows 已重启。开发端公网健康检查返回 status=ok、development=false、demo=false。官方微信开发者工具中独立诊断：wx.login 正常，公网登录 200、搜索 200（1 个结果）、单集列表 200（20 条）。随后实际页面重新登录、搜索“知行小酒馆”、点击结果进入单集列表全部通过，截图及 validation.json 位于 screenshots/windows-integration。单集列表原 500 已修复。

此轮为官方模拟器经公网访问 Windows 实际 API，未提交音频，未验证 Windows 模型、转写、TXT 导出或手机端完整流程；也未上传、提审或发布小程序。下一步先检查 Windows 当前 Python 环境的模型依赖、ffmpeg/ffprobe 和时区数据，再进行受控短音频验证。

用户依赖日志（日志(1).txt）：当前 base 环境 E:\Anaconda\Lib\site-packages 已安装 funasr 1.3.1、torch/torchaudio 2.11.0、modelscope 1.36.0、tzdata 2025.3；ffmpeg 和 ffprobe 8.1.1 均可启动并输出版本。pip show 只证明安装元数据存在，尚未验证实际导入、二进制依赖、模型加载与转写。下一步先进行不下载模型的实际导入及 CPU 张量检查，不盲目重装现有依赖。

用户实际导入日志（日志(2).txt）：最终打印 IMPORT_OK、CPU_TEST=2.0、CUDA_AVAILABLE=False、TIMEZONE=Asia/Shanghai，但 FunASR→sklearn→pandas→pyarrow 链出现 NumPy 1.x 编译扩展与当前 NumPy 2.2.6 不兼容的 ImportError。顶层导入完成不代表依赖链无异常，尚未加载模型。建议为项目新建无 system-site-packages 的 .venv，使用 NumPy 1.26.4、FunASR 1.3.1、同版本 torch/torchaudio 2.11.0 CPU 包及 API requirements；先在新环境完成导入和 pip check，后续再切换服务 Python。当前 base 服务可继续运行，不修改全局 Anaconda 依赖。Windows 环境尚待用户创建，未宣称兼容性验收通过。

用户已完成独立 .venv 安装：pip check 显示 No broken requirements found，实际导入输出 IMPORT_OK、NumPy 1.26.4、CPU_TEST 2.0、Asia/Shanghai，未再出现原 NumPy 错误。此为 Windows 依赖检查通过，模型仍待验证。

准备 deploy/miniprogram/podnotes-windows-audio-check.zip，含 11.33 秒自制合成中文 WAV 和两个已有检查脚本；ZIP CRC、脚本语法、音频格式检查通过。脚本缓存路径统一至 data/model-cache，与正式 launcher 一致，避免切换后重复下载。先运行 check_miniprogram_transcription.py 验证真实模型并将子进程日志写入 data/miniprogram-model-check/worker.log；成功后运行 check_miniprogram_transcription_pipeline.py 验证实际 STT、任务、TXT 导出和删除，但替换音频下载为本地样例，使用临时数据和本地测试登录，不会监听端口或修改线上生产登录。Windows 两项执行结果尚待用户提供，不是公网音频下载或手机验收。

## Windows 实际模型与本地任务流程通过

用户返回两项执行结果均为 passed：11.326125 秒自制中文音频经 SmartTranscriber / SenseVoice 输出 144 字、关键词均命中，首次检查耗时 270.7 秒；当前 funasr 1.3.1、torch/torchaudio 2.11.0+cpu。随后完整本地任务流程耗时 9.47 秒，通过 ffprobe、实际 STT 子进程、用户任务保存、鉴权 TXT 导出、删除及临时文件清理。首次耗时可能含模型下载和初始化，不能据此推算长音频速度；后一次也不是通用性能基准。

仍未覆盖真实公网音频下载或手机端任务全流程。下一步在原持有 AppSecret 环境变量的 PowerShell 中停止旧 API，使用 .\.venv\Scripts\python.exe scripts/run_miniprogram_server.py 重启。同一 data/miniprogram-server 和 data/model-cache 路径继续使用，转写子进程取 sys.executable，因此也将使用新环境；不调整 Cloudflare 或公开开发登录。尚待用户确认生产 API 已完成环境切换。

## 新环境重启后的公网回归与真机预览

用户确认按新环境命令重启。开发端再次验证公网 /mini/health 为 ok、development=false、demo=false；官方模拟器新 wx.login 后公网登录 200、搜索 200（1 个结果）、单集列表 200（20 条）。这不额外证明公网转写已完成。

尝试官方 CLI preview 生成手机二维码：首轮沙箱本机端口 EPERM，经用户授权扩展权限后进入微信 AppID 权限信息阶段，但连续两次返回 ECONNRESET（TLS 建立前连接断开），未成功生成本轮二维码。project.config.json AppID 仍为 wxcf1571f64e71f165。该失败发生于开发者工具访问微信预览服务，不能据此推断 Windows API 故障。下一步由用户在开发者工具界面点“预览”，如能生成二维码，再用管理员微信扫码并选择自己有权处理的短单集验证下载、转写、TXT 保存及返回任务页恢复；如界面同样失败，需要对应报错再排查。尚未上传发布版、提审或正式发布。

用户随后确认手机可正常使用，并提出转录大段、缺少时间和说话人的质量问题。已增加独立的 dialogue 模式及结构化阅读/导出，默认 basic 不变以便先验收模型；本机回归、模拟器样例和真实单人音频已通过。Windows 新模式及真实双人节目尚待更新验证，进度和更新包见 DIALOGUE_TRANSCRIPTION.md。未上传审核版或正式发布。

## GPU 硬件已确认，等待 CUDA 环境切换

日志(3).txt：NVIDIA GeForce RTX 4060 Ti、16380 MiB 显存，驱动 576.52，nvidia-smi 显示 CUDA 12.9，当前显存占用 1370 MiB。GPU 不是此前 CPU-only PyTorch 选包的限制。已核对官方 PyTorch previous-versions：2.11.0 与 torchaudio 2.11.0 有 Windows cu128 包；拟保持版本号只切换 CUDA 构建，停 API 后在 .venv 中安装，再做实际 GPU 张量运算、pip check 和同一短音频 dialogue 模式测试。无需先升级驱动或购买硬件，暂不安装独立 CUDA Toolkit。具体兼容性以实测为准。未确认安装成功、未测 GPU 转写，也未确认用户是否已按上一轮启用生产 dialogue 模式。

用户日志(4).txt 显示 cu128 下载过程中 Errno 28；用户后续核实 pip 缓存和 tempfile 均在 C 盘，剩余 C=5GB、E=111.6GB。指导在当前窗口将 TEMP/TMP/TMPDIR 和 PIP_CACHE_DIR 指向 E:\podnotes 下专用目录，不删除原缓存。日志(5).txt 确认已成功卸载 CPU 构建并安装 torch/torchaudio 2.11.0+cu128；这份日志尚无 pip check、CUDA 识别、GPU 实际运算或转写结果。后端尚待检查后恢复，不能将安装成功视为 GPU 转写验收通过。

用户随后回传 GPU 检查：pip check 无依赖冲突，PyTorch 2.11.0+cu128 检出 RTX 4060 Ti，实际 CUDA 矩阵运算返回 cuda:0。Windows dialogue 短音频模型检查 passed，11.326125 秒音频输出 126 字符、5 段、1 位说话人，总耗时 33.75 秒。按当前 dialogue.py 自动设备选择逻辑将使用 cuda:0；检查报告本身尚无单独设备字段。不能将本次总耗时与含下载的 CPU 首次 651.11 秒对比得出加速倍数，也不能证明双人分离质量。下一步同一 GPU 环境执行完整任务管线，成功后在原服务窗口 MINI_TRANSCRIPT_MODE=dialogue 重启 API，继续公网检查。等待提示、阶段耗时及常驻模型仍未实施。

用户确认项目已成功启动。开发端公网健康检查 status=ok、development=false、demo=false；重新启用官方开发者工具自动化后，新 wx.login 成功，公网登录 200、搜索 200（1 个结果）、单集列表 200（20 条）。本轮没有提交音频，没有独立证明运行中 API 的 Python 路径或模式配置，也未取得 GPU 下 Windows 完整任务管线回传。下一步为手机真实双人短节目检查和耗时记录；等待体验、模型常驻、精简版仍是待实施方案。

用户手机提示没有转写额度。代码核实：MINI_DAILY_LIMIT 默认 3；按 Asia/Shanghai 自然日统计用户全部已接收任务，失败、重启中断、删除的任务仍计数，删除文字不返还额度。当前未取得 Windows 数据库实际计数，不将提示认定为付费供应商余额问题。联调恢复方案：原服务窗口 Ctrl+C 后设置 MINI_DAILY_LIMIT=20、MINI_TRANSCRIPT_MODE=dialogue，再以 .venv Python 启动；该额度配置适用于所有账号，仅影响这个环境启动的服务。保留数据和单任务并发限制，不通过删除数据库或切换开发登录绕过。尚待用户实际执行确认。

用户确认已重启。官方开发者工具新 wx.login 经公网登录 200，鉴权 /mini/session 返回 200、daily_limit=20、demo=false，已验证实际服务每日上限修改生效；此值是上限，不是当前用户剩余次数，未查询用户实际已用次数。本轮未提交音频或消耗任务额度。

## 重新转写仍无时间/说话人的定位

用户报告新任务仍无对话和时间并要求核对耗时。通过新 wx.login 仅查询该账号已有 4 个任务（不创建或删除任务、不输出全文）：最新 E256 完成但 segments=[]、22376 字符、旧式 Title: 头且只有一个时间标记；此前 E255 的结果包含 1924 段、4 个模型说话人编号，最后时间 4144.565 秒。其余两个 E256 同为基础格式。说明服务确实曾生成结构化对话，最新结果却属于基础输出；Windows 进程环境不能直接读取，启动时环境变量退回 basic 是与现象一致的原因。所有旧任务均无 timing，不能回算准确处理时长，也不能把音频最后时间当作处理耗时。

新增 mode-timing 修复包与 launcher 参数明确选择 --mode dialogue --daily-limit 20；启动显示模式，health 公开非敏感模式/格式版本，API 将启动模式固定传给子进程，对话模式缺失结构化结果时拒绝静默成功；数据库补充 timing 保存排队、下载、转写（含模型加载）、总处理、提交到完成耗时与音频时长。新客户端可展示完成耗时。旧数据不改写，Windows 仍待用户部署此补丁。具体步骤见 DIALOGUE_TRANSCRIPTION.md。

用户修正 PowerShell 命令路径并确认已重启后，开发端实际核对公网 health：status=ok、development=false、demo=false、transcript_mode=dialogue、transcript_format_version=2；官方新 wx.login 与鉴权 session 均 200，daily_limit=20。已证明运行中 API 为新版对话模式，尚待新任务验证分段持久化及实际 Windows GPU 耗时。本轮检查未提交音频或消耗转写额度。

用户再次报告最新生成结果仍没有说话人和时间，并确认手机刚从开发者工具“预览”重新扫码打开，不能直接归因于微信最近使用的旧入口。本轮公网 health 仍为 dialogue/格式2，但最新任务数据未读到：本机官方自动化端口未开启，重开项目后 CLI 在微信 AppID 权限请求处 ECONNRESET（TLS 连接断开）。此前卡住的 CLI 已取消，不停止 Windows 后端。

已提供独立只读诊断脚本 scripts/diagnose_miniprogram_results.py，通过 SQLite URI mode=ro 读取最近5个任务的标题/状态/分段数/说话人/文本格式标志/计时与源文件 SHA256，不输出正文、会话或密钥。配套测试验证数据行不变且不泄露正文和 token，已通过；打包为 deploy/miniprogram/podnotes-task-diagnostics.zip，ZIP CRC 通过。等待 Windows 本地输出后区分最新任务未生成分段、展示未渲染或查看记录错位；本轮未更换转写模型、未提交新任务、未推断根因已修复。
