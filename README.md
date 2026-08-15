# SBAS-InSAR 全链路自动化（insar-genie）

**一个给 AI 工具（DSH / pi / Codex / Claude Code / Cursor）用的技能 + 实验全链路流水线**：
在对话里说出需求，AI 自动从 ASF 下载 Sentinel-1 数据、获取配套数据（DEM/GACOS/POEORB）、
基于 ENVI 和 SARscape 完成 SBAS-InSAR 全流程，并有守护进程全程自动监控汇报。

> 仓库结构：`SKILL.md`（AI 技能定义）+ `scripts/`（下载/配套工具）+ `experiment/`（SARscape 批处理 + 守护）+ `dsh/`（DSH 社区插件）+ 环境自检 + 验证脚本。

---

## ✨ 核心能力

| 阶段 | 能力 |
|---|---|
| **AI 数据下载** | 对话触发、同轨同向、逐时相全覆盖校验、轨道一致性、多线程分片（8×）、断点续传、多极化 |
| **AI 配套数据** | POEORB / GACOS（邮件自动收件）/ NASADEM 30m——全部官方源 |
| **AI-InSAR 处理** | 对话说"开始实验" → AI 识别地形、列参数表逐项确认 → 执行 SARscape 六步 bat（导入→连接图→干涉→反演×2→地理编码）→ 汇报；零硬编码（config.env）|
| **AI 守护监控** | AI 部署守护、自动体检、微信（Server酱）+ 邮件、崩溃自动重启、磁盘/停滞预警；用户随时问进展 AI 查日志回答 |
| **AI 可移植** | 对话说"检查环境"→ AI 跑自检并修复；"验证仓库"→ AI 跑全链路验证 |

---

## 📦 安装（按 Agent 选择一种）

### 🧩 DeepSeek Harness (DSH) — 一键安装为插件

本仓库直接以 **agent preset 插件** 形式安装：安装后新建会话选择「**SBAS 全链路**」模式，
AI 即自动携带 insar-genie 技能（下载/配套/实验/监控全部脚本），对话即用。

```bash
# Windows（PowerShell）
powershell -Command "irm https://raw.githubusercontent.com/jinhucoco/insar-genie/main/dsh/install-dsh.ps1 | iex"

# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/jinhucoco/insar-genie/main/dsh/install-dsh.sh | bash
```

安装后：
1. 打开 DSH Web 界面 → 点击「新建会话」
2. 选择模式（preset）: **SBAS 全链路**
3. 对话中说「配置 ASF 账号密码」→ 引导填写 Earthdata 凭证，即可开始

> 卸载：删除 `~/.dsh/.agent-presets/insar-genie/` 目录即可。
> 源码位置：仓库 `dsh/insar-genie/`（agent.cordis.yml + preset.yml + 自带技能），安装脚本 `dsh/install-dsh.ps1` / `dsh/install-dsh.sh`。

### 🤖 pi — npm 技能包

```bash
pi install npm:pi-asf-sentinel1-slc
```

安装后新会话自动注册技能（已开会话需 `/reload` 或重开会话）。

### 💻 Codex / Claude Code / Cursor 等 — 自动安装脚本

```bash
curl -fsSL https://raw.githubusercontent.com/jinhucoco/insar-genie/main/install.sh | bash
# 脚本自动：检测工具 → 安装到对应技能目录 → 装依赖 → 生成凭证模板
```

> 💡 Codex 沙箱用户：默认关闭网络 + HOME 只读，请在**宿主终端**跑安装，或浏览器下载 zip 手动解压。

### 📥 离线 / 手动安装

从 GitHub Releases 下载 `insar-genie-<version>.zip`，解压后将目录放到对应 Agent 的技能目录
（pi 为 `~/.pi/agent/skills/`，DSH 为 `~/.dsh/.agent-presets/`），再按上面方式在对话中开始使用。

---

## 🚀 快速开始（3 步，全部在对话中完成）

