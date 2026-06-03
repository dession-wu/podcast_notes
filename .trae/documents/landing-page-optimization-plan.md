# Landing Page 全面优化计划

> **参考文件**: `gemini-code-1779884268725.html`
> **目标文件**: `web-dashboard/src/app/page.tsx`, `web-dashboard/src/components/WaveCanvas.tsx`
> **日期**: 2026-05-27

---

## 一、参考设计分析

### 视觉风格特征
- **背景**: 纯黑 `#030305`，不规则粒子波浪（多重频率叠加）
- **左侧文案**: 小标签 + 大标题结构，蓝色高亮标签，白色细体标题
- **右侧卡片**: 深色半透明背景 `#09090d/80`，细边框 `white/[0.06]`，圆角 `2xl`
- **字体**: Plus Jakarta Sans + Space Grotesk (mono-tech)
- **表单**: 图标前缀输入框，圆角大按钮，底部切换链接

### 动效特征
- **粒子波浪**: 三重波形叠加（主波+谐波+漂移波），左侧宽右侧窄
- **透明度**: 左侧更亮，右侧自然收束
- **速度**: 极慢沉浸流动 `speed: 0.008`

---

## 二、任务分解

### Phase 1: WaveCanvas 背景重构
**文件**: `web-dashboard/src/components/WaveCanvas.tsx`

**修改内容**:
1. 将单一正弦波改为三重波形叠加:
   - `wave1`: 主波 `sin(x * 0.002 + time)`
   - `wave2`: 次级谐波 `sin(x * 0.005 - time * 0.7) * 0.4`
   - `wave3`: 慢速漂移波 `cos(x * 0.001 + time * 0.3) * 0.3`
2. 添加左右衰减效果:
   - 左侧粒子带宽、亮度高
   - 右侧接近卡片时自然收束
3. 调整参数:
   - `baseHeight: 140`
   - `verticalCount: 65`
   - `speed: 0.008`
   - `dotSize: 1.1`
4. 颜色调整为冷白蓝 `rgba(235, 242, 255, alpha)`

**验证标准**:
- 波浪呈现自然有机形态，无机械感
- 左侧亮右侧暗的渐变效果
- 60fps 流畅运行

---

### Phase 2: 左侧文案重构
**文件**: `web-dashboard/src/app/page.tsx`

**修改内容**:
1. 移除 `NEURAL ARCHITECTURE ACTIVE` 和 `SIGNAL_UPLINK_ESTABLISHED`
2. 替换为新文案结构:
   ```
   标签: AI-POWERED PODCAST INTELLIGENCE
   标题: 从播客中提取洞察，让内容创作更简单
   ```
3. 样式规范:
   - 标签: `text-[10px] uppercase tracking-[0.25em] text-blue-400 font-mono font-semibold`
   - 标题: `text-3xl text-white font-light tracking-tight leading-tight max-w-md`
4. 响应式: 移动端隐藏左侧文案区域

**验证标准**:
- 文案准确传达产品价值
- 与参考图片文字样式一致
- 不同屏幕尺寸下可读性良好

---

### Phase 3: 认证界面重构（登录/注册双模式）
**文件**: `web-dashboard/src/app/page.tsx`

**修改内容**:

#### 3.1 状态管理
- `mode: 'login' | 'register'`
- `formData`: email, password, confirmPassword, username
- `errors`: 字段级错误信息
- `isSubmitting`: 提交状态

#### 3.2 UI 结构
- 顶部 Badge: `Uplink Gateway`
- 标题: `登录 / Authenticate` / `注册 / Register`
- 副标题: 动态切换
- 表单字段:
  - 登录模式: 用户名/邮箱 + 密码
  - 注册模式: 用户名 + 邮箱 + 密码 + 确认密码
- 输入框: 左侧图标前缀（User, Lock, Mail）
- 按钮: `进入控制台 / Initialize Console` / `创建账户 / Create Account`
- 底部切换: `还没有账号？立即注册 →` / `已有账号？立即登录 →`

#### 3.3 表单验证
- 邮箱: 正则验证格式
- 密码: 最少6位
- 确认密码: 与密码一致
- 用户名: 最少2位
- 实时验证 + 提交验证
- 错误提示: 红色边框 + 错误文本

#### 3.4 交互反馈
- 加载状态: 按钮 spinner
- 成功: 绿色提示 + 自动跳转
- 失败: 红色提示

**验证标准**:
- 登录/注册模式切换流畅
- 表单验证逻辑正确
- 错误提示清晰
- 符合安全标准（密码输入框，不明文存储）

---

### Phase 4: Header & Footer 优化
**文件**: `web-dashboard/src/app/page.tsx`

**修改内容**:
1. Header:
   - 左侧: Logo 图标 + `PODCAST NOTES`
   - 右侧: `SYS_STATUS: ACTIVE` + 语言切换
2. Footer:
   - 左侧: `© 2026 PODCAST NOTES. ALL RIGHTS RESERVED.`
   - 右侧: `SECURE_SSL_ENCRYPTED`

---

### Phase 5: 视觉细节优化
**文件**: `web-dashboard/src/app/page.tsx`

**修改内容**:
1. 卡片样式调整:
   - 背景: `bg-[#09090d]/80`
   - 边框: `border-white/[0.06]`
   - 阴影: `shadow-[0_24px_80px_rgba(0,0,0,0.8)]`
   - 圆角: `rounded-2xl`
2. 输入框样式:
   - 背景: `bg-[#111116]`
   - 边框: `border-white/[0.05]`
   - 聚焦: `focus:border-white/20`
   - 左侧图标前缀
3. 按钮样式:
   - 阴影: `shadow-lg shadow-white/5`
   - 圆角: `rounded-full`

---

## 三、实施顺序

1. **Phase 1**: WaveCanvas 重构（独立组件，不影响其他）
2. **Phase 2**: 左侧文案重构（纯文本修改）
3. **Phase 4**: Header & Footer（结构微调）
4. **Phase 3**: 认证界面重构（核心功能，依赖其他部分）
5. **Phase 5**: 视觉细节优化（样式微调）
6. **验证**: `npm run build` + 功能测试

---

## 四、风险预防

- 所有修改保持与现有 Dashboard 路由兼容
- 不破坏已有的 AuthGuard 认证逻辑
- WaveCanvas 保持独立组件，可被 Dashboard 复用
- 表单验证在客户端完成，不依赖后端

---

## 五、验证清单

- [ ] WaveCanvas 波浪效果自然流畅
- [ ] 左侧文案在不同屏幕下显示正常
- [ ] 登录/注册模式切换正常
- [ ] 表单验证逻辑正确
- [ ] 错误提示显示正常
- [ ] 登录成功后跳转 Dashboard
- [ ] `npm run build` 通过
- [ ] 无 TypeScript 错误
