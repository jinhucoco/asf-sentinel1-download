# @dsh-custom/insar-genie-dsh

SBAS-InSAR 全链路 DSH 插件：`insar_run` / `insar_status` / `insar_templates` / `insar_register` / `insar_list` / `insar_experiment` / `insar_settings` 工具 + 参数防呆校验（2-4% 基线门禁）+ 实验注册表 + client UI（参数确认卡 / 进度面板 / 设置卡）。

**开箱即用**：插件自带完整 SBAS 执行链（`assets/scripts/` 下载/配套数据工具 + `assets/experiment/` SARscape 五步 batch 与守护脚本）。安装插件后 `insar_run` / `insar_experiment` 自动使用内置脚本，**无需另装技能或手动传脚本路径**。

## 安装

```powershell
dsh plugin --profile web add @dsh-custom/insar-genie-dsh -w
```

> **前提**：本包为源码包（`lib/` 不在仓库内），发布/打包前必须构建。本地开发用 `npm run build` 生成 `lib/` + `client/client.js`；`prepublishOnly`/`prepack` 已钩住 build，`npm publish` 时自动保证产物存在。`assets/` 随包携带（`files` 已含），安装即带脚本。

## 使用

- 对话：「跑 SBAS，区域 xxx.shp，2020-2025，VV」
- AI 识别地形 → 调用 `insar_templates` 取模板 → 生成参数表 → 用户确认 → `insar_run` 执行下载（list 清单 CSV 或 aoi+start+end，同步 await，数小时级）
- 注册实验：`insar_register`（写入注册表，记录参数快照，`maxPercBaseline` 防呆拦截非法值）
- 实验运行中：`insar_status` 查询五步进度与剩余时间（速率按 guard 日志动态计算，无数据时兜底 0.22 对/分）

## 全流程使用（装插件即跑）

装好插件后，其他用户即可在对话中全流程跑 SBAS 实验，无需额外配置脚本：

1. **首次配置**（设置 → insar-genie）：填 ASF 账号密码、GACOS 邮箱 + IMAP 授权码；ENVI/SARscape 路径已自动探测，工作目录默认 `G:\`。
2. **对话发起**：「跑 SBAS，区域 xxx.shp，2020-2025，VV」。
3. AI 自动：
   - 识别地形 → `insar_templates` 取模板 → 展示参数表（含 2-4% 基线防呆）→ 用户确认
   - `insar_register` 注册实验（写入注册表，记录参数快照）
   - `insar_run` 下载 SLC（`scriptDir` 默认用插件内置脚本，无需传）
   - `insar_experiment` 逐步执行 SARscape 五步（import_slc → cg → interf → inv1/inv2 → geocode）
   - `insar_status` 汇报进度（进度面板实时显示）
4. 需要自定义脚本位置时：设 `INSAR_GENIE_SCRIPTS` / `INSAR_GENIE_EXPERIMENT` 环境变量，或给 `insar_run` 的 `scriptDir` / `insar_experiment` 的 `experimentDir` 传值。

> 脚本路径解析优先级：显式参数 > 环境变量 > 插件内置 `assets/`（随包走，默认）。

## 工具

| 工具 | 作用 |
|---|---|
| `insar_run` | 执行 Sentinel-1 SLC 下载（内置 `assets/scripts/multi_download.py`；`scriptDir` 可选，默认内置目录，可用 `INSAR_GENIE_SCRIPTS` 环境变量或参数覆盖；--list 或 --aoi/--start/--end + --pol/--out，不设超时）|
| `insar_experiment` | 执行 SARscape 批处理步骤（内置 `assets/experiment/bat/<step>/<bat>`；按 step=import_slc/cg/interf/dem/gacos_bulk/gacos_import/inv1/inv2/geocode 在实验目录运行对应 bat）|
| `insar_status` | 读取实验状态（解析 auxiliary.sml / step_performed.sml / guard 日志；进度与 ETA）|
| `insar_templates` | 按地形返回参数模板（矿区/滑坡/城市/沙漠/黄土高原）|
| `insar_register` | 注册新实验到注册表（记录参数快照，返回 id；防呆校验基线）|
| `insar_list` | 列出已注册实验（id/name/terrain/status）|
| `insar_settings` | 读取解析后的设置值（含启动探测的 ENVI/SARscape 路径）|

## 设置（settings → insar-genie）

- earthdataUser / earthdataPassword：ASF 凭证
- gacosEmail / gacosImapAuthCode：GACOS 邮箱 + IMAP 授权码
- enviIdl / sarscapeLib：ENVI/SARscape 路径（**启动时自动探测**，无需手填）
- workDir / poeorbDir：数据目录（POEORB 默认 <实验目录>/poeorb；gacos/dem/slc 目录由实验目录管理）

## 防呆铁律

- 空间基线必须在 2-4%（`validateBaseline` 单一来源 `src/shared/baseline.ts`，host 与 client 共用；`insar_register` 写入前强制拦截 45% 事故）
- 执行后应校验 tmp/*/work/PARAMETERS_INFO_*.xml 实际落盘值 == 参数快照

## 状态

- host 工具：✅ 可用（7 个）
- client UI：✅ 已有（参数确认卡 / 进度面板 / 设置卡 / 实验列表），走 `conversation.chat.turnTail` + `settings.section` 插槽
- 构建：`npm run build`（tsc host + tsdown client）；测试 `npm test`（vitest 82 用例）
