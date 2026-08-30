# insar-genie 插件缺陷与优化待办(完整版)

> 用途:minqin2 全流程实测(2026-08-27~30)暴露的所有插件缺陷,供后续优化插件时逐项对照修复。
> 状态图例:🔴严重 / 🟡中等 / 🔧增强 / ✅已修 / 📌待优化 / ℹ️经验
> 远程仓库开发时以本清单为 TODO,修复后勾选。

---

## 一、下载链路

### D1 🔴 complete.flag 误写(已临时修,待正式修)
- **现象**:`multi_download.py` 遍历清单后**无差别写 complete.flag**——即使有大量失败文件(实测成功3/失败131/跳过12 也写)。
  后果链条:run_dl.py `_completed()` 见 flag → 不再拉起下载器 → 守护见 flag → 误报"完成"退出 → **实际丢失 131 景**。
- **现场**:2026-08-28 凌晨断网 131 景失败,误标;2026-08-29 又复现一次(成功10/失败9/跳过127 仍写 flag)。
- **临时修复**:删 flag + 重跑 run_dl.py。
- **待办**:写完 flag 前校验失败数==0;或 `_completed()` 改为 flag 存在**且无 .part/失败记录**才算完成。
- **文件**:`assets/scripts/multi_download.py`

### D7 🔧 下载器网络健壮性(IDM 式,待做)
- 分片 6 次重试失败后**整文件作废**(删所有 parts)——应只作废失败片;
- `timeout=(30,120)` 读超时太长,断连挂死——改 20-30s 断连即重连;
- 无动态降并发——连续失败渐进 8→4→2→1 线程;
- 无 TCP keep-alive;
- 无动态分片调度(完成一片接下一段,而非固定 8 段等最慢)。
- **文件**:`assets/scripts/multi_download.py`

### D6 🟡 asf_search 12.3.1 极化搜索 VV 返回 0(操作层解决,待文档化)
- CMR 中该区域 SLC 的 POLARIZATION 属性值是 `VV+VH`(1SDV 双极化),`polarization='VV'` 匹配不到 → 搜索 0。
- 解决:`--pol VV+VH` 下载,`ONLY_VV_POL` 导入取 VV。
- **待办**:analyze.py/download.py 遇 VV 搜索 0 结果时提示改用 VV+VH;文档注明。

### D12 🟡 import_slc_bulk.py 的 POWER_FLAG 误设 NotOK(本次新增)
- 现象:批量导入产物**无 `_pwr` 强度图**。`GENERATE_IW_EW_POWER_FLAG='NotOK'` 偏离官方模板/原 bat 的 `'OK'`(用户问"怎么没有 pwr 强度图")。
- 根因:参考官方文档"Make Power QL to FALSE"时过度解读,错关了功率图。
- **影响**:`_pwr` 是 multilooked 强度图(mosaic of bursts),官方用于**目视检查 AOI 覆盖/拼接质量**,不参与 SBAS 计算(处理用 `_slc_list`,不是 pwr)。
- **决策**:minqin2 主线已按 NotOK 跑完 36+ 时相(不返工);后续可写小脚本补生成 pwr。
- **待办**:脚本 POWER_FLAG 应默认 OK(与官方一致);可加 `--no-pwr` 选项供省空间场景。
- **文件**:`import_slc_bulk.py`(本地驱动脚本,非插件 assets)

---

## 二、SARscape 批处理执行

### D5 🟡 自动 config.env 的 SARSCAPE_LIB 缺 \auxiliary(已临时修,待正式修)
- 自动 config.env:`SARSCAPE_LIB=C:\Program Files\SARMAP SA\SARscape`(缺 `\auxiliary`)
  → bat 拼 `%SARSCAPE_LIB%\envi_extensions\idl\lib` 路径不存在 → **Execute 静默失败**(SetParam 全 1 但 Execute=0,极难察觉)。
- **待办**:configenv.js 需保证 sarscapeLib 含 `\auxiliary`(settings 探测值 vs bat 拼接需求不一致)。
- **文件**:`lib/host/configenv.js`、`lib/host/tools.js`

