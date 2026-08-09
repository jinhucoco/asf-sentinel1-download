# SBAS-InSAR 全链路自动化（AI 技能）

**一个给 AI 工具（pi / Codex / Claude Code / Cursor）用的技能 + 实验全链路流水线**：
在对话里说出需求，AI 自动从 ASF 下载 Sentinel-1 数据、获取配套数据（DEM/GACOS/POEORB）、
配合 SARscape 批处理完成 SBAS-InSAR 全流程，并有守护进程全程自动监控汇报。

> 仓库结构：`SKILL.md`（AI 技能定义）+ `scripts/`（下载/配套工具）+ `experiment/`（SARscape 批处理 + 守护）+ 环境自检 + 验证脚本。
> 遵循 `dev` 分支开发 → 测试 → 合并 `main` 的工作流。

---

## 🤖 AI 技能使用（核心方式）

### 安装到 AI 工具

```bash
# Pi 用户（自动注册为 pi 技能）
pi install npm:pi-asf-sentinel1-slc

# 其他 AI 工具（Codex / Claude Code / Cursor / pi）
curl -fsSL https://raw.githubusercontent.com/jinhucoco/asf-sentinel1-download/main/install.sh | bash
# 脚本自动：检测工具 → 安装到对应技能目录 → 装依赖 → 生成凭证模板
```

> ⚠️ **装好后记得配置账号密码**：在 AI 对话中说 **"配置 ASF 账号密码"**，AI 引导你输入并保存到 `config.json`。
> 💡 Codex 沙箱用户：默认关闭网络 + HOME 只读，请在**宿主终端**跑安装，或浏览器下载 zip 手动解压。

### 对话式使用（AI 自动执行）

| 你说 | AI 做什么 |
|---|---|
| "**从 ASF 下载哨兵数据**，区域 研究区.shp，时间 20240101 至 20240630，VV+VH" | Earthdata 认证 → AOI 转 WKT → 逐极化搜索 → (方向,轨道)分组 → 覆盖校验 → 清单确认 → 批量下载 |
| "**配置 ASF 账号密码**" | 引导输入 Earthdata 凭证，写入 config.json |
| "**分析这批数据质量**" | 轨道/卫星/frame 覆盖、逐时相检查、覆盖图、生成清单 |
| "**下载配套数据**（POEORB / GACOS / DEM）" | 按研究区自动获取精密轨道、大气延迟、30m DEM |

**技能触发词**（SKILL.md 定义）："从ASF下载哨兵数据"、"下载Sentinel-1"、"ASF下载S1"。

### 💬 真实对话示例（甘肃古浪 SBAS 实验）

完整演示「下载 → 配套数据 → AI-InSAR 处理 → 守护查询」全链路对话（示例数据：古浪 77 景 / 轨道 135 降轨 / VV）：

```
你: 从 ASF 下载哨兵数据，区域 古浪.shp，时间 20200101 至 20251231，VV
AI: 搜索完成，按(方向,轨道)分组：
      [1] DESCENDING / 轨道 135: 77 景 ✅ 覆盖研究区
      [2] ASCENDING  / 轨道 55:  38 景（部分覆盖）
    逐时相覆盖检查：77/77 有效。用轨道 135 吗？(1)
你: 1
AI: 清单已生成（77 景），确认下载？(y)
你: y
AI: 下载完成：77 景 SLC → sentinel1_data/（逐时相全覆盖，轨道一致性通过）

你: 下载配套数据
AI: 已获取——POEORB 77 个 / GACOS 77 个（ztd）/ DEM（n37e102/103、n38e102/103）

你: 开始 SBAS 实验
AI: 研究区识别：祁连山前 + 黄土丘陵（低相干）→ 建议参数：
      多视 8:2 | 时间基线 180 天 | Goldstein 窗 64 | MCF 解缠 0.2 | GACOS 大气
    1. 都用推荐值？ 2. 要调整吗？（如解缠改 Delaunay、模型改 quadratic）
你: 都用推荐值
AI: 已确认参数 → 执行连接图（376 对）→ 干涉图生成（预计 ~30 小时）→ 完成后进入反演

你: 实验进展如何
AI: 干涉图生成 79%（R_6→S_7），磁盘 617GB，预计明早完成，守护监控中
```

