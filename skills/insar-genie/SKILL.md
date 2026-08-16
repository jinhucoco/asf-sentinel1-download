---
name: insar-genie
description: >
  SBAS-InSAR 全链路 AI 技能：从 Sentinel-1 数据下载、配套数据（DEM/GACOS/POEORB）
  获取，到 SARscape 实验参数确认与批处理执行，再到守护监控，全程 AI 与用户对话交互、
  AI 自动执行。用户只需说出需求（提供时间范围 + shp/kml 矢量 + 极化），AI 自动完成。
  触发词：“从ASF下载哨兵数据”、“下载Sentinel-1”、“ASF下载S1”、“开始SBAS实验”、
  “跑SBAS”、“参数怎么设”、“实验进展如何”。
---

# SBAS-InSAR 全链路 AI 技能

## 定位（AI 交互执行原则）

**本技能的一切工具（scripts/ 下载工具、experiment/ 批处理与守护）都是为 AI 与用户
对话交互服务的**：用户用自然语言提出需求，AI 调用工具自动执行并汇报，用户无需手动
敲命令。AI 是执行主体，工具是 AI 的“手”。

```
用户对话 ──▶ AI（读取本 SKILL.md）──▶ 调用 scripts/experiment 工具 ──▶ 执行 ──▶ 汇报
```

## 环境要求

- Python 3.10+
- 依赖：`pip install asf_search pyshp shapely defusedxml matplotlib`（或 `pip install -r requirements.txt`）
- NASA Earthdata 账号（免费注册 https://urs.earthdata.nasa.gov/），凭证存技能目录 `config.json`
- 可选：matplotlib 用于覆盖图生成；tkinter 用于桌面进度条（无 GUI 环境可用 `--no-gui`）

## 何时使用

- 用户需要从 ASF 下载特定时间范围、特定区域的 Sentinel-1 数据
- 用户要开展 SBAS-InSAR 实验（下载 → 配套数据 → 参数确认 → 批处理 → 监控）
- 触发词：“从 ASF 下载哨兵数据”、“下载 Sentinel-1”、“ASF 下载 S1”、“开始 SBAS 实验”、“跑 SBAS”、“参数怎么设”、“实验进展如何”

**真实触发示例**（甘肃古浪实验）：

```
用户: 从 ASF 下载哨兵数据，区域 古浪.shp，时间 20200101 至 20251231，VV
AI: 搜索 → (方向,轨道)分组 → 覆盖校验 → 清单确认 → 下载 77 景（轨道 135 降轨）
用户: 下载配套数据
AI: POEORB 77 / GACOS 77 / DEM（n37e102/103、n38e102/103）
用户: 开始 SBAS 实验
AI: 识别地形 → 列参数表（8:2 多视/180 天/Goldstein 64/MCF 0.2/GACOS）→ 用户确认 → 执行
用户: 实验进展如何
AI: 查守护日志 → 汇报（如“干涉图生成 79%，预计明早完成”）
```

## 工作流

0. **凭证配置（首次使用）**：若技能目录无 `config.json` 或未配置，
   **主动询问用户**的 Earthdata 账号密码（免费注册 https://urs.earthdata.nasa.gov/），
   自动写入 `config.json`（用户无需手动编辑文件）。
   用户也可直接说："配置 ASF 账号密码：xxx / xxx"。
1. **确认输入**：时间范围（YYYYMMDD 起止）、矢量路径（shp/kml）、
   极化（默认 VV+VH,VV）、下载目录（默认 ./sentinel1_data）
2. **运行脚本**：

```bash
python scripts/download.py \
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

## 配套数据下载（SBAS 完整数据链）

主数据下载后，可一键获取 InSAR 处理所需的三种配套数据（均为官方源，无需百度网盘）：

### 1. 精密轨道文件（POEORB）

```bash
python scripts/poeorb_download.py \
  --list 下载清单.csv --out ./poeorb
# 或扫描 SLC 数据目录：
python scripts/poeorb_download.py \
  --data-dir ./sentinel1_data --out ./poeorb
