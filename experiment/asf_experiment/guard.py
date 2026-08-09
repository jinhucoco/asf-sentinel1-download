# -*- coding: utf-8 -*-
"""ASF 下载守护 v2：自动重启 + 异常通知（Server酱微信推送）。
检测：进程死/卡死自动重启；全局异常（磁盘满、连续失败、停滞）微信通知。
通知配置：notify_config.json（enabled + sendkey）。
用法: python -u guard.py
"""
import os, subprocess, sys, time, glob, json, urllib.request

OUT_DIR = 'G:/insar_data/gulang2_sbas'
BATCH = 'D:/work/data/asf_experiment/multi_download.py'
LOGF = 'D:/work/data/asf_experiment/guard.log'
WORKDIR = 'D:/work/data/asf_experiment'
CFG_FILE = os.path.join(WORKDIR, 'notify_config.json')
TOTAL = 154

_last_notify = {}  # event -> timestamp（节流）

def log(msg):
    line = f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    with open(LOGF, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def notify(title, desp=''):
    """Server酱微信推送（带节流：同一事件 30 分钟内不重复）"""
    try:
        cfg = json.load(open(CFG_FILE, encoding='utf-8')).get('serverchan', {})
        if not cfg.get('enabled') or not cfg.get('sendkey') or cfg['sendkey'].startswith('SCT填写'):
            return
        key = title[:20]
        now = time.time()
        interval = cfg.get('notify_interval_min', 30) * 60
        if key in _last_notify and now - _last_notify[key] < interval:
            return
        _last_notify[key] = now
        import urllib.parse
        url = f'https://sctapi.ftqq.com/{cfg["sendkey"]}.send'
        data = urllib.parse.urlencode({'title': f'[ASF下载] {title}', 'desp': desp[:2000]}).encode()
        req = urllib.request.Request(url, data=data, method='POST')
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
        log(f'[notify] {title} -> {resp.get("code")}')
    except Exception as e:
        log(f'[notify失败] {e}')

def download_alive():
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
          "| Where-Object { $_.CommandLine -like '*multi_download*' } "
          "| Measure-Object | Select-Object -ExpandProperty Count")
    try:
        out = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        return out not in ('', '0')
    except Exception:
        return True

def newest_activity():
    latest = 0
    for p in glob.glob(os.path.join(OUT_DIR, '*')) + glob.glob(os.path.join(OUT_DIR, '*.part*')):
        try:
            latest = max(latest, os.path.getmtime(p))
        except OSError:
            pass
    return latest

def disk_free_gb():
    out = subprocess.run(['df', '-h', '/g'], capture_output=True, text=True).stdout
    for line in out.split('\n'):
        parts = line.split()
        if len(parts) >= 4 and parts[0] == 'G:':
            try:
                return float(parts[3].replace('G', ''))
            except ValueError:
                pass
    return 999

def done_count():
    return sum(1 for f in glob.glob(os.path.join(OUT_DIR, '*.zip')) if os.path.getsize(f) > 1024)

def start_batch():
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    log('重启 multi_download.py（后台）...')
    DETACHED = 0x00000008 | 0x00000200
    subprocess.Popen(
        [sys.executable, '-u', BATCH],
        cwd=WORKDIR, env=env,
        stdout=open(os.path.join(WORKDIR, 'multi_run.log'), 'a', encoding='utf-8'),
        stderr=subprocess.STDOUT,
        creationflags=DETACHED,
        close_fds=True,
    )

def main():
    log('=== 守护 v2 启动（含微信通知）===')
    cf = os.path.join(WORKDIR, 'complete.flag')
    # 任务完成标记：存在则直接退出（不再拉起下载）
    if os.path.exists(cf):
        log('检测到 complete.flag（任务已完成），守护退出')
        sys.exit(0)
    last_done = done_count()
    while True:
        try:
            # 任务完成标记：守护退出（不再拉起下载进程）
            if os.path.exists(cf):
                log('检测到 complete.flag（任务已完成），守护退出')
                sys.exit(0)
            alive = download_alive()
            if not alive:
                # 遥控暂停/停止标记：不自动重启
                if os.path.exists(os.path.join(WORKDIR, 'pause.flag')) or os.path.exists(os.path.join(WORKDIR, 'stop.flag')):
                    log('遥控暂停/停止中，不重启')
                    time.sleep(60)
                    continue
                # 待决策：不自动重启（等用户回复或超时）
                dec = os.path.join(WORKDIR, 'decision.json')
                if os.path.exists(dec):
                    try:
                        d = json.load(open(dec, encoding='utf-8'))
                        if d.get('status') == 'pending':
                            log('待用户决策中，不自动重启')
                            time.sleep(60)
                            continue
                    except Exception:
                        pass
                log('未发现下载进程，自动重启')
                notify('下载进程消失，已自动重启', 'guard 检测到 multi_download 进程不在，已拉起新进程。')
                start_batch()
            else:
                last = newest_activity()
                if last and (time.time() - last) > 900:
                    log(f'下载停滞 {int(time.time()-last)//60} 分钟，杀进程重启')
                    notify('下载停滞超过15分钟，已杀进程重启', '网络或进程挂起，守护已自动处理。')
                    subprocess.run(['powershell', '-NoProfile', '-Command',
                        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
                        "| Where-Object { $_.CommandLine -like '*multi_download*' } "
                        "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
                        capture_output=True, timeout=30)
                    time.sleep(5)
                    start_batch()
            # 磁盘检测
            free = disk_free_gb()
            if free < 20:
                notify('磁盘空间不足！', f'G盘仅剩 {free}GB，下载可能失败，请尽快处理。')
            # 完成检测
            d = done_count()
            if d != last_done:
                if d >= TOTAL:
                    notify('全部下载完成！', f'{d}/{TOTAL} 景已下载到 G:/insar_data/gulang2_sbas/')
                else:
                    notify(f'下载进度 {d}/{TOTAL}', f'刚完成第 {d} 景（{d}/{TOTAL}），继续下载中。')
                last_done = d
        except Exception as e:
            log(f'检查异常: {e}')
        time.sleep(60)

if __name__ == '__main__':
    main()