---

## 🔗 全链路总览（AI + 批处理）

```
① 数据下载（AI 技能）          ② 数据准备（AI 技能）       ③ AI-InSAR 处理（AI 执行）     ④ 监控（守护 + AI 查询）
────────────────────          ────────────────────        ──────────────────────      ─────────────────
对话说"下载哨兵数据"    →      POEORB/GACOS/DEM      →      AI: 识别地形→列参数表   →     sbas_guard.py
AI 自动: 搜索/分组/      →      对话说"下载配套数据"   →      你确认 → AI 执行 bat    →     自动体检 30 分钟
覆盖校验/清单/下载             AI 自动获取             →      连接图                   →     微信 + 邮件
                    →                                  →      (bat/01_connection_graph)   异常自动重启
                                                        →      干涉图生成              →     磁盘预警
                                                        →      (bat/02_interferogram)   →     AI 随时查进度
                                                        →      反演 ×2 + 地理编码
                                                        →      (bat/03_* 待补)
```

- **① ② 由 AI 技能自动完成**（对话即用，不需要命令行）
- **③ AI 主导**：识别研究区 → 列参数表逐项确认 → 执行 `experiment/bat/` → 汇报（需 ENVI+SARscape）
- **④ 守护全程监控 + AI 随时汇报**（用户问“实验进展如何”，AI 查日志回答）

---

## 🌟 核心能力

| 阶段 | 能力 |
|---|---|
| **AI 数据下载** | 对话触发、同轨同向、逐时相全覆盖校验、轨道一致性、多线程分片（8×）、断点续传、多极化 |
| **AI 配套数据** | POEORB / GACOS（邮件自动收件）/ NASADEM 30m——全部官方源 |
| **AI-InSAR 处理** | 对话说"开始实验" → AI 识别地形、列参数表逐项确认 → 执行 SARscape 五步 bat（连接图→干涉→反演×2→地理编码）→ 汇报；零硬编码（config.env）|
| **AI 守护监控** | AI 部署守护、自动体检、微信（Server酱）+ 邮件、崩溃自动重启、磁盘/停滞预警；用户随时问进展 AI 查日志回答 |
| **AI 可移植** | 对话说"检查环境"→ AI 跑自检（27 项）并修复；"验证仓库"→ AI 跑全链路验证（34 项）|

---

## 📦 前置条件（Prerequisites）

| 依赖 | 必需？ | 说明 |
|---|---|---|
| **Python 3.10+** | ✅ | `pip install -r scripts/requirements.txt` |
| **ENVI + SARscape** | 处理阶段 ✅ | 商业软件，需自己的 license（下载/配套数据不需要）|
| **NASA Earthdata 账号** | ✅ | 免费注册，AI 对话中说"配置 ASF 账号密码" |
| **SLC 数据** | ✅ | AI 技能自动从 ASF 下载 |
| **GACOS/DEM/POEORB** | ✅ | AI 技能自动获取 |
| **通知凭证** | 可选 | Server酱 SendKey、SMTP 授权码（守护汇报用）|

---

## ⚡ 快速开始（全新用户）

**分两阶段：一次性环境准备 + 日常 AI 对话使用**。环境准备需要手动执行（AI 无法替你装软件），之后的一切操作都在 AI 对话中完成。

### 阶段 A：环境准备（一次性，约 10 分钟）

```bash
# 1. 拉取代码
 git clone --branch dev https://github.com/jinhucoco/asf-sentinel1-download.git
cd asf-sentinel1-download

# 2. 安装 Python 依赖
pip install -r scripts/requirements.txt

# 3. 安装为 AI 技能（核心：让 AI 能对话触发）
curl -fsSL https://raw.githubusercontent.com/jinhucoco/asf-sentinel1-download/main/install.sh | bash

# 4. 配置路径（复制模板并按本机修改）
copy experiment\config.example.env experiment\config.env
#   编辑 config.env：工作目录 / SLC 数据 / 输出盘 / DEM / GACOS / ENVI+SARscape 路径

# 5. 环境自检（27 项）——全部 [OK] 再继续（可让 AI 协助诊断 FAIL）
python experiment\check_environment.py
```

