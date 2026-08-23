# SDD 进度账本 — insar-genie DSH 插件

计划：docs/superpowers/plans/2026-08-22-insar-genie-dsh-plugin.md
仓库：C:\Users\86155\.pi\agent\skills\asf-sentinel1-download (dev)
计划修正提交：5a6ec1f（import修复）、07f59a8（@types/node）、926fc18（ExperimentLifecycle 命名）

## 任务状态

- Task 1: complete (commits 07f59a8..a027b7f, review 待定)
- Task 2: 未开始（简报已生成 task-2-brief.md）
- Task 3: 未开始（简报已生成 task-3-brief.md）
- Task 4-10: 未开始

## 备注
- npm 本机默认 omit=dev，需 --include=dev 装 devDeps
- 简报实验性 fixture 数据已对真实文件验证（step_performed 310对/1563行；auxiliary 标记顺序一致）
- tsc/vitest 必须在 dsh-plugin/ 目录下执行（仓库根无 tsconfig）

## Task 1 审查发现
- [重要] @types/node ^26.2.0 != 简报 ^22.0.0 → 已分派修复（改回 ^22.0.0）
- [次要] SBAS_STEPS 注释'五步'与 6 项列表矛盾（简报自带）→ 后续任务顺带改注'六步'
- [次要] 报告计数口径 6文件/1914 插入 vs 实际 7文件/1916（含计划修正）
- [已修复] @types/node 改回 ^22.0.0（提交 8834d68，lockfile 22.20.1，tsc exit 0）
- Task 1: complete (commits 07f59a8..8834d68, review clean 2nd pass)
- Task 2: 实现完成 62e9f6a，审查待定；潜在点：.gitignore 的 *.log 与 guard.log fixture 冲突（若需修复：.gitignore 增加 '!dsh-plugin/test/fixtures/' 例外）
- Task 2 审查: 通过（62e9f6a，逐字一致）; [重要] .gitignore *.log 与 fixtures 冲突 → 分派修复（加 !dsh-plugin/test/fixtures/*.log 例外）
- Task 2: complete (commits 62e9f6a + 0d3b29e, review clean after fix)
- Task 3: 实现完成 5e6967a（TDD RED→GREEN 4/4），审查待定
- Task 3: complete (commit 5e6967a, review clean; 次要: 报告行数误差/parseAuxiliarySteps 建键面/parsePairProgress 匹配面——均为简报逐字要求，不修)
- Task 4: 实现完成 5eb30a4（TDD RED→GREEN 6/6，全量 10/10），审查待定
- Task 4: complete (commit 5eb30a4, review clean; 次要观察: 副本防篡改未直接测/NaN 消息/缺失功能型 RED——均不修)
- Task 5: 实现完成 c40a634（TDD RED→GREEN 3/3，全量 13/13）；疑虑: 简报漏 import afterEach → 已最小修复（加 import），审查待定
- Task 5: complete (commit c40a634, review clean; afterEach import 修复已核实恰当)
- Task 6: 已分派实现者 f4afada5（runner.ts Python spawn 封装 TDD）
- Task 6: 实现完成 358eea7（TDD RED→GREEN 2/2，全量 15/15）；疑虑: -c→-e 修复（简报 bug）+ beforeEach/afterEach import，审查待定
- Task 6: complete (commit 358eea7, review clean; -c→-e 修复核实正确)
- Task 7: 已分派实现者 2ae73520（tools/settings/index 注册，含 POEORB；集成类，注意 cordis API 签名）
- Task 7 重试: 简报 API 修正（defineTool/ctx.tools + installSettingsSection 5参数，对照真实 dsh-tools/dsh-settings 类型验证），计划 bee81cf；已重新分派实现者 8f9cc8a1
- Task 7: 实现完成 3970bf0（5 处类型适配 + 2 疑虑，tsc exit 0 已独立验证），审查待定
- Task 7 审查: 通过（3970bf0，5 类型适配核实正确）
  [重要-修复] schemastery 幽灵依赖 → 补 package.json 声明（本次修）
  [重要-后续] insar_run 语义（长任务保持 queued）→ 建议任务10 或后续改 dsh-jobs 后台任务
  [次要] as never 可改 JsonValue/TerrainType、dispose 死代码、exec.signal 未转发、REGISTRY_DIR 注释、失败双标记
- Task 7: complete (commits 3970bf0 + a5958ee, review clean after schemastery dep fix; 遗留后续: insar_run 长任务语义建议改 dsh-jobs)
- Task 8: 推迟（用户决策 2026-08-22）——client UI 需完整 DSH client 构建链（tsdown/ModuleLoader/插槽注册/多个 client peer 依赖），dsh-plugin 无基建；改后续单独设计
- 计划修正: 任务8 标记为'推迟'，不阻塞 host 侧（任务9-10）
- Task 9: 已分派实现者 821eeb72（挂载到 agent preset + 安装脚本；client UI 推迟的表述调整）
- Task 9: 实现完成 2842ce7；疑虑: README 超前描述（skillDir/gacosDir 等不存在，仅 poeorbDir），审查待定
- Task 9 审查: 通过（2842ce7）; [重要-修复] README 超前描述（skillDir 等不存在）→ 分派修复对齐 settings.ts
- Task 9: complete (commits 2842ce7 + 69d7f67, review clean after README fix)
- Task 10: 已分派实现者 f9c3f806（端到端验证 + README（client UI 推迟调整）+ 推 dev）
- Task 10: complete (commit fb0cc34, pushed dev e258b9a..fb0cc34; 测试 15/15 + build 通过，实现者停滞改亲自完成)
- 全部 10 任务完成；下一步：最终整分支代码审查（MERGE_BASE..HEAD）
- 最终整分支审查: 已分派 263c0bb8（926fc18..fb0cc34，25 文件，含跨任务一致性/插件完整性/核心业务）
- 最终审查: 不可合并（3 关键）——K1 命名空间运行时抛错（已实测）/ K2 insar_run 调用不存在 CLI / K3 安装链路缺失
- 修复已分派 5547a03d（K1/K2/K3 + 重要#4 exports；用户确认方向）
- 修复已提交 f738484 + 推送 dev（10 文件，21/21 测试过，tsc 0）
- 复核审查已分派 ab2dd78f（K1/K2/K3/重要#4 逐一核实）
- 复核审查: 源码修复正确但 lib 旧构建（K1 运行时仍在）→ 已重建 lib + 补 bundles + lockfile 同步
- 部署收尾完成: 插件从 web profile 加载 OK（name=insar-genie-dsh），21/21 测试，本地=远程 f738484
- 遗留（合并后跟进）: insar_status 需 registry 写入路径（设计断裂）、异常诊断规则库、落盘校验、.gitignore 取反失效
- Task 8a: complete (60a77ce pushed; guard 路径探测/error 缺失/insar_register+insar_list; 22/22 tests, tsc 0)
- Task 8b: complete (6760a57 pushed; tsdown ModuleLoader bundle client.js, outExtensions .js fix, deps.neverBundle)
- Task 8c: complete (eff4931 pushed; 3 client 组件 + 10 client 测试，32/32 全过，双 tsc 0)
- client 接线说明: turnTail 按 kind 渲染 Progress/ParamConfirm，settings.section 渲染 SettingsCard；数据经 window.insarGenieBridge + props 注入（host 侧接线为后续）
- 最终审查(client): 已分派 5c53dbcb（9d1bdaa..eff4931，3 提交 8371 行）
- [部署同步] 安装副本（pnpm junction）缺 client/ —— 需重新 dsh plugin add 或手动同步 client.js 才生效（审查后处理）
- 最终审查(client): 两次子代理审查均环境停滞无结论（5c53dbcb、7b36b12e）→ 控制者独立核验通过
  核验证据: client.js ModuleLoader 格式有效/package.json dsh.client+exports 自洽/host 修复齐全/32 测试+双 tsc 通过/dev 已推 eff4931
- [部署同步] 安装副本需重新 dsh plugin add 同步 client/（pnpm junction 不自动传播新增目录）
- Task 8d: complete (a5d08a5 pushed; host→client 数据接线——conversationEvents Definition 累积 insar_status/list/register/templates 结果到 turn 数据，turnTail 改 chain select（修复缺 select 真实 shell 抛错），组件经 useSession 从会话快照取最新真实进度；55/55 测试 + 双 tsc 0；ParamConfirm 现由 insar_templates 结果驱动）
- 独立审查(client 接线): 已分派（聚焦 a5d08a5 接线正确性 + 真实 shell 契约合规）
- [部署同步] 完成: dsh plugin add 重装（BOM 修复后），安装副本现含 ./client exports + dsh.client.inject + client.js；profile bundles 已含 insar-genie-dsh
- 独立审查(client 接线 a5d08a5): NOT_MERGEABLE —— 3 严重（latestInsarStatus 取最旧/snapshot 喂 initial 而非 snapshot prop/跨 turn 泄漏压制 experiments+registered）+ 重要 4-5 + 次要 6-8
- 修复已提交 c667206 + 推送 dev（发现 1-3,5,7,8；60/60 测试 + 双 tsc 0；bundle 同步安装副本）
- 复核审查: 已分派（逐条核实 c667206 修复 + 发现 4 的测试补覆盖）
- 复核审查: MERGEABLE —— 8 发现全部真修复（非表面），60/60 + 双 tsc 0，工作区干净；剩余 4 项次要设计语义不阻塞（记录为后续迭代）：
  * 快照会话级最新跨实验混显（多实验会话旧 turn 面板显示另一实验进度；单实验主流程无影响）
  * 快照窗口截断/call=null 时陈旧回退（边缘场景）
  * fetchStatus 轮询 experimentId 兜底被移除（旧代码 registered.experimentId 兜底，现仅 latest.experimentId）
  * 多个完成 turn 各渲染一块"实时"面板（per-turn tail + 全局最新，设计取舍）
- client 接线: COMPLETE（a5d08a5 + c667206，dev 已推，复核 MERGEABLE）
- [用户用 Pi 修加载报错] 8 提交（cd074d5..08f37fd，本地=远程 08f37fd）：cordis.patch.yml 入库、inject 服务名 [tools,settings]/[slots,conversationEvents]、bundle 注册 id 改包全名、var module/exports 注入、dsh.client.inject 包名 vs client.js 服务名区分、P1 防呆接入 host 工具 + validateBaseline 去重 + 动态速率
- [GUI 端到端验证 2026-08-23] 浏览器打开正常（0 报错）；/plugins/@dsh-custom/insar-genie-dsh/client.js 加载 200；设置页出现 insar-genie 区段且 SettingsCard 完整渲染（9 字段+保存）；host 工具 insar_register/insar_list/insar_status 全链路可用（真实 G:\minqin1_result_SBAS_processing 读出 干涉图 21% 65/310）；注册表持久化于 ~/.insar-genie/experiments.json；测试实验已清理
- [设置 UX 改进] 229e55b：删死字段 registryDir（host 硬编码 registry 目录，用户无需配置）+ IMAP 授权码改名"邮箱授权码"（普通用户可读，未来扩展 POP3 复用）
- [启动时路径探测] 2a4d4a1：新增 src/host/probe.ts（环境变量>Program Files 探测 ENVI IDL + SARscape），探测结果作为设置 base 层默认值，UI 显示"▲ 启动时自动定位"标记；POEORB/工作目录不探测（保留手动）；70/70 测试 + 双 tsc 0；真实探测验证命中本机 C:\Program Files\Harris\ENVI56\...\envi_idl.exe + C:\Program Files\SARMAP SA\SARscape