```

- **对应规则**：SLC 获取时刻（UTC）落在 POEORB 文件 validity 区间内（文件名 `_V起_止`）
- 自动按（卫星, 日期）去重匹配，下载后解压为 `.EOF`；网络失败可重跑补漏（跳过已完成）

### 2. GACOS 大气延迟（ztd）

```bash
# 提交（每次 ≤20 日期，自动分批；结果邮件发送）
python scripts/gacos_download.py \
  --bbox "38.34 101.96 103.48 37.28" --list 时相日期.txt \
  --time 23:10 --email 你的邮箱 --out ./gacos

# 收件（IMAP 读邮箱 → 提取链接 → 下载解压 ztd；指数退避轮询）
python scripts/gacos_fetch.py \
  --mail-config mail.json --out ./gacos --expect 77 --loop
```

- 需要：邮箱 IMAP 授权码（163/QQ），UTC 时刻（从 SLC 文件名提取，如 `T231040` → 23:10）
- 输出 `YYYYMMDD.ztd` 二进制（SARscape/StaMPS 可直接引用）
- 已知坑：GACOS 偶发漏生成某日期 → 单独重提该日期即可

### 3. DEM（NASADEM 30m 官方源）

```bash
python scripts/dem_download.py \
  --aoi 研究区.shp --out ./dem
# 或直接给范围：
python scripts/dem_download.py \
  --lat 37.3 38.3 --lon 102.0 103.4 --out ./dem
```

- 自动从研究区推导分幅（如古浪 → n37e102/103 + n38e102/103）
- 官方源：USGS e4ftl01（NASADEM_HGT 30m，经 Earthdata 认证）
- 需要 Earthdata 账号（与 ASF 下载同账号），凭证读 config.json 或环境变量

> 依赖：GACOS 需 `pip install playwright && playwright install chromium`；DEM 需 `pip install earthaccess`

## 安装后必做：配置全部账户 🔑

**安装完成后第一件事：按需配置好以下账户**（未配置会认证失败或功能不可用）：
| 账户 | 用途 | 必需？ | 配置方式 |
|------|------|--------|---------|
| **NASA Earthdata** | SLC 主数据下载 + DEM 下载 | ✅ 必需 | 对话中说「配置 ASF 账号密码」交互式配置，或编辑 `config.json`（免费注册 https://urs.earthdata.nasa.gov/） |
| **邮箱（IMAP 授权码）** | GACOS 大气延迟结果收取 | ⚠️ 用 GACOS 时必需 | 任意能收邮件的邮箱（163/QQ），开启 IMAP 生成授权码，写入 `mail.json` |
| —— | POEORB 精密轨道 | ❌ 免账号 | ESA 公开服务器直接下载 |

> 🔔 对话中对 AI 说 **「配置 ASF 账号密码」** 可引导完成 Earthdata 配置；GACOS 邮箱配置可让 AI 协助生成 `mail.json`。

**凭证配置完成后，AI 必须主动提示用户就绪**：

```
AI: ✅ 凭证已配置，环境就绪！你现在可以这样使用：
     1. 下载数据 → 对我说“从 ASF 下载哨兵数据，区域 研究区.shp，时间 20240101 至 20240630，VV+VH”
     2. 配套数据 → “下载配套数据”
     3. 开始实验 → “开始 SBAS 实验”
     4. 查进度   → “实验进展如何”
```

## 通知配置交互（可选）

守护的微信/邮件通知是**可选**功能（不配置也能跑实验，只是收不到推送）。
用户提到「配置通知」「微信推送」或想开启告警时，AI 引导：

```
你: 配置通知
AI: ① 微信（Server酱）：引导注册 https://sct.ftqq.com → 获取 SendKey（SCT 开头）
     写入 experiment/asf_experiment/notify_config.json（serverchan.sendkey）
   ② 邮件：引导提供邮箱 + SMTP 授权码，写入 mail_config.json
   ③ 确认推送频率（默认白天 4 次进度 + 关键事件，5 条/天额度内）
   ④ 测试推送：发一条“通知已配置”验证
