# -*- coding: utf-8 -*-
"""ASF Sentinel-1 多线程分片下载器（技能的正式多线程版）。

两种用法：
  1. 清单驱动（推荐，配合 analyze.py 生成的清单）：
     python multi_download.py --list 清单.csv --out 下载目录 [--threads 8]
  2. 搜索驱动（指定轨道直接下载，跳过交互选择）：
     python multi_download.py --aoi 区域.shp --start 20200101 --end 20251231 \
       --pol VV+VH --track 135 --out 下载目录 [--threads 8]

特性：N 线程 Range 分片并发、分片级断点续传 + 重试 + 失败片循环补下、
大小 + MD5 双校验（坏数据自动删除重下）、已完成文件跳过、进度日志。
"""
import csv, os, sys, time, argparse, glob, shutil
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from download import aoi_to_wkt, iso_datetime, load_config, parse_polarization
import asf_search as asf
from asf_search import ASFSession

DEFAULT_THREADS = 8
RETRIES = 6
EXTRA_ROUNDS = 3

def log(msg, logfile):
    line = f'[{time.strftime("%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    if logfile:
        with open(logfile, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

def download_chunk(session, url, start, end, part_path, idx, logfile):
    """下载一个分片，支持断点续传（已下载部分跳过），失败重试"""
    existing = os.path.getsize(part_path) if os.path.exists(part_path) else 0
    if existing >= (end - start + 1):
        return True, existing  # 该片已完成
    start += existing
    headers = {'Range': f'bytes={start}-{end}'}
    for attempt in range(RETRIES):
        try:
            r = session.get(url, stream=True, headers=headers, timeout=(30, 120))
            if r.status_code in (200, 206):
                mode = 'ab' if existing else 'wb'
                with open(part_path, mode) as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                return True, os.path.getsize(part_path)
            log(f'  [片{idx}] HTTP {r.status_code}, 重试 {attempt+1}/{RETRIES}', logfile)
        except Exception as e:
            log(f'  [片{idx}] 错误 {str(e)[:60]}, 重试 {attempt+1}/{RETRIES}', logfile)
        time.sleep(5 * (attempt + 1))
    return False, 0

def md5_of(path):
    """计算文件 MD5（分块，适合大文件）"""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def single_download(session, url, dest, total_size, logfile, expected_md5=''):
    """单连接整文件下载：断点续传 + 重试 + 大小/MD5 校验（网络极差时自动降级的稳建模式）"""
    part = dest + '.part'
    existing = os.path.getsize(part) if os.path.exists(part) else 0
    for attempt in range(RETRIES + 2):
        try:
            headers = {}
            if existing:
                headers['Range'] = f'bytes={existing}-'
            r = session.get(url, stream=True, headers=headers, timeout=(60, 300))
            if r.status_code in (200, 206):
                with open(part, 'ab' if existing else 'wb') as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                size = os.path.getsize(part)
                if size == total_size:
                    os.replace(part, dest)
                    if expected_md5:
                        log(f'  计算 MD5 校验中...', logfile)
                        got = md5_of(dest)
                        if got != expected_md5:
                            log(f'  [WARN] MD5 不匹配! 删除重下', logfile)
                            os.remove(dest)
                            return False, size
                    return True, size
                existing = size  # 未完成，继续
            else:
                log(f'  [单连接] HTTP {r.status_code}, 重试 {attempt+1}', logfile)
        except Exception as e:
            log(f'  [单连接] 错误 {str(e)[:60]}, 重试 {attempt+1}', logfile)
        time.sleep(8 * (attempt + 1))
    return False, existing

def get_total_size(session, url):
    """Range 探测真实大小（HEAD 在 ASF 不可靠）"""
    r = session.get(url, headers={'Range': 'bytes=0-0'}, timeout=(30, 60))
    cr = r.headers.get('Content-Range', '')
    r.close()  # 释放连接
    if cr and '/' in cr:
        return int(cr.split('/')[-1])
    raise ValueError(f'无法获取文件大小: {url[:60]}')

def multi_download(session, url, dest, total_size, threads, logfile, expected_md5=''):
    n = threads if total_size >= 300 * 1024 * 1024 else 4
    chunk = total_size // n
    ranges = [(i * chunk, (i + 1) * chunk - 1) for i in range(n)]
    ranges[-1] = (ranges[-1][0], total_size - 1)

    parts = [dest + f'.part{i}' for i in range(n)]
    for p in glob.glob(dest + '.part*'):
        if p not in parts:
            try: os.remove(p)
            except OSError: pass

    results = {}
    with ThreadPoolExecutor(max_workers=n) as ex:
        futs = {ex.submit(download_chunk, session, url, s, e, parts[i], i, logfile): i
                for i, (s, e) in enumerate(ranges)}
        for fut in as_completed(futs):
            i = futs[fut]
            try: results[i] = fut.result()
            except Exception as e:
                results[i] = (False, 0)
                log(f'  [片{i}] 异常: {str(e)[:60]}', logfile)

    # 合并前：对失败分片循环补下（网络差时不轻易作废整个文件）
    for round_no in range(EXTRA_ROUNDS):
        failed = [i for i in range(n) if not results.get(i) or not results[i][0]]
        if not failed:
            break
        log(f'  [补下轮{round_no+1}] 失败分片 {failed}，重试中...', logfile)
        with ThreadPoolExecutor(max_workers=len(failed)) as ex:
            futs = {ex.submit(download_chunk, session, url, ranges[i][0], ranges[i][1], parts[i], i, logfile): i
                    for i in failed}
            for fut in as_completed(futs):
                i = futs[fut]
                try: results[i] = fut.result()
                except Exception as e: results[i] = (False, 0)

    # 合并
    with open(dest, 'wb') as out:
        for i in range(n):
            if not results.get(i) or not results[i][0]:
                log(f'  [片{i}] 失败，文件作废（下次重下）', logfile)
                for p in parts:
                    try: os.remove(p)
                    except OSError: pass
                return False, 0
            with open(parts[i], 'rb') as f:
                shutil.copyfileobj(f, out)
    for p in parts:
        os.remove(p)
    size = os.path.getsize(dest)
    if size != total_size:
        log(f'  大小不匹配 {size} != {total_size}，作废重下', logfile)
        os.remove(dest)
        return False, size
    # MD5 校验（ASF 官方 md5sum）
    if expected_md5:
        log(f'  计算 MD5 校验中...', logfile)
        got = md5_of(dest)
        if got != expected_md5:
            log(f'  [WARN] MD5 不匹配! 期望 {expected_md5} 实得 {got}，删除重下', logfile)
            os.remove(dest)
            return False, size
        log(f'  MD5 校验通过: {got[:16]}...', logfile)
    return True, size

def search_and_group(aoi, start, end, pols):
    wkt = aoi_to_wkt(aoi)
    results = []
    for pol in pols:
        r = asf.geo_search(platform='SENTINEL-1', processingLevel='SLC', beamMode='IW',
                           polarization=pol, start=iso_datetime(start), end=iso_datetime_end(end),
                           intersectsWith=wkt)
        results.extend(r)
    groups = {}
    for r in results:
        key = (r.properties.get('flightDirection'), str(r.properties.get('pathNumber')))
        groups.setdefault(key, []).append(r)
    return groups, results

def main():
    ap = argparse.ArgumentParser(description='ASF 多线程分片下载')
    ap.add_argument('--list', help='清单 CSV（date,frame,orbit,satellite,file 列），优先于搜索路径')
    ap.add_argument('--aoi', help='区域 shp/kml（搜索路径用）')
    ap.add_argument('--start', help='起始 YYYYMMDD')
    ap.add_argument('--end', help='结束 YYYYMMDD')
    ap.add_argument('--pol', default='VV+VH,VV', help='极化，逗号分隔')
    ap.add_argument('--track', type=int, help='指定轨道号（跳过交互选择）')
    ap.add_argument('--out', default='./sentinel1_data', help='下载目录')
    ap.add_argument('--threads', type=int, default=DEFAULT_THREADS, help='分片线程数')
    args = ap.parse_args()

    if not args.list and not (args.aoi and args.start and args.end):
        ap.error('需要 --list 或 --aoi/--start/--end 之一')

    skill_dir = os.path.dirname(os.path.abspath(__file__))
    cfg = load_config(os.path.join(skill_dir, 'config.json'))
    session = ASFSession()
    session.auth_with_creds(cfg['username'], cfg['password'])
    os.makedirs(args.out, exist_ok=True)
    logfile = os.path.join(args.out, 'multi_download.log')
    log(f'[OK] 认证成功: {cfg["username"]} | 线程={args.threads}', logfile)

    rows = []
    if args.list:
        with open(args.list, encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        log(f'清单驱动: {len(rows)} 条', logfile)
    else:
        pols = [parse_polarization(p) for p in args.pol.split(',')]
        groups, _ = search_and_group(args.aoi, args.start, args.end, pols)
        if not groups:
            log('[!] 未搜索到数据', logfile)
            return
        ranked = sorted(groups.items(), key=lambda kv: -len(kv[1]))
        if args.track:
            sel = None
            for (d, p), prods in ranked:
                if int(p) == args.track:
                    sel = prods
                    log(f'已指定轨道 {args.track}（{d}，{len(prods)} 景）', logfile)
                    break
            if sel is None:
                log(f'[!] 轨道 {args.track} 不在结果中，可用组：' +
                    ' '.join(f'{d}/轨道{p}({len(pr)})' for (d, p), pr in ranked), logfile)
                return
        else:
            print('可用 (方向,轨道) 组：')
            for i, ((d, p), prods) in enumerate(ranked, 1):
                print(f'  [{i}] {d} / 轨道 {p}: {len(prods)} 景')
            idx = (input('选择编号（回车默认 1）: ').strip() or '1')
            try:
                sel = ranked[int(idx) - 1][1]
            except (ValueError, IndexError):
                sel = ranked[0][1]
                log(f'编号无效，使用第 1 组', logfile)
        for r in sel:
            rows.append({'file': r.properties.get('fileName', '')})
        log(f'搜索路径: {len(rows)} 景', logfile)

    ok = fail = skip = fail_streak = 0
    completed = True  # 完整跑完清单才写 complete.flag（降级/中断不写）
    # 下载模式：multi=多线程分片，single=单文件（自动降级后，标记存输出目录）
    with open(os.path.join(args.out, 'mode.flag')) as f:
        mode = 'single' if os.path.exists(os.path.join(args.out, 'mode.flag')) and f.read().strip() == 'single' else 'multi'
    log(f'[MODE] 下载模式: {mode}{"（已自动降级）" if mode=="single" else ""}', logfile)
    for i, r in enumerate(rows, 1):
        fname = r.get('file', '').strip()
        if not fname:
            fail += 1
            continue
        # 文件名消毒（防路径穿越，F4）
        if fname.startswith('/') or '..' in fname.split('/') or (':' in fname.split('/')[0]) or fname in ('.', '..'):
            log(f'[{i}/{len(rows)}] [WARN] 非法文件名，跳过: {fname[:50]}', logfile)
            continue
        dest = os.path.join(args.out, fname)
        if os.path.exists(dest) and os.path.getsize(dest) > 1024:
            skip += 1
            log(f'[{i}/{len(rows)}] 跳过(已完成): {fname[:45]}', logfile)
            continue
        try:
            prod = asf.granule_search(fname.replace('.zip', ''))
            if not prod:
                log(f'[{i}/{len(rows)}] [FAIL] 未找到: {fname[:45]}', logfile)
                fail += 1
                continue
            url = prod[0].properties['url']
            expected_md5 = prod[0].properties.get('md5sum', '')
            total = get_total_size(session, url)
            log(f'[{i}/{len(rows)}] [DL] {fname[:40]}... {total/1e9:.2f}GB', logfile)
            t0 = time.time()
            if mode == 'multi':
                ok_flag, size = multi_download(session, url, dest, total, args.threads, logfile, expected_md5)
            else:
                ok_flag, size = single_download(session, url, dest, total, logfile, expected_md5)
            dt = time.time() - t0
            if ok_flag:
                ok += 1
                fail_streak = 0
                log(f'[{i}/{len(rows)}] [OK] {fname[:35]}... {size/1e9:.2f}GB ({dt/60:.1f}min, {size/max(dt,1)/1e6:.1f}MB/s)', logfile)
            else:
                fail += 1
                fail_streak += 1
                log(f'[{i}/{len(rows)}] [FAIL] {fname[:45]}', logfile)
                # 自动降级：多线程连续 2 个文件作废 → 切单文件模式（网络极差时的稳建保底）
                if mode == 'multi' and fail_streak >= 2:
                    with open(os.path.join(args.out, 'mode.flag'), 'w', encoding='utf-8') as f:
                        f.write('single')
                    log(f'[DOWNGRADE] 多线程连续 {fail_streak} 文件作废，自动切换单文件模式，退出重启', logfile)
                    completed = False
                    break
        except Exception as e:
            fail += 1
            log(f'[{i}/{len(rows)}] [WARN] {fname[:45]} :: {str(e)[:80]}', logfile)
        time.sleep(2)

    log(f'=== 完成: 成功 {ok} / 失败 {fail} / 跳过 {skip} ===', logfile)
    # 任务完成标记（配合守护脚本防止无限重启；仅完整跑完清单时写）
    if completed:
        try:
            cf = os.path.join(args.out, 'complete.flag')
            with open(cf, 'w', encoding='utf-8') as f:
                f.write(time.strftime('%Y-%m-%d %H:%M:%S'))
            log(f'[DONE] 任务完成，写入标记: {cf}', logfile)
        except Exception:
            pass

if __name__ == '__main__':
    main()
