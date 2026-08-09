# -*- coding: utf-8 -*-
"""ASF 多线程分片下载器：8 线程 Range 分片 + 断点续传 + 重试。
用法: python -u multi_download.py [--limit N]
"""
import csv, os, sys, time, argparse, glob
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

SKILL_DIR = 'C:/Users/86155/.pi/agent/skills/asf-sentinel1-download'
OUT_DIR = 'G:/insar_data/gulang2_sbas'
LIST = 'D:/work/data/asf_experiment/download_aligned.csv'
LOG = 'D:/work/data/asf_experiment/multi_download.log'
THREADS = 8
RETRIES = 6
EXTRA_ROUNDS = 3

sys.path.insert(0, SKILL_DIR)
from download import load_config
import asf_search as asf
from asf_search import ASFSession

def log(msg):
    line = f'[{time.strftime("%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def download_chunk(session, url, start, end, part_path, idx):
    """下载一个分片，支持断点续传（已下载部分跳过），失败重试"""
    # 分片断点续传：已有大小则从该位置续（ab 模式）
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
            else:
                log(f'  [片{idx}] HTTP {r.status_code}, 重试 {attempt+1}/{RETRIES}')
        except Exception as e:
            log(f'  [片{idx}] 错误 {str(e)[:60]}, 重试 {attempt+1}/{RETRIES}')
        time.sleep(5 * (attempt + 1))
    return False, 0

def md5_of(path):
    """计算文件 MD5（分块，适合大文件）"""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def single_download(session, url, dest, total_size, expected_md5=''):
    """单连接整文件下载：断点续传 + 重试 + 大小/MD5 校验（网络极差时的稳建模式）"""
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
                # 完成判定：续传后文件达到 total 才重命名
                size = os.path.getsize(part)
                if size == total_size:
                    os.replace(part, dest)
                    if expected_md5:
                        log(f'  计算 MD5 校验中...')
                        got = md5_of(dest)
                        if got != expected_md5:
                            log(f'  [WARN] MD5 不匹配! 删除重下')
                            os.remove(dest)
                            return False, size
                    return True, size
                # 未完成（可能网络中断但没抛异常）→ 继续循环
                existing = size
            else:
                log(f'  [单连接] HTTP {r.status_code}, 重试 {attempt+1}')
        except Exception as e:
            log(f'  [单连接] 错误 {str(e)[:60]}, 重试 {attempt+1}')
        time.sleep(8 * (attempt + 1))
    return False, existing

