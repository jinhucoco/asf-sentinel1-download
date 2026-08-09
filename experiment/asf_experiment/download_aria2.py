# -*- coding: utf-8 -*-
"""aria2 批量下载：时相对齐清单（154 景），断点续传 + 重试 + 日志。
用法: python download_aria2.py [--limit N] [--offset M]
"""
import csv, os, sys, subprocess, time, argparse

SKILL_DIR = 'C:/Users/86155/.pi/agent/skills/asf-sentinel1-download'
A2 = 'D:/tools/aria2/aria2-1.37.0-win-64bit-build1/aria2c.exe'
OUT_DIR = 'G:/insar_data/gulang2_sbas'
LIST = 'D:/work/data/asf_experiment/download_aligned.csv'
LOG = 'D:/work/data/asf_experiment/download_aria2.log'

sys.path.insert(0, SKILL_DIR)
from download import load_config
import asf_search as asf
from asf_search import ASFSession

def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--offset', type=int, default=0)
    args = ap.parse_args()

    cfg = load_config(os.path.join(SKILL_DIR, 'config.json'))
    session = ASFSession()
    session.auth_with_creds(cfg['username'], cfg['password'])
    auth_header = f"Authorization: {session.headers['Authorization']}"
    cookie = '; '.join(f'{c.name}={c.value}' for c in session.cookies)
    cookie_header = f"Cookie: {cookie}"
    log(f'[OK] 认证成功: {cfg["username"]}')

    rows = list(csv.DictReader(open(LIST, encoding='utf-8-sig')))
    rows = rows[args.offset:]
    if args.limit:
        rows = rows[:args.limit]
    log(f'清单: 待下载 {len(rows)} 景 → {OUT_DIR}')

    ok, fail, skip = 0, 0, 0
    for i, r in enumerate(rows, 1):
        fname = r['file']
        dest = os.path.join(OUT_DIR, fname)
        # 已完成（正式名存在且 >1KB）
        if os.path.exists(dest) and os.path.getsize(dest) > 1024:
            skip += 1
            log(f'[{i}/{len(rows)}] 跳过已完成: {fname[:45]} ({os.path.getsize(dest)/1e9:.2f}GB)')
            continue
        try:
            prod = asf.granule_search(fname.replace('.zip', ''))
            if not prod:
                log(f'[{i}/{len(rows)}] [FAIL] 未找到: {fname[:45]}')
                fail += 1
                continue
            url = prod[0].properties['url']
            log(f'[{i}/{len(rows)}] [DL] {fname[:45]}...')
            cmd = [A2, '-c', '-x8', '-s8', '--max-tries=3', '--retry-wait=15',
                   '--auto-file-renaming=false', '--allow-overwrite=false',
                   '--summary-interval=120', '--console-log-level=warn',
                   '--header', auth_header, '--header', cookie_header,
                   '-d', OUT_DIR, '-o', fname, url]
            t0 = time.time()
            rc = subprocess.run(cmd, capture_output=True, text=True, timeout=7200).returncode
            dt = time.time() - t0
            if rc == 0 and os.path.exists(dest) and os.path.getsize(dest) > 1024:
                ok += 1
                log(f'[{i}/{len(rows)}] [OK] {fname[:40]}... {os.path.getsize(dest)/1e9:.2f}GB ({dt/60:.1f}min)')
            else:
                fail += 1
                log(f'[{i}/{len(rows)}] [FAIL] 失败 rc={rc} ({dt/60:.1f}min): {fname[:45]}')
        except Exception as e:
            fail += 1
            log(f'[{i}/{len(rows)}] [WARN] 异常: {fname[:45]} :: {str(e)[:100]}')
        time.sleep(2)

    log(f'=== 批次完成: 成功 {ok} / 失败 {fail} / 跳过 {skip} ===')

if __name__ == '__main__':
    main()
