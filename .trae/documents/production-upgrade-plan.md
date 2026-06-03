# 播客笔记 MVP → 生产版本升级方案

> **文档版本**：V1.0  
> **撰写日期**：2026-06-01  
> **文档状态**：已确认，待实施  
> **决策依据**：用户确认优先搭建生产基础设施，采用 Docker Compose 多容器部署

---

## 一、执行摘要

### 1.1 目标
将现有 MVP 版本升级为可正式部署至生产服务器、供终端用户稳定使用的商业版本。

### 1.2 核心决策
- **优先级**：优先搭建生产基础设施（认证、数据库、Docker 部署）
- **部署方式**：Docker Compose 多容器部署
- **时间周期**：8 周（2 个月）
- **里程碑**：分 4 个阶段交付，每阶段 2 周

### 1.3 关键成果
- 完整的用户认证与权限系统
- 数据库持久化与数据管理
- Docker 化部署与运维体系
- 安全加固与性能优化
- 完整的测试与监控体系

---

## 二、当前状态分析

### 2.1 已完成功能（MVP）

| 模块 | 功能 | 状态 |
|-----|------|------|
| 核心引擎 | RSS 订阅解析、本地音频处理、Whisper 语音转写 | ✅ |
| 内容处理 | 内容理解与提炼、9 种笔记模板、图文生成 | ✅ |
| Web 后台 | 播客搜索、内容处理界面、转录查看器、历史记录 | ✅ |
| 模板系统 | 智能推荐 + 用户自选（刚完成） | ✅ |
| 基础设施 | 多 LLM 支持、重试机制、结构化日志 | ✅ |

### 2.2 生产环境缺口

| 缺口类别 | 具体问题 | 风险等级 |
|---------|---------|---------|
| **用户认证** | 无用户系统，任何人可访问 API | 🔴 高 |
| **数据持久化** | 数据存储在本地文件，无数据库 | 🔴 高 |
| **部署配置** | 无 Docker 配置，手动部署 | 🔴 高 |
| **安全策略** | 无 HTTPS、无 API 鉴权、无输入校验 | 🔴 高 |
| **监控告警** | 无运行时监控，故障无法及时发现 | 🟡 中 |
| **备份恢复** | 无数据备份策略，数据丢失风险 | 🟡 中 |
| **性能优化** | 无缓存、无连接池、无并发控制 | 🟡 中 |
| **测试覆盖** | 仅后端单元测试，缺少集成/E2E 测试 | 🟡 中 |

### 2.3 技术债务

1. **配置管理**：API 密钥硬编码在 .env，无加密存储
2. **错误处理**：部分接口缺少统一的错误响应格式
3. **日志分散**：日志写入文件，无集中收集
4. **前端状态**：无全局状态管理，组件间通信混乱
5. **代码组织**：core 模块过大，职责不够清晰

---

## 三、升级方案详述

### 3.1 阶段一：基础设施搭建（Week 1-2）

**目标**：建立生产级基础设施底座

#### 3.1.1 数据库设计与集成

**技术选型**：PostgreSQL（关系型数据）+ Redis（缓存/队列）

**数据模型设计**：

```python
# models/user.py — 用户模型
class User(BaseModel):
    id: UUID
    email: str  # 唯一，登录账号
    username: str
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime
    updated_at: datetime

# models/podcast.py — 播客记录
class PodcastRecord(BaseModel):
    id: UUID
    user_id: UUID  # 外键
    podcast_name: str
    episode_title: str
    audio_url: str | None
    rss_url: str | None
    status: Literal["pending", "processing", "completed", "failed"]
    created_at: datetime
    completed_at: datetime | None

# models/note.py — 笔记记录
class NoteRecord(BaseModel):
    id: UUID
    podcast_id: UUID  # 外键
    template_alias: str
    title: str
    content: str  # Markdown
    tags: list[str]
    word_count: int
    is_visual: bool
    image_paths: list[str] | None
    created_at: datetime

# models/transcription.py — 转录记录
class TranscriptionRecord(BaseModel):
    id: UUID
    podcast_id: UUID
    full_text: str
    segments: list[dict]  # JSONB
    language: str
    duration_seconds: int
    created_at: datetime
```