```

> 未配置时守护只写日志；用户随时可补配。

## 验证数据询问（可选）

精度验证是**可选**环节。实验开始前和结果产出时，AI 各问一次：

```
AI: 你是否有水准/GNSS 实测数据可用于精度验证？（没有就说“没有”，不影响流程）
    - 有 → 收集：观测点坐标、沉降量、观测时间（写入 experiment/validation_data/ 或用户指定位置）
    - 没有 → 跳过，标注“无外部验证数据”，用内部一致性判识（相干性/空洞分布/形变时空特征）
```

> 有验证数据时，最终形变结果按 CH/T 6006-2018 做精度分级验证；没有则仅报告内部质量判识。

## 数据分析（不下载）

下载前可用 `analyze.py` 先分析数据质量：

```bash
python scripts/analyze.py \
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
python scripts/robust_download.py \
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
python scripts/analyze.py \
  --aoi <矢量文件> --start <YYYYMMDD> --end <YYYYMMDD> --pol VV+VH --out <分析目录>
python scripts/multi_download.py \
  --list <分析目录>/list_DESCENDING_135.csv --out <下载目录> [--threads 8]

# 方式2：搜索驱动（指定轨道直接下载，跳过交互选择）
python scripts/multi_download.py \
  --aoi <矢量文件> --start <YYYYMMDD> --end <YYYYMMDD> \
  --pol VV+VH --track 135 --out <下载目录> [--threads 8]
```

- 8 线程 Range 分片并发（<300MB 自动用 4 片），分片级重试（每片 4 次 + backoff）
- **自动降级**：多线程连续 2 个文件作废时自动切换单文件模式（写 `<out>/mode.flag`，
  重启后走单连接整文件下载），网络极差时保底不中断。
  ⚠ 8-16 修复：网络断连（ConnectionReset）与下载失败（[FAIL]）**两条路径都累计**
  连续失败数（`maybe_downgrade` 纯函数）——旧版 except 分支不累计，网络越差
  越不降级，导致 8-16 民勤连续 3 文件被 ASF 硬限流踢掉仍不降级
- 断点续传：已完成文件跳过；失败分片清理后下次重下
- `bytes=0-0` 探测真实大小（ASF 的 HEAD 不可靠）
- 挂机建议：配合 **`download_guard.py` 下载守护**（每 30 分钟体检 + 邮件/Server酱报告 + 异常自动介入重启 + 完成通知）：

```bash
# 先跑下载（或直接让守护代启——守护会自动接管已运行的下载进程）
python scripts/multi_download.py --list 清单.csv --out <下载目录>
# 再开守护：每 30 分钟一封体检报告邮件（含进度/速度/状态/重启次数/日志尾部）；
# 异常（死亡/卡死）自动重启并即时通知；完成发通知后退出
python scripts/download_guard.py --list 清单.csv --out <下载目录> \
  --health-interval 30 \
  --mail-config mail_config.json --notify-config notify_config.json
