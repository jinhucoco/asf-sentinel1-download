# -*- coding: utf-8 -*-
"""列出最近 GACOS 邮件及其链接（不下载）"""
import re, json, imaplib, email
from email.header import decode_header

cfg = json.load(open('D:/work/data/asf_experiment/mail_config.json', encoding='utf-8'))
imaplib.Commands['ID'] = ('AUTH', 'NONAUTH', 'SELECTED')
M = imaplib.IMAP4_SSL(cfg['imap_host'], cfg['imap_port'], timeout=30)
M.login(cfg['address'], cfg['authcode'])
M._simple_command('ID', '("name" "gacos-list" "version" "1.0" "vendor" "pi")')
M.select('INBOX')
_, data = M.search(None, 'ALL')
ids = data[0].split()
print(f'共 {len(ids)} 封邮件', flush=True)
for num in ids[-25:]:
    _, md = M.fetch(num, '(RFC822)')
    msg = email.message_from_bytes(md[0][1])
    def dec(v):
        if not v: return ''
        parts = decode_header(v)
        return ''.join(b.decode(p or 'utf-8') if isinstance(b, bytes) else b for b, p in parts)
    subj = dec(msg.get('Subject', ''))
    date = msg.get('Date', '')
    body = ''
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                body = part.get_payload(decode=True).decode('utf-8', 'replace')
                break
    else:
        body = msg.get_payload(decode=True).decode('utf-8', 'replace') if msg.get_payload(decode=True) else ''
    links = re.findall(r'https?://www\.gacos\.net/pub/gacosresult/[A-Za-z0-9]+\.tar\.gz', body)
    if links:
        print(f'[{date}] {subj[:50]} -> {len(links)} links: {links[0].split("/")[-1]}', flush=True)
M.logout()