**实施文件**：
- `database/` — 数据库模块
  - `connection.py` — 连接池管理（asyncpg + SQLAlchemy）
  - `models.py` — ORM 模型定义
  - `migrations/` — Alembic 迁移脚本
  - `repositories/` — 数据访问层

#### 3.1.2 用户认证系统

**技术选型**：JWT + bcrypt + OAuth2（可选）

**功能模块**：
- 用户注册（邮箱 + 密码）
- 用户登录（JWT Token）
- 密码重置
- Token 刷新
- 权限控制（RBAC：admin/user）

**实施文件**：
- `backend/routers/auth.py` — 认证 API
- `backend/middleware/auth.py` — JWT 验证中间件
- `backend/services/auth_service.py` — 认证业务逻辑
- `web-dashboard/src/lib/auth.ts` — 前端认证封装

#### 3.1.3 Docker 化部署

**文件清单**：
- `Dockerfile.backend` — Python 后端镜像
- `Dockerfile.frontend` — Next.js 前端镜像
- `docker-compose.yml` — 多服务编排
- `docker-compose.prod.yml` — 生产环境配置
- `nginx/nginx.conf` — 反向代理配置
- `.dockerignore` — 构建忽略文件

**服务架构**：
```yaml
services:
  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
  
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
  
  frontend:
    build:
      context: ./web-dashboard
      dockerfile: Dockerfile.frontend
    depends_on:
      - backend
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend
```

**验收标准**：
- [ ] `docker-compose up` 一键启动全部服务
- [ ] 数据库自动迁移
- [ ] 前端通过 Nginx 反向代理访问后端
- [ ] 容器健康检查正常

---

### 3.2 阶段二：安全与性能强化（Week 3-4）

**目标**：系统安全加固与性能优化

#### 3.2.1 安全策略实施

| 安全措施 | 实施内容 | 优先级 |
|---------|---------|-------|
| HTTPS 强制 | Nginx SSL 配置，自动跳转 HTTPS | P0 |
| API 鉴权 | 所有非公开接口需 JWT Token | P0 |
| 输入校验 | Pydantic 模型校验 + SQL 注入防护 | P0 |
| 密码安全 | bcrypt 哈希，最小长度 8 位 | P0 |
| 速率限制 | Redis 基于的 API 限流（60 req/min） | P1 |
| CORS 收紧 | 生产环境只允许特定域名 | P1 |
| 安全头部 | HSTS、X-Frame-Options、CSP | P1 |
| 日志脱敏 | 敏感信息（API Key、密码）不记录 | P1 |

#### 3.2.2 性能优化

| 优化项 | 实施方案 | 预期效果 |
|-------|---------|---------|
| 数据库连接池 | asyncpg 连接池（min=5, max=20） | 减少连接开销 |
| Redis 缓存 | 缓存模板推荐结果（TTL=1h） | 减少重复计算 |
| 静态文件 CDN | Nginx 缓存前端静态资源 | 加速页面加载 |
| 数据库索引 | 为用户 ID、状态字段添加索引 | 加速查询 |
| 异步处理 | 转写任务放入后台队列 | 避免请求阻塞 |
| 图片压缩 | 生成图片时自动压缩 | 减少存储和带宽 |

#### 3.2.3 错误处理与日志升级