```

- **守护与下载平级**：守护每次检测前用 `detect_running` 重新找在跑下载器（含
  run_dl/计划任务/手动拉起的），只认自己 spawn 的 pid 会误判死亡反复重启
  → 双下载器抢同一文件（8-16 事故）；`run_dl.py` 已加命名互斥锁防并发拉起
- **Windows 进程检测用 PowerShell**（`Get-CimInstance Win32_Process`），wmic 输出
  列序不稳/偶发查不到进程，不可靠（8-16 实测）

- 下载日志在 `--out/multi_download.log`，守护日志在 `--out/download_guard.log`
- 适合 SBAS 全量时间序列（几百 GB 量级），耗时由网络决定，勿催

### ⚠️ 长下载必须系统级托管（2026-08-16 实测教训）

**web 宿主重启会杀掉其后台 job**（下载进程、守护、桥接一起死，且守护的自动重启
也没机会跑）。守护必须**脱离 web 宿主独立运行**，且**纯 python 无感后台**
（前台无任何 cmd/python 窗口——2026-08-16 用户要求，同 pi 独立后台体验）：
- **守护与下载是两个平级独立进程**：由 `run_dl.py` 启动器分别拉起（各带
  CREATE_NO_WINDOW + DETACHED_PROCESS），互不为父子；守护只【监控】下载器，
  下载器不依赖守护存活（守护死亡下载照跑）；
- 守护用 **pythonw.exe**（无控制台）；下载器用 **python.exe + 隐形启动**；
- 守护重启下载器时也用 DETACHED_PROCESS（重启的下载器同样脱离守护）；
- 不用 cmd/bat/vbs 任何壳（tasklist/wmic/taskkill 等控制台调用全部带
  CREATE_NO_WINDOW，无闪窗）。

```powershell
# 1) 写 run_dl.py 启动器：确保下载器没跑就拉起、守护没跑就拉起（各自 DETACHED）
# 2) 计划任务【每 5 分钟循环】直接跑 pythonw run_dl.py
$action = New-ScheduledTaskAction -Execute "C:\Python314\pythonw.exe" -Argument '"D:\path\run_dl.py"'
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName "insar-genie-dl-guard" -Action $action -Trigger $trigger -Force
# 3) 开机自启（pythonw 直启，无需 vbs）
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v InSarGenieDLGuard /t REG_SZ /d "\"C:\Python314\pythonw.exe\" \"D:\path\run_dl_guard.py\"" /f
```

- **守护本身有异常韧性**：体检循环整体 try/except，任何意外异常记录后继续（不会静默死亡）；
  配合每 5 分钟循环计划任务 = 守护死了自动拉起、下载器死了守护自动重启，**全链路自愈**。
- **无控制台适配**：download_guard.py 的打印用 `safe_print()`（pythonw 下 sys.stdout 为 None 不崩溃）；
  `build_download_cmd()` 会把 pythonw 换成 python.exe 再隐形 spawn（保证 print 正常）。

- **不要**：把下载/守护作为 DSH/pi 会话的后台任务跑（宿主重启即死，可能一夜零进展）；
- **不要**：同时跑两个下载器（守护 spawn 的 + 手动启动的会写同一批 .part 文件）；
- **bug 修复必须同步全部副本**（repo + skills/ 镜像 + dsh/ 预设 + 本机安装副本），
  只改一处会被后续同步覆盖回去（2026-08-16 mode.flag 复发案例，v1.5.1 已修复）。

### ⚠️ 裁剪/自定义清单必须复检（2026-08-15 实测教训）

`analyze.py` 的逐时相覆盖校验用的是**搜索返回的全部帧**；若为了省磁盘手工
裁剪清单（如跳过搭边冗余帧只留主覆盖帧），**裁剪后的清单必须下载前复核**——
单帧足迹会随轨道微变，个别时相主帧可能覆盖不足（实测 2025-02-06：帧 463 单帧
仅覆盖研究区 90.2%，补相邻帧 468 后并集才 100%）。

```bash
# 清单驱动 + 下载前逐时相覆盖复检（未达标时相告警；--strict 则终止）
python scripts/multi_download.py \
  --list 裁剪后清单.csv --out <下载目录> --verify-aoi 研究区.shp [--strict]
