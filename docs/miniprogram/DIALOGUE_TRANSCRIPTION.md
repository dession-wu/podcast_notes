# 中文对话转写优化

## 模式回退与耗时修复（最新更新）

用户重新转写后仍缺少时间和说话人。经官方微信登录访问用户本人任务，最新 E256 的 segments 为空，正文为旧式 Title: 头与单个时间标记；较早的 E255 有 1924 个结构化片段、4 个模型说话人编号，最后片段到 4144.565 秒。这证明后端曾生成对话结果，最新任务却输出基础格式；仅退出重进手机不能补回缺失信息。现有旧 API 不暴露运行模式，环境变量丢失/配置回到 basic 是与源码吻合的原因，尚不能远程直接读取 Windows 进程环境。

最新补丁 podnotes-windows-mode-timing-fix.zip 包含：启动参数 --mode/--daily-limit、未设置环境变量时默认 dialogue 的 launcher、模式与格式版本健康检查、运行时模式固定传给子进程、对话结果缺失时拒绝静默完成、任务阶段计时与 SQLite 非破坏迁移。小程序已增加完成任务耗时显示；手机需重新预览才更新 UI。

停止 API 后，解压补丁到现有项目目录，并在原服务窗口执行：

```powershell
Set-Location "E:\podnotes\podnotes-server"
.\.venv\Scripts\python.exe scripts/backup_miniprogram_store.py
.\.venv\Scripts\python.exe scripts/run_miniprogram_server.py --mode dialogue --daily-limit 20
```

启动必须显示 Transcript mode: dialogue; daily limit: 20。公网 /mini/health 应返回 transcript_mode=dialogue、transcript_format_version=2，后续再提交新任务。已有模型缓存和 GPU 环境复用，无需重新安装依赖。旧记录未保存完成时刻，无法回算实际处理耗时；新任务记录提交到完成、下载、模型子进程（含加载）、排队及音频时长。整体性能仍需用真实 Windows 节目测量。

本次修复验证：27 项后端测试、18 项客户端测试、官方 WXML/WXSS 编译、隔离部署包导入/RSS 检查通过。新增回归覆盖运行中模式不随后续环境变化而变、对话结果缺失时任务失败、列表和详情计时一致、旧库迁移不丢正文、删除清空结构化数据及计时。Mac 实际单人音频任务管线再次通过：提交至完成 29.51 秒，识别子进程 29.37 秒；本地下载夹具耗时不代表真实下载速度，Mac 结果不作为 Windows GPU 性能。

当前工作目标：将大段文本改为可读的对话稿，保存句级时间戳、匿名说话人和段落，同时保留全文搜索、复制、TXT 导出及旧记录。

## 实现与任务

- [x] 查明现状：SenseVoice 输出没有可靠句级时间时退化为整段；Mini worker 只写 TXT；API 强制关闭原独立说话人流程。
- [x] 增加本地 Paraformer + FSMN VAD + CT 标点 + CAM++ 对话模式，直接使用 sentence_info 的毫秒时间和 spk 标识。
- [x] 将模型说话人编号映射为“说话人 1、2”，不推断姓名，不为无时间戳的文本估算时间。
- [x] worker 同时写 TXT 和结构化片段，API 持久保存，SQLite 自动补充字段，旧记录默认空片段。
- [x] 阅读页逐段展示时间和说话人，支持按正文、编号、时间筛选；复制和 TXT 始终保留全文。
- [x] 删除、所有权隔离与临时文件清理覆盖结构化内容。
- [x] Windows 模型下载与真实单人音频验证。
- [ ] 双人授权音频人工核对时间和说话人；单人合成样例不能证明双人分离质量。
- [ ] Windows 开启新模式，更新手机预览并验收。

## Windows 更新和验证

将 podnotes-windows-dialogue-update.zip 放到 E:\Desktop，在项目目录执行：