def multi_download(session, url, dest, total_size, expected_md5=''):
    """分片并发下载，返回 (成功?, 大小)"""
    n = THREADS
    # 动态分片：<300MB 用 4 片，否则 8 片
    if total_size < 300 * 1024 * 1024:
        n = 4
    chunk = total_size // n
    ranges = [(i * chunk, (i + 1) * chunk - 1) for i in range(n)]
    ranges[-1] = (ranges[-1][0], total_size - 1)

    parts = [dest + f'.part{i}' for i in range(n)]
    # 清理残留分片
    for p in glob.glob(dest + '.part*'):
        if p not in parts:
            try: os.remove(p)
            except OSError: pass

    results = {}
    with ThreadPoolExecutor(max_workers=n) as ex:
        futs = {ex.submit(download_chunk, session, url, s, e, parts[i], i): i
                for i, (s, e) in enumerate(ranges)}
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = (False, 0)
                log(f'  [片{i}] 异常: {str(e)[:60]}')

    # 合并前：对失败分片循环补下（网络差时不轻易作废整个文件）
    for round_no in range(EXTRA_ROUNDS):
        failed = [i for i in range(n) if not results.get(i) or not results[i][0]]
        if not failed:
            break
        log(f'  [补下轮{round_no+1}] 失败分片 {failed}，重试中...')
        with ThreadPoolExecutor(max_workers=len(failed)) as ex:
            futs = {ex.submit(download_chunk, session, url, ranges[i][0], ranges[i][1], parts[i], i): i
                    for i in failed}
            for fut in as_completed(futs):
                i = futs[fut]
                try: results[i] = fut.result()
                except Exception as e: results[i] = (False, 0)

    # 合并
    with open(dest, 'wb') as out:
        for i in range(n):
            if not results.get(i) or not results[i][0]:
                log(f'  [片{i}] 失败，文件作废')
                for p in parts: os.remove(p)
                return False, 0
            with open(parts[i], 'rb') as f:
                out.write(f.read())
    for p in parts:
        os.remove(p)
    size = os.path.getsize(dest)
    if size != total_size:
        log(f'  大小不匹配 {size} != {total_size}，作废重下')
        os.remove(dest)
        return False, size
    # MD5 校验（ASF 官方 md5sum）
    if expected_md5:
        log(f'  计算 MD5 校验中...')
        got = md5_of(dest)
        if got != expected_md5:
            log(f'  [WARN] MD5 不匹配! 期望 {expected_md5} 实得 {got}，删除重下')
            os.remove(dest)
            return False, size
        log(f'  MD5 校验通过: {got[:16]}...')
    return True, size

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    WORKDIR = 'D:/work/data/asf_experiment'
    SKIP_FILE = os.path.join(WORKDIR, 'skip.flag')
    PAUSE_FILE = os.path.join(WORKDIR, 'pause.flag')
    STOP_FILE = os.path.join(WORKDIR, 'stop.flag')
    MODE_FILE = os.path.join(WORKDIR, 'mode.flag')
    COMPLETE_FILE = os.path.join(WORKDIR, 'complete.flag')

    # 新任务开始：清除旧完成标记（让遥控/定时汇报随新任务自动恢复）
    if os.path.exists(COMPLETE_FILE):
        try:
            os.remove(COMPLETE_FILE)
            log(f'[START] 新任务开始，清除旧 complete.flag（定时汇报已随任务恢复）')
        except OSError:
            pass

    # 下载模式：multi=多线程分片，single=单文件（自动降级后）
    mode = 'single' if os.path.exists(MODE_FILE) and open(MODE_FILE).read().strip() == 'single' else 'multi'
    log(f'[MODE] 下载模式: {mode}{"（已自动降级）" if mode=="single" else ""}')

    # 暂停/停止标记：直接退出（守护会尊重标记不重启）
    if os.path.exists(PAUSE_FILE):
        log(f'[STOP] 发现 pause.flag，退出（遥控“继续”恢复）')
        return
    if os.path.exists(STOP_FILE):
        log(f'[STOP] 发现 stop.flag，退出')
        return

    cfg = load_config(os.path.join(SKILL_DIR, 'config.json'))
    session = ASFSession()
    session.auth_with_creds(cfg['username'], cfg['password'])
    log(f'[OK] 认证成功: {cfg["username"]} | 线程={THREADS}')

    rows = list(csv.DictReader(open(LIST, encoding='utf-8-sig')))
    if args.limit:
        rows = rows[:args.limit]
    log(f'清单: {len(rows)} 景')

    ok, fail, skip, fail_streak = 0, 0, 0, 0
    completed = True  # 是否完整跑完清单（break 中断则 False，不写完成标记）
    for i, r in enumerate(rows, 1):
        fname = r['file']
        # 遥控跳过清单
        if os.path.exists(SKIP_FILE):
            with open(SKIP_FILE, encoding='utf-8') as f:
                skips = [l.strip() for l in f if l.strip()]
            if fname in skips:
                skip += 1
                log(f'[{i}/{len(rows)}] 跳过(遥控指定): {fname[:45]}')
                continue
        # 暂停/停止检查（每文件前）
        if os.path.exists(PAUSE_FILE):
            log(f'[STOP] 遥控暂停，退出')
            completed = False
            break
        if os.path.exists(STOP_FILE):
            log(f'[STOP] 遥控停止，退出')
            completed = False
            break
        dest = os.path.join(OUT_DIR, fname)
        if os.path.exists(dest) and os.path.getsize(dest) > 1024:
            skip += 1
            log(f'[{i}/{len(rows)}] 跳过(已完成): {fname[:45]}')
            continue
        # 丢弃单连接旧 .part（不兼容分片）
        old = dest + '.part'
        if os.path.exists(old):
            log(f'  清理旧单连接 .part ({os.path.getsize(old)//1024//1024}MB)')
            os.remove(old)
        try:
            prod = asf.granule_search(fname.replace('.zip', ''))
            if not prod:
                log(f'[{i}/{len(rows)}] [FAIL] 未找到: {fname[:45]}')
                fail += 1
                continue
            url = prod[0].properties['url']
            expected_md5 = prod[0].properties.get('md5sum', '')
            # Range 探测真实大小（HEAD 不支持时用 bytes=0-0）
            probe = session.get(url, headers={'Range': 'bytes=0-0'}, timeout=(30, 60))
            cr = probe.headers.get('Content-Range', '')
            probe.close()  # 释放连接
            total = int(cr.split('/')[-1]) if cr and '/' in cr else 0
            if total <= 0:
                raise ValueError(f'无法获取文件大小: {fname[:40]}')
            log(f'[{i}/{len(rows)}] [DL] {fname[:40]}... {total/1e9:.2f}GB')
            t0 = time.time()
            if mode == 'multi':
                ok_flag, size = multi_download(session, url, dest, total, expected_md5)
            else:
                ok_flag, size = single_download(session, url, dest, total, expected_md5)
            dt = time.time() - t0
            if ok_flag:
                ok += 1
                fail_streak = 0
                log(f'[{i}/{len(rows)}] [OK] {fname[:35]}... {size/1e9:.2f}GB ({dt/60:.1f}min, {size/dt/1e6:.1f}MB/s)')
            else:
                fail += 1
                fail_streak += 1
                log(f'[{i}/{len(rows)}] [FAIL] {fname[:45]} ({dt/60:.1f}min)')
                # 自动降级：多线程模式连续 2 个文件作废 → 切单文件模式
                if mode == 'multi' and fail_streak >= 2:
                    with open(MODE_FILE, 'w', encoding='utf-8') as f:
                        f.write('single')
                    log(f'[DOWNGRADE] 多线程连续 {fail_streak} 文件作废，自动切换单文件模式，退出重启')
                    completed = False
                    break
        except Exception as e:
            fail += 1
            fail_streak += 1
            log(f'[{i}/{len(rows)}] [WARN] {fname[:45]} :: {str(e)[:80]}')
        else:
            fail_streak = 0
        time.sleep(2)

    log(f'=== 完成: 成功 {ok} / 失败 {fail} / 跳过 {skip} ===')
    # 完整跑完清单 → 写完成标记（守护据此停止，避免无限重启）
    if completed:
        COMPLETE_FILE = os.path.join(WORKDIR, 'complete.flag')
        with open(COMPLETE_FILE, 'w', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S'))
        log(f'[DONE] 清单全部处理完毕，写入 complete.flag（守护将退出）')

if __name__ == '__main__':
    main()
