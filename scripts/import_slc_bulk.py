#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SLC 批量导入驱动 —— 按下行清单按"时相(日期)"分组,每组调一次 ImportSentinel1Format。

设计原则(2026-08-30 minqin2 实测 + SARscape 官方文档):
  1. 拼接时机: MAKE_SLC_LIST_MOSAIC_FLAG=OK 时,
     同一轨道多个 SLC 一起输入 → 自动拼接成 msc_slc_list;
     单文件输入 → 不拼接,直接 slc_list。故【按日期分组,组内全部 zip 一起传】即可,
     脚本无需自己判断单/双帧,交给 SARscape。
  2. AOI: 传入研究区 shp → SARscape 自动检查 "which bursts intersects the AOI",
     只导入相交 burst(官方 import-sentinel1.htm)。
  3. 通用性: 输入任意清单 CSV(列: date,frame,orbit,satellite,file),任意轨道/帧组合;
     按时相(date)分组,组内同轨道才拼(不同轨道拆开,各导各的)。

用法:
  python import_slc_bulk.py --list 清单.csv --slc-dir <zip目录> --out <输出目录>
        [--aoi 研究区.shp] [--pol ONLY_VV_POL] [--envi-idl <envi_idl.exe>]
        [--sarscape-lib <SARscape auxiliary>] [--tmp <临时目录>]
        [--skip N] [--max N] [--only-date YYYYMMDD]
        [--threads N]   # 并行时相数,默认 1(顺序跑,避免 SARscape 锁冲突)
输出:
  每时相: <out>/sentinel1_135_<日期>_<时间>_IW_D_VV[_msc]_slc_list(.split_bursts 目录)
  日志:   <out>/import_slc_bulk.log + 每时相 sarbatch_import_<日期>.txt
