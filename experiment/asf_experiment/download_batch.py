# -*- coding: utf-8 -*-
"""ASF 批量下载脚本：基于采样清单，复用技能的稳健下载逻辑。
用法: python download_batch.py [--limit N] [--resume]
  --limit N  : 只下载前 N 景（验证用）
  --resume   : 跳过已完整下载的文件
"""
import csv, os, sys, time, argparse

SKILL_DIR = 'C:/Users/86155/.pi/agent/skills/asf-sentinel1-download'
sys.path.insert(0, SKILL_DIR)

from robust_download import robust_download
from download import load_config
import asf_search as asf
from asf_search import ASFSession

OUT_DIR = 'G:/insar_data/gulang2_sbas'
LIST = 'D:/work/data/asf_experiment/download_aligned.csv'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='只下载前 N 景（0=全部）')
    ap.add_argument('--start-from', type=int, default=0, help='从第几个开始（断点续跑）')
    args = ap.parse_args()

    cfg = load_config(os.path.join(SKILL_DIR, 'config.json'))
    session = ASFSession()
    session.auth_with_creds(cfg['username'], cfg['password'])
    print(f'✅ ASF 认证成功: {cfg["username"]}')

    rows = list(csv.DictReader(open(LIST, encoding='utf-8-sig')))
    print(f'清单: {len(rows)} 景')
    if args.limit:
        rows = rows[args.start_from:args.start_from + args.limit]
    else:
        rows = rows[args.start_from:]

    os.makedirs(OUT_DIR, exist_ok=True)
    ok, fail, skip = 0, 0, 0
    for i, r in enumerate(rows, 1):
        fname = r['file']
        dest = os.path.join(OUT_DIR, fname)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            skip += 1
            print(f'[{i}/{len(rows)}] 跳过(已完成): {fname[:40]}')
            continue
        try:
            prod = asf.granule_search(fname.replace('.zip', ''))
            if not prod:
                print(f'[{i}/{len(rows)}] ❌ 未找到: {fname[:40]}')
                fail += 1
                continue
            # granule_search 可能返回多个（相同文件名跨帧？取第一个）
            product = prod[0]
            ok_flag, size = robust_download(product, OUT_DIR, session)
            if ok_flag:
                ok += 1
                print(f'[{i}/{len(rows)}] ✅ {fname[:30]}... {size/1e9:.2f} GB')
            else:
                fail += 1
                print(f'[{i}/{len(rows)}] ❌ 下载失败: {fname[:40]} ({size} bytes)')
        except Exception as e:
            fail += 1
            print(f'[{i}/{len(rows)}] ⚠️ 异常: {fname[:40]} :: {str(e)[:80]}')
        time.sleep(1)

    print(f'\n=== 完成: 成功 {ok} / 失败 {fail} / 跳过 {skip} ===')

if __name__ == '__main__':
    main()
