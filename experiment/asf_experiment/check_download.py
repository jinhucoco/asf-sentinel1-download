# -*- coding: utf-8 -*-
"""ASF 下载健康检查：一键输出状态摘要。
用法: python check_download.py
"""
import os, subprocess, glob, time

OUT_DIR = 'G:/insar_data/gulang2_sbas'
LOGF = 'D:/work/data/asf_experiment/multi_run.log'
LIST = 'D:/work/data/asf_experiment/download_aligned.csv'

def main():
    print('=' * 60)
    print(f'ASF 下载健康检查  {time.strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 60)

    # 1. 进程
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
          "| Where-Object { $_.CommandLine -like '*multi_download*' -or $_.CommandLine -like '*guard*' } "
          "| Select-Object ProcessId,@{n='C';e={$_.CommandLine.Split('\\')[-1]}} | Format-Table -HideTableHeaders")
    out = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                         capture_output=True, text=True, timeout=30).stdout
    dl = 'multi_download' in out.lower()
    gd = 'guard' in out.lower()
    print(f'进程: 下载={"运行中" if dl else "DOWN!"} | 守护={"运行中" if gd else "DOWN!"}')

    # 2. 进度
    total_files = 154
    done = [f for f in glob.glob(os.path.join(OUT_DIR, '*.zip')) if os.path.getsize(f) > 1024]
    parts = glob.glob(os.path.join(OUT_DIR, '*.part*'))
    cur = sum(os.path.getsize(p) for p in parts)
    print(f'完成: {len(done)}/{total_files} 景 | 当前文件分片: {cur/1e6:.0f} MB')

    # 3. 速度（最近日志时间戳与分片大小估算）
    # 4. 最近日志（错误/异常统计）
    if os.path.exists(LOGF):
        with open(LOGF, encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        errs = [l for l in lines if '错误' in l or '失败' in l or 'WARN' in l or '作废' in l]
        oks = [l for l in lines if '[OK]' in l and 'MD5' not in l]
        print(f'日志: 总 {len(lines)} 行 | 成功 {len(oks)} | 错误/失败 {len(errs)}')
        if errs:
            print(f'最近异常 ({min(3, len(errs))}条):')
            for l in errs[-3:]:
                print(' ', l.strip()[:100])
        print('最近5行:')
        for l in lines[-5:]:
            print(' ', l.strip()[:100])

    # 5. 磁盘
    d = subprocess.run(['df', '-h', '/g'], capture_output=True, text=True).stdout.split('\n')
    if len(d) > 1:
        print('G盘:', d[1].split()[:6])

if __name__ == '__main__':
    main()
