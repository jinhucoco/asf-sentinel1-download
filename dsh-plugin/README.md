# @dsh-custom/insar-genie-dsh

SBAS-InSAR 全链路 DSH 插件：`insar_run` / `insar_status` / `insar_templates` / `insar_register` / `insar_list` 工具 + 参数防呆校验（2-4% 基线门禁）+ 实验注册表 + client UI（参数确认卡 / 进度面板 / 设置卡）。

技能资产（SKILL.md / scripts/ / experiment/）由 agent preset `dsh/insar-genie/` 携带：**只装插件不带 preset 则 `insar_run` 依赖的 `multi_download.py` 等脚本不存在**，安装时须先装 preset（见下）。

## 安装

1. 安装 agent preset（携带技能与脚本）：
   `powershell -ExecutionPolicy Bypass -File dsh/install-dsh.ps1`
2. 安装插件（注意 pnpm workspace root 检查需加 `-w`）：
   `dsh plugin --profile web add @dsh-custom/insar-genie-dsh -w`

> **前提**：本包为源码包（`lib/` 不在仓库内），发布/打包前必须构建。本地开发用 `npm run build` 生成 `lib/` + `client/client.js`；`prepublishOnly`/`prepack` 已钩住 build，`npm publish` 时自动保证产物存在。

## 使用

- 对话：「跑 SBAS，区域 xxx.shp，2020-2025，VV」
- AI 识别地形 → 调用 `insar_templates` 取模板 → 生成参数表 → 用户确认 → `insar_run` 执行下载（list 清单 CSV 或 aoi+start+end，同步 await，数小时级）
- 注册实验：`insar_register`（写入注册表，记录参数快照，`maxPercBaseline` 防呆拦截非法值）
- 实验运行中：`insar_status` 查询五步进度与剩余时间（速率按 guard 日志动态计算，无数据时兜底 0.22 对/分）

## 工具

| 工具 | 作用 |
|---|---|
| `insar_run` | 执行 Sentinel-1 SLC 下载（`multi_download.py`；--list 清单 CSV 或 --aoi/--start/--end 搜索路径 + --pol/--out；cwd=scriptDir，不设超时）|
| `insar_status` | 读取实验状态（解析 auxiliary.sml / step_performed.sml / guard 日志；进度与 ETA）|
| `insar_templates` | 按地形返回参数模板（矿区/滑坡/城市/沙漠/黄土高原）|
| `insar_register` | 注册新实验到注册表（记录参数快照，返回 id；防呆校验基线）|
| `insar_list` | 列出已注册实验（id/name/terrain/status）|

## 设置（settings → insar-genie）

- earthdataUser / earthdataPassword：ASF 凭证
- gacosEmail / gacosImapAuthCode：GACOS 收件邮箱
- enviIdl / sarscapeLib：ENVI/SARscape 路径
- workDir / poeorbDir：数据目录（POEORB 默认 <实验目录>/poeorb；gacos/dem/slc 目录当前由实验目录管理）
- registryDir：实验注册表存储目录

## 防呆铁律

- 空间基线必须在 2-4%（`validateBaseline` 单一来源 `src/shared/baseline.ts`，host 与 client 共用；`insar_register` 写入前强制拦截 45% 事故）
- 执行后应校验 tmp/*/work/PARAMETERS_INFO_*.xml 实际落盘值 == 参数快照

## 状态

- host 工具：✅ 可用（5 个）
- client UI：✅ 已有（参数确认卡 / 进度面板 / 设置卡 / 实验列表），走 `conversation.chat.turnTail` + `settings.section` 插槽
- 构建：`npm run build`（tsc host + tsdown client）；测试 `npm test`（vitest 60 用例）
