# SBAS-InSAR 全链路自动化

从 **Sentinel-1 数据下载 → 配套数据（DEM/GACOS/POEORB）→ SARscape 批处理 → 形变监测 → 守护监控** 的完整自动化方案。

> 单一仓库管理全链路代码：数据下载工具（`scripts/`）+ 实验处理（`experiment/`）+ 环境自检 + 守护。
> 遵循 `dev` 分支开发 → 测试 → 合并 `main` 的工作流。

---

## 🔗 全链路总览

```
① 数据下载                   ② 数据准备               ③ SARscape 处理             ④ 监控
──────────────              ──────────────           ──────────────────         ──────────
SLC 主数据 (scripts/)   →    POEORB (scripts/)   →    Import SLC            →    守护监控
download.py                   poeorb_download.py      (bat/00_import 待补)      (asf_experiment/
multi_download.py       →    GACOS  (scripts/)   →    连接图                    sbas_guard.py)
robust_download.py            gacos_download.py       (bat/01_connection_graph)  自动体检
analyze.py / analysis.py      gacos_fetch.py     →    干涉图生成                微信/邮件告警
                    →        DEM    (scripts/)   →    (bat/02_interferogram)    异常自动重启
                              dem_download.py    →    反演 1/2 + 地理编码
                                                     (bat/03_* 待补)
```

- **下载工具**（`scripts/`）：所有用户都能用，不需要 ENVI
- **实验处理**（`experiment/`）：需要 ENVI + SARscape license
- **守护**（`experiment/asf_experiment/`）：全程自动监控，微信/邮件推送

---

## 🌟 核心特性

| 阶段 | 能力 |
|---|---|
| **数据下载** | 同轨同向、逐时相全覆盖校验、轨道一致性校验、多线程分片（8× 提速）、断点续传、多极化 |
| **配套数据** | POEORB 精密轨道 / GACOS 大气延迟（邮件自动收件）/ NASADEM 30m——全部官方源 |
| **批处理** | SARscape 五步批处理 bat（连接图 → 干涉 → 反演 ×2 → 地理编码），路径全配置化 |
| **守护监控** | 30 分钟自动体检、微信（Server酱）+ 邮件汇报、进程崩溃/停滞自动重启、磁盘预警 |
| **可移植** | 零硬编码路径（`config.env`）、环境自检 27 项、全新用户验证脚本 |

---

## 📦 前置条件（Prerequisites）

| 依赖 | 必需？ | 说明 |
|---|---|---|
| **Python 3.10+** | ✅ | `pip install -r scripts/requirements.txt` |
| **ENVI + SARscape** | 处理阶段 ✅ | 商业软件，需自己的 license（下载工具不需要）|
| **SLC 数据** | ✅ | 用本仓库工具从 ASF 下载（需 Earthdata 账号）|
| **GACOS/DEM/POEORB** | ✅ | 用本仓库配套工具获取 |
| **通知凭证** | 可选 | Server酱 SendKey、SMTP 授权码（守护汇报用）|

---

## ⚡ 快速开始（全新用户）

```bash
# 1. 拉取代码
git clone --branch dev https://github.com/jinhucoco/asf-sentinel1-download.git
cd asf-sentinel1-download

# 2. 安装 Python 依赖
pip install -r scripts/requirements.txt

# 3. 配置路径（复制模板并按本机修改）
copy experiment\config.example.env experiment\config.env
#   编辑 config.env：工作目录 / SLC 数据 / 输出盘 / DEM / GACOS / ENVI+SARscape 路径

# 4. 环境自检（27 项：配置/依赖/路径/软件/磁盘）——全部 [OK] 再继续
python experiment\check_environment.py

# 5. 全链路验证（34 项：仓库完整性/代码健康/工具可运行）——全部通过即可使用
python scripts\verify_clone.py
```

---

## 🚀 使用（按全链路阶段）

### ① 下载 S1 SLC 数据（scripts/）

```bash
# 先分析数据质量（轨道/卫星/frame 覆盖/逐时相/覆盖图/清单）
python scripts\analyze.py --aoi 研究区.kml --start 20200101 --end 20251231 \
  --pol VV+VH --out ./analysis --sample --plot

# 稳健下载（断点续传 + 超时 + 重试）
python scripts\robust_download.py --aoi 研究区.kml --start 20240101 --end 20240630 \
  --pol VV+VH --out ./sentinel1_data

# 大流量/慢网络首选（多线程分片约 8× 提速）
python scripts\multi_download.py --list ./analysis/list_DESCENDING_135.csv \
  --out ./sentinel1_data

# 对话式（AI 工具内）：
#   "从 ASF 下载哨兵数据，区域 研究区.shp，时间 20240101 至 20240630，VV+VH"
```

> 下载保证：同一相对轨道 + 同一方向 + 每个时相全覆盖研究区 + 轨道一致性校验。

