"""SBAS-InSAR 全链路环境自检。

用法（配置好 config.env 后）：
    python check_environment.py

逐项检查并输出 [OK]/[WARN]/[FAIL] 报告，任何 FAIL 退出码非 0。
检查项：
  1. config.env 是否已配置（非模板）
  2. Python 版本 / 依赖包
  3. 关键路径存在性（工作目录/数据/输出/DEM/GACOS）
  4. 软件环境（ENVI / IDL / SARscape）
  5. 下载/分析脚本可导入性
  6. 磁盘空间（结果盘）
  7. 通知配置（可选）
"""

import importlib.util
import os
import shutil
import sys

# Windows GBK 控制台兼容
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config_loader

CFG = config_loader.load_config()
RESULTS = []  # (level, category, message, hint)


def check(level, category, ok, message, hint=""):
    RESULTS.append((level, category, ok, message, hint))


# ---------- 1. config.env ----------
if not config_loader.CONFIG_FILE or not os.path.exists(config_loader.CONFIG_FILE):
    check(
        "FAIL",
        "config",
        False,
        "config.env 不存在",
        "复制模板: copy config.example.env config.env，然后编辑路径",
    )
else:
    check("OK", "config", True, f"config.env 已找到 ({config_loader.CONFIG_FILE})")


def is_template(v):
    return not v or "your" in str(v).lower() or "example" in str(v).lower() or "/path/to" in str(v)


# ---------- 2. Python / 依赖 ----------
PY_VER = sys.version_info
check(
    "OK",
    "python",
    PY_VER >= (3, 10),
    f"Python {PY_VER.major}.{PY_VER.minor}（需 >=3.10）",
    "请安装 Python 3.10+",
)

DEPS = ["asf_search", "shapefile", "shapely", "defusedxml", "matplotlib", "earthaccess"]
for dep in DEPS:
    ok = importlib.util.find_spec(dep) is not None
    check(
        "OK" if ok else "FAIL",
        "pip",
        ok,
        f"{dep}（pyshp 的模块名是 shapefile）" if dep == "shapefile" else dep,
        "pip install " + dep,
    )
# 可选依赖
for dep, note in [("playwright", "GACOS 收件需要"), ("PIL", "覆盖图可选")]:
    ok = importlib.util.find_spec(dep) is not None
    check("OK" if ok else "WARN", "pip", ok, f"{dep}（可选: {note}）", "pip install " + dep)


# ---------- 3. 关键路径 ----------
def check_path(cfg_key, label, kind="dir", optional=False):
    v = CFG.get(cfg_key, "")
    if is_template(v):
        check(
            "FAIL" if not optional else "WARN",
            "path",
            False,
            f"{label}: 未配置或为模板值 ({cfg_key}={v!r})",
            f"在 config.env 设置 {cfg_key}",
        )
        return
    exists = os.path.exists(v) if kind == "dir" else os.path.isfile(v)
    if exists:
        check("OK", "path", True, f"{label}: {v}")
    elif optional:
        check("WARN", "path", True, f"{label}: 不存在（可选）: {v}", f"检查 {cfg_key}")
    else:
        check("FAIL", "path", False, f"{label}: 不存在: {v}", f"确认 {cfg_key} 指向真实路径")


check_path("WORK_DIR", "工作目录")
check_path(
    "SLC_DATA",
    "SLC 数据目录",
    optional=True,
)  # 未下载数据前可空，下载工具会创建
check_path("RESULT_ROOT", "SARscape 输出盘", optional=True)
check_path("DEM_FILE", "DEM 文件", kind="file", optional=True)
check_path("GACOS_LIST", "GACOS 列表", kind="file", optional=True)
check_path("SAR_MODULES", "SARscape 参数输出文件", kind="file", optional=True)
check_path("SKILL_DIR", "技能目录（asf 工具）", kind="dir", optional=True)


# ---------- 4. 软件环境（ENVI / IDL / SARscape）----------
def check_soft(cfg_key, label, kind="file"):
    v = CFG.get(cfg_key, "")
    if is_template(v):
        check(
            "FAIL",
            "soft",
            False,
            f"{label}: 未配置 ({cfg_key})",
            f"在 config.env 设置 {cfg_key}（ENVI/SARscape 安装路径）",
        )
        return
    exists = os.path.exists(v)
    if exists:
        check("OK", "soft", True, f"{label}: {v}")
    else:
        check(
            "FAIL",
            "soft",
            False,
            f"{label}: 找不到: {v}",
            f"确认 ENVI/SARscape 已安装且 {cfg_key} 正确",
        )


