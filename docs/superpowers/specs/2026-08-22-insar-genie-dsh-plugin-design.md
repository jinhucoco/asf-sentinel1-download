# insar-genie DSH 插件设计（2026-08-22）

> 状态：设计已获用户批准（2026-08-22）
> 目标：把现有 insar-genie 技能（SBAS-InSAR 全链路 AI 技能）打包为 DSH 插件，面向**非专业用户**提供极简交互，重点解决参数确认防呆、进度可视化、模板推荐、异常诊断四大体验问题。

## 1. 背景与目标

### 1.1 现状

- **insar-genie 技能已存在**（`~/.pi/agent/skills/asf-sentinel1-download`，GH `jinhucoco/insar-genie`，dev 分支）：
  - `SKILL.md`：全链路 AI 交互指令（下载 → 配套数据 → 参数确认 → 批处理 → 守护监控）
  - `scripts/`：Python 工具链（download / poeorb / gacos / dem / multi_download / download_session）
  - `experiment/`：SARscape 批处理 bat + config + sbas_guard.py 守护
  - `progress_gui.py`：已有 tkinter 桌面进度条
- **已固化的经验教训**（近期 commit）：
  - 连接图空间基线 2% 铁律（`MIN_PERC_BASELINE=0, MAX_PERC_BASELINE=2`）
  - `PARAMETERS_INFO_*.xml` 是实际落盘参数的唯一权威（脚本/SetParam 不等于实际）
  - 配准路径 sparse-vs-dense 380x 差异、CPU 争用影响
  - 基线必须显式写进 bat，跑完查 `tmp/*/work/PARAMETERS_INFO_*.xml` 校验

### 1.2 目标用户

**非专业 InSAR 用户**：几乎不懂 SARscape，希望"一句话跑完实验"，但要求：

1. **参数确认防呆**：杜绝"4% 变 45%"类事故
2. **进度可视化**：实验跑几小时到几天，直观看到每步进度/剩余时间
3. **参数模板库**：按地形自动推荐已验证参数
4. **异常自动诊断**：失败/停滞自动定位原因 + 修复建议

### 1.3 非目标（YAGNI）

- 不做完整实验管理台（完整 Web 应用形态）
- 不做 MCP 服务器接入
- 不重写 Python 脚本（复用现有资产）
- 不做多用户/权限系统（本地单机）

## 2. 形态决策

**混合型：技能 + 关键 UI**（用户已确认）

- 技能层（SKILL.md + scripts/）负责 AI 对话执行全流程
- UI 层只做两个体验组件：参数确认卡片 + 进度面板
- 技术栈：DSH 原生 cordis 插件（host Node 侧）+ React 前端组件（client 侧），复用现有 Python 脚本

## 3. 总体架构

```
┌─────────────────────────────────────────────────────────┐
│               DSH 插件 @dsh-custom/insar-genie          │
├────────────────────────┬────────────────────────────────┤
│  HOST 侧 (Node/cordis)  │  CLIENT 侧 (React/前端)        │
│                        │                                │
│  · skill provider      │  · 参数确认卡片 (ParamConfirm)  │
│    (注册 insar-genie   │    - 地形→参数联动表单          │
│     SKILL + scripts)   │    - 防呆校验 (基线 2-4% 等)    │
│  · tool: insar_run     │  · 进度面板 (ProgressPanel)    │
│    (执行下载/批处理)    │    - 五步进度条 + 剩余时间      │
│  · tool: insar_status  │    - 异常定位 + 修复建议        │
│    (读 guard 日志/      │                                │
│     step_performed)    │                                │
│  · tool: insar_templates│                               │
│    (地形参数模板库)     │                                │
│  · 设置命名空间         │                                │
│    (账号/路径/凭证)     │                                │
│  · 实验注册表           │                                │
└────────────────────────┴────────────────────────────────┘
         │                              ▲
         │ 文件系统 (scripts/ + 状态文件)│
         ▼                              │
   Python 工具链 (复用现有 insar-genie) ─┘
   download.py / sbas_guard.py / bat 批处理
```

## 4. HOST 侧组件

### 4.1 技能 Provider（`src/host/skill.ts`）

- 实现 `dsh-skill-filesystem` 风格 provider，注册技能 `insar-genie`
- 打包 `SKILL.md` + `scripts/` + `experiment/` 为 `assets/`，插件加载时解压/链接到技能目录
- kebab-case 名称、`dsh.bundle` 声明

### 4.2 工具（`src/host/tools.ts`）

