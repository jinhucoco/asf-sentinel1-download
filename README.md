# ASF Sentinel-1 Download Skill（ASF 哨兵一号数据下载技能）

> 从 ASF (Alaska Satellite Facility) 自动下载用于 **SBAS-InSAR** 实验的 Sentinel-1 数据
> Automatically download Sentinel-1 data from ASF for **SBAS-InSAR** experiments

[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](#license)
[![Test](https://img.shields.io/badge/Tests-42%20passing-brightgreen)](#测试)
[![npm](https://img.shields.io/npm/v/pi-asf-sentinel1-slc?color=cb3837&logo=npm)](https://www.npmjs.com/package/pi-asf-sentinel1-slc)
[![GitHub](https://img.shields.io/badge/GitHub-jinhucoco%2Fasf--sentinel1--download-blue?logo=github)](https://github.com/jinhucoco/asf-sentinel1-download)

---

## 🌟 核心特性（Key Features）

- **🎯 面向 SBAS-InSAR 设计**：自动保证同一相对轨道 + 同一方向（升/降轨）+ 完全覆盖研究区，形成 12 天规则时序
- **🛡️ 三重一致性校验**：轨道一致性（同 frame 可能被不同轨道复用，下载前验证 pathNumber 完全一致）、卫星一致性（S1A/S1B/S1C 混用提示）、**逐时相覆盖检查**（每个时相影像并集必须完全覆盖研究区，单帧部分覆盖的时相自动排除）
- **📐 跨帧自动处理**：研究区压在上下两景边界时，自动识别并下载同一时相的全部帧（并集覆盖）
- **🛰️ 多极化支持**：默认同时搜索 `VV+VH` 与 `VV`，合并清单
- **🔄 稳健下载**：断点续传 + 超时保护 + 自动重试 + 桌面进度条，网络中断不丢进度
- **⚡ 多线程分片下载（multi_download.py）**：8 线程 Range 分片并发（大文件约 8× 提速），分片级断点续传 + 重试 + 失败片补下，大小 + MD5 双校验（坏数据自动重下），**网络极差时自动降级单文件模式**（连续 2 文件作废自动切换，不中断任务）
- **✅ 数据完整性保障**：所有下载路径均做大小 + ASF 官方 md5sum 双校验，校验不通过自动删除重下，杜绝坏数据进入实验
- **📄 多格式矢量**：支持 `.shp` / `.kml`（含 SARscape 导出的命名空间与三维带海拔坐标）
- **🔒 凭证本地安全**：Earthdata 账号密码存技能目录 `config.json`，交互式配置，不接触公开网络

遵循 **Agent Skills 标准**（https://agentskills.io/specification），可在 pi / Codex / Claude Code / Cursor 等支持该标准的工具中使用。

---

## 📦 安装（Installation）

### 前置条件（Prerequisites）

| 项 | 要求 |
|----|------|
| 操作系统 | Windows / Linux / macOS |
| Python | 3.10+ |
| NASA Earthdata 账号 | 免费注册：https://urs.earthdata.nasa.gov/ |
| 网络 | 可访问 api.asf.alaska.edu（中国大陆用户建议代理） |

### 路径 A：Pi 用户（推荐）

```bash
# 一键安装（自动注册为 pi 技能）
pi install npm:pi-asf-sentinel1-slc

# 安装 Python 依赖（asf_search / pyshp / shapely 等）
pip install asf_search pyshp shapely defusedxml matplotlib
```

### 路径 B：其他 AI 工具（Codex / Claude Code / Cursor）

**方式 1（推荐）：宿主终端一键安装**

```bash
curl -fsSL https://raw.githubusercontent.com/jinhucoco/asf-sentinel1-download/main/install.sh | bash
```

脚本自动完成：检测已安装的工具（Codex / Claude / pi）→ 安装到对应技能目录 → 安装 Python 依赖 → 生成凭证模板。未检测到任何工具时安装到通用位置 `~/.agents/skills/`。

**方式 2：手动安装（可选）**

下载 [asf-sentinel1-download-skill.zip](https://github.com/jinhucoco/asf-sentinel1-download/releases/latest/download/asf-sentinel1-download-skill.zip)，解压得到 `asf-sentinel1-download/` 文件夹，放入对应技能目录：

```
~/.codex/skills/       # Codex
~/.claude/skills/      # Claude Code
~/.pi/agent/skills/    # pi
~/.agents/skills/      # 通用
```

然后安装依赖：`pip install -r requirements.txt`。

> ⚠️ **别忘了**：安装完成后还需**配置 Earthdata 账号密码**（见下方「配置 Earthdata 凭证」），否则 ASF 认证会失败、无法下载数据。

> 💡 **Codex 沙箱用户必读**：Codex 沙箱默认**关闭网络**、**HOME 目录只读**，`curl | bash` 一键安装会失败。请在**宿主终端**（非沙箱）执行方式 1，或浏览器下载 zip 手动解压（方式 2，零命令行）。也可在对话中让 Codex 安装（需 `network_access=true` 且 `~/.codex` 可写）。安装脚本支持 `bash install.sh --dry-run` 预览操作，并在检测到沙箱时输出降级指引。
>
> 🔑 **装好后记得配置账号密码**：在 Codex 对话中说 **"配置 ASF 账号密码"**（或手动编辑 `~/.codex/skills/asf-sentinel1-download/config.json`，见下方「配置 Earthdata 凭证」）。未配置凭证时下载会认证失败。

### 配置 Earthdata 凭证（所有路径都需要）

**方式 A（推荐，交互式）：** 在 AI 对话中直接说 **"配置 ASF 账号密码"**，AI 引导输入并自动保存到 `config.json`，无需手动编辑文件。

**方式 B（手动）：** 编辑技能目录 `config.json`：

```json
{
  "username": "your_earthdata_username",
  "password": "your_earthdata_password"
}
```

> ⚠️ **安全提示**：`config.json` 含明文密码，仅本机使用，请确保文件权限仅本人可读写，切勿提交到公开仓库。

---

## ⚡ 快速开始（Quick Start）

**3 分钟上手：** ① 安装（见上）→ ② 配置凭证（对话中说"配置 ASF 账号密码"）→ ③ 直接使用：

在任意 AI 工具（pi / Codex / Claude Code）对话中说：

> **"从 ASF 下载哨兵数据，区域 研究区.shp，时间 20200101 至 20251231，VV+VH"**

AI 会自动完成全部流程，并**交互式询问**关键决策：

```
[OK] 认证成功
[OK] 极化 VV+VH: 搜索到 945 个结果
[OK] 共 5 个 (方向,轨道) 组

=== 可选轨道组（按景数排序） ===
  [1] DESCENDING / 轨道 135: 322 景
  [2] ASCENDING / 轨道 128: 248 景
  [3] DESCENDING / 轨道 33: 176 景
  ...
请选择要使用的轨道组编号（回车选默认第 1 个）: 1   ← 交互式选择

[OK] 轨道一致性校验通过: 全部 322 景均为轨道 135
[OK] 逐时相覆盖检查: 169 个有效时相 / 0 个无效
  frame 468: 154景 覆盖100% ✅完全覆盖
  frame 467: 15景  覆盖100% ✅完全覆盖

请选择取景频率:            ← 交互式选择
  [1] 全部（不采样）
  [2] 每月
  [3] 每季度
  [4] 每半年
  [5] 每年
输入编号（回车默认每月）: 2

每个区间取哪个时相？      ← 交互式选择
  [1] 最早时相
  [2] 中间时相
  [3] 最晚时相
输入编号（回车默认最早）: 1

[OK] 每月采样(first时相): 135 景
[OK] 清单已导出: sampled_DESCENDING_135_monthly.csv
输入 y 全部下载，n 取消: y      ← 交互式确认
[下载] ...（断点续传 + 桌面进度条）
```

---

## 🚀 使用（Usage）

### 对话式（推荐）

当技能被 AI 代理加载时，直接说：

> **"从 ASF 下载哨兵数据，区域 `研究区.shp`，时间 20240101 至 20240630，VV+VH 和 VV"**

AI 自动执行：认证 → 搜索 → 轨道分组 → 展示选择 → 覆盖校验 → 采样 → 确认 → 下载。

### 命令行（手动，不用 AI 对话时）

```bash
# 先分析数据质量（轨道/卫星/frame 覆盖/逐时相/覆盖图/清单）
python analyze.py --aoi 研究区.kml --start 20200101 --end 20251231 \
  --pol VV+VH --out ./analysis --sample --plot

# 再下载（稳健版：断点续传 + 超时 + 重试 + 桌面进度条）
python robust_download.py --aoi 研究区.kml --start 20240101 --end 20240630 \
  --pol VV+VH --out ./sentinel1_data

# 大流量/慢网络首选（多线程分片，约 8× 提速，自动降级保底）
# 方式1：清单驱动（推荐——先用 analyze.py 生成清单再批量挂机下载）
python analyze.py --aoi 研究区.kml --start 20200101 --end 20251231 \
  --pol VV+VH --out ./analysis
python multi_download.py --list ./analysis/list_DESCENDING_135.csv \
  --out ./sentinel1_data [--threads 8]

# 方式2：搜索驱动（指定轨道直接下载，跳过交互选择）
python multi_download.py --aoi 研究区.kml --start 20200101 --end 20251231 \
  --pol VV+VH --track 135 --out ./sentinel1_data [--threads 8]
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--aoi` | 是 | 矢量文件路径，`.shp` 或 `.kml`（WGS84 坐标） |
| `--start` / `--end` | 是 | 起止日期，格式 `YYYYMMDD` |
| `--pol` | 否 | 极化（逗号分隔可多个），默认 `VV+VH,VV` |
| `--out` | 否 | 下载目录，默认 `./sentinel1_data` |
| `--max` | 否 | 每个极化的结果数量上限 |
| `--sample` | 否 | （analyze.py）交互式采样：每月/每季/每半年/每年/全部 |
| `--plot` | 否 | （analyze.py）生成研究区 vs 影像覆盖图 |
| `--no-gui` | 否 | 关闭桌面进度条窗口 |

稳健下载特点：断点续传（`.part` 标记）、60s socket 超时、120s 读超时、最多 10 次自动重试、跳过已完成文件；搜索后生成 `inventory.txt` 数据清单。

**多线程版（multi_download.py）特点：**

| 能力 | 说明 |
|------|------|
| 分片并发 | 默认 8 线程 Range 分片（<300MB 自动 4 片），大文件提速明显 |
| 断点续传 | 分片级续传（中断的片从断点继续，不重下） |
| 失败自愈 | 每片重试 6 次 + 失败片循环补下 3 轮，网络断连不丢进度 |
| 大小探测 | `bytes=0-0` 探测真实大小（ASF 的 HEAD/Content-Length 不可靠） |
| 数据校验 | 大小 + **MD5 双校验**，不匹配自动删除重下 |
| 自动降级 | 多线程连续 2 文件作废 → 自动切单文件模式（`mode.flag`），任务不中断 |
| 完成标记 | 清单跑完写 `complete.flag`，配合守护脚本可自动停止 |
| 挂机友好 | 日志写 `--out/multi_download.log`，可反复重启续跑（跳过已完成） |

> 💡 实战验证：154 景（695GB，轨道 135 古浪，VV+VH）在持续断网环境下 35 小时完成，全程零数据损坏。

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
├── multi_download.py     # 多线程分片下载（8 线程并发 + MD5 双校验 + 自动降级，大流量首选）
├── progress_gui.py       # 桌面进度条（Tkinter）
├── requirements.txt      # 依赖清单
├── config.example.json   # 凭证模板（安装时复制为 config.json，本地填写真实账号）
├── install.sh            # 一键安装脚本（检测 Codex/Claude/pi）
└── tests/                # 42 个单元测试
    ├── test_download.py
    ├── test_analysis.py
    └── test_package_consistency.py   # 发布镜像与根目录一致性守护
```

> 📌 仓库 `skills/asf-sentinel1-download/` 是**发布镜像**（npm 与 install.sh 整体复制此目录），与根目录由 `tests/test_package_consistency.py` 自动校验同步。

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

**42 个测试全部通过**，覆盖：
- 日期/极化/方向参数解析
- shp/kml → WKT 转换（含 SARscape 三维坐标）
- 单景覆盖 + 跨帧并集覆盖
- 逐时相覆盖检查（每时相并集必须完全覆盖）
- 轨道一致性（同 frame 跨轨道检出）
- 卫星一致性（S1A/S1C）
- frame 覆盖面积比分析
- 按频率采样（月/季/半年/年）
- 发布镜像一致性（根目录 vs skills/ 副本，防漂移）
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
