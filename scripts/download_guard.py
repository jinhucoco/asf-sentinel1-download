"""ASF 多线程下载守护（download_guard.py）

配合 scripts/multi_download.py 使用：定时体检 + 邮件/微信推送 + 卡死/死亡
自动重启 + 完成通知。守护会先启动（或接管已运行）下载，再进入监控循环。

用法（示例）:
    python download_guard.py --list 清单.csv --out G:/minqin_sentinel1 [--threads 8]
                             [--work-start 9] [--work-end 18] [--report-every 2]
                             [--stall-min 40] [--no-restart]
                             [--mail-config mail_config.json] [--notify-config notify_config.json]

推送策略:
- 定时进度推送：仅【白天工作时间】按整点网格发（默认 09:00-18:00 每 2 小时一封，
  即 9/11/13/15/17 点），夜间静默不打扰；
- 事件推送：启动/完成/重启/卡死 等即时发送（不受时段限制）；
- 邮件读 mail_config.json（address/authcode/smtp_host/smtp_port，163/QQ SMTP 授权码）；
  微信读 notify_config.json（serverchan.sendkey，sct.ftqq.com），双通道同发。
- 自动重启：下载进程死亡/卡死（--stall-min 分钟无字节增长）自动重启，断点续传无缝
  续跑；complete.flag 已存在时绝不重启（防无限重启）。
"""

import argparse
import json
import os
import re
import smtplib
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText

SKILL_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
DEFAULT_WORK_START = 9
DEFAULT_WORK_END = 18
DEFAULT_REPORT_EVERY = 2
DEFAULT_STALL_MIN = 40


# ==================== 纯函数（可离线测试） ====================


def next_report_time(work_start, work_end, report_every, now=None):
    """下一个计划推送时刻（今日 work_start 起每 report_every 小时整点网格）。

    当前已过网格点（或 ≥ work_end）→ None（今天不再推，夜间静默）。
    now: 可注入（测试用），默认 datetime.now()。
    """
    now = now or datetime.now()
    today = now.date()
    for h in range(work_start, work_end, report_every):
        t = datetime(today.year, today.month, today.day, h)
        if now < t:
            return t
    return None


# ==================== 纯函数（可离线测试） ====================