### D3 🟡 run_gacos_bulk.bat 依赖 .rsc 配套(已临时修,待文档化)
- 只复制 `.ztd` 时报 `EC=70000 [WRONG INPUT PARAMETERS] theArg=xxx.ztd.rsc`——GACOS 需要 .ztd+.rsc 全套。
- **待办**:文档明确"gacos 输入需 .ztd+.rsc";或逐日期导入时跳过缺 rsc 的并告警。
- **文件**:`assets/experiment/bat/03_data_prep/run_gacos_bulk.bat`

### D4 🟡 merge_hgt_dem.py 文件名解析切片 bug(已修)
- `parse_hgt` 用 `base[3:6]` 解析经度,对标准命名 `n38e103.hgt` 取到 `e10` → 全部失败。
- **已修**:正则 `^([ns]?)(\d{2})e(\d{3})\.hgt$`(插件+工作区副本同步)。
- **文件**:`assets/experiment/tools/merge_hgt_dem.py`

### D8 🔧 IDL 批处理吞 stdout(诊断陷阱,需文档化)
- `envi_idl.exe -quiet -e` 的 print/HELP 不进 stdout,sarbatch_*.txt 只有 NLS 警告。
- 判断成败:靠 SARscapeBatch `openw` 写出的文件(如 sar_modules.txt 的 EXECUTE 字段)+ 产物 sml;
  真正错误在 `<tmp>/work/Process.trace` 的 `[SARS_LOG]`/`[CORE][!]`/`EC=70000` 行。
- **待办**:文档强调查 trace 而非 sarbatch(与 SKILL.md auxiliary.sml 铁律同理)。

---

## 三、参数确认 UI

### D2 🟡 地理编码参数确认卡字段过少 + onConfirmAll 空回调(待做,用户重点反馈)
- `insar_pipeline` 5 卡中地理编码卡仅 5 字段(RG/AZ 网格、COHERENCE_THR、GENERATE_RASTER/SHAPE),
  实际 run_geocode.bat 固化 23 参数,官方模板更多。
- `PipelineConfirm.js` 的 `onConfirmAll` 是**空回调 `() => {}`**——卡片只能展示,用户改的值不生效。
- **用户已确认方案**:minqin2 用 bat 固化参数(方案 B);卡片扩展(方案 A)后续做。
- **待办**:
  1. `pipeline.js` buildPipelineCards() geocode 数组补全(PRECISION_HEIGHT_THR=5m、PRECISION_VELOCITY_THR=8m/y、GENERATE_LOS/VERTICAL_FLAG、OCS 投影系、GEOCODE_ORBIT_INTERPOL 等,对齐 bat 23 参数)
  2. `PipelineConfirm.js` onConfirmAll 实现编辑值回传 host 并应用
- **文件**:`lib/host/pipeline.js`、`lib/client/PipelineConfirm.js`

---

## 四、SLC 导入(重点,本次核心)

### D11 🟡 run_import_slc.bat 无"按时相分组/拼接判断"机制(用户指出,已用驱动脚本绕开)
- 脚本 `file_search` 抓目录**所有 zip**,`MAKE_SLC_LIST_MOSAIC_FLAG='OK'` 无条件开。无逻辑判断:
  ① 研究区是否跨帧(单帧不拼/双帧拼)② 输入是否同一时相。
- **后果**:146 景全放一个目录跑 = 77 时相混拼,完全错误。导入单位必须是"时相(日期)"。
- **正确规则**(实测+官方文档):
  - 单帧覆盖(minqin1):每时相 1 景导入,不拼接 → `slc_list`
  - 双帧覆盖(minqin2):每时相 2 景(同轨 458+463)一起导入 → `msc_slc_list` 拼接
  - 官方: `_slc_list` 是 burst 的链接文件,**SBAS 后续处理读它**;`.split_bursts` 是实际数据
