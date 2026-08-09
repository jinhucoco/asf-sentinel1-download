# SBAS-InSAR 全链路实验脚本（experiment/）

从 S1 数据下载 → DEM/GACOS/POEORB 配套数据 → SBAS-InSAR 五步处理 → 监控守护的**全链路代码**。
本目录是版本管理源；实际运行在独立工作目录（见下）。

## 快速开始（别人拉取后怎么跑）

```bash
# 1. 复制配置模板并按本机环境修改
copy config.example.env config.env
#    编辑 config.env：工作目录 / SLC 数据 / 输出盘 / DEM / GACOS / ENVI+SARscape 路径

# 2. 安装 Python 依赖（下载/配套工具用）
pip install -r ../scripts/requirements.txt

# 3. 获取数据（可选，用仓库 scripts/ 里的工具）
python ../scripts/download.py --aoi 研究区.shp --start 20200101 --end 20251231 --pol VV+VH
python ../scripts/poeorb_download.py --data-dir %SLC_DATA% --out ./poeorb
python ../scripts/dem_download.py --aoi 研究区.shp --out ./dem
python ../scripts/gacos_download.py --bbox "..." --list 时相.txt --time 23:10 --email 你@邮箱 --out ./gacos

# 4. 运行 SARscape 批处理（需安装 ENVI + SARscape + license）
run_interf.bat        # 干涉图生成（第 2 步）
run_cg_final.bat      # 连接图生成（第 1 步）
run_gacos_import.bat  # GACOS 导入

# 5. 守护监控（自动体检 + 微信/邮件告警）
cd asf_experiment && python -u sbas_guard.py
```

## 环境要求（物理依赖）

| 依赖 | 说明 |
|---|---|
| **ENVI + SARscape** | 商业软件，需自己的 license（处理核心，代码无法替代）|
| **SLC 数据** | 从 ASF 下载（用 scripts/ 下载工具，需 Earthdata 账号）|
| **GACOS / DEM / POEORB** | 用 scripts/ 配套工具获取（GACOS 需邮箱）|
| **Python 3.10+** | asf_search/pyshp/shapely/defusedxml/matplotlib/earthaccess |
| **通知凭证**（可选）| Server酱 sendkey、SMTP 授权码（asf_experiment/notify_config.json、mail_config.json）|

## 配置说明（config.env）

所有脚本（bat + python）从 `config.env` 读取路径，**无硬编码路径**。
`config.env` 在本机（gitignore 不入库），`config.example.env` 是提交的模板。

| 配置项 | 含义 |
|---|---|
| WORK_DIR | 工作根目录（脚本/日志/清单）|
| SLC_DATA | S1 SLC 数据目录 |
| RESULT_ROOT / TMP_DIR | SARscape 输出 / 临时目录（大容量盘）|
| DEM_FILE / GACOS_LIST / SAR_MODULES | 数据与参数文件 |
| ENVI_IDL / IDL_EXE / SARSCAPE_LIB | 软件路径 |
| SKILL_DIR | 本仓库技能安装目录 |

## 目录结构

```
experiment/
├── config.example.env / config.env   路径配置（env 为本机值，不入库）
├── config_loader.py                  python 配置读取
├── check_environment.py              环境自检（27 项，配置好 config.env 后先跑）
├── bat/                              SARscape 批处理（按功能分类）
│   ├── 01_connection_graph/          连接图生成（第 1 步）
│   ├── 02_interferogram/             干涉图生成（第 2 步）
│   └── 03_data_prep/                 GACOS 导入 / DEM 提取 / geoid / 数据导入
├── asf_experiment/sbas_guard.py      守护（自动体检 + 微信/邮件）
├── scripts/plot_connection_graph.py  连接图绘制
├── 配套数据/                          GACOS 提交/收件、POEORB、DEM 工具
└── sar/dem/*.sml                     研究区 DEM 配置
```

## 工作流

- **开发/测试在 dev 分支，验证后合 main**（本仓库约定）
- 敏感配置（sendkey/授权码/凭证）**绝不入库**（.gitignore）
- 实际运行目录与版本管理源分离：改完代码从仓库同步到运行目录
