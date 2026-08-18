"""GACOS 结果自动收取。

GACOS 完成后邮件发 tar.gz 链接，本脚本 IMAP 读邮箱 → 提取链接 →
下载 → 解压 ztd。支持指数退避轮询。

依赖: 无（标准库）

用法:
  python gacos_fetch.py --mail-config mail.json --out ./gacos [--expect 77] [--loop]
  mail.json: {"address":"you@163.com","authcode":"授权码","imap_host":"imap.163.com",
              "imap_port":993,"smtp_host":"smtp.163.com","smtp_port":465}
"""

import argparse
import email
import glob
import imaplib
import json
import os
import re
import tarfile
import time
import urllib.request
from email.header import decode_header


def log(msg, logfile):
    line = f"[{time.strftime('%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    if logfile:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def connect_imap(cfg):
    """创建 IMAP 连接并登录（只建一次，后续轮询复用）。

    2026-08-17 民勤实测教训：旧版每次轮询都 login/logout，几十次短间隔
    登录触发 163 风控（SELECT Unsafe Login）。复用连接避免频繁认证。
    """
    imaplib.Commands["ID"] = ("AUTH", "NONAUTH", "SELECTED")
    M = imaplib.IMAP4_SSL(cfg["imap_host"], cfg.get("imap_port", 993), timeout=30)
    M.login(cfg["address"], cfg["authcode"])
    try:
        M._simple_command("ID", '("name" "gacos-fetch" "version" "1.0" "vendor" "pi")')
    except Exception:
        pass
    M.select("INBOX")
    return M


def fetch_mails(M, limit=40):
    """用已登录的 IMAP 连接读最近邮件，返回 (主题, 正文) 列表。

    不负责 login/logout（连接由调用方复用维护）。
    """
    M.select("INBOX")  # 确保处于 INBOX（异常后重连也重新定位）
    _, data = M.search(None, "ALL")
    ids = data[0].split()
    results = []
    for num in ids[-limit:]:
        _, md = M.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(md[0][1])

        def dec(v):
            if not v:
                return ""
            return "".join(
                b.decode(p or "utf-8") if isinstance(b, bytes) else b for b, p in decode_header(v)
            )

        subject = dec(msg.get("Subject", ""))
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8", "replace")
                    break
        else:
            body = (
                msg.get_payload(decode=True).decode("utf-8", "replace")
                if msg.get_payload(decode=True)
                else ""
            )
        results.append((subject, body))

    return results