```

复检输出每个时相并集覆盖率；`⚠ 时相: 并集覆盖 xx%` 的时相需补帧后重新生成清单。
底层实现：`analysis.verify_download_list()`（granule_search 取真实 footprint，
按清单逐时相并集覆盖检查）+ `analysis.per_date_coverage_report()`（纯函数）。

## 下载流程架构（v2 重构）

`scripts/download.py` 的下载主流程已封装为 **`DownloadSession` 类**（`scripts/download_session.py`）：
认证 → 搜索 → 分组 → 覆盖过滤 → 选择轨道组 → 校验（轨道一致性/逐时相覆盖）→ 批量下载
（HTTPS + host 白名单校验，防 SSRF/token 泄露）拆成可复用实例方法。
`run_download()` 保留为兼容包装（委托 `DownloadSession.run()`），原 v1 逻辑存于 `_run_download_v1`。

## 常见错误

| 问题 | 处理 |
|------|------|
| 登录失败 | 检查 config.json 凭证；Earthdata 可能要求两步验证，需手动完成 |
| 搜索结果为空 | 扩大时间范围或检查 AOI 坐标是否为 WGS84 |
| API 报错 | 检查网络/代理；ASF API 偶发限流，稍后重试 |
| shp 报错 | 确认 shp 是 WGS84（经纬度）坐标系 |

## 安全提示

config.json 含明文密码，仅本机使用，切勿分享或提交到仓库。

## 实验参数设置提醒机制 🎛️（SBAS-InSAR 全流程）

**数据下载完成后、开始 SARscape 实验前，AI 必须主动执行此机制**：
根据研究区**地形和位置**列出每一步的可调参数（不是只给默认值），
说明每个参数的**原理和适用场景**，**逐项询问用户意见**，用户确认后再执行。

> 💡 用户只需对话确认，AI 负责生成参数表、解释原理、执行批处理、汇报结果。

### 触发时机（用户说这些就启动参数确认流程）

- 「开始做实验」「跑 SBAS」「参数怎么设」「开始处理」
- 数据（SLC/POEORB/GACOS/DEM）全部下载完成后，自动衔接进入参数确认

### 参数确认流程（必须按序执行）

**第 0 步：识别研究区地形特征**（决定参数推荐方向）
- 向用户确认研究区类型：山区/平原/矿区/城市/滑坡区/植被区？
- 植被茂密区 → 低相干 → 推荐大视数 + Delaunay MCF + 低解缠阈值
- 城市/裸岩区 → 高相干 → 可小视数 + 经典 MCF + 高阈值
- 矿区/滑坡 → 形变可能非线性 → 建议 quadratic 模型对比 linear

**第 1 步：连接图（Connection Graph）**
| 参数 | 默认 | 依据/建议 |
|------|------|----------|
| 超主影像 | 自动选择 | 一般自动即可；手动选可能减少配对 |
| Max Temporal Baseline | 180 天 | 标准推荐 |
| Max Normal Baseline | 45-50% | 教程建议；太小易空间失相干 |
| Max Connections/Acq | ≥5（推荐 10）| 低于 5 反演解不可靠 |

**第 2 步：干涉工作流（Interferometric Process）**
| 参数 | 默认 | 依据/建议 |
|------|------|----------|
| Range/Azimuth Looks | 7/2（≈30m）| 视数大→噪声低但分辨率降；按地形调整 |
| 滤波方法 | Goldstein | 最常用；条纹密集用小窗口 |
| 解缠方法 | **Delaunay MCF** | SBAS 官方推荐！植被/潮湿区优于经典 MCF |
| 解缠阈值 | 0.2 | 区域增长法 0.15-0.2；低相干区偏低些 |
| 解缠等级 | 2（大范围低相干）| 减少错误提效率；>2 或致假信号 |
| 大气校正 | GACOS | 时相齐必选 |
| 叠掩阴影掩膜 | ON | 山地必开 |

**第 3 步：反演 Step1（形变模型）**
| 参数 | 默认 | 依据/建议 |
|------|------|----------|
| 形变模型 | linear | 最稳定；矿区/滑坡考虑 quadratic |
| 产品相干阈值 | 0.3 | 低于此像元 NaN；0.2 更宽松 |
| 残余高程 | 估计 ON | 去除地形相关相位 |
| GCP 轨道精炼 | 需人工 | 选稳定点（岩石/人工物），避水体植被 |

**第 4 步：反演 Step2（大气+形变分离）**
| 参数 | 默认 | 依据/建议 |
|------|------|----------|
| 大气低通 | 1200m | 空间滤波；大范围变化用大窗口 |
| 大气高通 | 365 天 | 时间滤波；默认即可 |
| 有效干涉 % | 65 | 每个网格点最小方程数 |

**第 5 步：地理编码（Geocoding）**
| 参数 | 默认 | 依据/建议 |
|------|------|----------|
| 输出网格 | 与多视匹配 | 8:2 多视 → 30m；4:1 → 15m |
| 速度精度阈值 | 8mm/y | 论文用严格值；探索可放宽 |
| 高程精度阈值 | 5m | 同上 |
| 相干阈值 | 0.1-0.3 | 结果点密度 vs 质量平衡 |

### 交互要求

1. **每次实验前必须列参数表**（上表），不能只跑默认
2. **逐项询问**用户意见（用列表形式，用户逐条回复或说"都用推荐值"）
3. 用户中途说「等一下，我还要改参数」→ 停止执行，等确认
4. 用户说「没问题」→ 才执行该步骤
5. 每步执行前**重复**此流程（不止第 2 步，每步都要确认）
6. 根据地形和位置**主动给推荐**，不能只罗列参数

### 提醒话术模板

```
【SBAS 实验 - 第 X 步参数确认】
研究区识别为：山区/植被区（低相干）
根据 SARscape 官方推荐，建议参数如下：
[参数表]
1. 以上参数是否都按推荐执行？
2. 有要调整的吗？（如解缠方法、视数、阈值）
```

> 💡 此机制的目的是：**先确认再执行**，避免跑完几小时发现参数不对重跑。

## 实验批处理执行（AI 自动运行 bat）

参数确认后，AI 按步骤执行 SARscape 批处理（`experiment/bat/`，路径已从 config.env 读取，零硬编码）：

| 步骤 | bat | 触发对话 |
|------|-----|---------|
| 第 1 步 连接图 | `experiment/bat/01_connection_graph/run_cg_final.bat` | 「开始第 1 步」 |
| 第 2 步 干涉图 | `experiment/bat/02_interferogram/run_interf.bat` | 「开始第 2 步」 |
| 第 3 步 反演1 | `experiment/bat/03_inversion/run_inv1.bat` | 「开始第 3 步」 |
| 第 4 步 反演2 | `experiment/bat/03_inversion/run_inv2.bat` | 「开始第 4 步」 |
| 第 5 步 地理编码 | `experiment/bat/04_geocode/run_geocode.bat` | 「开始第 5 步」 |
| 第 0 步 SLC 导入 | `experiment/bat/00_import/run_import_slc.bat`（ImportSentinel1Format，支持 ROI 裁剪/极化可选，verify 模式校验）| 「导入数据」 |

AI 执行要点：
- 每个 bat 从 `config.env` 读路径（若未配置先提示 `copy config.example.env config.env`）
- 执行前检查环境：`python experiment/check_environment.py` 全部 [OK]
- 长任务后台执行，向用户说明预计时长，期间定期查进度（守护日志）
- 完成/失败均汇报，异常引导用户决策

## 守护监控交互（AI 查实验状态）

实验运行期间由守护 `experiment/asf_experiment/sbas_guard.py` 自动监控（30 分钟体检 + 微信/邮件）。
**v4（2026-08-13 重构）**：守护已封装为 `Guardian` 类（状态机）——监控状态（阶段/CPU/重启计数）
是实例属性，主循环是 `run()`，`restart()` 用实例 `bat_file`。模块级工具函数（无状态）不变。
用户问「实验进展如何」「跑完没」「有没有异常」时，AI 查看守护日志汇报：

```bash
tail experiment/asf_experiment/sbas_guard.log   # 体检记录（进度/磁盘/异常）
```

### 🤖 守护三级唤醒机制（异常/里程碑 → 实时唤醒 AI 推理）

守护在**异常**（停滞/崩溃/磁盘不足）和**阶段完成**时唤醒 AI，三级通道：

```
wake_ai() →
  ① pi-web HTTP（装 pi-web 的）：POST /api/agent/<会话id> {type:prompt, message}
     → URL 自动扫描常见端口发现（兼容任意端口）；会话 id 自动从 /api/sessions 取
  ② 通用 pi RPC（只装标准 pi 的）：RPC_ENABLED=1 时守护 spawn `pi --mode rpc`，stdin 注入 prompt
  ③ wake_events.json 兜底：落盘，AI 下次会话检查接手
