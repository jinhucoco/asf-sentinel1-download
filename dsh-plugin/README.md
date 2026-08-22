# @dsh-custom/insar-genie-dsh

SBAS-InSAR 全链路 DSH 插件：insar_run / insar_status / insar_templates 工具 + 参数防呆校验（2-4% 基线门禁）+ 实验注册表。技能资产（SKILL.md / scripts/ / experiment/）由 agent preset `dsh/insar-genie/` 携带。

## 安装

1. 安装 agent preset（携带技能与脚本）：
   `powershell -ExecutionPolicy Bypass -File dsh/install-dsh.ps1`
2. 安装插件（注意 pnpm workspace root 检查需加 `-w`）：
   `dsh plugin --profile web add @dsh-custom/insar-genie-dsh -w`

## 使用

- 对话：「跑 SBAS，区域 xxx.shp，2020-2025，VV」
- AI 识别地形 → 调用 `insar_templates` 取模板 → 生成参数表 → 用户确认 → `insar_run` 执行下载（list 清单 CSV 或 aoi+start+end，同步 await，数小时级）
- 实验运行中：`insar_status` 查询五步进度与剩余时间（AI 汇报）

## 工具

| 工具 | 作用 |
|---|---|
| `insar_run` | 执行 Sentinel-1 SLC 下载（`multi_download.py`；--list 清单 CSV 或 --aoi/--start/--end 搜索路径 + --pol/--out；cwd=scriptDir，不设超时）|
| `insar_status` | 读取实验状态（解析 auxiliary.sml / step_performed.sml / guard 日志）|
| `insar_templates` | 按地形返回参数模板（矿区/滑坡/城市/沙漠/黄土高原）|

## 设置（settings → insar-genie）

- earthdataUser / earthdataPassword：ASF 凭证
- gacosEmail / gacosImapAuthCode：GACOS 收件邮箱
- enviIdl / sarscapeLib：ENVI/SARscape 路径
- workDir / poeorbDir：数据目录（POEORB 默认 <实验目录>/poeorb；gacos/dem/slc 目录当前由实验目录管理）
- registryDir：实验注册表存储目录

## 防呆铁律

- 空间基线必须在 2-4%（`validateBaseline` 拦截 45% 事故）
- 执行后应校验 tmp/*/work/PARAMETERS_INFO_*.xml 实际落盘值 == 参数快照

## 状态

- host 工具：✅ 可用
- client UI（参数确认卡片 / 进度面板）：⏸️ 推迟（需完整 DSH client 构建链，后续单独设计）
