import { existsSync, readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { join } from "node:path";
import { defineTool } from "@deepseek-ai/dsh-tools";
import { getTemplate, validateBaseline } from "./templates.js";
import { computeStatus } from "./status.js";
import { runPython } from "./runner.js";
import { resolveScriptsDir, resolveExperimentDir, hasBundledScripts } from "./paths.js";
/** 通用输出：宽松 object schema + JSON 文本渲染（同 dsh-tool-goal 的 GOAL_OUTPUT） */
const JSON_OUTPUT = {
    schema: { type: "object", additionalProperties: true },
    render: (_args, value) => [{
            type: "text",
            text: JSON.stringify(value) ?? "",
        }],
};
/**
 * 注册三个工具到 host tools 注册表。
 * 依赖：ctx.tools（host 工具运行时）、registry。
 */
export function registerTools(ctx, deps) {
    ctx.tools.register(defineTool({
        name: "insar_run",
        description: "Run the ASF Sentinel-1 SLC downloader (bundled scripts/multi_download.py) with the given download inputs. Synchronous await: the download runs to completion — hours for large AOIs — so do not expect an immediate return. Provide either a manifest CSV (list) or an AOI + time range (aoi/start/end); pass pol/out to control polarization and destination. scriptDir is optional: defaults to the plugin's bundled scripts directory (auto-installed).",
        parameters: {
            scriptDir: { type: "string", description: "Optional. Directory containing multi_download.py. Defaults to the plugin's bundled scripts dir (installed with the plugin). Override with INSAR_GENIE_SCRIPTS env or this arg." },
            list: { type: "string", description: "Manifest CSV path (columns: date,frame,orbit,satellite,file). List-driven path; takes precedence over aoi/start/end." },
            aoi: { type: "string", description: "AOI shapefile/kml path. Search-driven path; requires start and end." },
            start: { type: "string", description: "Start date YYYYMMDD (search-driven path)." },
            end: { type: "string", description: "End date YYYYMMDD (search-driven path)." },
            pol: { type: "string", description: "Polarization(s), comma-separated, e.g. 'VV+VH,VV'. Defaults to 'VV+VH,VV'." },
            out: { type: "string", description: "Download output directory. Defaults to '<scriptDir>/sentinel1_data'." },
            pythonBin: { type: "string", description: "Python executable path. Defaults to 'python'." },
        },
        output: JSON_OUTPUT,
        async execute(input) {
            // 脚本目录：显式传值 > 环境变量 > 插件内置 assets/scripts（开箱即用）。
            // 注意：显式/环境变量 override 直接采用（即使当前不存在也作为 cwd 传给 runner——
            // 下载脚本路径由用户负责；仅当完全未提供且内置缺失时才报错）。
            const scriptDir = resolveScriptsDir(input.scriptDir);
            if (!input.scriptDir && !process.env.INSAR_GENIE_SCRIPTS && !hasBundledScripts()) {
                throw new Error("insar_run: multi_download.py not found. Pass scriptDir or set INSAR_GENIE_SCRIPTS.");
            }
            const args = ["multi_download.py"];
            if (input.list) {
                // 清单驱动（与 multi_download.py 的 "list 优先于搜索路径" 语义一致）
                args.push("--list", input.list);
            }
            else {
                if (!input.aoi || !input.start || !input.end) {
                    throw new Error("insar_run: provide either list (manifest CSV) or aoi + start + end (search-driven download)");
                }
                args.push("--aoi", input.aoi, "--start", input.start, "--end", input.end);
            }
            if (input.pol)
                args.push("--pol", input.pol);
            if (input.out)
                args.push("--out", input.out);
            // 同步 await：数小时级下载，不设超时（runPython timeoutMs 缺省为 undefined）
            const result = await runPython(input.pythonBin ?? "python", args, scriptDir);
            if (result.exitCode !== 0) {
                throw new Error(`insar_run failed: ${result.stderr}`);
            }
            return { ok: true, args, scriptDir, stdout: result.stdout };
        },
    }));
    ctx.tools.register(defineTool({
        name: "insar_status",
        description: "Read an experiment's current SBAS progress (connection graph → geocoding) from its status files.",
        parameters: {
            experimentId: { type: "string", required: true, description: "Experiment id from the registry." },
        },
        output: JSON_OUTPUT,
        execute(input) {
            const exp = deps.registry.get(input.experimentId);
            if (!exp)
                throw new Error(`experiment not found: ${input.experimentId}`);
            const auxXml = readFileSafe(join(exp.dir, "auxiliary.sml"), "");
            const stepXml = readFileSafe(join(exp.dir, "work", "work_step_performed.sml"), "");
            // guard 日志：探测候选路径（真实布局 guard 日志在 workDir/asf_experiment，不在实验目录附近）
            const guardLog = readFileSafe(resolveGuardLog(exp), "");
            // 注：status.ts 的参数名是 stepPerformedXml（简报原文 stepXml 与现有代码不一致，已适配）
            return Promise.resolve(computeStatus({ auxXml, stepPerformedXml: stepXml, guardLog }));
        },
    }));
    ctx.tools.register(defineTool({
        name: "insar_templates",
        description: "Return a terrain parameter template (mining/landslide/urban/desert/loess) or the terrain list.",
        parameters: {
            terrain: { type: "string", description: "Terrain type; omit to list all." },
        },
        output: JSON_OUTPUT,
        execute(input) {
            if (input.terrain) {
                // 注：getTemplate 返回 interface ExperimentParams，无隐式索引签名，故 as never 适配 Record<string, JsonValue>
                return Promise.resolve(getTemplate(input.terrain));
            }
            return Promise.resolve({
                terrains: ["mining", "landslide", "urban", "desert", "loess"],
            });
        },
    }));
    ctx.tools.register(defineTool({
        name: "insar_register",
        description: "Register a new experiment in the registry (ProgressPanel's experiment list / insar_status need an entry). Creates the record and returns its id.",
        parameters: {
            name: { type: "string", required: true, description: "Experiment display name, e.g. 'minqin1'." },
            terrain: { type: "string", required: true, description: "Terrain type: mining|landslide|urban|desert|loess." },
            dir: { type: "string", required: true, description: "Experiment root directory (e.g. G:\\minqin1_SBAS_processing)." },
            slcDir: { type: "string", description: "SLC data directory." },
            poeorbDir: { type: "string", description: "Precise orbit (POEORB) directory." },
            gacosDir: { type: "string", description: "GACOS atmospheric delay directory." },
            demDir: { type: "string", description: "DEM directory." },
            params: { type: "object", additionalProperties: true, description: "Experiment parameter snapshot (ExperimentParams shape)." },
        },
        output: JSON_OUTPUT,
        execute(input) {
            // 防呆：写入注册表前校验空间基线必须在 2-4%，杜绝 45% 事故
            if (input.params?.maxPercBaseline !== undefined) {
                const gate = validateBaseline(input.params.maxPercBaseline);
                if (!gate.ok) {
                    throw new Error(`insar_register: ${gate.message}`);
                }
            }
            const id = deps.registry.create({
                name: input.name,
                terrain: input.terrain,
                dir: input.dir,
                dataDirs: {
                    slc: input.slcDir ?? "",
                    poeorb: input.poeorbDir ?? "",
                    gacos: input.gacosDir ?? "",
                    dem: input.demDir ?? "",
                },
                params: input.params,
                status: "draft",
            });
            return Promise.resolve({ ok: true, experimentId: id });
        },
    }));
    ctx.tools.register(defineTool({
        name: "insar_list",
        description: "List registered experiments (id/name/terrain/status). ProgressPanel's experiment selector uses this.",
        parameters: {
            _unused: { type: "string", description: "Unused; kept to satisfy schema." },
        },
        output: JSON_OUTPUT,
        execute() {
            return Promise.resolve({
                experiments: deps.registry.list().map((e) => ({
                    id: e.id,
                    name: e.name,
                    terrain: e.terrain,
                    status: e.status,
                    dir: e.dir,
                })),
            });
        },
    }));
    ctx.tools.register(defineTool({
        name: "insar_experiment",
        description: "Run one SBAS processing step (SARscape batch) for an experiment by step key. The batch script lives in the plugin's bundled experiment/bat/<step>/ directory (auto-installed); the working dir is the experiment's own directory. Steps: import_slc / cg / interf / dem / gacos_bulk / gacos_import / inv1 / inv2 / geocode.",
        parameters: {
            experimentId: { type: "string", required: true, description: "Experiment id from the registry (its dir is the working directory)." },
            step: { type: "string", required: true, description: "Step key. One of: import_slc, cg, interf, dem, gacos_bulk, gacos_import, inv1, inv2, geocode." },
            experimentDir: { type: "string", description: "Optional override. Defaults to the experiment's registered dir. Override with INSAR_GENIE_EXPERIMENT env or this arg." },
            timeoutMs: { type: "number", description: "Optional timeout in ms for the batch run; defaults to no timeout (long SARscape steps)." },
        },
        output: JSON_OUTPUT,
        execute(input) {
            const exp = deps.registry.get(input.experimentId);
            if (!exp)
                throw new Error(`experiment not found: ${input.experimentId}`);
            const experimentRoot = resolveExperimentDir(input.experimentDir);
            const batName = stepToBat(input.step);
            const batPath = join(experimentRoot, "bat", batName);
            if (!existsSync(batPath)) {
                throw new Error(`insar_experiment: no batch for step '${input.step}' (looked at ${batPath})`);
            }
            return runBatch(batPath, exp.dir, input.timeoutMs).then((r) => {
                if (r.exitCode !== 0) {
                    throw new Error(`insar_experiment failed (${input.step}, exit ${r.exitCode}): ${r.stderr}`);
                }
                return { ok: true, step: input.step, bat: batName, experimentDir: exp.dir, stdout: r.stdout };
            });
        },
    }));
    ctx.tools.register(defineTool({
        name: "insar_settings",
        description: "Read the resolved insar-genie settings (credentials/paths after startup path probing). Returns the effective values; ENVI IDL + SARscape paths are auto-detected at plugin startup unless manually overridden.",
        parameters: {
            _unused: { type: "string", description: "Unused; kept to satisfy schema." },
        },
        output: JSON_OUTPUT,
        execute() {
            const s = deps.settings?.get();
            return Promise.resolve({
                earthdataUser: s?.earthdataUser ?? "",
                earthdataPassword: s?.earthdataPassword ?? "",
                gacosEmail: s?.gacosEmail ?? "",
                gacosImapAuthCode: s?.gacosImapAuthCode ?? "",
                enviIdl: s?.enviIdl ?? "",
                sarscapeLib: s?.sarscapeLib ?? "",
                workDir: s?.workDir ?? "",
                poeorbDir: s?.poeorbDir ?? "",
            });
        },
    }));
}
/** step 键 → bat 文件名（对应插件内置 experiment/bat/<子目录>/<bat>） */
function stepToBat(step) {
    const map = {
        import_slc: join("00_import", "run_import_slc.bat"),
        cg: join("01_connection_graph", "run_cg_final.bat"),
        interf: join("02_interferogram", "run_interf.bat"),
        dem: join("03_data_prep", "run_dem.bat"),
        gacos_bulk: join("03_data_prep", "run_gacos_bulk.bat"),
        gacos_import: join("03_data_prep", "run_gacos_import.bat"),
        inv1: join("03_inversion", "run_inv1.bat"),
        inv2: join("03_inversion", "run_inv2.bat"),
        geocode: join("04_geocode", "run_geocode.bat"),
    };
    const hit = map[step];
    if (!hit)
        throw new Error(`unknown step '${step}' (valid: ${Object.keys(map).join(", ")})`);
    return hit;
}
/** 执行 Windows batch（cmd /c），捕获输出（SARscape 步骤可能是长任务） */
function runBatch(batPath, cwd, timeoutMs) {
    return new Promise((resolve) => {
        const child = spawn("cmd", ["/c", batPath], { cwd, stdio: ["ignore", "pipe", "pipe"] });
        let stdout = "";
        let stderr = "";
        const cap = 64 * 1024;
        const push = (s, b) => (s + b.toString("utf8")).slice(-cap);
        child.stdout?.on("data", (b) => { stdout = push(stdout, b); });
        child.stderr?.on("data", (b) => { stderr = push(stderr, b); });
        const timer = timeoutMs !== undefined && timeoutMs > 0
            ? setTimeout(() => { child.kill("SIGTERM"); }, timeoutMs)
            : undefined;
        child.on("error", (e) => { if (timer)
            clearTimeout(timer); resolve({ exitCode: null, stdout, stderr: `${stderr}\n${String(e)}` }); });
        child.on("close", (code) => { if (timer)
            clearTimeout(timer); resolve({ exitCode: code, stdout, stderr }); });
    });
}
function readFileSafe(path, fallback) {
    try {
        return readFileSync(path, "utf8");
    }
    catch {
        return fallback;
    }
}
/**
 * 定位 guard 日志（sbas_guard.log）。真实布局中日志在 workDir/asf_experiment，
 * 实验目录可能与之分离（如实验在 G:\，日志在 D:\work\data\asf_experiment），
 * 故探测多个候选路径，返回第一个存在的；都不存在返回空串（调用方 readFileSafe 兜底）。
 */
function resolveGuardLog(exp) {
    // 候选 1：实验目录自身下的 asf_experiment
    const self = join(exp.dir, "asf_experiment", "sbas_guard.log");
    if (existsSync(self))
        return self;
    // 候选 2：实验目录父级下的 asf_experiment
    const parent = join(exp.dir, "..", "asf_experiment", "sbas_guard.log");
    if (existsSync(parent))
        return parent;
    // 候选 3：DSH_HOME 下的 asf_experiment（sbas_guard.py 用 WORK_DIR，此处尽力探测）
    if (process.env.DSH_HOME) {
        const home = join(process.env.DSH_HOME, "asf_experiment", "sbas_guard.log");
        if (existsSync(home))
            return home;
    }
    return "";
}
