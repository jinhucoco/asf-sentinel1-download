# ASF Sentinel-1 Download Skill（ASF 哨兵一号数据下载技能）

> 从 ASF (Alaska Satellite Facility) 自动下载用于 **SBAS-InSAR** 实验的 Sentinel-1 数据
> Automatically download Sentinel-1 data from ASF for **SBAS-InSAR** experiments

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](#license)
[![Test](https://img.shields.io/badge/Tests-33%20passing-brightgreen)](#测试)
[![npm](https://img.shields.io/npm/v/pi-asf-sentinel1-slc?color=cb3837&logo=npm)](https://www.npmjs.com/package/pi-asf-sentinel1-slc)
[![GitHub](https://img.shields.io/badge/GitHub-jinhucoco%2Fasf--sentinel1--download-blue?logo=github)](https://github.com/jinhucoco/asf-sentinel1-download)

> **🚀 快速安装**：`pi install npm:pi-asf-sentinel1-slc`

---

## 🌟 核心特性（Key Features）

- **🎯 面向 SBAS-InSAR 设计**：自动保证同一轨道（相对轨道号）+ 同一方向（升/降轨）+ 完全覆盖研究区
- **🔍 方向自动探测**：不预设升降轨，搜索后按 (方向, 轨道) 分组统计景数，让你选择用哪组
- **🛡️ 轨道一致性严格校验**：下载前验证组内所有影像 pathNumber 完全一致（同 frame 可能被不同轨道复用）
- **✅ 逐时相覆盖检查**：每个时相（同一天）影像并集必须完全覆盖研究区才有效，单帧部分覆盖的时相自动排除
- **🛰️ 卫星一致性检查**：S1A/S1B/S1C 多卫星混杂自动提示
- **📊 数据分析模式**：`analyze.py` 输出轨道/卫星/frame 覆盖/逐时相/覆盖图/清单，交互式采样频率
- **📐 跨帧自动识别**：研究区压在上下两景边界时，自动识别并下载同一时相的上下两景
- **🛰️ 多极化支持**：默认同时搜索 `VV+VH`（双极化）和 `VV`（单极化），合并清单
- **📄 多格式矢量**：支持 `.shp` / `.kml`（含 SARscape 导出的 `earth.google.com` 命名空间 + 三维带海拔坐标）
- **🔄 稳健下载**：断点续传 + 超时保护 + 自动重试，网络中断不丢进度
- **📋 数据列表展示**：搜索后展示完整清单（日期/轨道/方向/极化/帧号/文件名），并保存到 `inventory.txt`
- **📊 桌面进度条**：下载时 Tkinter 窗口实时显示当前文件 + 总进度 + 百分比
- **🔒 凭证安全**：Earthdata 账号密码存本地 `config.json`，请手动设置文件权限仅本人可读

---

## 📦 安装（Installation）

### 前置条件（Prerequisites）

| 项 | 要求 |
|----|------|
| 操作系统 | Windows / Linux / macOS（进度条 GUI 推荐 Windows，其他平台可用 `--no-gui`） |
| Python | 3.10+ |
| NASA Earthdata 账号 | 免费注册：https://urs.earthdata.nasa.gov/ |
| 网络 | 可访问 api.asf.alaska.edu（中国大陆用户建议代理） |

### ⭐ 方式一：作为 Pi Skill 安装（推荐）

**这是最推荐的方式**——安装后即可通过对话直接触发技能：

```bash
# 一键安装（自动注册为 pi 技能）
pi install npm:pi-asf-sentinel1-slc

# 安装 Python 依赖（asf_search / pyshp / shapely 等）
pip install asf_search pyshp shapely defusedxml matplotlib
```

安装完成后，直接对 pi 说：

> **"从 ASF 下载哨兵数据，区域 `研究区.shp`，时间 20240101 至 20240630，VV+VH"**

pi 会自动加载技能并执行：认证 → 搜索 → 轨道分组 → 覆盖校验 → 采样 → 下载。

### 方式二：克隆 GitHub 仓库

```bash
# 克隆技能
git clone https://github.com/jinhucoco/asf-sentinel1-download.git ~/.pi/agent/skills/asf-sentinel1-download

# 安装依赖
pip install -r requirements.txt
```

### 配置 Earthdata 凭证（两种方式都需要）

NASA 免费注册: https://urs.earthdata.nasa.gov/，然后编辑 `config.json` 填入账号密码：

```json
{
  "username": "your_earthdata_username",
  "password": "your_earthdata_password"
}
```

> ⚠️ **安全提示**：config.json 含明文密码，请确保文件权限仅本人可读写，切勿提交到公开仓库。

---

## 🤖 在其他 AI 工具中使用（Codex / Claude Code / Cursor 等）

本技能遵循 **Agent Skills 标准**（https://agentskills.io/specification），
可以在任何支持该标准的 AI 工具中使用。**一条命令自动完成**：检测工具 →
安装技能 → 安装 Python 依赖 → 生成凭证模板。

### ⭐ 一键安装（推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/jinhucoco/asf-sentinel1-download/main/install.sh | bash
```

脚本会自动：
1. 检测已安装的 AI 工具（Codex / Claude Code / pi）并安装到对应技能目录
2. 安装 Python 依赖（asf_search / pyshp / shapely / defusedxml / matplotlib）
3. 生成 `config.json` 凭证模板（提示你填入 Earthdata 账号密码）
4. 未检测到任何工具时，安装到通用位置 `~/.agents/skills/`

### 手动安装（可选）

```bash
# 1. 获取技能
git clone https://github.com/jinhucoco/asf-sentinel1-download.git

# 2. 复制到对应工具目录
cp -r skills/asf-sentinel1-download ~/.codex/skills/   # Codex
cp -r skills/asf-sentinel1-download ~/.claude/skills/  # Claude Code
cp -r skills/asf-sentinel1-download .agents/skills/    # 项目级（通用）

# 3. 安装依赖 + 配置凭证
pip install -r requirements.txt
cp config.example.json config.json  # 编辑填入账号密码
```

> 💡 **pi 用户**：直接 `pi install npm:pi-asf-sentinel1-slc` 即可（无需脚本）。

---

## ⚡ 快速开始（Quick Start）

**3 分钟上手：** 配置 → 分析 → 采样 → 下载

```bash
# ① 配置凭证（一次性）：编辑 config.json 填入 Earthdata 账号密码
#    {"username": "...", "password": "..."}

# ② 先分析数据质量（推荐）：轨道/卫星/frame 覆盖/逐时相/覆盖图
python analyze.py --aoi 研究区.shp --start 20200101 --end 20251231 \
  --pol VV+VH --out ./analysis --plot

# ③ 交互式采样：选择频率（月/季/半年/年/全部）与时相规则
python analyze.py --aoi 研究区.shp --start 20200101 --end 20251231 \
  --pol VV+VH --out ./analysis --sample

# ④ 按清单下载（断点续传 + 桌面进度条）
python robust_download.py --aoi 研究区.shp --start 20200101 --end 20251231 \
  --pol VV+VH --out ./sentinel1_data
```

**典型输出（一步到位）：**

```
[OK] 认证成功
[OK] 极化 VV+VH: 搜索到 322 个结果
[OK] 轨道一致性: ✅ [135]    卫星: S1A/S1C
  frame 468: 154景 覆盖100% ✅完全覆盖
  frame 467: 15景  覆盖100% ✅完全覆盖
[OK] 逐时相覆盖: 169 有效 / 0 无效
请选择取景频率: [2] 每月 → 每月采样 135 景
[OK] 清单已导出: sampled_DESCENDING_135_monthly.csv
```

> 💡 **最小流程**：只下载不分析的话，直接 `python download.py --aoi 研究区.shp --start ... --end ... --pol VV+VH` 即可。

---

## 🚀 使用（Usage）

### 交互式（推荐，对话式触发技能）

当技能被 AI 代理（如 pi）加载时，直接说：

> "从 ASF 下载哨兵数据，区域 `研究区.shp`，时间 20240101 至 20240630，VV+VH 和 VV"

AI 会自动执行：认证 → 搜索 → 轨道分组 → 展示选择 → 清单确认 → 下载。

### 命令行（手动）

```bash
python download.py \
  --aoi 研究区.kml \
  --start 20240101 \
  --end 20240630 \
  --pol "VV+VH,VV" \
  --out ./sentinel1_data
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--aoi` | 是 | 矢量文件路径，`.shp` 或 `.kml`（WGS84 坐标） |
| `--start` / `--end` | 是 | 起止日期，格式 `YYYYMMDD` |
| `--pol` | 否 | 极化（逗号分隔可多个），默认 `VV+VH,VV` |
| `--out` | 否 | 下载目录，默认 `./sentinel1_data`（当前目录下） |
| `--max` | 否 | 每个极化的结果数量上限 |

### 稳健下载（网络不稳定时推荐）

```bash
python robust_download.py \
  --aoi 研究区.kml --start 20240101 --end 20240630 \
  --pol VV+VH --out ./sentinel1_data
```

特点：断点续传（`.part` 标记）、60s socket 超时、120s 读超时、最多 10 次自动重试、跳过已完成文件。
下载时自动弹出**桌面进度条窗口**（当前文件 + 总进度 + 百分比），
加 `--no-gui` 可关闭进度条。搜索后会生成 `inventory.txt` 数据清单。

---

## 🧠 工作原理（How It Works）

### SBAS-InSAR 数据要求

SBAS（小基线集）干涉处理要求时间序列内所有影像：

1. **同一相对轨道**（pathNumber 一致）——保证几何关系一致
2. **同一方向**（升轨/降轨一致）——保证观测几何一致
3. **完全覆盖研究区**——保证研究区每个点都有完整时序
4. **规则时间间隔**——Sentinel-1 12 天重访周期

### 自动选择流程

```
① 矢量 → WKT（shp 用 pyshp，kml 用 ElementTree，兼容多种命名空间/三维坐标）
② Earthdata 认证（ASFSession.auth_with_creds → EDL token + asf-urs cookie）
③ 逐极化搜索（不限定方向）并合并结果
④ 按 (飞行方向, 相对轨道号) 分组
⑤ 覆盖判断：
   ├─ 单景完全覆盖（同轨道同帧 footprint 一致）→ 直接可用
   └─ 并集覆盖（研究区跨上下景边界时，同一时相多帧并集覆盖）→ 提示并保留
⑥ 展示各轨道组景数 → 用户选择
⑦ 严格校验：
   ├─ 轨道一致性（组内所有影像 pathNumber 必须完全一致）
   ├─ 卫星一致性（S1A/S1B/S1C 不混用提示）
   └─ 逐时相覆盖（每个时相并集必须完全覆盖研究区，无效时相自动排除）
⑧ 清单确认（可输入轨道号筛选）→ 批量下载
⑨ 下载校验（大小 > 0）
```

### 数据分析模式（推荐先分析后下载）

```bash
python analyze.py --aoi 研究区.kml --start 20200101 --end 20251231 \
  --pol VV+VH --out ./analysis --sample --plot
```

输出：轨道/卫星一致性、frame 覆盖分析（面积比/是否完全覆盖）、
逐时相覆盖统计、覆盖图、CSV 清单。加 `--sample` 会交互式询问
采样频率（每月/每季/每半年/每年/全部）与时相规则（最早/中/最晚）。

### 跨帧边界处理（Cross-Frame）

Sentinel-1 SLC 产品按 frame 切分（每帧约 250km）。当研究区恰好压在上下两帧边界时：

- **单帧**都不完全覆盖研究区 ❌
- **同一时相的上下两帧并集**完全覆盖 ✅

本技能用 shapely `unary_union` 计算组内所有影像 footprint 的并集判断覆盖，自动识别并下载同一时相的所有帧。

### 关键代码（核心覆盖判断）

```python
def group_union_covers(wkt_aoi, products):
    """判断一组影像的 footprint 并集是否完全覆盖研究区"""
    from shapely.geometry import shape
    from shapely.wkt import loads
    from shapely.ops import unary_union
    aoi = loads(wkt_aoi)
    polys = [shape(r.geometry) for r in products if r.geometry]
    union = unary_union(polys)
    return union.covers(aoi)
```

---

## 🔬 真实实验示例（Real Example）

以安徽地区某研究区、2025-07-01 至 2025-10-01、轨道 142 升轨为例：

```
[OK] AOI → WKT: POLYGON((116.749206 32.830839, ...))
[OK] Earthdata 认证成功
[OK] 极化 VV+VH: 搜索到 8 个结果
[OK] 共 1 个 (方向,轨道) 组
[OK] 完全覆盖研究区的轨道组: ASCENDING/142

序号  日期        相对轨道  方向        极化    文件名
1   20250923  142       ASCENDING  VV+VH   S1A_IW_SLC__1SDV_..._061114.zip
2   20250911  142       ASCENDING  VV+VH   S1A_IW_SLC__1SDV_..._060939.zip
3   20250830  142       ASCENDING  VV+VH   S1A_IW_SLC__1SDV_..._060764.zip
4   20250818  142       ASCENDING  VV+VH   S1A_IW_SLC__1SDV_..._060589.zip
5   20250806  142       ASCENDING  VV+VH   S1A_IW_SLC__1SDV_..._060414.zip
6   20250725  142       ASCENDING  VV+VH   S1A_IW_SLC__1SDV_..._060239.zip
7   20250713  142       ASCENDING  VV+VH   S1A_IW_SLC__1SDV_..._060064.zip
8   20250701  142       ASCENDING  VV+VH   S1A_IW_SLC__1SDV_..._059889.zip
```

8 景、12 天均匀间隔（07-01 → 07-13 → 07-25 → 08-06 → 08-18 → 08-30 → 09-11 → 09-23）、同一轨道 142 升轨、全部 VV+VH 双极化——完美的 SBAS 时间序列。

---

## 📁 文件结构（File Structure）

```
asf-sentinel1-download/
├── SKILL.md              # 技能定义（frontmatter + 触发条件 + 工作流）
├── download.py           # 主脚本（搜索 + 轨道分组 + 覆盖判断 + 下载）
├── analyze.py            # 数据分析模式（轨道/卫星/frame/逐时相/每月采样/覆盖图）
├── analysis.py           # 分析核心函数库（可独立调用）
├── robust_download.py    # 稳健下载（断点续传 + 超时 + 重试 + 数据列表）
├── progress_gui.py       # 桌面进度条（Tkinter）
├── requirements.txt      # 依赖清单
├── config.json           # Earthdata 凭证（本地安全存储）
└── tests/                # 33 个单元测试
    ├── test_download.py
    └── test_analysis.py
```

### download.py 核心函数

| 函数 | 职责 |
|------|------|
| `aoi_to_wkt` / `shp_to_wkt` / `kml_to_wkt` | 矢量 → WKT 多边形 |
| `parse_polarization` / `parse_direction` | 极化/方向参数归一化 |
| `footprint_contains` | 单景覆盖判断 |
| `group_union_covers` | 组内并集覆盖判断（跨帧） |
| `group_by_frame` | 同帧识别（同一时相上下景） |
| `group_by_orbit` | 按 (方向, 轨道) 分组 |
| `run_download` | 主流程（含轨道/卫星/逐时相严格校验） |
| `_confirm` | 用户确认（y/轨道号/取消） |

### analysis.py 核心函数

| 函数 | 职责 |
|------|------|
| `check_per_date_coverage` | 逐时相覆盖检查（每时相并集必须完全覆盖） |
| `check_orbit_consistency` | 轨道一致性（同 frame 跨轨道检出） |
| `check_satellite_consistency` | 卫星一致性（S1A/S1B/S1C） |
| `analyze_frame_coverage` | 每帧覆盖面积比/景数/时相范围 |
| `sample_by_frequency` | 按频率采样（月/季/半年/年/全部 + 时相规则） |
| `ask_frequency` / `ask_rule` | 交互式询问采样频率与时相规则 |
| `export_list` | 清单导出（TXT + CSV） |
| `plot_coverage` | 研究区 vs 影像覆盖图 |

---

## 🧪 测试（Testing）

```bash
pip install pytest
cd asf-sentinel1-download
python -m pytest tests/ -v
```

**33 个测试全部通过**，覆盖：
- 日期/极化/方向参数解析
- shp/kml → WKT 转换（含 SARscape 三维坐标）
- 单景覆盖 + 跨帧并集覆盖
- 逐时相覆盖检查（每时相并集必须完全覆盖）
- 轨道一致性（同 frame 跨轨道检出）
- 卫星一致性（S1A/S1C）
- frame 覆盖面积比分析
- 按频率采样（月/季/半年/年）
- 文件名消毒、URL 白名单（安全）
- 清单格式、确认流程

---

## ⚠️ 已知限制（Known Limitations）

- **仅限 Sentinel-1 SLC IW**：当前硬编码 `processingLevel=SLC`、`beamMode=IW`（最常用组合）；如需 GRD 或 EW 模式需修改代码
- **WGS84 坐标**：shp 必须为经纬度坐标系（UTM 等投影需先转换）
- **大文件**：SLC 单景约 4.5GB，8 景约 36GB，请确保磁盘空间充足
- **网络**：ASF 大文件下载建议稳定网络；`robust_download.py` 提供断点续传

---

## 🤝 贡献（Contributing）

欢迎提交 PR 或 issue：
- 支持更多产品类型（GRD/EW）
- 增加 ASF 其他卫星（ALOS-2 等）
- 自动化 SBAS 预处理流程

---

## 📄 License

MIT License

---

## 🙏 致谢（Acknowledgments）

- [ASF (Alaska Satellite Facility)](https://asf.alaska.edu/) — 数据源与官方 Python 库
- [asf_search](https://github.com/asfadmin/Discovery-asf_search) — 官方搜索库
- [shapely](https://shapely.readthedocs.io/) — 几何覆盖计算
- 本技能由 SAR 科研工作流驱动设计，用于 SBAS-InSAR 时序形变监测