| 工具 | 作用 | 底层调用 |
|---|---|---|
| `insar_run` | 执行下载/批处理/守护（参数来自确认卡片）。**异步**：创建后台任务（复用 dsh-jobs），立即返回任务 id，状态由 registry 跟踪 | `spawn` Python 脚本（download.py、bat、sbas_guard.py），不阻塞工具调用 |
| `insar_status` | 读取实验状态 | 解析 `work_step_performed.sml` + `auxiliary.sml` + `sbas_guard.log` |
| `insar_templates` | 按地形推荐参数模板 | 内置模板库（矿区/滑坡/城市/沙漠/黄土高原）|

### 4.3 状态解析服务（`src/host/status.ts`）

- `parseExperimentStatus(dir)`：五步进度（连接图/干涉/解缠/反演/地理编码）+ 每步完成度 + 剩余时间
- 数据源：`work_step_performed.sml`（每对 step 标记）+ `Process.log`（每对耗时）
- 输出结构化 JSON 供 client 面板渲染 + AI 汇报

### 4.4 设置命名空间（`src/host/settings.ts`）

| 配置项 | 说明 | 对应现有 |
|---|---|---|
| Earthdata 账号/密码 | ASF SLC 下载 | `config.json` |
| GACOS 邮箱 IMAP 授权码 | 大气延迟收取 | `mail.json` |
| ENVI / SARscape 路径 | 批处理调用 | `config.env` 的 `ENVI_IDL`/`SARSCAPE_LIB` |
| 数据盘路径（`G:` 等） | 大文件存储根 | `WORK_DIR` |
| **精密轨道（POEORB）目录** | **下载/存放路径，默认 `<实验目录>/poeorb`，可覆盖为公共轨道库** | `poeorb_download.py --out` |

### 4.5 实验注册表（`src/host/registry.ts`）

- 记录当前/历史实验：目录、地形、参数快照、状态、启动时间
- 每个实验记录 `dataDirs: { slc, poeorb, gacos, dem }` 四类数据目录快照
- 持久化到 `~/.dsh/insar-genie/experiments.json`

## 5. CLIENT 侧组件

> **挂载位置决策（2026-08-22 晚，用户授权自主执行）**：经调研 DSH 真实插槽生态（`slots.inject` 全量清单），可用插槽为 `conversation.chat.turnTail` / `conversation.chat.node` / `conversation.input.dock/left/overlay` / `settings.section` / `settings.general.item` / `settings.plugin.item` / `shell.overlay`——**没有独立侧边栏固定面板插槽**（侧边栏由 dsh-better-sidebar 私有实现，不暴露通用插槽）。因此：
> - **ProgressPanel → `conversation.chat.turnTail`**：对话消息尾部，**自带 30s 轮询 `insar_status`，不依赖 AI 主动汇报**——用户只要在看对话，进度实时可见
> - **ParamConfirm → `conversation.chat.turnTail`**：AI 生成参数时渲染确认表单
> - **SettingsCard + 实验总览 → `settings.section`**：设置页插件区（dshmarket 同款 Discover/Themes/Installed 模式），常驻可查历史
>
> **构建链（参考 dshmarket）**：`tsdown` 打包 client → `client/client.js`（ModuleLoader 格式，`window.__ModuleLoader__.load({id, factory})`）；新增 devDeps（tsdown/react/react-dom/@types/react/@testing-library/react/jsdom/dsh-client-runtime/dsh-client-ui-primitives/dsh-client-ui-slots/dsh-client-ui-settings-plugins/dsh-invariants）；`dsh.client` 配置 `{inject: [...], platform: "web"}`；package.json exports 加 `./client`。

### 5.1 参数确认卡片（ParamConfirm）

- 触发：AI 执行 `insar_run` 前，先推确认卡，不直接执行
- 内容：
  - 地形识别结果（AI 自动判定，用户可改）
  - 联动参数表：多视 / 时间基线 / 空间基线（显式显示 2%/4% 而非默认 45%）/ 滤波 / 解缠 / GACOS
  - **防呆校验**：基线不在 2-4% 区间 → 红色警告 + 阻断确认
  - 数据目录确认：SLC / POEORB / GACOS / DEM 四条路径 + 修改入口
- 交互：确认 / 修改后确认 / 取消
- 挂载：`conversation.chat.turnTail`

### 5.2 进度面板（ProgressPanel）

- 数据源：`insar_status` 工具
- 展示：
  - 五步流程条（连接图 → 干涉 → 解缠 → 反演1 → 反演2 → 地理编码）
  - 当前步细粒度进度（干涉图 = 已完成对/总对 + 每对耗时 → 剩余时间）
  - 数据盘占用
  - 异常区：停滞/失败定位 + 修复建议按钮
- 刷新：**自带 30s 轮询 `insar_status`（不依赖 AI 汇报）**；实验选择：从注册表列出现有实验（下拉）
- 挂载：`conversation.chat.turnTail`

### 5.3 与 host 通信