### 阶段 B：日常使用（全部在 AI 对话中）

```
你: “配置 ASF 账号密码”        → AI 引导输入 Earthdata 凭证
你: “从 ASF 下载哨兵数据，区域 研究区.shp，时间 20240101 至 20240630，VV+VH”
                              → AI 自动搜索/校验/确认/下载
你: “下载配套数据”            → AI 获取 POEORB/GACOS/DEM
你: “开始 SBAS 实验”          → AI 列参数表 → 你确认 → AI 跑批处理
你: “实验进展如何”            → AI 查守护日志汇报
```

> 验证：`python scripts/verify_clone.py`（34 项）可在 AI 协助下跑，确保仓库/环境就绪。

---

## 🚀 深入使用（全部环节：对话优先）

> 每个环节都是 **「你说 → AI 自动做」**；命令行仅作高级/调试用（AI 也可帮你敲）。

### ① 下载 S1 SLC 数据

**对话方式**（推荐）：

```
你: “从 ASF 下载哨兵数据，区域 研究区.shp，时间 20200101 至 20251231，VV+VH”
AI: ① Earthdata 认证 → ② AOI 转 WKT → ③ 逐极化搜索 → ④ (方向,轨道)分组
    → ⑤ 覆盖校验（只保留全覆盖轨道组）→ ⑥ 列清单给你确认 → ⑦ 批量下载 → ⑧ 汇报
```

下载保证（AI 自动执行，无需你关心）：同一相对轨道 + 同一方向 + 每个时相全覆盖研究区 + 轨道一致性校验。

**命令方式**（高级/调试，AI 可代敲）：

```bash
python scripts\analyze.py --aoi 研究区.kml --start 20200101 --end 20251231 --pol VV+VH --out ./analysis --sample --plot
python scripts\robust_download.py --aoi 研究区.kml --start 20240101 --end 20240630 --pol VV+VH --out ./sentinel1_data
python scripts\multi_download.py --list ./analysis/list_DESCENDING_135.csv --out ./sentinel1_data
```

### ② 获取配套数据

**对话方式**（推荐）：

```
你: “下载配套数据”（或分别说“下载 POEORB / GACOS / DEM”）
AI: 自动按研究区获取——POEORB 精密轨道（免账号）、GACOS 大气延迟（提交→收邮件→下载 ztd）、NASADEM 30m（自动分幅）
```

**命令方式**（高级/调试）：

```bash
python scripts\poeorb_download.py --data-dir ./sentinel1_data --out ./poeorb
python scripts\gacos_download.py --bbox "38.34 101.96 103.48 37.28" --list 时相日期.txt --time 23:10 --email 你的邮箱 --out ./gacos
python scripts\gacos_fetch.py --mail-config mail.json --out ./gacos --expect 77 --loop
python scripts\dem_download.py --aoi 研究区.shp --out ./dem
```

### ③ AI-InSAR 处理（需 ENVI+SARscape）

**对话方式**（推荐）：

```
你: “开始 SBAS 实验” / “开始第 1 步”
AI: ① 识别研究区地形 → ② 列该步参数表（含原理）→ ③ 你确认/调整 → ④ 执行 bat → ⑤ 汇报
```

> 每步执行前 AI 都会先列参数确认（见 SKILL.md「实验参数设置提醒机制」），不盲跑默认值。

**命令方式**（高级）：

```bash
experiment\bat\01_connection_graph\run_cg_final.bat   # 连接图（第 1 步）
experiment\bat\02_interferogram\run_interf.bat        # 干涉图生成（第 2 步）
# 反演 ×2 + 地理编码（第 3-5 步 bat 待补，参数已定）
```

> 所有 bat 从 `config.env` 读路径，**零硬编码**；分类存放 `01_connection_graph` / `02_interferogram` / `03_data_prep`。

### ④ 守护监控

**对话方式**（推荐）：

```
你: “开始监控”           → AI 部署守护并启动（整目录复制到 WORK_DIR/ + python -u sbas_guard.py）
你: “实验进展如何”       → AI 查守护日志汇报（进度/磁盘/异常）
你: “跑完没/有没有异常”  → AI 读体检记录回答
```

