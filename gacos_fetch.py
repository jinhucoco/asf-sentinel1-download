# -*- coding: utf-8 -*-
"""GACOS 结果自动收取 —— 技能正式版。

GACOS 处理完成后发邮件（含 tar.gz 下载链接），本脚本 IMAP 读邮箱 →
提取链接 → 下载 → 解压 ztd。支持指数退避轮询。

依赖: 无（标准库）

用法:
  python gacos_fetch.py --mail-config mail.json --out ./gacos [--expect 77] [--loop]
  mail.json: {"address":"you@163.com","authcode":"授权码","imap_host":"imap.163.com",
              "imap_port":993,"smtp_host":"smtp.163.com","smtp_port":465}
"""
import os, re, json, imaplib, email, time, sys, glob, tarfile, argparse
from email.header import decode_header
import urllib.request

def log(msg, logfile):
    line = f'[{time.strftime("%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    if logfile:
        with open(logfile, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

def fetch_mails(cfg, limit=40):
    """读最近邮件，返回 (主题, 正文) 列表"""
    imaplib.Commands['ID'] = ('AUTH', 'NONAUTH', 'SELECTED')
    M = imaplib.IMAP4_SSL(cfg['imap_host'], cfg.get('imap_port', 993), timeout=30)
    M.login(cfg['address'], cfg['authcode'])
    try:
        M._simple_command('ID', '("name" "gacos-fetch" "version" "1.0" "vendor" "pi")')
    except Exception:
        pass
    M.select('INBOX')
    _, data = M.search(None, 'ALL')
    ids = data[0].split()
    results = []
    for num in ids[-limit:]:
        _, md = M.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(md[0][1])
        def dec(v):
            if not v: return ''
            return ''.join(b.decode(p or 'utf-8') if isinstance(b, bytes) else b for b, p in decode_header(v))
        subject = dec(msg.get('Subject', ''))
        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True).decode('utf-8', 'replace')
                    break
        else:
            body = msg.get_payload(decode=True).decode('utf-8', 'replace') if msg.get_payload(decode=True) else ''
        results.append((subject, body))
    M.logout()
    return results

def main():
    ap = argparse.ArgumentParser(description='GACOS 结果收取')
    ap.add_argument('--mail-config', required=True, help='邮箱配置 JSON')
    ap.add_argument('--out', default='./gacos', help='输出目录')
    ap.add_argument('--expect', type=int, default=0, help='期望 ztd 数量（达到即停）')
    ap.add_argument('--loop', action='store_true', help='指数退避轮询：30s→1m→2m→5m→10m→30m')
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logfile = os.path.join(args.out, 'gacos_fetch.log')
    cfg = json.load(open(args.mail_config, encoding='utf-8'))

    def one_round():
        try:
            mails = fetch_mails(cfg)
        except Exception as e:
            log(f'IMAP 失败: {str(e)[:80]}', logfile)
            return 0
        got = 0
        for subject, body in mails:
            links = re.findall(r'https?://www\.gacos\.net/pub/gacosresult/[A-Za-z0-9]+\.tar\.gz', body)
            if not links:
                continue
            got += 1
            log(f'邮件: {subject[:35]} | 链接 {len(links)} 个', logfile)
            for url in links:
                name = url.split('/')[-1]
                tgz = os.path.join(args.out, name)
                if not (os.path.exists(tgz) and os.path.getsize(tgz) > 1000):
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=300) as r, open(tgz, 'wb') as f:
                        while True:
                            c = r.read(1 << 20)
                            if not c: break
                            f.write(c)
                    log(f'  下载: {name} ({os.path.getsize(tgz)/1e6:.1f}MB)', logfile)
                try:
                    with tarfile.open(tgz, 'r:gz') as t:
                        t.extractall(args.out)
                    ztds = [os.path.basename(m.name) for m in tarfile.open(tgz, 'r:gz').getmembers() if m.name.endswith('.ztd')]
                    log(f'  解压 ztd: {len(ztds)} 个', logfile)
                except Exception as e:
                    log(f'  解压失败: {str(e)[:60]}', logfile)
        n = len(glob.glob(os.path.join(args.out, '*.ztd')))
        log(f'当前 ztd: {n}{f"/{args.expect}" if args.expect else ""}', logfile)
        return n

    n = one_round()
    if not args.loop or (args.expect and n >= args.expect):
        print(f'ztd: {n}，完成')
        return

    # 指数退避轮询
    intervals = [30, 60, 120, 300, 600, 1800]
    round_no = 0
    while not args.expect or n < args.expect:
        time.sleep(intervals[min(round_no, len(intervals) - 1)])
        round_no += 1
        n = one_round()
    print(f'=== 全部 {args.expect} 个 ztd 收齐！===')

if __name__ == '__main__':
    main()