**统一错误响应格式**：
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数校验失败",
    "details": [
      {"field": "email", "message": "邮箱格式不正确"}
    ],
    "trace_id": "abc-123-xyz"
  }
}
```

**日志升级**：
- 结构化 JSON 日志输出到 stdout
- 集成日志收集（ELK Stack / Grafana Loki）
- 请求链路追踪（trace_id）

**验收标准**：
- [ ] 所有 API 接口都有鉴权保护
- [ ] HTTPS 正常工作，HTTP 自动跳转
- [ ] 压力测试：100 并发请求，响应时间 < 2s
- [ ] 错误响应格式统一

---

### 3.3 阶段三：监控与运维体系（Week 5-6）

**目标**：建立完整的监控告警和运维能力

#### 3.3.1 监控告警系统

**技术选型**：Prometheus + Grafana + Alertmanager

**监控维度**：

| 维度 | 指标 | 告警阈值 |
|------|------|---------|
| 系统资源 | CPU、内存、磁盘、网络 | CPU > 80%, 磁盘 > 85% |
| 应用性能 | 请求延迟、QPS、错误率 | P99 > 2s, 错误率 > 1% |
| 业务指标 | 日活用户、处理任务数 | 任务堆积 > 100 |
| 数据库 | 连接数、慢查询、锁等待 | 连接数 > 80% |
| 容器 | 重启次数、健康状态 | 重启 > 3 次/小时 |

**实施文件**：
- `monitoring/prometheus.yml` — Prometheus 配置
- `monitoring/grafana/dashboards/` — Grafana 仪表盘
- `monitoring/alerts.yml` — 告警规则
- `backend/middleware/metrics.py` — 应用指标暴露

#### 3.3.2 数据备份与恢复

**备份策略**：
- PostgreSQL：每日全量备份（pg_dump）+ WAL 归档
- 用户文件：每日增量备份（rsync）
- 备份保留：7 天本地 + 30 天远程（可选 S3）

**实施文件**：
- `scripts/backup.sh` — 备份脚本
- `scripts/restore.sh` — 恢复脚本
- `scripts/backup-cron` — 定时任务配置

#### 3.3.3 健康检查与自愈

**健康检查端点**：
- `/api/health` — 基础健康
- `/api/health/db` — 数据库连接
- `/api/health/redis` — Redis 连接
- `/api/health/disk` — 磁盘空间

**自愈机制**：
- Docker restart policy：unless-stopped
- 容器内存限制：防止 OOM 拖垮主机
- 健康检查失败自动重启

**验收标准**：
- [ ] Grafana 仪表盘可查看所有关键指标
- [ ] 模拟高负载触发告警，通知正常送达
- [ ] 备份脚本执行成功，数据可恢复
- [ ] 停止数据库容器，健康检查返回异常

---

### 3.4 阶段四：测试与质量保障（Week 7-8）

**目标**：构建全面的测试体系，确保上线质量

#### 3.4.1 测试体系构建

| 测试类型 | 工具 | 覆盖范围 | 目标覆盖率 |
|---------|------|---------|-----------|
| 单元测试 | pytest | 后端业务逻辑 | > 80% |
| 集成测试 | pytest + TestClient | API 接口 | > 70% |
| 前端单元测试 | Vitest | 组件、工具函数 | > 60% |
| E2E 测试 | Playwright | 核心用户流程 | 关键路径 |
| 性能测试 | locust | 并发压力测试 | 100 并发 |
| 安全测试 | bandit + safety | 代码安全扫描 | 无高危漏洞 |

#### 3.4.2 CI/CD 流水线

**技术选型**：GitHub Actions

**流水线阶段**：
```yaml
stages:
  - lint:      # ESLint + ruff + mypy
  - test:      # 单元测试 + 集成测试
  - security:  # bandit + safety + npm audit
  - build:     # Docker 镜像构建
  - deploy:    # 自动部署到 staging
  - e2e:       # Playwright E2E 测试
  - promote:   # 手动触发部署到 production