**命令方式**（高级）：

```bash
cp -r experiment/asf_experiment D:/work/data/
cd D:/work/data/asf_experiment && python -u sbas_guard.py
```

守护能力：30 分钟自动体检 + 微信（Server酱）/邮件汇报 + 崩溃自动重启 + 磁盘/停滞预警（5 条/天额度内只推关键事件）。

### ⑤ 环境自检与验证

**对话方式**（推荐）：

```
你: “检查环境” → AI 跑 check_environment.py，有 [FAIL] 按提示修复后重跑
你: “验证仓库” → AI 跑 verify_clone.py，34 项全过即可使用
```

**命令方式**（高级）：

```bash
python experiment\check_environment.py   # 27 项环境检查
python scripts\verify_clone.py           # 34 项仓库/代码/工具验证
```

---

## 📁 文件结构（File Structure）

```
asf-sentinel1-download/
├── SKILL.md                     # AI 技能定义（frontmatter 触发词 + 工作流）
├── scripts/                     # 数据下载 + 配套数据工具（AI 技能执行体）
│   ├── download.py              # 主下载（搜索/分组/覆盖/校验/下载）
│   ├── analyze.py / analysis.py # 数据质量分析与清单
│   ├── multi_download.py        # 多线程分片下载
│   ├── robust_download.py       # 稳健下载（断点续传）
│   ├── poeorb_download.py / gacos_download.py / gacos_fetch.py / dem_download.py
│   ├── progress_gui.py          # 桌面进度条
│   ├── requirements.txt         # Python 依赖
│   └── verify_clone.py          # 全链路验证脚本
├── skills/                      # 技能发布镜像（安装机制，测试守护同步）
├── tests/                       # 47 个单元测试
├── experiment/                  # 实验处理（需 ENVI/SARscape）
│   ├── config.example.env       # 路径配置模板（本机值 config.env 不入库）
│   ├── config_loader.py         # python 配置读取
│   ├── check_environment.py     # 环境自检（27 项）
│   ├── README.md                # 实验区说明
│   ├── bat/                     # SARscape 批处理（按步骤分类）
│   │   ├── 01_connection_graph/ # 连接图（第 1 步）
│   │   ├── 02_interferogram/    # 干涉图生成（第 2 步）
│   │   └── 03_data_prep/        # GACOS 导入 / DEM / geoid
│   ├── asf_experiment/          # 守护运行单元（部署整目录到 WORK_DIR/）
│   │   └── sbas_guard.py        # 守护（体检/汇报/自动重启）
│   ├── tools/                   # 实验辅助（连接图绘制等）
│   ├── 配套数据/                # GACOS 收件工具等
│   └── sar/dem/                 # 研究区 DEM 配置
├── README.md / install.sh / package.json
└── docs/
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
- 守护 `sbas_guard.py` 独立运行，读 config + notify/mail 配置

---

## 🧪 测试（Testing）

```bash
cd asf-sentinel1-download
python -m pytest tests/ -q          # 47 个单元测试（下载逻辑 + 镜像一致性）
python scripts/verify_clone.py      # 34 项全链路验证（全新用户视角）
```

---

## ⚠️ 已知限制（Known Limitations）

- **第 0 步 SLC 导入 bat 待补**：当前用 SARscape GUI 手动导入（77 景），自动化 bat 未写（见待办）
- **第 3-5 步 bat 待补**：反演 ×2 + 地理编码的批处理未生成（参数已定，实验进行中）
- **ENVI/SARscape 为商业软件**：需自己的 license，代码无法替代
- **仓库名暂未改**：当前为 asf-sentinel1-download，全链路化后计划更名
- **GACOS 依赖邮箱**：需 IMAP 授权码，偶发漏生成某日期需单独重提

---

## 📄 License

MIT

## 🙏 致谢（Acknowledgments）

- ASF（Alaska Satellite Facility）数据与 asf_search 库
- sarmap 的 SARscape 批处理接口
- GACOS（Generic Atmospheric Correction Online Service）
