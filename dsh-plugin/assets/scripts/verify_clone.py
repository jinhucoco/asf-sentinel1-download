"""全链路全新用户验证脚本。

模拟"用户 clone 仓库后"的完整验证，覆盖：
  A. 仓库完整性：文件结构 / 无敏感文件 / 无硬编码路径
  B. 代码健康：全部 .py 语法、bat 变量引用完整性
  C. 环境自检：调用 experiment/check_environment.py
  D. 下载工具：CLI --help 可运行、模块 import 链
  E. 实验 bat（非破坏性）：config 读取 / 关键文件存在（不实际跑 SARscape）

用法（仓库根目录）：
    python scripts/verify_clone.py
"""

import os
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = []


def check(level, cat, ok, msg, hint=""):
    RESULTS.append((level, cat, ok, msg, hint))


# ---------- 收集文件清单 ----------
def walk(reldir, exts):
    out = []
    base = os.path.join(REPO, reldir)
    for dp, _, fn in os.walk(base):
        for f in fn:
            if f.endswith(exts) and "__pycache__" not in dp:
                out.append(os.path.join(dp, f))
    return sorted(out)


py_files = walk(".", (".py",))
bat_files = walk("experiment", (".bat",))
scripts_py = walk("scripts", (".py",))

# ---------- A. 仓库完整性 ----------
print("=" * 56)
print(" A. 仓库完整性")
print("=" * 56)

# A1 关键文件
required = [
    "SKILL.md",
    "README.md",
    "package.json",
    "install.sh",
    "config.example.json",
    "scripts/requirements.txt",
    "scripts/download.py",
    "scripts/analysis.py",
    "scripts/multi_download.py",
    "experiment/config.example.env",
    "experiment/config_loader.py",
    "experiment/check_environment.py",
    "experiment/README.md",
    "experiment/bat/01_connection_graph/run_cg_final.bat",
    "experiment/bat/02_interferogram/run_interf.bat",
]
for f in required:
    ok = os.path.exists(os.path.join(REPO, f))
    check("OK" if ok else "FAIL", "repo", ok, f"关键文件: {f}", "仓库不完整，请检查 clone")

# A2 敏感文件必须不存在
forbidden = ["config.json", "notify_config.json", "mail_config.json", "processed_mail.json"]
leaked = []
for dp, _, fn in os.walk(REPO):
    if ".git" in dp or "__pycache__" in dp:
        continue
    for f in fn:
        if f in forbidden or re.match(r"dl_(token|cookie|url|auth)", f):
            leaked.append(os.path.join(dp, f))
check(
    "OK" if not leaked else "FAIL",
    "repo",
    not leaked,
    "无敏感文件" if not leaked else f"⚠️ 发现敏感文件: {leaked}",
    "敏感配置（凭证/token）绝不能入库",
)

# A3 bat 无硬编码盘符路径
bad_hard = []
for b in bat_files:
    s = open(b, encoding="utf-8", errors="replace").read()
    left = set(re.findall(r'[A-Z]:\\[^ "\'%\n]+', s))
    if left:
        bad_hard.append((os.path.relpath(b, REPO), left))
check(
    "OK" if not bad_hard else "FAIL",
    "repo",
    not bad_hard,
    f"{len(bat_files)} 个 bat 无硬编码路径" if not bad_hard else f"硬编码残留: {bad_hard[:3]}",
    "所有路径应从 config.env 读取",
)

# ---------- B. 代码健康 ----------
print("=" * 56)
print(" B. 代码健康")
print("=" * 56)

# B1 全部 py 语法
bad_syntax = []
for p in py_files:
    try:
        compile(open(p, encoding="utf-8", errors="replace").read(), p, "exec")
    except SyntaxError as e:
        bad_syntax.append(f"{os.path.relpath(p, REPO)}: {e}")
check(
    "OK" if not bad_syntax else "FAIL",
    "code",
    not bad_syntax,
    f"{len(py_files)} 个 .py 语法检查" + ("" if not bad_syntax else f" 失败: {bad_syntax[:3]}"),
    "修复语法错误",
)