```powershell
Expand-Archive -LiteralPath "E:\Desktop\podnotes-windows-dialogue-update.zip" -DestinationPath "E:\podnotes\podnotes-server" -Force
Set-Location "E:\podnotes\podnotes-server"
.\.venv\Scripts\python.exe scripts/backup_miniprogram_store.py
.\.venv\Scripts\python.exe scripts/check_miniprogram_transcription.py --audio data/miniprogram-model-check/owned-sample.wav --mode dialogue
```

首次下载额外模型。失败请看 data/miniprogram-model-check/worker.log，尚未切换正在运行的旧模式。成功报告应有 segment_count、speaker_count；另可在 data/miniprogram-model-check/transcript.txt 与 transcript-segments.json 检查实际文本和时间。对任意自有双人录音可改 --audio 指向对应路径，模型分出两个编号不等于已人工验证正确。

基础样例通过后测试真实任务存储及导出：

```powershell
.\.venv\Scripts\python.exe scripts/check_miniprogram_transcription_pipeline.py --audio data/miniprogram-model-check/owned-sample.wav --mode dialogue
```

两项通过后，在原持有 AppSecret 环境的服务窗口 Ctrl+C，再启用模式：

```powershell
$env:MINI_TRANSCRIPT_MODE = "dialogue"
.\.venv\Scripts\python.exe scripts/run_miniprogram_server.py
```

最新 launcher 在环境变量未设置时默认对话模式；回退使用启动参数 --mode basic。推荐始终显式指定 --mode，避免历史窗口的环境变量影响选择。旧记录不自动重跑，缺失的时间和声音信息无法从旧文字恢复，需重新提交原音频。

Mac 小程序源代码已更新，但手机需通过开发者工具重新生成预览才能看到新阅读布局。没有提审或正式发布。

## 验证边界

自动化：26 项 Mini 后端测试、17 项客户端测试及官方 WXML/WXSS 编译通过；官方微信模拟器使用明确标注的三段双人界面样例，验证了段落布局、时间显示、按说话人筛选及清空。截图位于 screenshots/dialogue。界面样例未发送音频或创建真实转写任务。

Mac 实际模型检查通过：11.326 秒自制单人中文语音产生 5 个带时间语句、1 位说话人，人工检查输出包含预期语句。首次耗时 644 秒包含识别/标点/说话人模型下载（约 2GB 级资源）与初始化，不是纯推理性能。随后真实本地任务管线检查通过，26.75 秒完成 STT、结构化保存、鉴权 TXT 导出、删除与临时文件清理；网络下载仍为本地音频夹具。Mac 环境为 FunASR 1.4.17、torch 2.15.0，不能代替用户 Windows FunASR 1.3.1 实测，不能据此宣称双人分离质量通过。

Windows 用户已回传新模式实际检查 passed：音频 11.326125 秒，5 段、1 位说话人、输出 126 字符；首次耗时 651.11 秒，FunASR 1.3.1、torch/torchaudio 2.11.0+cpu。此为用户 Windows 模型加载和单人样例成功，尚未回传 Windows dialogue 模式的完整任务管线检查，也未启用生产新模式或验证真实双人分离质量。

新增测试检查模型响应解析、缺失时间拒绝处理、旧 SQLite 迁移、所有权隔离、worker/API/导出链路及删除清理；这些测试使用模型输出夹具，不证明真实模型识别准确率。旧模式仍可使用，中文新模式可能增加 CPU 处理时间。尚未评估方言、多语种、重叠发言与背景音乐下的质量，不保证准确率提升。

