# -*- coding: utf-8 -*-
"""ASF 下载决策管理器：需要用户决策时，生成决策问题（含选项），
通过微信（Server酱）+ 邮件推送，用户回复选项编号即执行。
超时（默认 60 分钟）未回复 → 执行默认选项，保证任务不卡死。

决策文件: D:/work/data/asf_experiment/decision.json
状态: pending -> answered / resolved
"""
import os, json, time, glob, subprocess, sys

WORKDIR = 'D:/work/data/asf_experiment'
DEC_FILE = os.path.join(WORKDIR, 'decision.json')
NOTIFY_CFG = os.path.join(WORKDIR, 'notify_config.json')
MAIL_CFG = os.path.join(WORKDIR, 'mail_config.json')
LOG = os.path.join(WORKDIR, 'decision.log')

def log(msg):
    line = f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def load():
    if os.path.exists(DEC_FILE):
        try:
            return json.load(open(DEC_FILE, encoding='utf-8'))
        except Exception:
            return None
    return None

def pending():
    d = load()
    return d if d and d.get('status') == 'pending' else None

def create(question, options, default_key, timeout_min=60):
    """创建决策：options = [{'key':'A','text':'...','action':'...'}, ...]"""
    d = {
        'id': f'dec_{int(time.time())}',
        'question': question,
        'options': options,
        'default': default_key,
        'created_at': time.time(),
        'deadline': time.time() + timeout_min * 60,
        'status': 'pending',
        'choice': None,
    }
    with open(DEC_FILE, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    log(f'决策创建: {question}')
    return d

def push(cfg_notify=None, cfg_mail=None):
    """推送决策：Server酱微信 + 邮件，附选项（自动加载配置）"""
    if cfg_notify is None:
        try:
            cfg_notify = json.load(open(NOTIFY_CFG, encoding='utf-8')).get('serverchan', {})
        except Exception:
            cfg_notify = {}
    if cfg_mail is None:
        try:
            cfg_mail = json.load(open(MAIL_CFG, encoding='utf-8'))
        except Exception:
            cfg_mail = None
    d = load()
    if not d or d['status'] != 'pending':
        return
    opts = '\n'.join(f'{o["key"]}. {o["text"]}' for o in d['options'])
    body = (f'{d["question"]}\n\n选项：\n{opts}\n\n'
            f'回复邮件（主题或正文写选项编号，如 A）即可。\n'
            f'{d["deadline"] and ""}{time.strftime("%H:%M", time.localtime(d["deadline"]))} 前未回复将自动执行默认选项（{d["default"]}）。')
    # 微信推送（含选项）
    try:
        if cfg_notify and cfg_notify.get('enabled') and cfg_notify.get('sendkey'):
            import urllib.request, urllib.parse
            url = f'https://sctapi.ftqq.com/{cfg_notify["sendkey"]}.send'
            data = urllib.parse.urlencode({'title': f'[ASF下载·需决策] {d["question"][:30]}', 'desp': body}).encode()
            urllib.request.urlopen(urllib.request.Request(url, data=data, method='POST'), timeout=15)
            log('决策已推送到微信')
    except Exception as e:
        log(f'微信推送失败: {e}')
    # 邮件推送（仅每天 09:10-18:00 时间窗内，且 mail_report 开关开启；微信已即时推送）
    try:
        now = time.localtime()
        t = now.tm_hour * 60 + now.tm_min
        mail_on = True
        try:
            nc = json.load(open(NOTIFY_CFG, encoding='utf-8'))
            mail_on = nc.get('mail_report', {}).get('enabled', True)
        except Exception:
            pass
        if (9 * 60 + 10) <= t <= (18 * 60) and mail_on and cfg_mail:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['Subject'] = f'[ASF下载·需决策] {d["question"][:30]}'
            msg['From'] = cfg_mail['address']; msg['To'] = cfg_mail['address']
            host, port = cfg_mail['smtp_host'], cfg_mail.get('smtp_port', 465)
            s = smtplib.SMTP_SSL(host, port, timeout=30) if port == 465 else smtplib.SMTP(host, port, timeout=30)
            if port != 465: s.starttls()
            s.login(cfg_mail['address'], cfg_mail['authcode'])
            s.sendmail(cfg_mail['address'], [cfg_mail['address']], msg.as_string())
            s.quit()
            log('决策已发送到邮件')
    except Exception as e:
        log(f'邮件推送失败: {e}')

def match_reply(text):
    """把用户回复解析为选项：优先匹配编号(A/B/C/1/2/3)，其次选项文本关键词"""
    d = load()
    if not d or d['status'] != 'pending':
        return None
    t = (text or '').strip().lower()
    for o in d['options']:
        key = o['key'].lower()
        if t == key or t == key + '.' or t.isdigit() and int(t) == d['options'].index(o) + 1:
            return o
        # 文本关键词匹配：选项文本包含在回复中，或回复是选项文本的子串
        if len(t) > 1 and (o['text'].lower() in t or t in o['text'].lower()):
            return o
    return None

def answer(choice_key, cfg_mail=None):
    """记录决策结果并执行动作"""
    d = load()
    if not d:
        return
    opt = next((o for o in d['options'] if o['key'].lower() == choice_key.lower()), None)
    if not opt:
        log(f'无效选项: {choice_key}')
        return
    d['status'] = 'answered'
    d['choice'] = opt['key']
    d['answered_at'] = time.time()
    json.dump(d, open(DEC_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    log(f'决策已答: {choice_key} -> {opt["action"]}')
    execute_action(opt['action'], cfg_mail)

def auto_resolve(cfg_mail=None):
    """超时未回复 → 执行默认选项"""
    d = load()
    if not d or d['status'] != 'pending':
        return False
    if time.time() < d['deadline']:
        return False
    log(f'决策超时，执行默认选项: {d["default"]}')
    d['status'] = 'answered'
    d['choice'] = d['default']
    d['answered_at'] = time.time()
    json.dump(d, open(DEC_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    execute_action(d['default'], cfg_mail)
    return True

def execute_action(action, cfg_mail=None):
    """执行决策动作（与遥控指令复用同一套控制标记）"""
    if action == 'pause':
        open(os.path.join(WORKDIR, 'pause.flag'), 'w').close()
        if os.path.exists(os.path.join(WORKDIR, 'stop.flag')): os.remove(os.path.join(WORKDIR, 'stop.flag'))
        _kill()
        log('决策动作: 暂停')
        _reply_mail(cfg_mail, '[ASF下载] 已按决策暂停', '已执行：暂停下载。')
    elif action == 'stop':
        open(os.path.join(WORKDIR, 'stop.flag'), 'w').close()
        if os.path.exists(os.path.join(WORKDIR, 'pause.flag')): os.remove(os.path.join(WORKDIR, 'pause.flag'))
        _kill()
        log('决策动作: 停止')
        _reply_mail(cfg_mail, '[ASF下载] 已按决策停止', '已执行：停止任务。')
    elif action == 'resume' or action == 'resume_skip_failed':
        for f in ('pause.flag', 'stop.flag'):
            if os.path.exists(os.path.join(WORKDIR, f)): os.remove(os.path.join(WORKDIR, f))
        _kill()
        time.sleep(3)
        subprocess.Popen([sys.executable, '-u', 'multi_download.py'], cwd=WORKDIR,
                         env=dict(os.environ, PYTHONIOENCODING='utf-8'),
                         stdout=open(os.path.join(WORKDIR, 'multi_run.log'), 'a', encoding='utf-8'),
                         stderr=subprocess.STDOUT, creationflags=0x00000008 | 0x00000200, close_fds=True)
        log('决策动作: 继续下载')
        _reply_mail(cfg_mail, '[ASF下载] 已按决策继续', '已执行：继续下载（跳过失败文件）。')
    elif action == 'skip':
        cur = _current_downloading()
        if cur:
            with open(os.path.join(WORKDIR, 'skip.flag'), 'a', encoding='utf-8') as f:
                f.write(cur + '\n')
            # 删除该文件的分片（正确的 G 盘路径）
            for p in glob.glob(os.path.join('G:/insar_data/gulang2_sbas', cur + '.part*')):
                try: os.remove(p)
                except OSError: pass
        _kill()
        time.sleep(3)
        subprocess.Popen([sys.executable, '-u', 'multi_download.py'], cwd=WORKDIR,
                         env=dict(os.environ, PYTHONIOENCODING='utf-8'),
                         stdout=open(os.path.join(WORKDIR, 'multi_run.log'), 'a', encoding='utf-8'),
                         stderr=subprocess.STDOUT, creationflags=0x00000008 | 0x00000200, close_fds=True)
        log('决策动作: 跳过当前')
        _reply_mail(cfg_mail, '[ASF下载] 已按决策跳过', '已执行：跳过当前文件继续。')

def _kill():
    subprocess.run(['powershell', '-NoProfile', '-Command',
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
        "| Where-Object { $_.CommandLine -like '*multi_download*' } "
        "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
        capture_output=True, timeout=30)

def _current_downloading():
    OUT_DIR = 'G:/insar_data/gulang2_sbas'
    for p in glob.glob(os.path.join(OUT_DIR, '*.part*')):
        name = os.path.basename(p)
        if '.part' in name:
            return name.split('.part')[0]
    return ''

def _reply_mail(cfg_mail, subject, body):
    if not cfg_mail:
        return
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = cfg_mail['address']; msg['To'] = cfg_mail['address']
        s = smtplib.SMTP_SSL(cfg_mail['smtp_host'], cfg_mail.get('smtp_port', 465), timeout=30)
        s.login(cfg_mail['address'], cfg_mail['authcode'])
        s.sendmail(cfg_mail['address'], [cfg_mail['address']], msg.as_string())
        s.quit()
    except Exception as e:
        log(f'回复邮件失败: {e}')

def resolve_if_answered(cfg_mail=None):
    """守护调用：决策已被用户回答则确保动作执行"""
    return load() and load().get('status') == 'answered'

if __name__ == '__main__':
    # 测试：创建示例决策
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--test', action='store_true')
    args = ap.parse_args()
    if args.test:
        create('连续多个文件下载失败，如何处理？',
               [{'key': 'A', 'text': '跳过失败文件继续下载', 'action': 'resume_skip_failed'},
                {'key': 'B', 'text': '暂停下载，等我处理', 'action': 'pause'},
                {'key': 'C', 'text': '停止整个任务', 'action': 'stop'}],
               default_key='A', timeout_min=60)
        print('测试决策已创建:', DEC_FILE)