```

**实施文件**：
- `.github/workflows/ci.yml` — CI 流水线
- `.github/workflows/cd-staging.yml` — Staging 部署
- `.github/workflows/cd-production.yml` — 生产部署

#### 3.4.3 上线策略

**分阶段上线**：
1. **内部测试**（1 天）：团队内部验证
2. **Staging 环境**（3 天）：预生产环境全面测试
3. **灰度发布**（3 天）：5% → 25% → 50% → 100% 流量
4. **正式发布**：全量开放

**回滚策略**：
- 保留上一版本 Docker 镜像
- 数据库迁移支持回滚（downgrade 脚本）
- 一键回滚脚本：`scripts/rollback.sh`

**验收标准**：
- [ ] 单元测试覆盖率 > 80%
- [ ] E2E 测试通过核心流程
- [ ] 安全扫描无高危漏洞
- [ ] 压力测试 100 并发通过
- [ ] 灰度发布期间错误率 < 0.1%

---

## 四、技术架构升级

### 4.1 目标架构

```
┌─────────────────────────────────────────────────────────────┐
│                         用户层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Web 浏览器  │  │  移动端浏览器 │  │    API 客户端       │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          ▼                ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                      Nginx 反向代理                           │
│         HTTPS / 负载均衡 / 静态缓存 / 速率限制                  │
└─────────────────────────────────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────┐  ┌─────────────────────────────────────────┐
│   Next.js 前端   │  │           FastAPI 后端                   │
│  (Docker 容器)   │  │         (Docker 容器)                    │
│                 │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│                 │  │  │  Auth   │  │ Process │  │ Analyze │  │
│                 │  │  │ Router  │  │ Router  │  │ Router  │  │
│                 │  │  └────┬────┘  └────┬────┘  └────┬────┘  │
│                 │  │       └─────────────┴─────────────┘      │
│                 │  │                   │                       │
│                 │  │  ┌────────────────┼────────────────┐     │
│                 │  │  │                ▼                │     │
│                 │  │  │  ┌─────────┐  ┌─────────┐      │     │
│                 │  │  │  │  Auth   │  │ Business│      │     │
│                 │  │  │  │ Service │  │ Service │      │     │
│                 │  │  │  └────┬────┘  └────┬────┘      │     │
│                 │  │  │       └─────────────┘          │     │
│                 │  │  │                │                │     │
│                 │  │  │  ┌─────────────┼─────────────┐ │     │
│                 │  │  │  ▼             ▼             ▼ │     │
│                 │  │  │  PostgreSQL   Redis        Local │     │
│                 │  │  │  (数据持久化)  (缓存/队列)    (文件)│     │
│                 │  │  └──────────────────────────────┘     │
└─────────────────┘  └─────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                      监控与运维层                             │
│  ┌───────────┐  ┌───────────┐  ┌─────────────────────────┐  │
│  │ Prometheus │  │  Grafana  │  │      Alertmanager       │  │
│  │  (指标收集) │  │  (可视化)  │  │      (告警通知)          │  │
│  └───────────┘  └───────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 代码结构优化

```
podcast_notes/
├── backend/                 # FastAPI 后端
│   ├── routers/             # API 路由层
│   ├── services/            # 业务逻辑层
│   ├── middleware/          # 中间件（认证、日志、限流）
│   ├── dependencies/        # 依赖注入
│   └── main.py              # 应用入口
├── web-dashboard/           # Next.js 前端
│   ├── src/
│   │   ├── app/             # 页面路由
│   │   ├── components/      # 组件
│   │   ├── lib/             # 工具函数
│   │   └── hooks/           # 自定义 Hooks
│   └── package.json
├── core/                    # 核心处理引擎
│   ├── content_processor.py
│   ├── template_recommender.py
│   ├── transcriber.py
│   └── image_generator.py
├── database/                # 数据库模块（新增）
│   ├── connection.py
│   ├── models.py
│   ├── repositories/
│   └── migrations/
├── config/                  # 配置管理
│   └── settings.py
├── monitoring/              # 监控配置（新增）
│   ├── prometheus.yml
│   ├── grafana/
│   └── alerts.yml
├── scripts/                 # 运维脚本（新增）
│   ├── backup.sh
│   ├── restore.sh
│   └── health_check.sh
├── docker/                  # Docker 配置（新增）
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
├── nginx/                   # Nginx 配置（新增）
│   ├── nginx.conf
│   └── ssl/
├── tests/                   # 测试
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── .github/                 # CI/CD（新增）
    └── workflows/
        ├── ci.yml
        ├── cd-staging.yml
        └── cd-production.yml
```