实现参考：[FunASR 官方 Python API](https://github.com/modelscope/FunASR/blob/main/docs/python_api.md)，句级时间取 start/end，说话人取 sentence_info 内的 spk。


### 2026-11-02：日志(6) 核查

Windows 三个关键源文件 SHA256 与本地修复版完全一致。最新 E253（9ac5d4f650c04f1e0fff3dee00da2647，20:34:27 创建）completed，但 segments=0、timing={}、legacy_header=true；E255 仍有 1924 片段、4 个说话人标签。公网健康检查再次返回 dialogue / format 2。当前代码完成任务必写 timing，且 dialogue 空片段必失败，因此这些证据尚不能解释最新记录由哪个运行实例处理；不得再简单归因于前端缓存或磁盘源码未更新。旧队列消费者或不同启动目录仍需运行时证据验证。

已更新只读诊断包：增加本机 8010 健康状态、监听 PID、相关 Python 进程 PID/父 PID/启动时间/解释器路径/显式模式（不输出命令行或密钥），补充 store/dialogue 文件哈希和数据库路径。2 个测试通过，覆盖只读与敏感命令行不泄漏。Windows 实际运行检查仍待用户返回；未终止任何远程进程，也未再次提交转写。历史任务无 timing，无法可靠计算其实际转写耗时。


### 2026-11-02 runtime diagnostic V3

Log (9): listener PID 26424 has project venv launcher parent 27260; both explicitly use dialogue mode, started at 20:31:30 CST. This parent/child chain does not establish duplicate queue consumers or a broken venv. All five source hashes match. The fixed-path database has latest E253 created 20:34 with empty timing/segments. Actual service database identity remains unverified: launcher preserves MINI_DATA_DIR overrides.

V3 health adds storage_id (SHA256 of normcase resolved DB path, first 16 hex characters), not the path or task contents. Diagnostic compares actual service storage_id with inspected database, returning true/false/null. Launcher prints actual DB path and sys.prefix locally. 30 regression tests passed. Artifact podnotes-runtime-check-v3.zip contains sources only. Windows installation/restart and storage comparison remain pending; no new transcription submitted, no root cause confirmed.


### Log (10): V3 deployment verified

Windows V3 diagnostic reports database_matches_running_service=true, storage_id=831bc4d2eaf2c7a2, listener PID 16212 with venv launcher parent 2676, start 2026-11-02 21:51:26.823 CST, explicit dialogue. Independent public HTTPS health returned the same V3 storage_id and dialogue mode. Latest stored task remains E253 created 20:34:27, before this service started, with no new task after restart. This verifies current deployment/routing/storage identity only, not successful new transcription or the historical cause. Existing E255 has 1924 segments and four automatic speaker labels; can check frontend on this record without reprocessing. Old completed records are not reprocessed automatically. Next acceptance: existing E255 rendering, then one new short authorized episode via phone and V3 metadata verifying mode/timing/segments. Historical E253 processing duration unavailable.


### Worker protocol 4: fence incompatible queue consumers

Log (11) disproves a fix after V3 restart: E252 created 21:54:54 completed with no timing/segments. Historical cause remains unproven. All-Python process enumeration found older PIDs 4256 and 20864; command lines remain unreadable even after requested elevation. These processes are not confirmed project members and must not be killed speculatively.

V4 non-destructively adds claim_version/claim_pid and a SQLite BEFORE UPDATE trigger rejecting queued-to-downloading transitions by older Store.claim SQL. Existing connections are also fenced; rejected claims remain queued after rollback. New claim atomically records protocol 4 and PID. This intentionally requires the upgraded worker for future queue processing. No old transcript is rewritten. API health now reports worker_protocol and worker_alive; task timing records worker version/PID and logs only safe task metadata. Diagnostic now includes unclassified Python processes, avoiding the previous filtered blind spot.

33 regression tests passed, including pre-existing legacy connection rejection, atomic concurrent new claims, worker thread liveness, data migration, structured result validation and isolation. Windows deployment remains pending; no claim of observed legacy consumer or successful real V4 task yet. ZIP podnotes-worker-guard-v4.zip contains source and a PowerShell installer only, no secrets/data/models. Installer backs up database first, stops only a readable/verified mini API listener on 8010, then starts dialogue/limit20. Other Python PIDs are untouched. PowerShell installer has not been executed on Windows locally; inspect user output after deployment.