check_soft("ENVI_IDL", "ENVI+IDL 可执行文件 (envi_idl.exe)")
check_soft("IDL_EXE", "IDL 可执行文件 (idl.exe)")
check_soft("SARSCAPE_LIB", "SARscape 扩展库目录", kind="dir")

# SARscape 关键扩展子目录
sc = CFG.get("SARSCAPE_LIB", "")
if sc and os.path.isdir(sc):
    key_subs = ["envi_extensions"]  # SARSCAPE_LIB 本身即 auxiliary 根
    missing = [s for s in key_subs if not os.path.exists(os.path.join(sc, s))]
    if missing:
        check(
            "FAIL",
            "soft",
            False,
            f"SARscape 扩展子目录缺失: {missing}",
            "确认 SARSCAPE_LIB 指向 SARscape auxiliary 根目录（含 envi_extensions/）",
        )
    else:
        check("OK", "soft", True, "SARscape 扩展子目录完整")


# ---------- 5. 脚本可导入性 ----------
def check_import(mod_name, path, label):
    try:
        spec = importlib.util.spec_from_file_location(mod_name, path)
        if spec is None or spec.loader is None:
            raise ImportError("无法加载")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        check("OK", "script", True, f"{label} 可导入")
    except Exception as e:
        check("FAIL", "script", False, f"{label} 导入失败: {e}", "确认 pip 依赖已装（见上）")


scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if os.path.isdir(scripts_dir):
    for mod, fname, label in [
        ("_dc", "download.py", "download.py"),
        ("_an", "analysis.py", "analysis.py"),
        ("_mu", "multi_download.py", "multi_download.py"),
    ]:
        p = os.path.join(scripts_dir, fname)
        if os.path.exists(p):
            check_import(mod, p, label)


# ---------- 6. 磁盘空间（结果盘）----------
disk_root = CFG.get("RESULT_ROOT") or CFG.get("TMP_DIR") or "."
try:
    free = shutil.disk_usage(disk_root).free / 1024**3
    if free > 20:
        check("OK", "disk", True, f"结果盘剩余 {free:.0f}GB（{disk_root}）")
    elif free > 5:
        check("WARN", "disk", True, f"结果盘剩余 {free:.0f}GB（建议 >20GB）: {disk_root}")
    else:
        check(
            "FAIL",
            "disk",
            False,
            f"结果盘空间不足 {free:.0f}GB: {disk_root}",
            "换大容量磁盘，SBAS 输出可达几十 GB",
        )
except Exception as e:
    check("WARN", "disk", True, f"磁盘检查失败: {e}")


# ---------- 7. 通知配置（可选）----------
for name, fname in [("微信通知", "notify_config.json"), ("邮件通知", "mail_config.json")]:
    p = os.path.join(CFG.get("WORK_DIR", "."), "asf_experiment", fname)
    if os.path.exists(p):
        check("OK", "notify", True, f"{name}配置存在: {fname}")
    else:
        check("WARN", "notify", True, f"{name}未配置（可选，守护仍可运行）: {fname}")


# ---------- 报告 ----------
print("=" * 56)
print(" SBAS-InSAR 全链路环境自检报告")
print("=" * 56)
fails = warns = 0
for level, cat, ok, msg, hint in RESULTS:
    mark = {"OK": "[ OK ]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[level]
    print(f"{mark} [{cat:<6}] {msg}")
    if hint and not ok:
        print(f"          -> {hint}")
    if level == "FAIL":
        fails += 1
    elif level == "WARN":
        warns += 1

print("=" * 56)
print(f" 结果: {len(RESULTS)} 项检查 | FAIL={fails} WARN={warns} OK={len(RESULTS) - fails - warns}")
if fails:
    print(" !! 环境未就绪，请按上方 -> 提示修复后重跑")
elif warns:
    print(" !! 环境可用，但有可选项未就绪（不影响核心链路）")
else:
    print(" == 环境就绪，可运行全链路自动化 ==")
    print()
    print("使用指南（对 AI 说）：")
    print("  1. 配置凭证:  “配置 ASF 账号密码”")
    print(
        "  2. 下载数据:  “从 ASF 下载哨兵数据，区域 研究区.shp，时间 YYYYMMDD 至 YYYYMMDD，VV+VH”"
    )
    print("  3. 配套数据:  “下载配套数据”")
    print("  4. 开始实验:  “开始 SBAS 实验”")
    print("  5. 查进度:    “实验进展如何”")
print("=" * 56)
sys.exit(1 if fails else 0)
