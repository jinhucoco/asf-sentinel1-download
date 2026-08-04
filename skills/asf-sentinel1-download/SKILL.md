---
name: asf-sentinel1-download
description: >
  从 ASF (Alaska Satellite Facility) 网站自动下载 Sentinel-1 数据。
  当用户提供时间范围 + shp/kml 矢量文件 + 网页参数（SLC/IW/极化），
  需要批量下载哨兵一号影像时使用。触发词："从ASF下载哨兵数据"、
  "下载Sentinel-1"、"ASF下载S1"。
---

# ASF Sentinel-1 数据下载

## 概述

用户提供时间范围、矢量文件（shp/kml）、参数后，使用 ASF 官方搜索库
(asf_search) 自动完成：Earthdata 认证（凭证存本目录 config.json）、
AOI 矢量转 WKT、逐极化搜索（默认 VV+VH 与 VV 一起）并合并，
按 (飞行方向, 相对轨道) 分组并统计各轨道景数展示给用户选择，
自动过滤完全覆盖研究区的轨道组，列出清单等待确认、批量下载。
基于官方 API，稳定可靠。

## 环境要求

- Python 3.10+
- 依赖：`pip install asf_search pyshp shapely defusedxml matplotlib`（或 `pip install -r requirements.txt`）
- NASA Earthdata 账号（免费注册 https://urs.earthdata.nasa.gov/），凭证存技能目录 `config.json`
- 可选：matplotlib 用于覆盖图生成；tkinter 用于桌面进度条（无 GUI 环境可用 `--no-gui`）

## 何时使用

- 用户需要从 ASF 下载特定时间范围、特定区域的 Sentinel-1 数据
- 触发词："从 ASF 下载哨兵数据"、"下载 Sentinel-1"、"ASF 下载 S1"

## 工作流

0. **凭证配置（首次使用）**：若技能目录无 `config.json` 或未配置，
   **主动询问用户**的 Earthdata 账号密码（免费注册 https://urs.earthdata.nasa.gov/），
   自动写入 `config.json`（用户无需手动编辑文件）。
   用户也可直接说："配置 ASF 账号密码：xxx / xxx"。
1. **确认输入**：时间范围（YYYYMMDD 起止）、矢量路径（shp/kml）、
   极化（默认 VV+VH,VV）、下载目录（默认 ./sentinel1_data）
2. **运行脚本**：

```bash
python ~/.pi/agent/skills/asf-sentinel1-download/download.py \
  --aoi <矢量文件> --start <YYYYMMDD> --end <YYYYMMDD> \
  --pol VV+VH,VV --out <下载目录>
```

3. **选择轨道组**：脚本按 (方向,轨道) 分组展示各轨道景数，输入编号选择
4. **等待确认**：打印结果清单，输入 `y`（全部下载）、轨道号（筛选），或 `n`（取消）
5. **下载完成**：校验文件存在且大小 > 0，汇报数量与路径

> 💡 **交互式凭证**：告诉 AI "配置 ASF 账号密码"，AI 会引导你输入并保存到 config.json，全程无需手动编辑文件。

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--aoi` | 是 | 矢量文件路径，支持 `.shp` 或 `.kml`（shp 需为 WGS84 坐标） |
| `--start` / `--end` | 是 | 起止日期，格式 `YYYYMMDD` |
| `--pol` | 否 | 极化（逗号分隔可多个），默认 `VV+VH,VV`（双极化和单极化一起） |
| `--out` | 否 | 下载目录，默认 `./sentinel1_data`（当前目录下） |
| `--max` | 否 | 每个极化的结果数量上限（默认不限） |

## SBAS 轨道保证

- **方向不预设**：搜索时不限定升/降轨，按 (飞行方向, 相对轨道) 分组后
  统计各轨道景数，**展示给你选择**用哪组
- **同一轨道**：选定后组内所有影像同方向、同轨道号（pathNumber），
  满足 SBAS 时间序列要求
- **轨道一致性严格校验**：下载前验证组内所有影像 pathNumber 完全一致。
  实测发现同 frame 编号可能被不同轨道复用（如 frame 468 混 62/135），
  不同轨道绝不能混入同一 SBAS 序列
- **卫星一致性检查**：S1A/S1B/S1C 不同卫星混用会提示警告（2025 年后
  S1C 接管部分轨道）
- **逐时相覆盖检查**：**同一时相（同一天）所有影像的并集必须完全覆盖研究区**
  才是有效时相。单帧部分覆盖的时相自动排除（用户核心要求：不是整组并集，
  而是每个时相单独检查）
- **跨帧自动处理**：研究区压在上下两景边界时，同一时相的上下景并集覆盖 →
  全部下载
- **多极化**：`VV+VH` 与 `VV` 分别搜索后合并，清单中标明各文件极化

## 数据分析（不下载）

下载前可用 `analyze.py` 先分析数据质量：

```bash
python ~/.pi/agent/skills/asf-sentinel1-download/analyze.py \
  --aoi <矢量文件> --start <YYYYMMDD> --end <YYYYMMDD> \
  --pol VV+VH --out <输出目录> --sample --plot
