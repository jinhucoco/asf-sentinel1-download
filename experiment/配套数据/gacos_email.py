# -*- coding: utf-8 -*-
"""GACOS 结果自动收取：IMAP 读邮箱 → 提取 tar.gz 链接 → 下载解压校验。
用法: python gacos_email.py
"""
import os, re, json, imaplib, email, time, sys, glob
from email.header import decode_header
import urllib.request

WORKDIR = 'D:/work/data/配套数据'
GACOS_DIR = os.path.join(WORKDIR, 'GACOS')
LOG = os.path.join(WORKDIR, 'gacos_fetch.log')

def log(msg):
    line = f'[{time.strftime("%H:%M:%S")}] {msg}'
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def load_mail_cfg():
    return json.load(open('D:/work/data/asf_experiment/mail_config.json', encoding='utf-8'))

def fetch_gacos_mails(cfg, limit=30):
    """读取最近邮件，返回含 GACOS 链接的 (主题, 正文) 列表"""
    imaplib.Commands['ID'] = ('AUTH', 'NONAUTH', 'SELECTED')
    M = imaplib.IMAP4_SSL(cfg['imap_host'], cfg['imap_port'], timeout=30)
    M.login(cfg['address'], cfg['authcode'])
    M._simple_command('ID', '("name" "gacos-fetch" "version" "1.0" "vendor" "pi")')
    M.select('INBOX')
    _, data = M.search(None, 'ALL')
    ids = data[0].split()
    results = []
    for num in ids[-limit:]:
        _, md = M.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(md[0][1])
        def dec(v):
            if not v: return ''
            parts = decode_header(v)
            return ''.join(b.decode(p or 'utf-8') if isinstance(b, bytes) else b for b, p in parts)
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

def extract_links(body):
    """提取 GACOS tar.gz 下载链接"""
    return re.findall(r'https?://www\.gacos\.net/pub/gacosresult/[A-Za-z0-9]+\.tar\.gz', body)

def download_targz(url, out_dir):
    name = url.split('/')[-1]
    dest = os.path.join(out_dir, name)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return 'skip', dest
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, 'wb') as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk: break
            f.write(chunk)
    return 'ok', dest

def extract_and_check(tgz, out_dir):
    import tarfile
    with tarfile.open(tgz, 'r:gz') as t:
        t.extractall(out_dir)
    # 返回提取的 ztd 文件
    base = os.path.splitext(os.path.basename(tgz))[0].replace('.tar', '')
    return base

def main():
    os.makedirs(GACOS_DIR, exist_ok=True)
    cfg = load_mail_cfg()
    log('读取邮箱 GACOS 邮件...')
    try:
        mails = fetch_gacos_mails(cfg)
    except Exception as e:
        log(f'IMAP 失败: {str(e)[:80]}')
        return
    found = 0
    for subject, body in mails:
        links = extract_links(body)
        if not links:
            continue
        found += 1
        log(f'邮件: {subject[:40]} | 链接 {len(links)} 个')
        for url in links:
            st, tgz = download_targz(url, GACOS_DIR)
            if st != 'skip':
                log(f'  下载: {os.path.basename(tgz)} ({os.path.getsize(tgz)/1e6:.1f}MB)')
            try:
                import tarfile
                with tarfile.open(tgz, 'r:gz') as t:
                    t.extractall(GACOS_DIR)
                ztds = [os.path.basename(m.name) for m in tarfile.open(tgz, 'r:gz').getmembers() if m.name.endswith('.ztd')]
                log(f'  解压 ztd: {ztds}')
            except Exception as e:
                log(f'  解压失败: {str(e)[:60]}')
    if found == 0:
        log('未找到 GACOS 结果邮件（可能还在处理中）')

    # 汇总 ztd 数量
    ztds = sorted(glob.glob(os.path.join(GACOS_DIR, '*.ztd')))
    log(f'=== 当前 ztd 总数: {len(ztds)} ===')
    if ztds:
        log('已有: ' + ' '.join(os.path.basename(z)[:8] for z in ztds[:10]) + (' ...' if len(ztds) > 10 else ''))

if __name__ == '__main__':
    main()