```
你: 帮我配置环境
AI：拉代码/装依赖/跑 setup_env.py 向导（自动探测路径）→ 生成 config.env → 自检 27 项
你: 配置 ASF 账号密码
AI：引导输入 Earthdata 凭证，写入 config.json
你: 从 ASF 下载哨兵数据，区域 研究区.shp，时间 20240101 至 20240630，VV+VH
AI：自动搜索/校验/确认/下载（开始使用！）
```

> 环境验证：对 AI 说「验证仓库」，AI 跑 34 项全链路验证确保就绪。

---

## 🛠️ 使用说明

> 每个环节都是 **「你说 → AI 自动做」**，无需任何命令行操作。

### ① 环境自检与验证

```
你: “检查环境” → AI 跑 check_environment.py，有 [FAIL] 按提示修复后重跑
你: “验证仓库” → AI 跑 verify_clone.py，34 项全过即可使用
```

### ② 下载 S1 SLC 数据

```
你: “从 ASF 下载哨兵数据，区域 研究区.shp，时间 20200101 至 20251231，VV+VH”
AI: ① Earthdata 认证 → ② AOI 转 WKT → ③ 逐极化搜索 → ④ (方向,轨道)分组
    → ⑤ 覆盖校验（只保留全覆盖轨道组）→ ⑥ 列清单给你确认 → ⑦ 批量下载 → ⑧ 汇报
```

下载保证（AI 自动执行，无需你关心）：同一相对轨道 + 同一方向 + 每个时相全覆盖研究区 + 轨道一致性校验。

### ③ 获取配套数据

```
你: “下载配套数据”（或分别说“下载 POEORB / GACOS / DEM”）
AI: 自动按研究区获取——POEORB 精密轨道（免账号）、GACOS 大气延迟（提交→收邮件→下载 ztd）、NASADEM 30m（自动分幅）
```

### ④ AI-InSAR 处理（需 ENVI+SARscape）

```
你: “开始 SBAS 实验” / “开始第 1 步”
AI: ① 识别研究区地形 → ② 列该步参数表（含原理）→ ③ 你确认/调整 → ④ 执行 bat → ⑤ 汇报
```

> 每步执行前 AI 都会先列参数确认（见 SKILL.md「实验参数设置提醒机制」），不盲跑默认值。
> 所有 bat 从 `config.env` 读路径，**零硬编码**；按步骤分类存放 `00_import` ~ `04_geocode`。

### ⑤ 守护监控

```
你: “开始监控”           → AI 部署守护并启动（整目录复制到 WORK_DIR/ + python -u sbas_guard.py）
你: “实验进展如何”       → AI 查守护日志汇报（进度/磁盘/异常）
你: “跑完没/有没有异常”  → AI 读体检记录回答
```

守护能力：30 分钟自动体检 + 微信（Server酱）/邮件汇报 + 崩溃自动重启 + 磁盘/停滞预警（5 条/天额度内只推关键事件）。

---

## 📁 文件结构（File Structure）