# B2 bat 变量引用完整性（%VAR% 都应在 config.example.env 定义）
cfg_keys = set()
for line in open(os.path.join(REPO, "experiment/config.example.env"), encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        cfg_keys.add(line.split("=", 1)[0].strip())
# 额外允许的内置/循环变量
builtin_ok = {
    "ERRORLEVEL",
    "PATH",
    "TEMP",
    "TMP",
    "CD",
    "DATE",
    "TIME",
    "RANDOM",
    "CMDCMDLINE",
    "PROCESSOR_ARCHITECTURE",
    "OS",
    "USERNAME",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "PATHEXT",
    "COMSPEC",
    "PROGRAMFILES",
    "PROGRAMDATA",
    "WINDIR",
    "SYSTEMROOT",
    "NUMBER_OF_PROCESSORS",
    "a",
    "b",
    "x",
    "y",
    "i",
}
bad_var = []
for b in bat_files:
    s = open(b, encoding="utf-8", errors="replace").read()
    for v in set(re.findall(r"%([A-Za-z_][A-Za-z0-9_]*)%", s)):
        if v not in cfg_keys and v not in builtin_ok and v != "a" and v != "b":
            # 排除 for 循环变量（%%a 等已转义为 %% 不会匹配到，此处兜底）
            if v not in ("a", "b"):
                bad_var.append((os.path.relpath(b, REPO), v))
check(
    "OK" if not bad_var else "FAIL",
    "code",
    not bad_var,
    f"{len(bat_files)} 个 bat 变量引用完整" if not bad_var else f"未定义变量: {bad_var[:5]}",
    "bat 引用的变量必须在 config.example.env 定义",
)

# ---------- C. 环境自检 ----------
print("=" * 56)
print(" C. 环境自检 (check_environment.py)")
print("=" * 56)
env_check = os.path.join(REPO, "experiment", "check_environment.py")
if os.path.exists(env_check):
    r = subprocess.run(
        [sys.executable, env_check],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = r.stdout.strip().split("\n")
    summary = [l for l in out if "结果:" in l or "就绪" in l or "未就绪" in l]
    check(
        "OK" if r.returncode == 0 else "FAIL",
        "env",
        r.returncode == 0,
        f"环境自检退出码={r.returncode} " + (" ".join(summary) if summary else ""),
    )
else:
    check("FAIL", "env", False, "check_environment.py 缺失")

# ---------- D. 下载工具 ----------
print("=" * 56)
print(" D. 下载工具")
print("=" * 56)


def run_cli(script, args):
    p = os.path.join(REPO, "scripts", script)
    r = subprocess.run(
        [sys.executable, p] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return r.returncode == 0


cli_ok = {}
for script, args in [
    ("download.py", ["--help"]),
    ("analyze.py", ["--help"]),
    ("robust_download.py", ["--help"]),
    ("multi_download.py", ["--help"]),
    ("poeorb_download.py", ["--help"]),
    ("dem_download.py", ["--help"]),
    ("gacos_download.py", ["--help"]),
    ("gacos_fetch.py", ["--help"]),
]:
    ok = run_cli(script, args)
    cli_ok[script] = ok
    check("OK" if ok else "FAIL", "tool", ok, f"CLI 可运行: {script} --help")

# import 链
import_ok = True
try:
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import download, analysis, analyze, robust_download, multi_download  # noqa
    from analysis import check_per_date_coverage  # noqa
except Exception as e:
    import_ok = False
    import_err = str(e)
check(
    "OK" if import_ok else "FAIL",
    "tool",
    import_ok,
    "scripts 模块 import 链正常" if import_ok else f"import 失败: {import_err}",
    "确认 pip 依赖已安装",
)

# ---------- E. 实验 bat（非破坏性）----------
print("=" * 56)
print(" E. 实验 bat（非破坏性检查）")
print("=" * 56)
# config.env 存在则验证路径
cfg = {}
cfg_p = os.path.join(REPO, "experiment", "config.env")
if os.path.exists(cfg_p):
    for line in open(cfg_p, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    check("OK", "bat", True, f"config.env 已配置（{len(cfg)} 项）")
    # 关键路径存在性
    for key, label, kind in [
        ("WORK_DIR", "工作目录", "dir"),
        ("RESULT_ROOT", "输出盘", "dir"),
        ("ENVI_IDL", "ENVI", "file"),
        ("SARSCAPE_LIB", "SARscape", "dir"),
    ]:
        v = cfg.get(key, "")
        if not v:
            continue
        exists = os.path.isdir(v) if kind == "dir" else os.path.isfile(v)
        check(
            "OK" if exists else "WARN",
            "bat",
            True if exists else True,
            f"{label} 路径 {'存在' if exists else '不存在'}: {v}",
        )
else:
    check(
        "WARN",
        "bat",
        True,
        "config.env 未创建（用户需 copy config.example.env config.env）",
        "全新用户首次运行前必须复制模板",
    )

# ---------- 汇总 ----------
print("=" * 56)
print(" 验证汇总")
print("=" * 56)
fails = warns = 0
for level, cat, ok, msg, hint in RESULTS:
    mark = {"OK": "[ OK ]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[level]
    print(f"{mark} [{cat:<4}] {msg}")
    if hint and not ok:
        print(f"          -> {hint}")
    if level == "FAIL":
        fails += 1
    elif level == "WARN":
        warns += 1
print("=" * 56)
print(f" 结果: {len(RESULTS)} 项 | FAIL={fails} WARN={warns} OK={len(RESULTS) - fails - warns}")
if fails:
    print(" !! 仓库存在必须修复的问题，详见上方 FAIL 项")
elif warns:
    print(" == 仓库可用，WARN 项为可选项（数据/凭证需用户自备）==")
else:
    print(" == 全部通过：全新用户配置 config.env 后即可运行 ==")
print("=" * 56)
sys.exit(1 if fails else 0)