---

## 五、资源需求评估

### 5.1 开发资源

| 阶段 | 工作量 | 关键任务 |
|------|-------|---------|
| 阶段一 | 3 人周 | 数据库设计、用户认证、Docker 化 |
| 阶段二 | 2 人周 | 安全加固、性能优化、错误处理 |
| 阶段三 | 2 人周 | 监控告警、备份恢复、健康检查 |
| 阶段四 | 2 人周 | 测试体系、CI/CD、灰度发布 |
| **总计** | **9 人周** | |

### 5.2 服务器资源（生产环境）

| 服务 | CPU | 内存 | 存储 | 说明 |
|------|-----|------|------|------|
| PostgreSQL | 2 核 | 4GB | 100GB SSD | 数据持久化 |
| Redis | 1 核 | 2GB | 10GB | 缓存/队列 |
| Backend | 2 核 | 4GB | 20GB | FastAPI 应用 |
| Frontend | 1 核 | 2GB | 10GB | Next.js SSR |
| Nginx | 1 核 | 1GB | 5GB | 反向代理 |
| Monitoring | 1 核 | 2GB | 50GB | Prometheus/Grafana |
| **总计** | **8 核** | **15GB** | **195GB** | |

**推荐配置**：2 核 4GB（最低）/ 4 核 8GB（推荐）/ 8 核 16GB（理想）

### 5.3 外部依赖

| 服务 | 用途 | 成本 |
|------|------|------|
| LLM API | 内容生成 | 按量付费 |
| 域名 + SSL | HTTPS | ~100元/年 |
| 服务器 | 托管 | ~300元/月（4核8GB）|
| 对象存储（可选）| 备份 | ~50元/月 |

---

## 六、风险与应对

### 6.1 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 数据库迁移失败 | 中 | 高 | 先备份，使用 Alembic 逐步迁移，保留回滚脚本 |
| Docker 性能问题 | 中 | 中 | 资源限制、健康检查、监控告警 |
| 安全漏洞 | 低 | 高 | 代码扫描、渗透测试、及时更新依赖 |
| 第三方 API 变更 | 中 | 中 | 抽象适配层、多提供商备份 |

### 6.2 项目风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 进度延期 | 中 | 中 | 分阶段交付，每阶段有独立价值 |
| 需求蔓延 | 高 | 中 | 严格按方案执行，新需求入 Backlog |
| 人员变动 | 低 | 高 | 文档完善、代码规范、知识共享 |

### 6.3 运维风险

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 数据丢失 | 低 | 极高 | 每日备份、异地备份、定期恢复演练 |
| 服务宕机 | 中 | 高 | 健康检查、自动重启、监控告警 |
| 流量突增 | 中 | 中 | 限流、扩容、CDN |

---

## 七、验收标准

### 7.1 功能验收

| 验收项 | 标准 | 验证方式 |
|--------|------|---------|
| 用户注册登录 | 可正常注册、登录、登出 | 手动测试 |
| 数据持久化 | 笔记、播客记录可保存和查询 | 单元测试 + 手动测试 |
| Docker 部署 | `docker-compose up` 一键启动 | 脚本验证 |
| API 鉴权 | 未登录无法访问受保护接口 | 自动化测试 |
| HTTPS | 所有流量通过 HTTPS | 浏览器验证 |

### 7.2 性能验收

| 验收项 | 标准 | 验证方式 |
|--------|------|---------|
| API 响应时间 | P99 < 2s | 压力测试 |
| 并发处理 | 100 并发正常 | locust 测试 |
| 数据库查询 | 简单查询 < 100ms | 性能测试 |
| 前端加载 | 首屏 < 3s | Lighthouse |

### 7.3 安全验收

