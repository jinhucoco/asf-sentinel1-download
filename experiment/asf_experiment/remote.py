# -*- coding: utf-8 -*-
"""ASF 下载邮件遥控模块：IMAP 轮询收件箱，解析指令执行。
用法: python -u remote.py   （常驻，每 120 秒轮询）
指令（邮件主题或正文含关键词，发件人须在白名单）：
  暂停/pause    继续/resume    跳过/skip    进度/status    停止/stop
控制文件：pause.flag / stop.flag / skip.flag（跳过清单，一行一个文件名）
"""
import os, re, time, glob, subprocess, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decision

WORKDIR = 'D:/work/data/asf_experiment'
OUT_DIR = 'G:/insar_data/gulang2_sbas'
MAIL_CFG = os.path.join(WORKDIR, 'mail_config.json')
LOGF = os.path.join(WORKDIR, 'remote.log')
POLL_SEC = 120
REPORT_START = 9 * 60 + 10   # 09:10 开始
REPORT_END = 18 * 60            # 18:00 结束
SKILL_DIR = 'C:/Users/86155/.pi/agent/skills/asf-sentinel1-download'
sys.path.insert(0, SKILL_DIR)

def log(msg):
    line = f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    with open(LOGF, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def load_cfg():
    if not os.path.exists(MAIL_CFG):
        return None
    return json.load(open(MAIL_CFG, encoding='utf-8'))

def send_mail(cfg, subject, body):
    """SMTP 发送邮件（通知回复）"""
    import smtplib
    from email.mime.text import MIMEText
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = cfg['address']
    msg['To'] = cfg['address']  # 发给自己
    host = cfg.get('smtp_host')
    port = cfg.get('smtp_port', 465)
    try:
        if port == 465:
            s = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            s = smtplib.SMTP(host, port, timeout=30)
            s.starttls()
        s.login(cfg['address'], cfg['authcode'])
        s.sendmail(cfg['address'], [cfg['address']], msg.as_string())
        s.quit()
        log(f'[mail] 已发送: {subject}')
        return True
    except Exception as e:
        log(f'[mail失败] {e}')
        return False

def in_report_hours():
    """是否在邮件汇报时间窗（每天 09:10-18:00），其余时段不打扰休息"""
    now = time.localtime()
    t = now.tm_hour * 60 + now.tm_min
    return REPORT_START <= t <= REPORT_END

def mail_report_enabled():
    """邮件报送总开关（notify_config.json mail_report.enabled）"""
    try:
        cfg = json.load(open(os.path.join(WORKDIR, 'notify_config.json'), encoding='utf-8'))
        return cfg.get('mail_report', {}).get('enabled', True)
    except Exception:
        return True

def task_active():
    """下载任务是否活跃：无 complete.flag（未完成）且（下载进程在跑 或 有 .part 分片）
    任务完成（complete.flag 存在）→ False，定时汇报自动停止"""
    if os.path.exists(os.path.join(WORKDIR, 'complete.flag')):
        return False
    if download_running():
        return True
    # 无进程但有无分片残留（中断/暂停中）
    return bool(glob.glob(os.path.join(OUT_DIR, '*.part*')))

def set_notify_switch(wechat=None, mail=None):
    """设置微信推送/邮件报送开关（遥控指令用），返回 (wechat, mail) 当前状态"""
    path = os.path.join(WORKDIR, 'notify_config.json')
    cfg = json.load(open(path, encoding='utf-8'))
    if wechat is not None:
        cfg['serverchan']['enabled'] = wechat
    if mail is not None:
        cfg['mail_report']['enabled'] = mail
    json.dump(cfg, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return cfg['serverchan'].get('enabled', True), cfg['mail_report'].get('enabled', True)

def load_processed():
    """已处理邮件的 Message-ID 集合（幂等去重）"""
    f = os.path.join(WORKDIR, 'processed_mail.json')
    try:
        return set(json.load(open(f, encoding='utf-8')))
    except Exception:
        return set()

def save_processed(ids):
    f = os.path.join(WORKDIR, 'processed_mail.json')
    json.dump(sorted(ids)[-500:], open(f, 'w', encoding='utf-8'))

def poll_inbox(cfg):
    """IMAP 读取最近邮件（ALL + Message-ID 去重，不依赖 UNSEEN 状态）"""
    import imaplib
    import email
    from email.header import decode_header
    processed = load_processed()
    try:
        # 163 强制要求 IMAP ID 命令（RFC 2971），否则 SELECT 报 Unsafe Login
        imaplib.Commands['ID'] = ('AUTH', 'NONAUTH', 'SELECTED')
        M = imaplib.IMAP4_SSL(cfg['imap_host'], cfg.get('imap_port', 993), timeout=30)
        M.login(cfg['address'], cfg['authcode'])
        try:
            typ, data = M._simple_command('ID', '("name" "pi-download-remote" "version" "1.0" "vendor" "pi-asf")')
            M._untagged_response(typ, data, 'ID')
        except Exception:
            pass  # 非 163 邮箱无此要求
        M.select('INBOX')
        _, data = M.search(None, 'ALL')
        ids = data[0].split()
        results = []
        new_processed = set(processed)
        # 最近 50 封（收件箱量小，避免用户回复被挤出窗口）
        for num in ids[-50:]:
            _, msg_data = M.fetch(num, '(RFC822)')
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            mid = msg.get('Message-ID', '').strip()
            if mid and mid in processed:
                continue
            if mid:
                new_processed.add(mid)
            def dec(v):
                if not v: return ''
                parts = decode_header(v)
                return ''.join(b.decode(p or 'utf-8') if isinstance(b, bytes) else b for b, p in parts)
            sender = dec(msg.get('From', ''))
            subject = dec(msg.get('Subject', ''))
            body = ''
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_payload(decode=True).decode('utf-8', 'replace')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', 'replace') if msg.get_payload(decode=True) else ''
            # 跳过系统自己发的（From 和 To 相同且为系统通知）—— 由指令关键词自然处理
            results.append((sender, subject, body))
        save_processed(new_processed)
        M.logout()
        return results
    except Exception as e:
        log(f'[IMAP失败] {e}')
        return []

def is_trusted(sender, cfg):
    """白名单校验：精确匹配邮箱地址（防子串/前缀伪造）"""
    trusted = cfg.get('trusted_sender', '')
    if not trusted:
        return False
    import re
    s = sender or ''
    # 优先取尖括号内标准邮箱格式；否则整串精确匹配
    m = re.search(r'<([\w.+-]+@[\w.-]+\.[a-z]{2,})>', s)
    addr = m.group(1).lower() if m else s.strip().strip('"').lower()
    return addr == trusted.lower()

def is_system_mail(subject):
    """系统域邮件：主题含 [ASF下载] 的都跳过（含 Re/回复 变体，防自我回复循环）"""
    return '[ASF下载]' in subject

def clean_body(body):
    """去掉邮件回复引用部分，只保留用户实际输入"""
    markers = ['-----原始邮件-----', '------------------ 原始邮件', '-------- 原始邮件',
               'On ', '发自我的', '----- Reply Message -----',
               '---- 回复邮件', '----- 回复邮件']
    for m in markers:
        idx = body.find(m)
        if idx > 0:
            body = body[:idx]
    # 去掉引用行（> 开头）
    lines = [l for l in body.split('\n') if not l.strip().startswith('>')]
    return '\n'.join(lines)

def current_downloading():
    """当前正在下载的文件名（从分片推断）"""
    for p in glob.glob(os.path.join(OUT_DIR, '*.part*')):
        name = os.path.basename(p)
        if '.part' in name:
            return name.split('.part')[0]
    return ''

def kill_download():
    subprocess.run(['powershell', '-NoProfile', '-Command',
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
        "| Where-Object { $_.CommandLine -like '*multi_download*' } "
        "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
        capture_output=True, timeout=30)

def download_running():
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
          "| Where-Object { $_.CommandLine -like '*multi_download*' } "
          "| Measure-Object | Select-Object -ExpandProperty Count")
    try:
        out = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        return out not in ('', '0')
    except Exception:
        return True

def status_text():
    done = sum(1 for f in glob.glob(os.path.join(OUT_DIR, '*.zip')) if os.path.getsize(f) > 1024)
    parts = glob.glob(os.path.join(OUT_DIR, '*.part*'))
    cur = sum(os.path.getsize(p) for p in parts)
    cur_name = current_downloading()
    paused = os.path.exists(os.path.join(WORKDIR, 'pause.flag'))
    stopped = os.path.exists(os.path.join(WORKDIR, 'stop.flag'))
    return (f'完成 {done}/154 景\n'
            f'当前文件: {cur_name[:45]}\n'
            f'当前分片: {cur/1e9:.2f} GB\n'
            f'状态: {"暂停" if paused else "已停止" if stopped else "下载中"}\n'
            f'进程: {"运行中" if download_running() else "未运行"}')

def full_report():
    """完整下载状况报告（邮件汇报格式）"""
    import subprocess as _sp
    lines = []
    lines.append('=' * 50)
    lines.append(f'ASF 下载状况汇报  {time.strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append('=' * 50)
    # 进程
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
          "| Select-Object ProcessId,CommandLine "
          "| Format-Table -HideTableHeaders -Wrap")
    try:
        out = _sp.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True, timeout=30).stdout
        has_dl = 'multi_download' in out
        has_gd = 'guard' in out
        has_rm = 'remote' in out
    except Exception:
        has_dl = has_gd = has_rm = False
    lines.append(f'进程: 下载={"运行中" if has_dl else "DOWN!"} | 守护={"运行中" if has_gd else "DOWN!"} | 遥控={"运行中" if has_rm else "DOWN!"}')
    # 进度
    done = sum(1 for f in glob.glob(os.path.join(OUT_DIR, '*.zip')) if os.path.getsize(f) > 1024)
    parts = glob.glob(os.path.join(OUT_DIR, '*.part*'))
    cur = sum(os.path.getsize(p) for p in parts)
    cur_name = current_downloading()
    lines.append(f'完成: {done}/154 景 | 当前: {cur_name[:40]}')
    if parts:
        lines.append(f'当前文件进度: {cur/1e9:.2f} GB')
    # 速度估算（日志时间戳）
    # 最近日志
    logf = os.path.join(WORKDIR, 'multi_run.log')
    if os.path.exists(logf):
        with open(logf, encoding='utf-8', errors='replace') as f:
            logs = f.readlines()
        errs = [l for l in logs if '错误' in l or '失败' in l or 'WARN' in l or '作废' in l]
        lines.append(f'日志: 总 {len(logs)} 行 | 错误/失败 {len(errs)} 条')
        if errs:
            lines.append('最近异常:')
            for l in errs[-3:]:
                lines.append('  ' + l.strip()[:90])
    # 磁盘
    try:
        d = _sp.run(['df', '-h', '/g'], capture_output=True, text=True).stdout.split('\n')
        if len(d) > 1:
            lines.append('G盘: ' + ' '.join(d[1].split()[:6]))
    except Exception:
        pass
    lines.append('=' * 50)
    return '\n'.join(lines)

def execute(cfg, sender, subject, body):
    # 只匹配主题 + 清洗后的正文（用户实际输入），避免引用误触发
    text = (subject + ' ' + body).lower()
    reply = None
    if re.search(r'暂停|pause', text):
        open(os.path.join(WORKDIR, 'pause.flag'), 'w').close()
        if os.path.exists(os.path.join(WORKDIR, 'stop.flag')):
            os.remove(os.path.join(WORKDIR, 'stop.flag'))
        kill_download()
        reply = '已暂停下载（守护不会重启）。回复"继续"恢复。'
    elif re.search(r'继续|resume', text):
        if os.path.exists(os.path.join(WORKDIR, 'pause.flag')):
            os.remove(os.path.join(WORKDIR, 'pause.flag'))
        if os.path.exists(os.path.join(WORKDIR, 'stop.flag')):
            os.remove(os.path.join(WORKDIR, 'stop.flag'))
        kill_download()  # 确保单实例
        time.sleep(3)
        subprocess.Popen([sys.executable, '-u', 'multi_download.py'], cwd=WORKDIR,
                         env=dict(os.environ, PYTHONIOENCODING='utf-8'),
                         stdout=open(os.path.join(WORKDIR, 'multi_run.log'), 'a', encoding='utf-8'),
                         stderr=subprocess.STDOUT,
                         creationflags=0x00000008 | 0x00000200, close_fds=True)
        reply = '已恢复下载（断点续传继续）。'
    elif re.search(r'跳过|skip', text):
        cur = current_downloading()
        if cur:
            skip_file = os.path.join(WORKDIR, 'skip.flag')
            with open(skip_file, 'a', encoding='utf-8') as f:
                f.write(cur + '\n')
            for p in glob.glob(os.path.join(OUT_DIR, cur + '.part*')):
                try: os.remove(p)
                except OSError: pass
            kill_download()
            time.sleep(3)
            subprocess.Popen([sys.executable, '-u', 'multi_download.py'], cwd=WORKDIR,
                             env=dict(os.environ, PYTHONIOENCODING='utf-8'),
                             stdout=open(os.path.join(WORKDIR, 'multi_run.log'), 'a', encoding='utf-8'),
                             stderr=subprocess.STDOUT,
                             creationflags=0x00000008 | 0x00000200, close_fds=True)
            reply = f'已跳过当前文件并继续下一个:\n{cur[:60]}'
        else:
            reply = '当前没有正在下载的文件（可能已完成或未运行）。'
    elif re.search(r'进度|status|状态', text):
        reply = full_report()
    elif re.search(r'关闭微信|关微信|停微信|微信推送关|微信关', text):
        w, m = set_notify_switch(wechat=False)
        reply = f'已关闭微信推送（当前：微信={"开" if w else "关"}，邮件汇报={"开" if m else "关"}）'
    elif re.search(r'开启微信|开微信|打开微信|微信推送开|微信开', text):
        w, m = set_notify_switch(wechat=True)
        reply = f'已开启微信推送（当前：微信={"开" if w else "关"}，邮件汇报={"开" if m else "关"}）'
    elif re.search(r'关闭汇报|关汇报|停汇报|邮件汇报关|汇报关', text):
        w, m = set_notify_switch(mail=False)
        reply = f'已关闭邮件汇报（当前：微信={"开" if w else "关"}，邮件汇报={"开" if m else "关"}）'
    elif re.search(r'开启汇报|开汇报|打开汇报|邮件汇报开|汇报开', text):
        w, m = set_notify_switch(mail=True)
        reply = f'已开启邮件汇报（当前：微信={"开" if w else "关"}，邮件汇报={"开" if m else "关"}）'
    elif re.search(r'停止|stop', text):
        open(os.path.join(WORKDIR, 'stop.flag'), 'w').close()
        if os.path.exists(os.path.join(WORKDIR, 'pause.flag')):
            os.remove(os.path.join(WORKDIR, 'pause.flag'))
        kill_download()
        reply = '已彻底停止下载任务。如需恢复删除 stop.flag 后启动。'
    if reply:
        send_mail(cfg, '[ASF下载] 指令已执行', reply)

def main():
    cfg = load_cfg()
    if not cfg:
        log('未找到 mail_config.json，等待配置...')
        return
    log(f'遥控启动: {cfg["address"]}（每 {POLL_SEC}s 轮询，每 2h 邮件汇报）')
    last_report = 0
    _reported_done = False
    while True:
        try:
            # 1. 超时决策自动执行默认
            decision.auto_resolve(cfg)
            # 2. 待决策时：邮件回复当作选项答案（决策邮件是 [ASF下载] 域）
            pend = decision.pending()
            if pend:
                for sender, subject, body in poll_inbox(cfg):
                    if not is_trusted(sender, cfg):
                        continue
                    opt = decision.match_reply(subject + ' ' + clean_body(body))
                    if opt:
                        log(f'决策回复: {opt["key"]}')
                        decision.answer(opt['key'], cfg)
                    else:
                        log(f'回复无法匹配选项: {(subject+body)[:40]}')
            else:
                # 3. 无待决时：遥控指令（仅处理非 [ASF下载] 域的用户新邮件）
                for sender, subject, body in poll_inbox(cfg):
                    if is_system_mail(subject):
                        continue  # 系统域邮件跳过
                    if is_trusted(sender, cfg):
                        log(f'收到指令: {subject[:30]}')
                        execute(cfg, sender, subject, clean_body(body))
                    else:
                        log(f'忽略未知发件人: {sender[:40]}')
        except Exception as e:
            log(f'轮询异常: {e}')
        # 定时邮件汇报：仅当下载任务活跃时（任务完成自动停止，不打扰）
        if not task_active():
            if not _reported_done:
                _reported_done = True
                log('[DONE] 下载任务不活跃（已完成或未开始），定时邮件汇报已停止，静默待命')
        else:
            _reported_done = False
            # 每 2 小时，09:10-18:00 时间窗内，开关开启时
            if mail_report_enabled() and time.time() - last_report >= 7200 and in_report_hours():
                last_report = time.time()
                send_mail(cfg, f'[ASF下载] 定时进度汇报 {time.strftime("%H:%M")}', full_report())
            # 18:00 额外最终汇报（距上次 ≥30 分钟才发，避免与 17:10 重复）
            elif (mail_report_enabled() and time.localtime().tm_hour == 18 and time.localtime().tm_min == 0
                  and time.time() - last_report >= 1800):
                last_report = time.time()
                send_mail(cfg, '[ASF下载] 18:00 最终进度汇报', full_report())
        time.sleep(POLL_SEC)

if __name__ == '__main__':
    main()
