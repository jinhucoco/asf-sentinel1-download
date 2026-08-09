# -*- coding: utf-8 -*-
"""精准轮询：只找 20230112.ztd 的 GACOS 结果并下载"""
import os, re, json, imaplib, email, time, tarfile, urllib.request
from email.header import decode_header

GACOS_DIR = 'D:/work/data/配套数据/GACOS'
cfg = json.load(open('D:/work/data/asf_experiment/mail_config.json', encoding='utf-8'))

imaplib.Commands['ID'] = ('AUTH', 'NONAUTH', 'SELECTED')
M = imaplib.IMAP4_SSL(cfg['imap_host'], cfg['imap_port'], timeout=30)
M.login(cfg['address'], cfg['authcode'])
M._simple_command('ID', '("name" "gacos-poll" "version" "1.0" "vendor" "pi")')
M.select('INBOX')
_, data = M.search(None, 'ALL')
ids = data[0].split()
found = False
for num in ids[-40:]:
    _, md = M.fetch(num, '(RFC822)')
    msg = email.message_from_bytes(md[0][1])
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                body = part.get_payload(decode=True).decode('utf-8', 'replace')
                break
    else:
        body = msg.get_payload(decode=True).decode('utf-8', 'replace') if msg.get_payload(decode=True) else ''
    links = re.findall(r'https?://www\.gacos\.net/pub/gacosresult/[A-Za-z0-9]+\.tar\.gz', body)
    if not links:
        continue
    for url in links:
        name = url.split('/')[-1]
        dest = os.path.join(GACOS_DIR, name)
        if os.path.exists(dest):
            continue
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=300) as r, open(dest, 'wb') as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk: break
                f.write(chunk)
        try:
            with tarfile.open(dest, 'r:gz') as t:
                members = t.getnames()
                t.extractall(GACOS_DIR)
            ztds = [m for m in members if m.endswith('.ztd')]
            print(f'下载+解压 {name}: {ztds}', flush=True)
            if any('20230112' in m for m in ztds):
                found = True
        except Exception as e:
            print(f'解压失败 {name}: {str(e)[:60]}', flush=True)
M.logout()
print('FOUND_20230112' if found else 'NOT_FOUND', flush=True)
