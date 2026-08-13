"""环境配置向导：AI-Agent 调用来完成 config.env 的生成/更新。

用法（AI 对话中执行，或手动）：
    python setup_env.py           # 交互式：自动探测路径 + 逐项确认
    python setup_env.py --auto    # 全自动：探测值直接写入（AI 调用）

功能：
  1. 自动探测常见路径（ENVI / IDL / SARscape / 数据盘 / 工作目录）
  2. 基于模板生成 config.env（保留已有配置项）
  3. 交互确认每项（回车采用探测值，输入自定义，skip 跳过）
  4. 完成后提示运行 check_environment.py 自检
"""

import glob
import os
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLE = os.path.join(HERE, "config.example.env")
TARGET = os.path.join(HERE, "config.env")

AUTO = "--auto" in sys.argv


# ---------- 路径探测 ----------
def probe_envi_idl():
    pats = [
        r"C:\Program Files\Harris\ENVI*\IDL*\bin\bin.x86_64\envi_idl.exe",
        r"C:\Program Files\Harris\ENVI*\IDL*\bin\bin.x86_64\idl.exe",
        r"D:\Program Files\Harris\ENVI*\IDL*\bin\bin.x86_64\envi_idl.exe",
    ]
    for p in pats:
        hits = sorted(glob.glob(p))
        if hits:
            return hits[0]
    return ""


def probe_sarscape():
    for p in [
        r"C:\Program Files\SARMAP SA\SARscape\auxiliary",
        r"D:\Program Files\SARMAP SA\SARscape\auxiliary",
    ]:
        if os.path.isdir(p):
            return p
    return ""


def probe_disk():
    """返回剩余空间最大的盘（如 G:/），或 C:/"""
    best, best_free = "", -1
    for letter in "CDEFGH":
        d = letter + ":/"
        try:
            free = shutil.disk_usage(d).free
            if free > best_free:
                best, best_free = d, free
        except OSError:
            continue
    return best or "C:/"


def probe_slc():
    """常见 SLC 数据目录"""
    for p in [r"E:/gulangoutdata2", r"D:/sentinel1_data", r"D:/sar_data"]:
        if os.path.isdir(p):
            return p
    return ""


# ---------- 读取现有配置 ----------
def read_existing():
    cfg = {}
    if os.path.exists(TARGET):
        for line in open(TARGET, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg


def read_template():
    cfg = {}
    if os.path.exists(EXAMPLE):
        for line in open(EXAMPLE, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    return cfg


# ---------- 交互确认 ----------
def ask(key, label, probe, existing, required=True):
    current = existing.get(key, "")
    default = probe() if callable(probe) else probe
    default = current or default
    if AUTO:
        val = default
        if not val and required:
            val = input(f"[!] 无法探测 {label}，请输入: ").strip()
    else:
        hint = f"（探测: {default}）" if default else ""
        ans = input(f"{label} [{default}]{hint} 回车采用 / 输入自定义 / skip 跳过: ").strip()
        if ans.lower() == "skip":
            return None
        val = ans or default
    if not val and required:
        print(f"[X] {label} 不能为空")
        sys.exit(1)
    return val


def main():
    print("=" * 56)
    print(" SBAS-InSAR 环境配置向导")
    print("=" * 56)
    if not os.path.exists(EXAMPLE):
        print("[X] 找不到 config.example.env 模板:", EXAMPLE)
        sys.exit(1)

    existing = read_existing()
    tpl = read_template()
    disk = probe_disk()

    print(
        f"[..] 探测结果: 主数据盘={disk}, ENVI={probe_envi_idl() or '未找到'}, "
        f"SARscape={probe_sarscape() or '未找到'}"
    )
    print("     （已存在配置将作为默认值，可修改）" if existing else "     （全新配置）")
    print()

    fields = [
        ("WORK_DIR", "工作目录（数据/运行副本）", lambda: "D:/work/data", True),
        ("RESULT_ROOT", "SARscape 输出盘", lambda: disk + "insar_result", True),
        ("TMP_DIR", "临时目录", lambda: disk + "insar_result/tmp", True),
        ("SLC_DATA", "SLC 数据目录", probe_slc, False),
        ("DEM_FILE", "DEM 文件", lambda: "", False),
        ("GACOS_LIST", "GACOS 列表", lambda: "", False),
        ("SAR_MODULES", "SARscape 参数输出", lambda: "D:/work/data/sar_modules.txt", False),
        ("INTERF_BAT", "干涉 bat 相对路径", lambda: "bat/02_interferogram/run_interf.bat", True),
        ("ENVI_IDL", "ENVI+IDL 可执行", probe_envi_idl, True),
        (
            "IDL_EXE",
            "IDL 可执行",
            lambda: probe_envi_idl().replace("envi_idl.exe", "idl.exe") if probe_envi_idl() else "",
            False,
        ),
        ("SARSCAPE_LIB", "SARscape 扩展库", probe_sarscape, True),
        ("SKILL_DIR", "技能安装目录", lambda: "", False),
    ]

    out = dict(tpl)
    out.update(existing)
    for key, label, probe, req in fields:
        val = ask(key, label, probe, existing, required=req)
        if val is not None:
            out[key] = val

    with open(TARGET, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 由 setup_env.py 生成（可用 config.example.env 对照）\n")
        f.writelines(f"{k}={out.get(k, tpl[k])}\n" for k in tpl)
        for k, v in out.items():
            if k not in tpl:
                f.write(f"{k}={v}\n")
    print()
    print("[OK] 已写入:", TARGET)
    print()
    print("下一步（AI 继续）:")
    print("  python experiment/check_environment.py   # 自检 27 项")
    print("  有 [FAIL] 按提示修复后重跑，全部 [OK] 即可开始实验")


if __name__ == "__main__":
    main()
