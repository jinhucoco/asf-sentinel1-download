"""ASF 多线程下载守护（download_guard.py）

配合 scripts/multi_download.py 使用：周期体检（邮件报告）+ 异常自动介入 +
完成通知。守护会先启动（或接管已运行）下载，再进入监控循环。

用法（示例）:
    python download_guard.py --list 清单.csv --out G:/minqin_sentinel1 [--threads 8]
                             [--health-interval 30] [--stall-min 40] [--no-restart]
                             [--mail-config mail_config.json] [--notify-config notify_config.json]

体检与推送策略（2026-08-16 用户要求）:
- 每 --health-interval 分钟（默认 30）体检一次：
  正常 → 邮件发送体检报告（进度/速度/进程状态/重启次数/日志尾部）；
  异常（进程死亡/卡死）→ 自动介入处理（重启下载）+ 即时通知，报告标注处理结果；
- 事件推送：启动/完成/重启/卡死 即时发送；
- 邮件读 mail_config.json（address/authcode/smtp_host/smtp_port，163/QQ SMTP 授权码）；
  微信读 notify_config.json（serverchan.sendkey，sct.ftqq.com），双通道同发。
- 自动重启：下载进程死亡/卡死（--stall-min 分钟无字节增长）自动重启，断点续传无缝
  续跑；complete.flag 已存在时绝不重启（防无限重启）。

长下载部署建议（2026-08-16 教训）:
- 本守护**必须脱离 web 宿主独立运行**（web 重启会杀 DSH 后台 job/守护自身）：
  推荐 Task Scheduler 计划任务（定时触发，svchost 拉起）+ HKCU Run 开机自启；
  参见 SKILL.md「多线程下载」章节的部署示例。
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
DEFAULT_HEALTH_INTERVAL = 30
DEFAULT_STALL_MIN = 40


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
                # 只统计带 [n/total] 前缀的行，避免把每次启动写的
                # "[OK] 认证成功" 等无前缀行计入 ok
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


def _no_window_flags():
    """Windows 下隐藏控制台窗口的标志（tasklist/wmic/taskkill 闪窗修复）"""
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def detect_running(out):
    """找正在跑的 multi_download 进程（命令行含 --out <out>）→ pid 或 None

    2026-08-16 改用 PowerShell：wmic 输出列顺序不稳、行尾正则取 pid 不可靠，
    曾导致守护误判下载器死亡而反复 RESTART（与 run_dl/计划任务/手动拉起者
    互不知晓，双下载器抢同一文件）。
    """
    norm = os.path.normcase(os.path.abspath(out))
    try:
        ps = (
            "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" "
            "| Where-Object { $_.CommandLine -match 'multi_download' } "
            '| ForEach-Object { "$($_.ProcessId)|$($_.CommandLine)" }'
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=_no_window_flags(),
        )
        for line in r.stdout.splitlines():
            pid_s, sep, cmd = line.partition("|")
            if not sep:
                continue
            if norm in os.path.normcase(cmd):
                return int(pid_s)
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
            creationflags=_no_window_flags(),
        )
        return str(pid) in r.stdout
    except Exception:
        return True


def kill_pid(pid):
    try:
        subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True,
            timeout=20,
            creationflags=_no_window_flags(),
        )
    except Exception:
        pass


def build_download_cmd(args):
    """由守护参数重建 multi_download 命令（重启/启动用）。

    用 python.exe（非 pythonw，确保 print 正常）+ 隐形启动标志。
    """
    py = sys.executable
    if py.lower().endswith("pythonw.exe"):
        py = py[: -len("pythonw.exe")] + "python.exe"
    cmd = [
        py,
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


def safe_print(line):
    """无控制台环境（pythonw/DEVNULL）下打印不崩溃"""
    try:
        if sys.stdout is not None:
            print(line, flush=True)
    except Exception:
        pass


def log(glog, msg):
    line = f"[{datetime.now().strftime('%m-%d %H:%M:%S')}] {msg}"
    safe_print(line)
    with open(glog, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def log_err(msg):
    safe_print(f"[ERR] {msg}")


def spawn_downloader(cmd):
    """独立启动下载器：CREATE_NO_WINDOW（无窗口）+ DETACHED_PROCESS（脱离守护，
    与守护平级独立）+ 输出重定向 NUL。

    2026-08-16 用户要求：守护与下载是【两个独立进程】，守护不"拥有"下载器——
    守护死亡不影响下载，下载死亡由守护监控重启。本函数用于守护发现下载器死亡后
    的重启（初始启动由 run_dl.py 启动器平级拉起，两边互不为父子）。
    """
    flags = 0
    if os.name == "nt":
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        flags |= getattr(subprocess, "CREATE_DETACHED_PROCESS", 0)
    return subprocess.Popen(
        cmd,
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def health_body(logfile, prog, out, alive=True, restarts=0, note="", speed_mbps=None):
    """体检报告正文（进度 + 进程状态 + 重启次数 + 速度 + 日志尾部）"""
    lines = []
    if os.path.exists(logfile):
        try:
            with open(logfile, encoding="utf-8", errors="replace") as f:
                tail = f.readlines()[-8:]
            lines = ["".join(tail[-8:])]
        except OSError:
            pass
    speed = f"{speed_mbps:.1f} MB/s" if speed_mbps is not None else "—"
    state = "✅ 正常" if alive else "❌ 进程不在"
    return (
        f"体检时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"状态: {state} {note}\n"
        f"完成: {prog['ok']}/{prog['total']} 个文件 | 失败: {prog['fail']} | 跳过: {prog['skip']}\n"
        f"当前: {prog['current'] or '无'}\n"
        f"已下载: {dir_bytes(out) / 1e9:.2f} GB | 速度: {speed}\n"
        f"重启次数: {restarts}\n"
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
        "--health-interval",
        type=int,
        default=DEFAULT_HEALTH_INTERVAL,
        help="体检间隔（分钟，默认 30）：每周期发一封体检报告邮件，异常自动介入",
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
            proc = spawn_downloader(cmd)
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
    last_health = 0.0  # 首次体检：启动即发
    last_health_bytes = last_bytes
    last_health_time = time.time()

    while True:
        time.sleep(60)
        try:
            now = datetime.now()

            # 完成检测
            if os.path.exists(complete):
                prog = parse_progress(logfile)
                body = health_body(logfile, prog, out, restarts=restart_count)
                title = f"下载完成 {prog['ok']}/{prog['total']}"
                notify_all(mail, notify, title, body)
                log(glog, f"[DONE] complete.flag 出现，发送完成通知（重启 {restart_count} 次）")
                return

            # 存活 / 卡死检查（每分钟；发现问题立即介入处理）
            # 每次检测前刷新 pid：下载器可能由 run_dl/计划任务/手动拉起，守护与
            # 下载是平级进程，不能只认自己 spawn 的 pid（2026-08-16 双下载器教训）
            pid = detect_running(out) or pid
            alive = bool(pid) and is_alive(pid) if pid else False
            total = dir_bytes(out)
            growing = total > last_bytes
            stall_sec = time.time() - last_byte_time
            note = ""
            if should_restart(alive, growing, stall_sec, args.stall_min):
                if args.no_restart:
                    note = f"⚠ 检测到{'进程死亡' if not alive else '卡死'}（--no-restart 未重启）"
                    log(glog, f"[WARN] {note}")
                else:
                    reason = (
                        "进程死亡" if not alive else f"卡死（{int(stall_sec // 60)} 分钟无增长）"
                    )
                    log(glog, f"[RESTART] {reason}，重启下载")
                    if pid:
                        kill_pid(pid)
                    time.sleep(5)
                    cmd = build_download_cmd(args)
                    proc = spawn_downloader(cmd)
                    pid = proc.pid
                    with open(pidfile, "w") as f:
                        f.write(str(pid))
                    restart_count += 1
                    last_bytes = dir_bytes(out)
                    last_byte_time = time.time()
                    notify_all(mail, notify, f"下载已重启（第 {restart_count} 次）", reason)
                    note = f"⚠ 已介入处理: {reason}"
            if growing:
                last_bytes = total
                last_byte_time = time.time()

            # 30 分钟体检报告（健康也发；异常标注处理结果）
            if time.time() - last_health >= args.health_interval * 60:
                prog = parse_progress(logfile)
                speed = (total - last_health_bytes) / max(time.time() - last_health_time, 1) / 1e6
                body = health_body(
                    logfile,
                    prog,
                    out,
                    alive=alive,
                    restarts=restart_count,
                    note=note,
                    speed_mbps=speed,
                )
                title = f"下载体检 {prog['ok']}/{prog['total']}（{now.strftime('%m-%d %H:%M')}）"
                notify_all(mail, notify, title, body)
                log(
                    glog,
                    f"[HEALTH] 体检报告已发送: {prog['ok']}/{prog['total']} | {note or '正常'}",
                )
                last_health = time.time()
                last_health_bytes = total
                last_health_time = time.time()
        except SystemExit:
            raise
        except Exception as e:
            # 意外异常绝不退出：记录后继续（2026-08-16 教训：守护曾静默死亡
            # 且无自愈机制，下载长时间无人管）
            log(glog, f"[ERR] 体检循环异常（已忽略继续）: {str(e)[:120]}")
            time.sleep(10)


if __name__ == "__main__":
    main()