def main():
    ap = argparse.ArgumentParser(description="GACOS 结果收取")
    ap.add_argument("--mail-config", required=True, help="邮箱配置 JSON")
    ap.add_argument("--out", default="./gacos", help="输出目录")
    ap.add_argument("--expect", type=int, default=0, help="期望 ztd 数量（达到即停）")
    ap.add_argument("--loop", action="store_true", help="指数退避轮询：30s→1m→2m→5m→10m→30m")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logfile = os.path.join(args.out, "gacos_fetch.log")
    cfg = json.load(open(args.mail_config, encoding="utf-8"))

    # 2026-08-17 民勤实测修复：IMAP 连接只建一次，one_round 复用；
    # 认证被风控（Unsafe Login）时 30 分钟不重试，避免加重风控
    M = None
    blocked_until = 0.0  # 风控退避截止时间戳

    def ensure_conn():
        nonlocal M, blocked_until
        if M is not None:
            return M
        if time.time() < blocked_until:
            return None
        try:
            M = connect_imap(cfg)
            log("IMAP 连接已建立（复用）", logfile)
            return M
        except imaplib.IMAP4.error as e:
            emsg = str(e).lower()
            M = None
            if "unsafe" in emsg or "login" in emsg or "denied" in emsg:
                blocked_until = time.time() + 1800  # 风控：30 分钟退避
                log(
                    f"IMAP 认证被风控拒绝（{str(e)[:60]}），30 分钟内不再重试。"
                    f"请网页登录 mail.163.com 后重新运行。",
                    logfile,
                )
            else:
                log(f"IMAP 连接失败: {str(e)[:80]}", logfile)
            return None
        except Exception as e:
            M = None
            log(f"IMAP 连接异常: {str(e)[:80]}", logfile)
            return None

    def one_round():
        nonlocal M
        conn = ensure_conn()
        if conn is None:
            return 0
        try:
            mails = fetch_mails(conn)
        except imaplib.IMAP4.error as e:
            emsg = str(e).lower()
            M = None  # 连接已失效，下轮重连
            if "unsafe" in emsg or "login" in emsg or "denied" in emsg:
                log(
                    f"IMAP 认证被风控拒绝（{str(e)[:60]}），30 分钟内不再重试。"
                    f"请网页登录 mail.163.com 后重新运行。",
                    logfile,
                )
            else:
                log(f"IMAP 操作失败（下轮重连）: {str(e)[:80]}", logfile)
            return 0
        except Exception as e:
            M = None
            log(f"IMAP 操作异常（下轮重连）: {str(e)[:80]}", logfile)
            return 0
        got = 0
        for subject, body in mails:
            links = re.findall(
                r"https?://www\.gacos\.net/pub/gacosresult/[A-Za-z0-9]+\.tar\.gz", body
            )
            if not links:
                continue
            got += 1
            log(f"邮件: {subject[:35]} | 链接 {len(links)} 个", logfile)
            for url in links:
                name = url.split("/")[-1]
                tgz = os.path.join(args.out, name)

                if not (os.path.exists(tgz) and os.path.getsize(tgz) > 1000):
                    # 2026-08-17 民勤实测：GACOS 下载偶发 502/网络错误，
                    # 单文件失败不应中断整个收件循环（记录后下轮重试）
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=300) as r, open(tgz, "wb") as f:
                            while True:
                                c = r.read(1 << 20)
                                if not c:
                                    break
                                f.write(c)
                        log(f"  下载: {name} ({os.path.getsize(tgz) / 1e6:.1f}MB)", logfile)
                    except Exception as e:
                        log(f"  下载失败(下轮重试): {name}: {str(e)[:60]}", logfile)
                        if os.path.exists(tgz):
                            os.remove(tgz)  # 清掉残文件，避免误判已下载
                        continue
                try:
                    with tarfile.open(tgz, "r:gz") as t:
                        # 防 tar 路径穿越
                        for m in t.getmembers():
                            if (
                                m.name.startswith("/")
                                or ".." in m.name.split("/")
                                or (":" in m.name.split("/")[0])
                            ):
                                raise ValueError(f"不安全成员: {m.name}")
                        t.extractall(args.out)
                    ztds = [
                        os.path.basename(m.name)
                        for m in tarfile.open(tgz, "r:gz").getmembers()
                        if m.name.endswith(".ztd")
                    ]
                    log(f"  解压 ztd: {len(ztds)} 个", logfile)
                except Exception as e:
                    log(f"  解压失败: {str(e)[:60]}", logfile)
        n = len(glob.glob(os.path.join(args.out, "*.ztd")))
        log(f"当前 ztd: {n}{f'/{args.expect}' if args.expect else ''}", logfile)

        return n

    n = one_round()
    if not args.loop or (args.expect and n >= args.expect):
        print(f"ztd: {n}，完成")
        return

    # 指数退避轮询（风控等待优先于固定间隔）
    intervals = [30, 60, 120, 300, 600, 1800]
    round_no = 0
    while not args.expect or n < args.expect:
        wait = intervals[min(round_no, len(intervals) - 1)]
        remain = blocked_until - time.time()
        if remain > 0:
            wait = max(wait, remain)  # 被风控时等到解封再试
        time.sleep(wait)
        round_no += 1
        n = one_round()
    print(f"=== 全部 {args.expect} 个 ztd 收齐！===")


if __name__ == "__main__":
    main()
