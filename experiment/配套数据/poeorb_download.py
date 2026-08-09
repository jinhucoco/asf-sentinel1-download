# -*- coding: utf-8 -*-
"""Sentinel-1 精密轨道文件（POEORB）下载器。
对应规则：SLC 获取时刻（UTC）必须落在 POEORB 的 validity 区间内。
用法: python poeorb_download.py [--limit N]
"""
import csv, os, re, sys, time, zipfile, argparse, urllib.request

BASE = 'https://step.esa.int/auxdata/orbits/Sentinel-1/POEORB'
LIST = 'D:/work/data/asf_experiment/download_aligned.csv'
OUT = 'D:/work/data/配套数据/POEORB'
LOG = os.path.join(OUT, 'poeorb.log')

SAT_MAP = {'Sentinel-1A': 'S1A', 'Sentinel-1B': 'S1B', 'Sentinel-1C': 'S1C'}

def log(msg):
    line = f'[{time.strftime("%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def fetch_dir(url):
    """抓取 HTTP 目录索引，返回文件名列表"""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        html = r.read().decode('utf-8', 'replace')
    return re.findall(r'href="([^"]+\.EOF\.zip)"', html)

def validity_of(fname):
    """从 EOF 文件名解析 validity 区间 (start_ts, end_ts)"""
    m = re.search(r'_V(\d{8}T\d{6})_(\d{8}T\d{6})\.EOF', fname)
    if not m:
        return None, None
    return m.group(1), m.group(2)

def find_eof(sat, ymd, hms):
    """找到覆盖 (ymd hms) UTC 时刻的 POEORB 文件名"""
    y, m, d = ymd[:4], ymd[4:6], ymd[6:8]
    url = f'{BASE}/{sat}/{y}/{m}/'
    try:
        files = fetch_dir(url)
    except Exception as e:
        log(f'  目录访问失败 {url}: {str(e)[:60]}')
        return None
    target = f'{ymd}T{hms}'
    best = None
    for f in files:
        vs, ve = validity_of(f)
        if not vs:
            continue
        if vs <= target <= ve:
            # 精确匹配：目标时刻在区间内
            return f
    return None

def download_eof(url, dest_zip, dest_eof):
    """下载并解压 EOF"""
    if os.path.exists(dest_eof) and os.path.getsize(dest_eof) > 100:
        return 'skip'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest_zip, 'wb') as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    with zipfile.ZipFile(dest_zip) as z:
        z.extractall(os.path.dirname(dest_eof))
    os.remove(dest_zip)
    return 'ok'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    rows = list(csv.DictReader(open(LIST, encoding='utf-8-sig')))
    if args.limit:
        rows = rows[:args.limit]

    os.makedirs(OUT, exist_ok=True)
    # 提取唯一 (卫星, 日期, 时刻)
    seen = {}
    for r in rows:
        sat_short = SAT_MAP.get(r['satellite'])
        if not sat_short:
            continue
        m = re.search(r'_(\d{8})T(\d{6})', r['file'])
        if not m:
            continue
        ymd, hms = m.group(1), m.group(2)
        key = (sat_short, ymd)
        if key not in seen:
            seen[key] = hms  # 保留首个时刻（同一天多帧用同一 EOF）

    log(f'待匹配时相: {len(seen)} 个（去重后）')
    ok = fail = 0
    for i, ((sat, ymd), hms) in enumerate(seen.items(), 1):
        eof = find_eof(sat, ymd, hms)
        if not eof:
            log(f'[{i}/{len(seen)}] [FAIL] 未找到 {sat} {ymd}T{hms} 的 POEORB')
            fail += 1
            time.sleep(1)
            continue
        y, m = ymd[:4], ymd[4:6]
        url = f'{BASE}/{sat}/{y}/{m}/{eof}'
        dest_eof = os.path.join(OUT, eof.replace('.zip', ''))
        dest_zip = os.path.join(OUT, eof)
        try:
            st = download_eof(url, dest_zip, dest_eof)
            ok += 1
            log(f'[{i}/{len(seen)}] [{st.upper()}] {sat} {ymd} -> {eof[:60]}')
        except Exception as e:
            fail += 1
            log(f'[{i}/{len(seen)}] [FAIL] {sat} {ymd}: {str(e)[:70]}')
        time.sleep(1)

    log(f'=== POEORB 完成: 成功 {ok} / 失败 {fail} ===')

if __name__ == '__main__':
    main()