- **绕开方案(已成)**:本地驱动脚本 `import_slc_bulk.py`——按日期分组、组内同轨校验、逐个 Execute、幂等续跑、AOI 裁剪。
- **待办(插件级)**:给 run_import_slc.bat 增加"按清单日期分组"驱动(相当于把 import_slc_bulk.py 逻辑并入插件);SLC_OUTPUT 不应默认=SLC_DATA。
- **文件**:`assets/experiment/bat/00_import/run_import_slc.bat`

### D13 🟡 导入驱动脚本与插件职责边界(本次新增,规划性)
- 当前导入完全靠本地 `import_slc_bulk.py` + `run_import_guard.py`(计划任务自愈),未进插件。
- **待办(插件级)**:把"按时相分组批量导入 + 断点续跑 + 守护"作为插件新工具(如 `insar_import_bulk`),
  输入清单/zip 目录/AOI,内部按日期分组调 ImportSentinel1Format。
- 同时解决:GROUPING 校验(同轨/同时相)、输出目录隔离、失败续跑、每时相 sar_modules 落盘位置。

### D14 🟡 GACOS 批处理产物无 `_geo` 后缀是否被干涉接受(待实测)
- 现象:批量 `run_gacos_bulk.bat` 导入 GACOS,产物命名 `20200104`(无 `_geo` 后缀),
  GUI 导入则生成 `20200104_geo`(SARscape 对 geocoded 产物的命名约定)。
- 对比验证:我的产物与历史 GUI 产物格式完全一致
  (product_type=GACOS ZDT、GeocodedImage=OK、ENVI float32 WGS84、覆盖 minqin2 区域),
  仅命名后缀不同;SARscape 识别 GACOS 靠 .sml/.hdr 内容而非文件名。
- **待实测**:干涉(Interferometric Process)的 WATER_VAVOUR_FILE_LIST 引用 `20200104`(无 _geo)
  是否能正常加载;若 SARscape 严格要求 `_geo`,则软链/重命名补后缀(不重新导入)。
- 测试时机:SLC 导入完成后,用 1-2 对干涉实测。
- 文件:`assets/experiment/bat/03_data_prep/run_gacos_bulk.bat`(命名约定可改进为输出 `_geo`)

---

## 五、经验与教训(沉淀,非缺陷)

### D9 ℹ️ GACOS 163 IMAP 风控
- 连接复用+30min 退避;断连自动重连,无需干预。SKILL.md 已记载。

### D10 ℹ️ "批处理只出 1 个 burst" 是误判(已撤回)
- 事实:批处理导入完整工作,单景需 30-40min(多 swath 28 burst 逐个生成);等待不足会误判。
- **教训**:判断导入产出不完整,必须等 trace 出现 END / slc_list 矢量 / 进程退出,或至少 40min+;
  勿凭中间产物数量下结论(与 D8 同理)。访问 SARscape 官方文档/模板是排查正道。

### 官方文档要点(import-sentinel1.htm)
- "The software checks which bursts intersects the AOI and only these bursts will be imported"(GUI check 机制)
- "_slc_list 是 burst 链接,SBAS 处理读它;.split_bursts 是实际数据"
- "Make mosaic same track: TRUE" 控制同轨多 SLC 拼接
- `_pwr` 由 "Make Power QL" 生成,用于目视检查(不参与计算)

---

## 修复优先级建议
1. 🔴 D1(complete.flag)→ 数据丢失级,最优先
2. 🟡 D5(SARSCAPE_LIB \auxiliary)→ 静默失败,任何新手都会踩
3. 🟡 D11+D13(SLC 导入按时相分组/批量工具)→ minqin2 实测核心痛点
4. 🟡 D2(地理编码卡片+onConfirmAll)→ 用户明确反馈
5. 🟡 D3/D6/D12(文档化 + flag 默认值)
6. 🔧 D7/D8(健壮性 + 文档)

## 验证方式(修后必测)
- D1:造失败场景确认不写 flag;成功后写
- D5:insar_pipeline 生成的 config.env 直接可跑(不手动改)
- D4:任意标准 NASADEM 命名能 merge
- D11:多时相清单批量导入,产物每时相一个 msc_slc_list,不混拼
- D2:卡片显示完整 geocode 参数,onConfirmAll 改值后实际执行生效