```

分析输出：
- **轨道/卫星一致性**：检出同 frame 跨轨道、多卫星混杂
- **frame 覆盖分析**：每帧景数、时相范围、覆盖面积比、是否完全覆盖
- **逐时相覆盖检查**：有效/无效时相统计
- **采样**（`--sample`）：交互式询问频率（月/季/半年/年/全部）与时相规则（最早/中/最晚），只对有效轨道组询问
- **覆盖图**（`--plot`）：研究区 vs 各 frame 影像覆盖范围可视化
- **清单导出**：TXT + CSV（日期/帧号/轨道号/卫星/文件名）

## 稳健下载

网络不稳定时使用 `robust_download.py`（断点续传 + 超时 + 重试）：

```bash
python ~/.pi/agent/skills/asf-sentinel1-download/robust_download.py \
  --aoi <矢量文件> --start <YYYYMMDD> --end <YYYYMMDD> \
  --pol VV+VH --out <下载目录>
```

- 断点续传：`.part` 标记，中断后自动从已下载部分继续
- 超时保护：60s socket 超时 + 120s 读超时，挂起不卡死
- 自动重试：`--retry` 指定次数（默认 10），跳过已完成文件
- 桌面进度条：默认显示 Tkinter 进度窗口，`--no-gui` 关闭

## 多线程下载（网络慢/量大时首选）

单连接慢时用 `multi_download.py`（8 线程 Range 分片并发，深夜/带宽好时自动提速，
约 8× 单连接速度）：

```bash
# 方式1：清单驱动（推荐——先用 analyze.py 生成清单再批量下载，可挂机续跑）
python ~/.pi/agent/skills/asf-sentinel1-download/analyze.py \
  --aoi <矢量文件> --start <YYYYMMDD> --end <YYYYMMDD> --pol VV+VH --out <分析目录>
python ~/.pi/agent/skills/asf-sentinel1-download/multi_download.py \
  --list <分析目录>/list_DESCENDING_135.csv --out <下载目录> [--threads 8]

# 方式2：搜索驱动（指定轨道直接下载，跳过交互选择）
python ~/.pi/agent/skills/asf-sentinel1-download/multi_download.py \
  --aoi <矢量文件> --start <YYYYMMDD> --end <YYYYMMDD> \
  --pol VV+VH --track 135 --out <下载目录> [--threads 8]
```

- 8 线程 Range 分片并发（<300MB 自动用 4 片），分片级重试（每片 4 次 + backoff）
- 断点续传：已完成文件跳过；失败分片清理后下次重下
- `bytes=0-0` 探测真实大小（ASF 的 HEAD 不可靠）
- 挂机建议：配合守护循环（检测进程死/卡死自动重启），日志在 `--out/multi_download.log`
- 适合 SBAS 全量时间序列（几百 GB 量级），耗时由网络决定，勿催

## 常见错误

| 问题 | 处理 |
|------|------|
| 登录失败 | 检查 config.json 凭证；Earthdata 可能要求两步验证，需手动完成 |
| 搜索结果为空 | 扩大时间范围或检查 AOI 坐标是否为 WGS84 |
| API 报错 | 检查网络/代理；ASF API 偶发限流，稍后重试 |
| shp 报错 | 确认 shp 是 WGS84（经纬度）坐标系 |

## 安全提示

config.json 含明文密码，仅本机使用，切勿分享或提交到仓库。
