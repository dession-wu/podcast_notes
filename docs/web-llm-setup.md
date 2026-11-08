# 播客 Web：默认模型、累计试用与个人 Key

默认模型为北京百炼 `qwen3.7-flash`，非思考模式。每个 Web 账号在本项目累计3次 AI 操作，多段/多次内部模型调用共用一次。只有真实模型调用才占用预留；有效模型输出首次返回后计次，技术失败或空结果释放。规则分析、转写、图片排版和查看保存结果不占AI次数。

## 用户配置

打开「个人服务设置 → 管理我的 AI 模型」（`/account`），查看已用、剩余和处理中次数。没有个人 Key 时使用运营默认模型；免费额度用尽后在此配置自己的 Key。已有个人 Key 时始终优先使用，调用失败不回退运营额度。删除 Key 不重置累计次数。

百炼用户在[百炼控制台](https://bailian.console.aliyun.com/)选择北京地域，开通按量模型服务、创建 API Key，并确认余额及 `qwen3.7-flash` 权限。Web 当前只支持百炼北京地域 Key，也兼容原来的 DeepSeek、OpenAI 官方端点。不要把新加坡等地域 Key 填入北京配置。

密码框不会显示或回填原 Key。点击「保存并验证」发出一个个人账号承担的最小模型请求；失败保留原配置并在原页面显示提示。401 检查 Key，403 检查地域/权限，429 检查限流、额度或稍后重试，余额不足先充值。

## 重试与缓存

Web 公共 API 客户端统一添加 `X-LLM-Operation-ID`。相同请求输入在同一浏览器标签页内重试、页面刷新后仍复用 ID；不同输入产生新 ID。浏览器只持久保存 SHA-256 指纹与随机ID，不保存正文或 Key。HTTP 本地预览缺少 SubtleCrypto 时只在内存中复用，生产使用 HTTPS。

服务器绑定真实登录账号、请求输入指纹、操作ID。已完成操作返回原HTTP结果、不再次调用上游；进行中返回409，稍后重试同操作。个人Key操作也缓存，避免重试造成重复个人API费用。客户端ID本身不能伪造身份或扩大免费额度。

## 运营配置

Windows优先使用 `BAILIAN_API_KEY`；其次读取 `BAILIAN_API_KEY_FILE` 指定的DPAPI文件。两者未配置时仅Windows使用统一默认路径：

`E:\podnotes\podnotes-server\config\ops-secrets\bailian-secret.bin`

该文件由最后本机密码窗口流程创建，使用 DPAPI LocalMachine 并限制ACL；不要向聊天、命令行参数、版本库或前端环境变量写入真实Key。未发现文件时显示未配置，不查找其它旧Key。

Linux容器不能解密Windows DPAPI文件。根目录 `docker-compose.yml` 已显式传入可选 `BAILIAN_API_KEY`，`BAILIAN_API_KEY_FILE` 在Linux容器中固定留空；通过部署环境/受控secret注入，不把Key放入 `NEXT_PUBLIC_*` 或镜像构建参数。更新运营凭据后重启Web gateway及其个人worker以刷新环境。此变更没有执行任何部署。

账号目录与Web账本使用 `/app/data/accounts`，SQLite为 `web_llm.sqlite3`；该目录和个人工作空间均位于既有 `podcast_data:/app/data` 持久卷。备份应包含账号库、加密配置、账本和用户结果。升级不要执行 `docker compose down -v`，也不要只恢复用户库却丢弃账本，否则累计次数会丢失。

## 验收与恢复

隔离测试应覆盖并发第4次拒绝、失败释放、用户隔离、同输入ID重试返回原结果、不同输入复用ID拒绝、个人Key重试缓存、删除Key不重置、非AI不计次和死进程预留恢复。恢复仅释放确认已退出的进程，不按任意TTL释放活跃操作。

有效模型输出已记成功但最终HTTP结果尚未持久化的极短崩溃窗口，重试会提示已生成、引导查看保存结果，不再次调用上游；该窗口无法保证取回尚未保存的模型正文。完整HTTP结果写入后可正常幂等返回原响应。