| 验收项 | 标准 | 验证方式 |
|--------|------|---------|
| 密码安全 | bcrypt 哈希，最小 8 位 | 代码审查 |
| SQL 注入 | 无注入漏洞 | 安全扫描 |
| XSS | 无 XSS 漏洞 | 安全扫描 |
| 依赖安全 | 无高危漏洞 | `safety check` |

### 7.4 运维验收

| 验收项 | 标准 | 验证方式 |
|--------|------|---------|
| 监控覆盖 | 所有关键指标可查看 | Grafana 验证 |
| 告警触发 | 模拟故障，告警正常送达 | 手动测试 |
| 备份恢复 | 备份成功，数据可恢复 | 恢复演练 |
| 健康检查 | 各组件健康状态可查询 | API 测试 |

---

## 八、实施时间表

```
Week 1-2: 基础设施搭建
├── Day 1-3:  数据库设计与集成
├── Day 4-6:  用户认证系统
├── Day 7-8:  Docker 化部署
├── Day 9-10: 集成测试与修复
└── 里程碑:   系统可 Docker 一键启动

Week 3-4: 安全与性能
├── Day 11-13: API 鉴权与输入校验
├── Day 14-16: HTTPS 与安全头部
├── Day 17-18: 性能优化（缓存、连接池）
├── Day 19-20: 错误处理与日志升级
└── 里程碑:   系统通过安全扫描

Week 5-6: 监控与运维
├── Day 21-23: Prometheus + Grafana 搭建
├── Day 24-25: 告警规则配置
├── Day 26-27: 备份恢复脚本
├── Day 28-30: 健康检查与自愈
└── 里程碑:   监控体系可正常运行

Week 7-8: 测试与上线
├── Day 31-33: 测试体系构建
├── Day 34-35: CI/CD 流水线
├── Day 36-38: E2E 测试与修复
├── Day 39-40: 灰度发布与正式上线
└── 里程碑:   生产环境稳定运行
```

---

## 九、文档清单

### 9.1 需要编写的文档

| 文档 | 责任人 | 时间节点 |
|------|-------|---------|
| 部署文档 | 运维工程师 | Week 2 |
| API 文档 | 后端工程师 | Week 2 |
| 用户手册 | 产品经理 | Week 6 |
| 运维手册 | 运维工程师 | Week 6 |
| 安全白皮书 | 安全工程师 | Week 4 |
| 故障处理手册 | 运维工程师 | Week 6 |

### 9.2 需要更新的文档

| 文档 | 更新内容 |
|------|---------|
| README.md | 部署说明、快速开始 |
| PRD.md | 生产版本功能更新 |
| CHANGELOG.md | 版本变更记录 |

---

## 十、附录

### 10.1 关键决策记录

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| 数据库 | SQLite / PostgreSQL / MySQL | PostgreSQL | 功能丰富、性能优秀、JSON 支持好 |
| 缓存 | 内存 / Redis | Redis | 持久化、分布式、队列支持 |
| 部署 | 单机 / Docker / K8s | Docker Compose | 复杂度适中，满足当前需求 |
| 监控 | Prometheus / CloudWatch | Prometheus | 开源、社区活跃、与 Grafana 集成好 |
| CI/CD | GitHub Actions / Jenkins | GitHub Actions | 与代码仓库集成、无需额外维护 |

### 10.2 技术栈总览（生产版）

| 层级 | 技术选型 |
|-----|---------|
| 后端框架 | Python 3.10+ + FastAPI |
| 数据库 | PostgreSQL 16 + asyncpg |
| 缓存 | Redis 7 |
| ORM | SQLAlchemy 2.0 + Alembic |
| 认证 | JWT + bcrypt |
| 前端框架 | Next.js 16 + React 19 |
| 容器化 | Docker + Docker Compose |
| 反向代理 | Nginx |
| 监控 | Prometheus + Grafana + Alertmanager |
| CI/CD | GitHub Actions |
| 测试 | pytest + Vitest + Playwright |

---

*本文档由产品与技术团队联合编写，将随着项目迭代持续更新。*
*最后更新：2026-06-01*