- `inject` 依赖（`dsh-client-runtime`、`dsh-api-remotes` 等）+ API gateway 调 host 工具
- 组件注册到 UI 插槽（见上方挂载位置决策）

### 5.4 模板库 UI（轻量）

- `insar_templates` 数据渲染为下拉/卡片：选地形 → 预览参数 → 一键填入确认卡

### 5.5 SettingsCard + 实验总览

- 设置页 `settings.section` 内：凭证（Earthdata/GACOS）、路径（ENVI/SARscape/workDir/**poeorbDir**）、实验列表/历史（从注册表读）
- 参考 dshmarket 的 PluginCard/SettingsCard 模式


## 6. 数据流与交互时序

```
用户: "跑 SBAS，区域 xxx.shp，2020-2025，VV"
  │
  ▼
① AI 读 insar-genie 技能 → 识别地形 → 调 insar_templates 取模板
  │
  ▼
② AI 生成参数表 → 推 ParamConfirm 卡片（基线显式 2%/4%，不在区间→红色警告阻断）
  │
  ▼ 用户确认（可改）
③ host 记录实验到 registry（含 poeorb/gacos/dem/slc 目录快照）
  │
  ▼
④ insar_run 执行下载 → 配套数据（poeorb/gacos/dem）
  │
  ▼
⑤ insar_run 执行批处理（bat → SARscape）→ 启动 sbas_guard.py 守护
  │
  ▼
⑥ ProgressPanel 每 30s 调 insar_status → 渲染五步进度 + 剩余时间
  │
  ▼
⑦ 异常/停滞 → host 解析日志 → 面板显示修复建议 → AI 自动处理或问用户
  │
  ▼
⑧ 完成 → 面板提示 + AI 汇报结果
```

状态流转：`draft → queued → running → paused → failed(带诊断) → done`

## 7. 错误处理与异常诊断

### 7.1 分层错误模型

| 层 | 错误类型 | 处理方式 |
|---|---|---|
| 配置层 | 凭证缺失/路径不存在/磁盘不足 | 启动前预检，缺失项在确认卡列出，阻断执行 |
| 下载层 | 网络失败/ASF 429/MD5 不符 | 复用 multi_download.py 重试 + 断点续传 |
| 批处理层 | SARscape 退出码非 0 / bat 参数失效 | 捕获退出码 + 解析 sarbatch_*.txt，结构化错误码 |
| 运行层 | 进程停滞/守护误判/崩溃 | sbas_guard.py 停滞检测（CPU 增量 + 文件写入）|

### 7.2 异常诊断规则库（内置，来自交接文档教训）

- "Progress 100% 但 auxiliary.sml 无 OK" → 误报完成，查子步骤标记
- "baseline estimation failure" → burst 级诊断，非整体失败，让任务跑完
- "SetParam 返回 0" → 参数名静默失效，查官方全名
- 停滞但 CPU 活跃 → main_sbas 内存密集属正常
- "PARAMETERS_INFO 落盘值 != 快照值" → 参数未生效告警

### 7.3 防呆校验（执行前）

- 基线区间校验：空间基线 2-4%（可配置放宽，但必须显式）→ 不在区间阻断
- 落盘校验：执行后解析 `tmp/*/work/PARAMETERS_INFO_*.xml` 实际值 == 快照，不一致告警
- 参数名校验：bat 生成时内置官方大写全名白名单

## 8. 测试策略

| 层 | 内容 | 方式 |
|---|---|---|
| 单元测试 | status.ts 解析 step_performed.sml / Process.log / guard 日志 | 真实历史日志 fixture（民勤 8/18、当前 GUI 轮样本）|
| 单元测试 | 参数模板 / 基线校验 / 落盘 XML 校验 | 纯函数断言：45% 拦截、2%/4% 通过 |
| 集成测试 | bat 生成 → 参数写入正确（基线显式）| 2% 连接图试跑验证 |
| 端到端 | 假实验流程（mock spawn）| 状态机流转验证 |
| UI 测试 | ParamConfirm / ProgressPanel | Playwright（webapp-testing）|

## 9. 实施阶段（YAGNI）

- **阶段 1 — 核心闭环**：skill provider + insar_status + registry + settings（含 POEORB）+ ProgressPanel
- **阶段 2 — 防呆执行**：insar_run + bat 自动生成（基线显式）+ 落盘校验 + ParamConfirm
- **阶段 3 — 诊断与模板**：异常诊断规则库 + 模板库 UI + insar_templates

## 10. 分发

- npm 包 `@dsh-custom/insar-genie`（或 GitHub 仓库），`dsh plugin` 安装
- 打包 `assets/`（SKILL.md + scripts/ + experiment/），首次加载解压/链接到技能目录