"""

import argparse
import csv
import os
import subprocess
import sys
import time
from collections import OrderedDict

def log(msg, logfile):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    if logfile:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(line + "\n")

def group_by_date(rows, logfile):
    """按日期分组,组内校验同轨道;不同轨道拆组。返回 OrderedDict date -> [rows]"""
    groups = OrderedDict()
    for r in sorted(rows, key=lambda x: x["date"]):
        d = r["date"]
        orbit = r.get("orbit", "?")
        key = d
        # 同一日期如果混不同轨道,按轨道拆开(避免误拼)
        if key in groups:
            existing = groups[key][0].get("orbit", "?")
            if existing != orbit:
                alt = f"{d}_{orbit}"
                log(f"[GROUP] {d} 混轨道 {existing}/{orbit},拆分到 {alt}", logfile)
                key = alt
        groups.setdefault(key, []).append(r)
    return groups

def build_idl_cmd(zips, out_dir, aoi, pol, sar_lib, tmp_dir, date_label):
    """构造 ImportSentinel1Format 的 IDL 批处理命令(和 run_import_slc.bat 等价)。"""
    inp = "[" + ",".join(f"'{z}'" for z in zips) + "]"
    # 输出名: 与输入一一对应,out_dir/<zip名去掉扩展>(RENAME 规则会在其上补 sentinel1_135_... 吗?
    # 实测: 传具体输出名时,SARscape RENAME=OK 会自动重命名为 sentinel1_135_<日期>_..._slc_list;
    # 传目录则报 EC=70000。故按历史 bat: outs = out_dir + '/' + basename(zip, '.zip')
    outs = "[" + ",".join(f"'{out_dir}/{os.path.splitext(os.path.basename(z))[0]}'" for z in zips) + "]"
    # ROI 分支单独构造,避免引号嵌套问题
    if aoi:
        roi_branch = (
            "if strlen('" + aoi + "') gt 0 then c=o.SetParam(P+'INPUT_ROI_FILE','" + aoi
            + "') else c=1 & printf,u,'SETROI:',byte(c) & "
        )
    else:
        roi_branch = "c=1 & printf,u,'SETROI:',byte(c) & "
    idl = (
        "!PATH=!PATH+';'+'%s\\envi_extensions\\idl\\lib'+';'+'%s\\envi_extensions\\idl\\lib\\hook'"
        "+';'+'%s\\envi_extensions\\envi\\sarscape_local_sav' & "
        "resolve_routine,'sarscape_batch_init',/COMPILE_FULL_FILE & "
        "SARscape_Batch_Init,Temp_Directory='%s' & "
        "openw,u,'%s',/get_lun & "
        "o=obj_new('SARscapeBatch',Module='ImportSentinel1Format') & "
        "P='MAIN_IMPORT_SENTINEL1_CMD.' & "
        "printf,u,'OBJ:',byte(OBJ_VALID(o)) & "
        "r0=o.SetParam('GENERAL_PARAMETERS_CMD.RENAME_THE_FILE_USING_PARAMETERS_FLAG','OK') & "
        "printf,u,'SETRENAME:',byte(r0) & "
        "a=o.SetParam(P+'SARSCAPEENVIRONMENT','IDL_ENVI_ENV') & printf,u,'SETENV:',byte(a) & "
        "b=o.SetParam(P+'INPUT_FILE_LIST',%s) & printf,u,'SETIN:',byte(b) & "
        "%s"
        "d=o.SetParam(P+'OUTPUT_FILE_LIST',%s) & printf,u,'SETOUT:',byte(d) & "
        "e=o.SetParam(P+'GENERATE_IW_EW_POWER_FLAG','OK') & printf,u,'SETPWR:',byte(e) & "
        "f=o.SetParam(P+'CROSS_COPOLARIZATION_FLAG','%s') & printf,u,'SETPOL:',byte(f) & "
        "g=o.SetParam(P+'MAKE_SLC_LIST_MOSAIC_FLAG','OK') & printf,u,'SETMOS:',byte(g) & "
        "h=o.SetParam(P+'REBUILD_ALL_FLAG','NotOK') & printf,u,'SETRBL:',byte(h) & "
        "i=o.SetParam(P+'REMOVE_NOISE_FROM_LUT_FLAG','OK') & printf,u,'SETNOISE:',byte(i) & "
        "j=o.SetParam(P+'SKIP_SAMPLE_FLAG','NotOK') & printf,u,'SETSMP:',byte(j) & "
        "k=o.SetParam(P+'CONTINUE_WHEN_FAIL_FLAG','OK') & printf,u,'SETCF:',byte(k) & "
        "l=o.SetParam(P+'ONLY_REPORTS_FLAG','NotOK') & printf,u,'SETREP:',byte(l) & "
        "m=o.SetParam(P+'SKIP_ORBIT_WARNING_FLAG','NotOK') & printf,u,'SETORB:',byte(m) & "
        "n=o.SetParam(P+'EXIT_INSTEAD_WARNING_FLAG','NotOK') & printf,u,'SETEXIT:',byte(n) & "
        "v=o.VerifyParams() & printf,u,'VERIFY:',byte(v) & "
        "r=o.Execute() & printf,u,'EXECUTE:',byte(r) & "
        "free_lun,u & exit"
    ) % (
        sar_lib, sar_lib, sar_lib, tmp_dir, out_dir.replace("\\", "/") + "/sar_modules_" + date_label + ".txt",
        inp,
        roi_branch,
        outs,
        pol,
    )
    return idl

def run_one(env_idl, zips, out_dir, aoi, pol, sar_lib, tmp_dir, date_label, workdir, logfile):
    """为一个时相(组)执行导入;返回 (ok, sarbatch_path)。"""
    if not os.path.exists(workdir):
        os.makedirs(workdir, exist_ok=True)
    idl = build_idl_cmd(zips, out_dir, aoi, pol, sar_lib, tmp_dir, date_label)
    sarbatch = os.path.join(workdir, f"sarbatch_import_{date_label}.txt")
    # 注意: -quiet 下 IDL print 进 stdout 但被吞;执行状态看 sar_modules_<date>.txt 的 EXECUTE 字段
    cmd = [env_idl, "-quiet", "-e", idl]
    log(f"[RUN] {date_label}: {len(zips)} 景 -> {out_dir}", logfile)
    try:
        with open(sarbatch, "w", encoding="utf-8", errors="replace") as f:
            r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, timeout=7200)
        # 执行成功判据: EXECUTE:1 出现在 sar_modules_<date>.txt(Execute 返回 1)
        smod = os.path.join(out_dir, f"sar_modules_{date_label}.txt")
        ok = False
        if os.path.exists(smod):
            with open(smod, encoding="utf-8", errors="replace") as f:
                content = f.read()
            ok = "EXECUTE:1" in content or "EXECUTE:   1" in content
        log(f"[DONE] {date_label}: exit={r.returncode} execute_ok={ok}", logfile)
        return ok, sarbatch
    except subprocess.TimeoutExpired:
        log(f"[TIMEOUT] {date_label}: 超过 2 小时,跳过(可续跑)", logfile)
        return False, sarbatch
    except Exception as ex:
        log(f"[ERR] {date_label}: {ex}", logfile)
        return False, sarbatch

def main():
    ap = argparse.ArgumentParser(description="SLC 批量导入(按时相分组,通用)")
    ap.add_argument("--list", required=True, help="清单 CSV (date,frame,orbit,satellite,file)")
    ap.add_argument("--slc-dir", required=True, help="zip 所在目录")
    ap.add_argument("--out", required=True, help="导入输出目录")
    ap.add_argument("--aoi", default="", help="研究区 shp(可选,AOI 裁剪 burst)")
    ap.add_argument("--pol", default="ONLY_VV_POL", help="极化(默认 ONLY_VV_POL)")
    ap.add_argument("--envi-idl", default=r"C:\Program Files\Harris\ENVI56\IDL88\bin\bin.x86_64\envi_idl.exe")
    ap.add_argument("--sarscape-lib", default=r"C:\Program Files\SARMAP SA\SARscape\auxiliary")
    ap.add_argument("--tmp", default="", help="临时目录(默认 <out>/tmp)")
    ap.add_argument("--threads", type=int, default=1, help="并行时相数(默认 1,顺序跑防锁冲突)")
    ap.add_argument("--skip", type=int, default=0, help="跳过前 N 个时相(续跑)")
    ap.add_argument("--max", type=int, default=0, help="最多跑 N 个时相(0=全部)")
    ap.add_argument("--only-date", default="", help="只跑某日期 YYYYMMDD")
    args = ap.parse_args()

    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)
    tmp_dir = args.tmp or os.path.join(out_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    workdir = os.path.dirname(os.path.abspath(args.list))  # 与清单同目录放 sarbatch
    logfile = os.path.join(out_dir, "import_slc_bulk.log")

    with open(args.list, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        log("[ERR] 清单为空", logfile)
        return 1

    groups = group_by_date(rows, logfile)
    labels = list(groups.keys())
    log(f"[START] {len(labels)} 个时相,{len(rows)} 景,输出 {out_dir}", logfile)

    start_i = args.skip
    end_i = len(labels) if args.max == 0 else min(start_i + args.max, len(labels))
    if args.only_date:
        od = args.only_date.replace("-", "")
        matches = [i for i, k in enumerate(labels) if k.replace("-", "").startswith(od)]
        if not matches:
            log(f"[ERR] 未找到日期 {args.only_date}", logfile)
            return 1
        start_i, end_i = matches[0], matches[0] + 1
        labels = [labels[matches[0]]]

    ok_count = fail_count = skipped = 0
    for i in range(start_i, end_i):
        key = labels[i]
        group = groups[key]
        date_label = key.replace("-", "")
        # 已完成跳过: 产物目录存在即视为完成(REBUILD_ALL=NotOK 语义)
        msc_glob_pattern = f"sentinel1_*{date_label}*_IW_D_VV*slc_list*"
        import glob as _glob
        done = [p for p in _glob.glob(os.path.join(out_dir, msc_glob_pattern))
                if not p.endswith((".kml", ".shp", ".shx", ".dbf", ".prj", ".sml"))]
        if done:
            log(f"[SKIP] {key}: 已存在产物 {os.path.basename(done[0])},跳过", logfile)
            skipped += 1
            continue
        zips = [os.path.join(args.slc_dir, r["file"]) for r in group]
        missing = [z for z in zips if not os.path.exists(z)]
        if missing:
            log(f"[SKIP] {key}: 缺 zip {missing}", logfile)
            fail_count += 1
            continue
        # 同一时相多个 zip:确认同轨道(组已按轨道拆过)
        date_label = key.replace("-", "")
        ok, sarbatch = run_one(
            args.envi_idl, zips, out_dir, args.aoi, args.pol,
            args.sarscape_lib, tmp_dir, date_label, workdir, logfile,
        )
        if ok:
            ok_count += 1
        else:
            fail_count += 1
            # 及时反馈失败,不盲目继续后续时相(常见原因是 SARscape 环境问题)
            log(f"[NOTE] {date_label} 执行未确认成功,续跑请加 --skip {i+1} 或 --only-date {date_label}", logfile)

    log(f"[DONE] 完成 {ok_count} 成功 / {fail_count} 未确认 / {skipped} 跳过(已完成),共 {end_i - start_i} 时相", logfile)
    return 0 if fail_count == 0 else 2

if __name__ == "__main__":
    sys.exit(main())