def parse_progress(log_path):
    """解析 multi_download.log → {ok, fail, skip, current, total}

    识别行: "[12/85] [OK] xxx" / "[FAIL]" / "跳过(已完成)" / "[DL] 当前文件"
    """
    ok = fail = skip = 0
    current = ""
    total = 0
    if not os.path.exists(log_path):
        return {"ok": 0, "fail": 0, "skip": 0, "current": "", "total": 0}
    with open(log_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.search(r"\[(\d+)/(\d+)\]", line)
            if m:
                total = int(m.group(2))
            if "[OK]" in line:
                ok += 1
            elif "[FAIL]" in line:
                fail += 1
            elif "跳过(已完成)" in line:
                skip += 1
            if "[DL]" in line:
                current = line.strip()[-60:]
    return {"ok": ok, "fail": fail, "skip": skip, "current": current, "total": total}


def should_restart(alive, bytes_growing, stall_seconds, stall_min):
    """死亡 或 卡死（stall_min 分钟无字节增长）→ True"""
    return not alive or (not bytes_growing and stall_seconds >= stall_min * 60)


def dir_bytes(out):
    """输出目录当前体积（含 .part 分片）"""
    total = 0
    try:
        for name in os.listdir(out):
            p = os.path.join(out, name)
            if os.path.isfile(p):
                total += os.path.getsize(p)
    except OSError:
        pass
    return total


# ==================== 邮件 / 微信 ====================


def send_mail(cfg, subject, body):
    """163/QQ SMTP 授权码发信（mail_config.json: address/authcode/smtp_host/smtp_port）"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = cfg["address"]
    msg["To"] = cfg["address"]
    with smtplib.SMTP_SSL(cfg["smtp_host"], int(cfg.get("smtp_port", 465)), timeout=30) as s:
        s.login(cfg["address"], cfg["authcode"])
        s.sendmail(cfg["address"], [cfg["address"]], msg.as_string())


def send_wechat(notify, title, body):
    """Server酱推送（可选；notify_config.json: serverchan.enabled/sendkey）"""
    sc = (notify or {}).get("serverchan", {})
    if not sc.get("enabled") or not sc.get("sendkey"):
        return False
    url = "https://sctapi.ftqq.com/{}.send".format(sc["sendkey"])
    data = urllib.parse.urlencode({"title": title[:32], "desp": body[:8000]}).encode()
    urllib.request.urlopen(url, data=data, timeout=20)
    return True


def notify_all(mail, notify, title, body):
    """邮件 + 微信（有配置就发），返回是否至少发出一条"""
    sent = False
    if mail.get("address") and mail.get("authcode"):
        try:
            send_mail(mail, title, body)
            sent = True
        except Exception as e:
            log_err(f"邮件发送失败: {str(e)[:80]}")
    try:
        sent = send_wechat(notify, title, body) or sent
    except Exception as e:
        log_err(f"微信推送失败: {str(e)[:80]}")
    return sent


# ==================== 进程检测 / 重启 ====================


def detect_running(out):
    """找正在跑的 multi_download 进程（命令行含 --out <out>）→ pid 或 None"""
    norm = os.path.normcase(os.path.abspath(out))
    try:
        r = subprocess.run(
            [
                "wmic",
                "process",
                "where",
                "name like '%python%'",
                "get",
                "processid,commandline",
                "/format:csv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        for line in r.stdout.splitlines():
            if "multi_download" not in line:
                continue
            if norm in os.path.normcase(line):
                m = re.search(r"(\d+)\s*$", line.strip())
                if m:
                    return int(m.group(1))
    except Exception:
        pass
    return None


def is_alive(pid):
    """Windows tasklist 查进程存活；查不到时假定存活避免误重启"""
    try:
        r = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return str(pid) in r.stdout
    except Exception:
        return True


def kill_pid(pid):
    try:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=20)
    except Exception:
        pass


def build_download_cmd(args):
    """由守护参数重建 multi_download 命令（重启/启动用）"""
    cmd = [
        sys.executable,
        os.path.join(SKILL_SCRIPTS, "multi_download.py"),
        "--list",
        args.list,
        "--out",
        args.out,
    ]
    if args.threads:
        cmd += ["--threads", str(args.threads)]
    if args.verify_aoi:
        cmd += ["--verify-aoi", args.verify_aoi]
    if args.strict:
        cmd += ["--strict"]
    return cmd


def log(glog, msg):
    line = f"[{datetime.now().strftime('%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(glog, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_err(msg):
    print(f"[ERR] {msg}", flush=True)


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def summary_body(logfile, prog, out):
    lines = []
    if os.path.exists(logfile):
        try:
            with open(logfile, encoding="utf-8", errors="replace") as f:
                tail = f.readlines()[-8:]
            lines = ["".join(tail[-8:])]
        except OSError:
            pass
    return (
        f"完成: {prog['ok']}/{prog['total']} 个文件 | 失败: {prog['fail']} | 跳过: {prog['skip']}\n"
        f"当前: {prog['current'] or '无'}\n"
        f"已下载: {dir_bytes(out) / 1e9:.2f} GB\n"
        f"--- 日志尾部 ---\n" + "\n".join(lines)
    )


# ==================== 主循环 ====================


def main():
    ap = argparse.ArgumentParser(description="ASF 多线程下载守护（定时邮件 + 自动重启）")
    ap.add_argument("--list", required=True, help="下载清单 CSV（传给 multi_download.py）")
    ap.add_argument("--out", required=True, help="下载目录")
    ap.add_argument("--threads", type=int, default=8, help="分片线程数")
    ap.add_argument("--verify-aoi", help="下载前逐时相覆盖复检 AOI（透传）")
    ap.add_argument("--strict", action="store_true", help="复检未达标终止（透传）")
    ap.add_argument(
        "--work-start",
        type=int,
        default=DEFAULT_WORK_START,
        help="定时进度推送开始小时（默认 9，夜间静默）",
    )
    ap.add_argument(
        "--work-end",
        type=int,
        default=DEFAULT_WORK_END,
        help="定时进度推送结束小时（默认 18，不含）",
    )
    ap.add_argument(
        "--report-every",
        type=int,
        default=DEFAULT_REPORT_EVERY,
        help="工作时段内进度推送间隔（小时，默认 2）",
    )
    ap.add_argument(
        "--stall-min", type=int, default=DEFAULT_STALL_MIN, help="卡死判定（分钟无增长）"
    )
    ap.add_argument("--no-restart", action="store_true", help="只监控推送，不自动重启")
    ap.add_argument("--mail-config", default="mail_config.json", help="邮件配置 JSON")
    ap.add_argument("--notify-config", default="notify_config.json", help="微信通知配置 JSON")
    args = ap.parse_args()

    out = args.out
    os.makedirs(out, exist_ok=True)
    glog = os.path.join(out, "download_guard.log")
    logfile = os.path.join(out, "multi_download.log")
    pidfile = os.path.join(out, "guard.download.pid")
    complete = os.path.join(out, "complete.flag")

    mail = load_json(args.mail_config)
    notify = load_json(args.notify_config)
    if not mail.get("address"):
        log(glog, f"[!] 未找到邮件配置（{args.mail_config}），将只写日志不推送")

    # ---- 启动或接管下载 ----
    pid = detect_running(out)
    if pid is None and not os.path.exists(complete):
        if args.no_restart:
            log(glog, "[!] 未检测到下载进程且 --no-restart，守护仅监控/推送")
        else:
            cmd = build_download_cmd(args)
            proc = subprocess.Popen(cmd)
            pid = proc.pid
            with open(pidfile, "w") as f:
                f.write(str(pid))
            log(glog, f"[START] 下载已启动 pid={pid}")
    elif pid:
        with open(pidfile, "w") as f:
            f.write(str(pid))
        log(glog, f"[ADOPT] 接管已运行下载 pid={pid}")

    if os.path.exists(complete):
        log(glog, "[DONE] 检测到 complete.flag（下载已完成），守护退出")
        return

    notify_all(mail, notify, "下载守护已启动", f"输出目录: {out}\n清单: {args.list}")
    log(glog, "[OK] 守护已就绪（邮件推送开启）")

    last_bytes = dir_bytes(out)
    last_byte_time = time.time()
    restart_count = 0
    next_report = None  # 下一个计划推送时刻（工作时段整点网格）

    while True:
        time.sleep(60)
        now = datetime.now()

        # 完成检测
        if os.path.exists(complete):
            prog = parse_progress(logfile)
            body = summary_body(logfile, prog, out)
            title = f"下载完成 {prog['ok']}/{prog['total']}"
            notify_all(mail, notify, title, body)
            log(glog, f"[DONE] complete.flag 出现，发送完成通知（重启 {restart_count} 次）")
            return

        # 定时进度推送：仅白天工作时间整点网格（夜间静默；事件推送不受限）
        if next_report is None:
            next_report = next_report_time(args.work_start, args.work_end, args.report_every, now)
        if next_report is not None and now >= next_report:
            prog = parse_progress(logfile)
            title = f"下载进度 {prog['ok']}/{prog['total']}（{now.strftime('%H:%M')}）"
            body = summary_body(logfile, prog, out)
            notify_all(mail, notify, title, body)
            log(glog, f"[MAIL] 计划进度推送: {prog['ok']}/{prog['total']}")
            next_report = None  # 重新计算下一个网格点

        # 存活 / 卡死检查
        alive = bool(pid) and is_alive(pid) if pid else False
        total = dir_bytes(out)
        growing = total > last_bytes
        stall_sec = time.time() - last_byte_time
        if should_restart(alive, growing, stall_sec, args.stall_min):
            if args.no_restart:
                log(
                    glog, f"[WARN] 下载进程{'死亡' if not alive else '卡死'}（--no-restart 不重启）"
                )
            else:
                reason = "进程死亡" if not alive else f"卡死（{int(stall_sec // 60)} 分钟无增长）"
                log(glog, f"[RESTART] {reason}，重启下载")
                if pid:
                    kill_pid(pid)
                time.sleep(5)
                cmd = build_download_cmd(args)
                proc = subprocess.Popen(cmd)
                pid = proc.pid
                with open(pidfile, "w") as f:
                    f.write(str(pid))
                restart_count += 1
                last_bytes = dir_bytes(out)
                last_byte_time = time.time()
                notify_all(mail, notify, f"下载已重启（第 {restart_count} 次）", reason)
        if growing:
            last_bytes = total
            last_byte_time = time.time()


if __name__ == "__main__":
    main()