```
insar-genie/
├── SKILL.md                     # AI 技能定义（frontmatter 触发词 + 工作流）
├── scripts/                     # 数据下载 + 配套数据工具（AI 技能执行体）
│   ├── download.py              # 主下载（纯函数：WKT/覆盖/清单）
│   ├── download_session.py      # DownloadSession 类（认证/搜索/选择/校验/下载编排）
│   ├── analyze.py / analysis.py # 数据质量分析与清单
│   ├── multi_download.py        # 多线程分片下载
│   ├── robust_download.py       # 稳健下载（断点续传）
│   ├── poeorb_download.py / gacos_download.py / gacos_fetch.py / dem_download.py
│   ├── progress_gui.py          # 桌面进度条
│   ├── requirements.txt         # Python 依赖
│   └── verify_clone.py          # 全链路验证脚本
├── skills/                      # 技能发布镜像（安装机制，测试守护同步）
├── tests/                       # 48 个单元测试（含镜像一致性）
├── .github/workflows/test.yml   # CI：pytest + ruff + 语法 + bat 控制字符检查
├── pyproject.toml / .pre-commit-config.yaml  # ruff 规范 + 提交前自动检查
├── dsh/                         # DSH 社区插件（agent preset + 安装脚本）
│   ├── insar-genie/             #   preset 包（agent.cordis.yml + preset.yml + 自带技能镜像）
│   ├── install-dsh.ps1 / install-dsh.sh
├── experiment/                  # 实验处理（需 ENVI/SARscape）
│   ├── config.example.env       # 路径配置模板（本机值 config.env 不入库）
│   ├── config_loader.py         # python 配置读取
│   ├── check_environment.py     # 环境自检（27 项）
│   ├── setup_env.py             # 环境配置向导（自动探测路径）
│   ├── README.md                # 实验区说明
│   ├── bat/                     # SARscape 批处理（按步骤分类）
│   │   ├── 00_import/           # SLC 导入（第 0 步，ROI 裁剪/极化可选）
│   │   ├── 01_connection_graph/ # 连接图（第 1 步）
│   │   ├── 02_interferogram/    # 干涉图生成（第 2 步）
│   │   ├── 03_data_prep/        # GACOS 导入 / DEM / geoid
│   │   ├── 03_inversion/        # 反演 Step1 + Step2（第 3 步）
│   │   └── 04_geocode/          # 地理编码（第 5 步）
│   ├── asf_experiment/          # 守护运行单元（部署整目录到 WORK_DIR/）
│   │   └── sbas_guard.py        # 守护 v4（Guardian 类：状态机监控/体检/汇报/自动重启）
│   ├── tools/                   # 实验辅助（连接图绘制等）
│   └── sar/dem/                 # 研究区 DEM 配置
├── README.md / install.sh / package.json / config.example.json / LICENSE
└── docs/                        # 文档与示意图
```

---

## 🧠 工作原理

### AI 技能（SKILL.md + scripts/）

- **触发**：对话中出现触发词（"从ASF下载哨兵数据"等），AI 加载 SKILL.md 按流程执行
- **认证**：ASFSession.auth_with_creds()（EDL token + asf-urs cookie），凭证存 config.json
- **SBAS 数据要求**：同一相对轨道 + 同一方向 + 每个时相全覆盖研究区
- **覆盖校验**：单景 `footprint.covers(aoi)` → 跨帧并集 `unary_union.covers(aoi)`
- **轨道一致性**：下载前校验组内 pathNumber 完全一致（防同 frame 混轨道）
- **逐时相检查**：每个时相（同一天）并集必须全覆盖，无效时相自动排除

### 实验处理（experiment/）

- SARscape 批处理通过 `config.env` 读取全部路径，**零硬编码**
- bat 用 `%~dp0..\..\config.env` 定位配置；python 用 `config_loader.py`
- 守护 `sbas_guard.py` **v4（Guardian 类，状态机）**独立运行：监控状态为实例属性，
  主循环 `run()`，`restart()` 用实例 bat_file；读 config + notify/mail 配置
- 下载流程封装为 **`DownloadSession` 类**（download_session.py）：认证/搜索/分组/
  覆盖过滤/选择/校验/下载拆成可复用方法，`run_download()` 兼容委托

---

## 🛡️ 质量保障（CI + 规范）

- **GitHub Actions CI**：每次 push/PR 自动跑 ①pytest（48 测试）②ruff lint ③ruff format ④全部 Python 语法 ⑤bat 控制字符扫描
- **ruff**：代码规范统一（pyproject.toml 定制：中文注释/脚本惯用法适配）
- **pre-commit**：提交前自动 ruff + pytest，防止脏代码进 dev
- **镜像一致性测试**：`skills/` 发布镜像与根目录脚本必须同步（改一处忘另一处立即报警）
- **平台兼容**：sanitize_filename 等跨平台处理（Windows/Linux 行为一致）

---

## 📄 License

MIT

## 🙏 致谢（Acknowledgments）

- ASF（Alaska Satellite Facility）数据与 asf_search 库
- sarmap 的 SARscape 批处理接口
- GACOS（Generic Atmospheric Correction Online Service）