### ② 获取配套数据（scripts/）

```bash
# POEORB 精密轨道（免账号）
python scripts\poeorb_download.py --data-dir ./sentinel1_data --out ./poeorb

# GACOS 大气延迟（提交 → 邮件收结果 → 自动下载 ztd）
python scripts\gacos_download.py --bbox "38.34 101.96 103.48 37.28" \
  --list 时相日期.txt --time 23:10 --email 你的邮箱 --out ./gacos
python scripts\gacos_fetch.py --mail-config mail.json --out ./gacos --expect 77 --loop

# NASADEM 30m（研究区自动分幅）
python scripts\dem_download.py --aoi 研究区.shp --out ./dem
```

### ③ SARscape 批处理（experiment/bat/，需 ENVI+SARscape）

```bash
# 按步骤执行（路径已从 config.env 读取，无需改代码）
experiment\bat\01_connection_graph\run_cg_final.bat   # 连接图（第 1 步）
experiment\bat\02_interferogram\run_interf.bat        # 干涉图生成（第 2 步）
# 反演 ×2 + 地理编码（第 3-5 步 bat 待补，参数已定）
```

> 所有 bat 从 `config.env` 读路径，**无硬编码**；分类存放：`01_connection_graph` / `02_interferogram` / `03_data_prep`。

### ④ 守护监控（experiment/asf_experiment/）

```bash
# 部署到运行目录（版本源路径 = 运行路径，整目录复制）
cp -r experiment/asf_experiment D:/work/data/
cd D:/work/data/asf_experiment
python -u sbas_guard.py
```

守护能力：30 分钟自动体检（日志 + 邮件）+ 微信推送（完成/异常/日汇总）+ 进程崩溃自动重启 + 磁盘/停滞预警。推送策略：Server酱 5 条/天额度内只推关键事件。

### ⑤ 环境自检与验证

```bash
python experiment\check_environment.py   # 27 项环境检查（别人机器配置好后先跑）
python scripts\verify_clone.py           # 34 项仓库/代码/工具验证
```

---

## 📁 文件结构（File Structure）

```
asf-sentinel1-download/
├── scripts/                      # 数据下载工具（npm 发布单元）
│   ├── download.py               # 主下载（搜索/分组/覆盖/校验/下载）
│   ├── analyze.py / analysis.py  # 数据质量分析与清单
│   ├── multi_download.py         # 多线程分片下载
│   ├── robust_download.py        # 稳健下载（断点续传）
│   ├── poeorb_download.py / gacos_download.py / gacos_fetch.py / dem_download.py
│   ├── progress_gui.py           # 桌面进度条
│   ├── requirements.txt          # Python 依赖
│   └── verify_clone.py           # 全链路验证脚本
├── skills/                       # 技能发布镜像（安装机制，测试守护同步）
├── tests/                        # 47 个单元测试
├── experiment/                   # 实验处理（需 ENVI/SARscape）
│   ├── config.example.env        # 路径配置模板（本机值 config.env 不入库）
│   ├── config_loader.py          # python 配置读取
│   ├── check_environment.py      # 环境自检（27 项）
│   ├── README.md                 # 实验区说明
│   ├── bat/                      # SARscape 批处理（按步骤分类）
│   │   ├── 01_connection_graph/  # 连接图（第 1 步）
│   │   ├── 02_interferogram/     # 干涉图生成（第 2 步）
│   │   └── 03_data_prep/         # GACOS 导入 / DEM / geoid
│   ├── asf_experiment/           # 守护运行单元（部署整目录到 WORK_DIR/）
│   │   └── sbas_guard.py         # 守护（体检/汇报/自动重启）
│   ├── tools/                    # 实验辅助（连接图绘制等）
│   ├── 配套数据/                 # GACOS 收件工具等
│   └── sar/dem/                  # 研究区 DEM 配置
├── SKILL.md / README.md / install.sh / package.json
└── docs/
```

---

## 🧠 工作原理

### 下载工具核心逻辑（scripts/）

- **SBAS 数据要求**：所有影像同一相对轨道（pathNumber）+ 同一方向（升/降轨），且每个时相完全覆盖研究区
- **覆盖校验**：单景 `footprint.covers(aoi)` → 跨帧并集 `unary_union.covers(aoi)`
- **轨道一致性**：下载前校验组内 pathNumber 完全一致（防同 frame 混轨道）
- **逐时相检查**：每个时相（同一天）并集必须全覆盖，无效时相自动排除

### 实验处理（experiment/）

- SARscape 批处理通过 `config.env` 读取全部路径，**零硬编码**
- bat 用 `%~dp0..\..\config.env` 定位配置；python 用 `config_loader.py`
- 守护 `sbas_guard.py` 独立运行（不依赖旧版自动化系统），读 config + notify/mail 配置

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
