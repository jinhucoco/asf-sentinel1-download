"""Sentinel-1 精密轨道文件（POEORB）下载器。

对应规则：SLC 获取时刻（UTC）必须落在 POEORB 的 validity 区间内
（文件名 _V<起>T<起时>_<止>T<止时> 即区间）。

用法:
  python poeorb_download.py --list 下载清单.csv --out ./poeorb
  python poeorb_download.py --data-dir ./sentinel1_data --out ./poeorb   # 扫描 SLC 目录

清单格式: date,frame,orbit,satellite,file（file 列含 S1A_IW_SLC__1SDV_20200104T231040_...）
"""

import argparse
import csv
import glob
import os
import re
import time
import urllib.request
import zipfile

BASE = "https://step.esa.int/auxdata/orbits/Sentinel-1/POEORB"
SAT_MAP = {
    "Sentinel-1A": "S1A",
    "Sentinel-1B": "S1B",
    "Sentinel-1C": "S1C",
    "S1A": "S1A",
    "S1B": "S1B",
    "S1C": "S1C",
}


def log(msg, logfile):
    line = f"[{time.strftime('%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    if logfile:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def fetch_dir(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    with urllib.request.urlopen(req, timeout=60) as r:
        html = r.read().decode("utf-8", "replace")
    return re.findall(r'href="([^"]+\.EOF\.zip)"', html)


def find_eof(sat, ymd, hms):
    """返回覆盖 (ymd hms) UTC 时刻的 POEORB 文件名"""

    y, m = ymd[:4], ymd[4:6]
    url = f"{BASE}/{sat}/{y}/{m}/"
    try:
        files = fetch_dir(url)
    except Exception as e:
        log(f"  目录访问失败 {url}: {str(e)[:60]}", None)
        return None

    target = f"{ymd}T{hms}"
    for f in files:
        mm = re.search(r"_V(\d{8}T\d{6})_(\d{8}T\d{6})\.EOF", f)
        if mm and mm.group(1) <= target <= mm.group(2):
            return f
    return None


def download_eof(url, dest_zip, dest_eof):
    if os.path.exists(dest_eof) and os.path.getsize(dest_eof) > 100:
        return "skip"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest_zip, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    with zipfile.ZipFile(dest_zip) as z:
        # 防 zip 路径穿越
        for m in z.namelist():
            if m.startswith("/") or ".." in m.split("/") or (":" in m.split("/")[0]):
                raise ValueError(f"不安全成员: {m}")
        z.extractall(os.path.dirname(dest_eof))
    os.remove(dest_zip)
    return "ok"


def collect_timepoints(rows):
    """从清单行提取唯一 (卫星, 日期, 时刻)"""
    seen = {}
    for r in rows:
        fname = r.get("file", "")
        sat = SAT_MAP.get(r.get("satellite", "") or fname.split("_")[0])
        m = re.search(r"_(\d{8})T(\d{6})", fname)
        if not sat or not m:
            continue
        key = (sat, m.group(1))
        if key not in seen:
            seen[key] = m.group(2)
    return seen


def main():
    ap = argparse.ArgumentParser(description="POEORB 精密轨道下载")
    ap.add_argument("--list", help="下载清单 CSV（date,frame,orbit,satellite,file）")
    ap.add_argument("--data-dir", help="SLC 数据目录（自动扫描 zip 文件名）")
    ap.add_argument("--out", default="./poeorb", help="输出目录")

    args = ap.parse_args()
    if not args.list and not args.data_dir:
        ap.error("需要 --list 或 --data-dir")

    os.makedirs(args.out, exist_ok=True)
    logfile = os.path.join(args.out, "poeorb.log")

    rows = []
    if args.list:
        with open(args.list, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    else:
        for z in glob.glob(os.path.join(args.data_dir, "*.zip")):
            rows.append(
                {"file": os.path.basename(z), "satellite": os.path.basename(z).split("_")[0]}
            )

    timepoints = collect_timepoints(rows)
    log(f"待匹配时相: {len(timepoints)} 个", logfile)

    ok = fail = 0
    for i, ((sat, ymd), hms) in enumerate(timepoints.items(), 1):
        eof = find_eof(sat, ymd, hms)
        if not eof:
            log(
                f"[{i}/{len(timepoints)}] [FAIL] 未找到 {sat} {ymd}T{hms} 的 POEORB（可稍后重跑补漏）",
                logfile,
            )
            fail += 1

            time.sleep(1)
            continue
        y, m = ymd[:4], ymd[4:6]
        url = f"{BASE}/{sat}/{y}/{m}/{eof}"
        dest_eof = os.path.join(args.out, eof.replace(".zip", ""))
        try:
            st = download_eof(url, os.path.join(args.out, eof), dest_eof)
            ok += 1

            log(f"[{i}/{len(timepoints)}] [{st.upper()}] {sat} {ymd} -> {eof[:60]}", logfile)
        except Exception as e:
            fail += 1
            log(f"[{i}/{len(timepoints)}] [FAIL] {sat} {ymd}: {str(e)[:70]}", logfile)
        time.sleep(1)

    log(f"=== POEORB 完成: 成功 {ok} / 失败 {fail}（失败可重跑补漏）===", logfile)


if __name__ == "__main__":
    main()