```

唤醒消息示例（异常场景 AI 收到后应诊断而非盲从）：
- 疑似停滞 → AI 查 main_sbas CPU 活跃/trace → 判断真停滞还是误判（内存密集不写盘≠停滞）
- 崩溃重启 → AI 查 trace 错误/配置 → 决定是否调整
- 阶段完成 → AI 检查产物质量 → 确认再进下一步

### ⚠️ 会话启动时必须检查 wake_events（异常/里程碑接手）

守护在异常（停滞/崩溃/磁盘不足）和阶段完成时写入 `asf_experiment/wake_events.json`
（三级通道①/②失败时落盘等待）。**AI 每次会话启动时**：

```bash
cat experiment/asf_experiment/wake_events.json   # 有 handled:false 的事件？
```

- **有未处理事件 → 先处理再继续**：诊断（查 trace/CPU/产物）→ 决策（修复/重启/调整）→ 标记 handled
- **error 类**：优先诊断根因（防误判，如内存密集阶段不写盘≠停滞）
- **milestone 类**：检查该阶段产物质量，确认后再进下一步

- 进度：`Interf generation [R_x]-[S_y] Progress [NN%]`
- 异常：崩溃/停滞/磁盘不足会记录并已自动重启/告警
- 推送策略：Server酱 5 条/天额度只推关键事件（完成/异常/日汇总/启动）

## 环境自检与全新用户验证（AI 协助）

新环境（或用户换了机器）时，AI 协助完成：

```bash
python experiment/setup_env.py            # 配置向导：自动探测 ENVI/SARscape/数据盘，逐项确认，生成 config.env
python experiment/check_environment.py    # 27 项：config/依赖/路径/软件/磁盘
python scripts/verify_clone.py            # 34 项：仓库完整性/代码健康/工具可运行
```

- 用户说「帮我配置环境」→ AI 运行 setup_env.py 向导（探测 + 确认）→ 生成 config.env
- 任一项 [FAIL]，AI 按提示修复并重新验证；全部 [OK] 才继续实验


## ⚠️ SARscape batch 参数名铁律（2026-08-12 实测教训）

**SetParam 参数名必须用官方大写全名（带完整子模块前缀），GUI 面板名 / xsd 小写名都会静默失效**
（SetParam 返回 0，SARscape 不报错继续用默认参数跑，事后才发现结果不对）：

| ❌ 无效写法（静默失效） | ✅ 有效写法（官方） |
|------------------------|--------------------|
| `GRID_SIZE` / `geocode_rg_grid_size` | `GEOCODE_CMD.GEOCODE_RG_GRID_SIZE` |
| `VELOCITY_THRESHOLD` / `precision_velocity_thr` | `MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.PRECISION_VELOCITY_THR` |
| `PRODUCT_COHERENCE_THRESHOLD`（geocode 内） | `MAIN_INSAR_STACK_SBAS_GEOCODE_CMD.COHERENCE_THR` |
| `GENERATE_LOS_FLAG`（缺前缀/小写） | `DISPLACEMENT_PROJECTION_CMD.GENERATE_LOS_FLAG` |

**官方参数模板位置**：
`C:\Program Files\SARMAP SA\SARscape\auxiliary\envi_extensions\idl\help\SARscape\` 下每个模块有
`sarmap_sb_*.pro` 示例（如 `sarmap_sb_sbasgeocoding.pro`），含该模块全部 SetParam 调用。

**验证方法**（跑正式 Execute 前必做）：写 verify-only bat，逐个 `SetParam` 后打印 `byte(p)`
——返回 1 才生效、0 即失效；再 `VerifyParams()` 确认整体通过。**不能只看 Execute 跑起来了**：
参数名无效时 SARscape 会静默用默认值跑完（如 geocode 默认 14m 网格），事后用产物 `.sml` 的
`EastingGridSize` 等字段反查才能发现（30m 应 = `0.00025` 度）。

**SARscape 批处理进程架构**：`envi_idl.exe`（IDL 批处理壳，可能先退并打印 EXECUTE:0）+
`main_sbas.exe`（实际 C++ 计算进程，内存密集峰值 7.3GB）。判断进程是否在跑**必须查 main_sbas**
（wmic/tasklist 全查，勿只 grep envi_idl），文件持续写入是更可靠的存活信号。

**REBUILD 重跑注意**：重跑某步骤时 auxiliary.sml 仍保留旧 `OK` 标记 → 守护可能误报「全流程完成」
且停止监控（进程崩溃不自动重启）。重跑期间需人工盯进程，或守护加「进程活跃则不报 DONE」保护
（已修复于 sbas_guard.py）。
