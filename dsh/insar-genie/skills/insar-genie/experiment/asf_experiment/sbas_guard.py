"""SBAS 干涉处理守护 v4（2026-08-13 重构）
监控 + 自动体检 + 主动汇报（不依赖用户询问）

v4 重构（行为保持）：
  - 原 v3 为 680 行面向过程：全局状态变量（_last_cpu/_reported_done/_restart_count…）
    散落在 main() 里，状态管理混乱（曾致误报 DONE）。
  - 现封装为 Guardian 类（状态机）：状态 → 实例属性，main 循环 → run()。
    模块级工具函数（无状态，读配置常量）保持不变。
用法: python -u sbas_guard.py
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

# ---- 配置（experiment/config.env，可移植；见 config.example.env 模板）----
_CFG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _CFG_DIR)
from config_loader import load_config

_CFG = load_config()
WORK_DIR = _CFG.get("WORK_DIR", "D:/work/data")
WORKDIR = os.path.join(WORK_DIR, "asf_experiment")
SBAS_ROOT = _CFG.get("RESULT_ROOT", "G:/gulang2_result_SBAS_processing")
# CG 目录名可配置（config.env CG_DIR_NAME；默认古浪名，民勤=CG_minqin_full_SBAS_processing）
CG_DIR = os.path.join(SBAS_ROOT, _CFG.get("CG_DIR_NAME", "CG_gulang2_SBAS_processing"))
TMP_WORK = os.path.join(SBAS_ROOT, "tmp", "work")
WORK_STACK = os.path.join(CG_DIR, "work", "work_interferogram_stacking")
BAT_FILE = os.path.join(WORK_DIR, _CFG.get("INTERF_BAT", "bat/02_interferogram/run_interf.bat"))
# ---- 多步骤监控（SBAS 五步，按 auxiliary.sml 状态推进）----
# bat 名可配置（config.env BAT_PREFIX，如民勤用 _minqin 后缀）
_BP = _CFG.get("BAT_PREFIX", "")
STEPS = [
    (
        "step1_connection",
        ("generate_connection_graph",),
        "第 1 步 连接图",
        f"bat/01_connection_graph/run_cg_final{_BP}.bat",
    ),
    (
        "step2_interferogram",
        ("interf_stack", "unwrapping"),
        "第 2 步 干涉+解缠",
        f"bat/02_interferogram/run_interf{_BP}.bat",
    ),
    (
        "step3_inversion1",
        ("first_inversion",),
        "第 3 步 反演1",
        f"bat/03_inversion/run_inv1{_BP}.bat",
    ),
    (
        "step4_inversion2",
        ("second_inversion",),
        "第 4 步 反演2",
        f"bat/03_inversion/run_inv2{_BP}.bat",
    ),
    (
        "step5_geocode",
        ("geocod_reflat",),
        "第 5 步 地理编码",
        f"bat/04_geocode/run_geocode{_BP}.bat",
    ),
]
LOG = os.path.join(WORKDIR, "sbas_guard.log")
CFG_FILE = os.path.join(WORKDIR, "notify_config.json")
MAIL_CFG = os.path.join(WORKDIR, "mail_config.json")
DONE_FLAG = os.path.join(WORKDIR, "sbas_done.flag")
PS1_FILE = os.path.join(WORK_DIR, "hide_idl_window.ps1")
WAKE_EVENTS = os.path.join(WORKDIR, "wake_events.json")  # 待 AI 处理事件（下次会话接手）
REPORT_START = 9 * 60 + 10  # 09:10
REPORT_END = 18 * 60  # 18:00
WECHAT_REPORT_TIMES = [(10, 0), (12, 0), (14, 30), (17, 0)]  # 白天 4 次微信进度推送（HH, MM）
POLL_SEC = 60
STALL_MIN = 45  # 停滞判定（分钟）- SARscape 合成相位可静默30+分钟
HEALTH_CHECK_MIN = 30  # 强制体检间隔（分钟）- 用户睡觉不询问也主动汇报
CPU_STALL_CHECK_MIN = 10  # CPU 卡死检测窗口（分钟）
DETACHED = 0x00000008 | 0x00000200
CREATE_NO_WINDOW = 0x08000000

_last_notify = {}


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def write_wake_event(etype, message, stage=None):
    """记录待 AI 处理事件（守护无法实时唤醒时，AI 下次会话接手）"""
    events = []
    if os.path.exists(WAKE_EVENTS):
        try:
            events = json.load(open(WAKE_EVENTS, encoding="utf-8"))
        except Exception:
            events = []
    events.append(
        {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": etype,  # error / done / milestone
            "stage": stage,
            "message": message,
            "handled": False,
        }
    )
    try:
        json.dump(
            events[-20:], open(WAKE_EVENTS, "w", encoding="utf-8"), ensure_ascii=False, indent=1
        )
    except Exception:
        pass


# RPC 会话（通用 pi 唤醒通道，不依赖 pi-web）
_rpc_proc = None
_rpc_stdin = None
# pi-web 发现缓存（自动探测一次记住）
_piweb_cache = {"url": "", "sid": ""}


def discover_piweb():
    """自动发现 pi-web：配置 PI_WEB_URL > 环境变量 > 扫描常见端口（验证 /api/sessions）。"""
    if _piweb_cache["url"]:
        return _piweb_cache["url"]
    url = _CFG.get("PI_WEB_URL", "").strip() or os.environ.get("PI_WEB_URL", "").strip()
    if url:
        _piweb_cache["url"] = url.rstrip("/")
        return _piweb_cache["url"]
    import socket

    for port in (30141, 3000, 3001, 8080, 4173):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                pass
        except OSError:
            continue
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/sessions")
            resp = json.loads(urllib.request.urlopen(req, timeout=2).read().decode("utf-8"))
            if isinstance(resp, dict) and "sessions" in resp:
                _piweb_cache["url"] = f"http://127.0.0.1:{port}"
                log(f"[pi-web发现] {_piweb_cache['url']}")
                return _piweb_cache["url"]
        except Exception:
            continue
    return ""


def discover_session_id(web):
    """获取 pi-web 会话 id：配置 > 环境变量 > /api/sessions 取最近活跃。"""
    sid = _CFG.get("PI_WEB_SESSION", "").strip() or os.environ.get("PI_SESSION_ID", "").strip()
    if sid:
        _piweb_cache["sid"] = sid
        return sid
    if _piweb_cache["sid"]:
        return _piweb_cache["sid"]
    try:
        req = urllib.request.Request(f"{web}/api/sessions")
        resp = json.loads(urllib.request.urlopen(req, timeout=5).read().decode("utf-8"))
        sessions = resp.get("sessions") or []
        if sessions:
            _piweb_cache["sid"] = sessions[0].get("id", "")
            return _piweb_cache["sid"]
    except Exception:
        pass
    return ""


def rpc_enabled():
    """RPC_ENABLED 是否启用（'1'/'true'/'yes'/'on' 均为启用）"""
    return str(_CFG.get("RPC_ENABLED", "")).strip().lower() in ("1", "true", "yes", "on")


def ensure_rpc():
    """确保通用 pi RPC 会话存在（spawn `pi --mode rpc`，持有 stdin）。"""
    global _rpc_proc, _rpc_stdin
    if _rpc_proc is not None and _rpc_proc.poll() is None:
        return True
    if not rpc_enabled():
        return False
    cmd = _CFG.get("RPC_CMD", "pi")
    args = [cmd, "--mode", "rpc"]
    provider = _CFG.get("RPC_PROVIDER", "")
    model = _CFG.get("RPC_MODEL", "")
    if provider:
        args += ["--provider", provider]
    if model:
        args += ["--model", model]
    try:
        _rpc_proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        _rpc_stdin = _rpc_proc.stdin
        log("[RPC会话已启动] 通用 pi RPC 唤醒通道就绪")
        return True
    except Exception as e:
        log(f"[RPC启动失败] {e}（需 pi 命令可用，或配置 RPC_CMD 完整路径）")
        return False


def discover_dsh():
    """发现 DSH web：配置 DSH_WEB_URL > 环境变量 > 默认 http://127.0.0.1:3080。"""
    url = (
        _CFG.get("DSH_WEB_URL", "").strip()
        or os.environ.get("DSH_WEB_URL", "").strip()
        or "http://127.0.0.1:3080"
    )
    return url.rstrip("/")


def dsh_rpc(web, method, payload, timeout=15):
    """DSH RPC 信封：POST /api/<method>（loopback 免鉴权，协议同 WeCom 桥接）。"""
    import uuid

    body = json.dumps(
        {
            "type": "client-request",
            "rpcId": str(uuid.uuid4()),
            "method": method,
            "payload": payload,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{web}/api/{method}", data=body, headers={"Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
    return resp.get("result", {})


def wake_dsh(message):
    """DSH 唤醒：session.list 发现活跃会话 → session.prompt 注入诊断消息。

    用户主力助手为 DSH（3080）时启用；失败静默返回 False 走下一通道。
    """
    web = discover_dsh()
    try:
        result = dsh_rpc(web, "session.list", {})
        if not result.get("ok"):
            return False
        items = result.get("value", {}).get("items") or []
        items.sort(key=lambda it: it.get("updatedAt", 0), reverse=True)
        sid = ""
        for it in items:  # 优先 running 的非空白会话
            if it.get("running") and not it.get("blank"):
                sid = it.get("sessionId", "")
                break
        if not sid:  # 其次最近更新的非空白会话
            for it in items:
                if not it.get("blank"):
                    sid = it.get("sessionId", "")
                    break
        if not sid:
            return False
        r = dsh_rpc(
            web,
            "session.prompt",
            {
                "sessionId": sid,
                "mode": "queue",
                "content": [{"type": "text", "text": message}],
            },
        )
        return bool(r.get("ok"))
    except Exception as e:
        log(f"[DSH唤醒失败] {str(e)[:80]}")
        return False


def wake_ai(message, etype="error", stage=None):
    """唤醒 AI 推理，四级通道：① DSH (3080) → ② pi-web HTTP → ③ 通用 pi RPC → ④ wake_events 兜底。"""
    if wake_dsh(message):
        log(f"[唤醒AI-DSH] {message[:50]}")
        return True
    web = discover_piweb()
    sid = discover_session_id(web) if web else ""
    if web and sid:
        try:
            req = urllib.request.Request(
                f"{web}/api/agent/{sid}",
                data=json.dumps({"type": "prompt", "message": message}, ensure_ascii=False).encode(
                    "utf-8"
                ),
                headers={"Content-Type": "application/json"},
            )
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode("utf-8"))
            if resp.get("success"):
                log(f"[唤醒AI] {message[:50]}")
                return True
            log(f"[唤醒失败] {resp}")
        except Exception as e:
            log(f"[唤醒失败] {e}")
    if ensure_rpc():
        try:
            _rpc_stdin.write(
                json.dumps({"type": "prompt", "message": message}, ensure_ascii=False) + "\n"
            )
            _rpc_stdin.flush()
            log(f"[RPC唤醒AI] {message[:50]}")
            return True
        except Exception as e:
            log(f"[RPC唤醒失败] {e}")
    write_wake_event(etype, message, stage)
    return False


def load_cfg():
    try:
        return json.load(open(MAIL_CFG, encoding="utf-8"))
    except Exception:
        return None


def mail_report_enabled():
    try:
        cfg = json.load(open(CFG_FILE, encoding="utf-8"))
        return cfg.get("mail_report", {}).get("enabled", True)
    except Exception:
        return True


def notify_wechat(title, desp=""):
    """Server酱微信推送（节流 30 分钟）"""
    try:
        cfg = json.load(open(CFG_FILE, encoding="utf-8")).get("serverchan", {})
        if not cfg.get("enabled") or not cfg.get("sendkey") or cfg["sendkey"].startswith("SCT填写"):
            return
        key = title[:20]
        now = time.time()
        interval = cfg.get("notify_interval_min", 30) * 60
        if key in _last_notify and now - _last_notify[key] < interval:
            return
        _last_notify[key] = now
        url = f"https://sctapi.ftqq.com/{cfg['sendkey']}.send"
        data = urllib.parse.urlencode({"title": f"[SBAS] {title}", "desp": desp[:2000]}).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
        log(f"[微信] {title} -> {resp.get('code')}")
    except Exception as e:
        log(f"[微信失败] {e}")


def send_mail(subject, body):
    cfg = load_cfg()
    if not cfg:
        return False
    import smtplib
    from email.mime.text import MIMEText

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = cfg["address"]
        msg["To"] = cfg["address"]
        host = cfg.get("smtp_host")
        port = cfg.get("smtp_port", 465)
        if port == 465:
            s = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            s = smtplib.SMTP(host, port, timeout=30)
            s.starttls()
        s.login(cfg["address"], cfg["authcode"])
        s.sendmail(cfg["address"], [cfg["address"]], msg.as_string())
        s.quit()
        log(f"[邮件] 已发送: {subject}")
        return True
    except Exception as e:
        log(f"[邮件失败] {e}")
        return False


def in_report_hours():
    now = time.localtime()
    t = now.tm_hour * 60 + now.tm_min
    return REPORT_START <= t <= REPORT_END


def run_hidden(args, **kw):
    kw.setdefault("capture_output", True)
    kw.setdefault("timeout", 30)
    return subprocess.run(args, creationflags=CREATE_NO_WINDOW, **kw)


def popen_hidden(args, **kw):
    return subprocess.Popen(args, creationflags=DETACHED | CREATE_NO_WINDOW, **kw)


def sbas_process_alive():
    """检测 SARscape 计算进程: envi_idl 或 main_sbas 任一存在即视为活跃"""
    ps = (
        "$c1 = (Get-CimInstance Win32_Process -Filter \"Name='envi_idl.exe'\" | Measure-Object).Count; "
        "$c2 = (Get-CimInstance Win32_Process -Filter \"Name='main_sbas.exe'\" | Measure-Object).Count; "
        "[math]::Max($c1, $c2)"
    )
    try:
        out = run_hidden(["powershell", "-NoProfile", "-Command", ps], text=True).stdout.strip()
        return out not in ("", "0")
    except Exception:
        return True


def cpu_seconds():
    """main_sbas 累计 CPU 秒数（用于判断是否真的在计算）"""
    try:
        out = run_hidden(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-Process main_sbas -ErrorAction SilentlyContinue | Select-Object -First 1).CPU",
            ],
            text=True,
        ).stdout.strip()
        return float(out) if out and out.replace(".", "").isdigit() else -1
    except Exception:
        return -1


def _stage_work_dirs():
    """各阶段 work 目录（停滞检测需覆盖全部，防止误判跨阶段静止）"""
    dirs = [WORK_STACK]
    for sub in ["work_first_inversion", "work_second_inversion", "work_geocoding"]:
        d = os.path.join(CG_DIR, "work", sub)
        if os.path.isdir(d):
            dirs.append(d)
    return dirs


def work_latest_mtime():
    """全部阶段 work 目录最新文件活动时间（SARscape 实际产出）"""
    latest = 0
    for d in _stage_work_dirs():
        try:
            for f in os.listdir(d):
                fp = os.path.join(d, f)
                try:
                    latest = max(latest, os.path.getmtime(fp))
                except OSError:
                    pass
        except OSError:
            pass
    return latest


def work_file_count():
    """全部阶段 work 目录文件总数（进度推进指标）"""
    total = 0
    for d in _stage_work_dirs():
        try:
            total += len(os.listdir(d))
        except OSError:
            pass
    return total


def trace_mtime():
    t = os.path.join(TMP_WORK, "Process.trace")
    try:
        return os.path.getmtime(t)
    except OSError:
        return 0


def trace_error():
    """检查 trace 尾部是否有错误关键字。

    2026-08-18 民勤教训：**只认致命关键字**（[CORE][!]/Error:/FATAL/call_exit_program）。
    "baseline estimation failure" 是 burst 级中间诊断，不代表整体失败（连接图
    trace 可大量出现但仍成功，民勤 2926 对大量标 failure 最终 CG OK）——**绝不能
    把它加入本列表**，否则守护会误报并中断正常任务。成败判据 = auxiliary.sml
    步骤标记 + CG_report ACCEPT 数。
    """
    t = os.path.join(TMP_WORK, "Process.trace")
    try:
        size = os.path.getsize(t)
        with open(t, "rb") as f:
            f.seek(max(0, size - 200000))
            tail = f.read().decode("utf-8", errors="replace")
        for kw in ["[CORE][!]", "Error:", "FATAL", "call_exit_program"]:
            if kw in tail:
                for line in tail.split("\n"):
                    if kw in line:
                        return line.strip()[:120]
        return ""
    except Exception:
        return ""


def parse_progress():
    """从 Process.working 解析当前进度"""
    try:
        wf = os.path.join(TMP_WORK, "Process.working")
        with open(wf, encoding="utf-8", errors="replace") as f:
            content = f.read().strip()
        lines = [l for l in content.split("\n") if l.strip()]
        if lines:
            return lines[-1]
    except Exception:
        pass
    return ""


def count_interf_pairs():
    try:
        rep = os.path.join(CG_DIR, "connection_graph", "CG_report.txt")
        if os.path.exists(rep):
            return sum(
                1 for l in open(rep, encoding="utf-8", errors="replace") if "SECONDARY :" in l
            )
    except Exception:
        pass
    return 376


def completed_pairs():
    """已完成的干涉对（sint 文件数/2, 每对产生 rg+az 两个 sint）"""
    if os.path.isdir(WORK_STACK):
        return sum(1 for f in os.listdir(WORK_STACK) if f.endswith("_original_sint"))
    return 0


def sml_step_status():
    """读 auxiliary.sml 各步骤状态 → {tag: bool}（OK=True / NotOK=False）"""
    status = {}
    aux = os.path.join(CG_DIR, "auxiliary.sml")
    try:
        txt = open(aux, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"<([a-z_]+)>(OK|NotOK)</\1>", txt):
            status[m.group(1)] = m.group(2) == "OK"
    except Exception:
        pass
    return status


def step_done(tags):
    """指定步骤（一组 auxiliary.sml 标签）是否全部完成"""
    st = sml_step_status()
    return all(st.get(t) for t in tags)


def current_stage():
    """当前进行中的步骤索引（第一个未完成的）；全部完成返回 None"""
    for i, (_, tags, _, _) in enumerate(STEPS):
        if not step_done(tags):
            return i
    return None


def hide_idl_windows():
    """隐藏所有 IDL Workbench 窗口（单次执行 ps1）"""
    try:
        ps1 = PS1_FILE
        if os.path.exists(ps1):
            run_hidden(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1])
    except Exception:
        pass


def disk_free_gb():
    """结果盘剩余（跨平台：shutil.disk_usage，不再依赖 Unix df）"""
    try:
        import shutil

        return shutil.disk_usage(SBAS_ROOT).free / 1024**3
    except Exception:
        pass
    return 999


def output_size_gb():
    """输出目录大小（跨平台：shutil 递归统计，不再依赖 Unix du）"""
    try:
        total = 0
        for root, _, files in os.walk(SBAS_ROOT):
            for fn in files:
                try:
                    total += os.path.getsize(os.path.join(root, fn))
                except OSError:
                    pass
        return f"{total / 1024**3:.1f}G"
    except Exception:
        return "?"


def full_report():
    lines = []
    stage = current_stage()
    stage_txt = f"第 {stage + 1}/5 步: {STEPS[stage][2]}" if stage is not None else "全部完成 🎉"
    lines.append(f"SBAS 处理进度汇报  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("-" * 40)
    prog = parse_progress()
    total = count_interf_pairs()
    done = completed_pairs()
    alive = sbas_process_alive()
    lines.append(f"当前阶段: {stage_txt}")
    lines.append(f"进程状态: {'运行中' if alive else '未运行'}")
    lines.append(f"当前进度: {prog if prog else '(读取中/未开始)'}")
    lines.append(f"已完成干涉对: {done}/{total} ({done / total * 100:.1f}%)")
    st = sml_step_status()
    lines.append(
        "步骤状态: "
        + " ".join(f"{n}={'✅' if st.get(t) else '⏳'}" for _, ts, n, _ in STEPS for t in ts[:1])
    )
    lines.append(f"输出大小: {output_size_gb()}")
    free = disk_free_gb()
    lines.append(f"结果盘剩余: {free:.0f}GB")
    lines.append("")
    lines.append("产物目录:")
    for sub in [
        "connection_graph",
        "interferogram_stacking",
        "first_inversion",
        "second_inversion",
        "geocoding",
    ]:
        d = os.path.join(CG_DIR, sub)
        n = len(os.listdir(d)) if os.path.isdir(d) else 0
        lines.append(f"  {sub}/: {n} 个文件")
    return "\n".join(lines)


class Guardian:
    """SBAS 五步守护（状态机）。

    v4 重构：把 v3 的 main() 全局状态变量（_last_cpu/_reported_done/_restart_count…）
    封装为实例属性，主循环为 run()。行为与 v3 完全一致。
    """

    def __init__(self):
        self.bat_file = BAT_FILE  # 当前阶段绑定的 bat（崩溃自动重启用）
        # ---- 监控状态（原 main() 局部变量）----
        self.last_report = 0
        self.last_health = 0
        self.last_wechat = 0
        self._reported_done = False
        self._reported_running = False
        self._last_progress = ""
        self._last_cpu = -1
        self._last_cpu_time = 0
        self._last_work_count = 0
        self._reported_slow = False
        self._restart_count = 0
        self._last_restart_time = 0
        self._reported_r38_done = False

    # ---------- 重启（用实例 bat_file，不再依赖全局 BAT_FILE）----------
    def restart(self):
        run_hidden(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process envi_idl,main_sbas,sarsnt -ErrorAction SilentlyContinue | Stop-Process -Force",
            ]
        )
        time.sleep(3)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        log(f"重启 SBAS 任务（{os.path.basename(self.bat_file)}）...")
        try:
            popen_hidden(
                ["cmd", "/c", self.bat_file],
                cwd=WORK_DIR,
                env=env,
                stdout=open(os.path.join(WORKDIR, "sbas_run.log"), "a", encoding="utf-8"),
                stderr=subprocess.STDOUT,
                close_fds=True,
            )
            return True
        except Exception as e:
            log(f"重启失败: {e}")
            return False

    # ---------- 主循环 ----------
    def run(self):
        # Windows 控制台默认 GBK：emoji（如 🎉）会崩，重配置为 utf-8
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        log("=== SBAS 守护 v4 启动（自动体检 + 主动汇报）===")

        while True:
            try:
                stage = current_stage()
                if stage is None:
                    # auxiliary.sml 显示全部完成，但 SARscape 进程仍活跃 = 重跑/后处理进行中，
                    # 勿误报 DONE（旧标记 OK 不代表当前没在重算）
                    if sbas_process_alive():
                        if not self._reported_running:
                            self._reported_running = True
                            log("[INFO] SARscape 进程运行中（疑似重跑/后处理），继续监控不报 DONE")
                        time.sleep(POLL_SEC)
                        continue
                    # 真正全部完成（无进程）
                    if not self._reported_done:
                        self._reported_done = True
                        log("[DONE] SBAS 全流程完成！")
                        notify_wechat("SBAS 全流程完成！", full_report())
                        send_mail("[SBAS] SBAS 全流程完成 🎉", full_report())
                        open(DONE_FLAG, "w").write(time.strftime("%Y-%m-%d %H:%M:%S"))
                    time.sleep(POLL_SEC)
                    continue

                if step_done(STEPS[stage][1]):
                    # 当前阶段完成 → 通知 + 写事件（AI 可接手分析中间产物），下次循环推进
                    if not self._reported_done:
                        self._reported_done = True
                        log(f"[DONE] {STEPS[stage][2]} 完成！")
                        notify_wechat(f"{STEPS[stage][2]} 完成！", full_report())
                        wake_ai(
                            f"{STEPS[stage][2]} 完成！请检查该阶段产物质量（相干/残差/解缠），"
                            f"确认无误后再进入下一步。",
                            etype="milestone",
                            stage=STEPS[stage][2],
                        )
                    time.sleep(POLL_SEC)
                    continue
                self._reported_done = False

                # 当前阶段进行中：绑定该阶段 bat（崩溃自动重启用）
                self.bat_file = os.path.join(WORK_DIR, STEPS[stage][3])

                alive = sbas_process_alive()
                now = time.time()

                # ===== 异常退出检测（进程消失时）=====
                if not alive:
                    if os.path.exists(os.path.join(WORKDIR, "pause.flag")) or os.path.exists(
                        os.path.join(WORKDIR, "stop.flag")
                    ):
                        log("遥控暂停/停止中，不重启")
                    else:
                        # 查 trace 错误
                        err = trace_error()
                        # 防重启风暴: 10 分钟内最多重启 3 次
                        if now - self._last_restart_time < 600:
                            self._restart_count += 1
                        else:
                            self._restart_count = 1
                        self._last_restart_time = now
                        if self._restart_count >= 3:
                            log("!!! 重启超过3次，停止自动重启，等待人工干预")
                            notify_wechat(
                                "反复崩溃，停止自动重启！",
                                f"10分钟内重启{self._restart_count}次，可能数据/配置问题。\n{trace_error()}",
                            )
                            wake_ai(
                                f"反复崩溃（10 分钟内 {self._restart_count} 次）已停止自动重启。"
                                f"请诊断根因：查 trace 错误、配置、磁盘，给出修复方案。"
                                f"trace 错误: {trace_error() or '无'}",
                                etype="error",
                                stage="反复崩溃",
                            )
                        else:
                            log(f"未发现 SARscape 进程，自动重启 (第{self._restart_count}次)")
                            notify_wechat(
                                f"干涉进程消失，自动重启(第{self._restart_count}次)",
                                f"异常信息: {err or '无错误标记'}\n已拉起新进程。",
                            )
                            wake_ai(
                                f"实验进程消失，守护自动重启第 {self._restart_count} 次。"
                                f"异常信息: {err or '无错误标记'}。请诊断是否有潜在问题，"
                                f"如需调整（参数/配置）请告知。",
                                etype="error",
                                stage=STEPS[stage][2],
                            )
                            self.restart()
                    self._reported_running = False
                else:
                    if not self._reported_running:
                        self._reported_running = True
                        log("[INFO] 干涉进程运行中")
                        notify_wechat(
                            "干涉处理已启动",
                            "SBAS 第2步（376干涉对，8:2多视，GACOS校正）开始运行。",
                        )
                        self._last_cpu = cpu_seconds()
                        self._last_cpu_time = now
                        self._last_progress = parse_progress()
                        self._last_work_count = work_file_count()

                    # ===== CPU 卡死检测（进程在但没在算）=====
                    cpu = cpu_seconds()
                    if (
                        cpu >= 0
                        and self._last_cpu >= 0
                        and (now - self._last_cpu_time) >= CPU_STALL_CHECK_MIN * 60
                    ):
                        delta = cpu - self._last_cpu
                        if delta < 30:  # 10分钟内CPU增量<30秒 = 基本没在算
                            log(f"警告: main_sbas CPU 10分钟仅增 {delta:.0f}s，疑似卡死")
                            if not self._reported_slow:
                                self._reported_slow = True
                                notify_wechat(
                                    "警告: 处理疑似卡死",
                                    f"main_sbas CPU 10分钟仅增{delta:.0f}s，进程在但可能没计算。\n当前进度: {parse_progress()}",
                                )
                        else:
                            self._reported_slow = False
                        self._last_cpu = cpu
                        self._last_cpu_time = now

                    # ===== 停滞检测（无文件活动 且 CPU 无增长才判停滞）=====
                    work_mtime = work_latest_mtime()
                    t = max(trace_mtime(), work_mtime)
                    cpu_now = cpu_seconds()
                    cpu_growth = (
                        (cpu_now - self._last_cpu) if (cpu_now >= 0 and self._last_cpu >= 0) else -1
                    )
                    # 反演/合成相位等内存密集阶段可能长时间不写盘，但 CPU 持续增长 = 在计算
                    if t and (now - t) > STALL_MIN * 60 and cpu_growth < 5:
                        # 先唤醒 AI 诊断（防误判：反演/合成相位内存密集可能长时间不写盘）
                        wake_ai(
                            f"检测到疑似停滞：{int(now - t) // 60} 分钟无文件活动且 CPU 无增长。"
                            f"请诊断：查 main_sbas CPU 活跃、trace 内容、当前阶段 {STEPS[stage][2]}，"
                            f"判断是真停滞还是误判，决定是否杀进程重启。",
                            etype="error",
                            stage=STEPS[stage][2],
                        )
                        log(f"干涉停滞 {int(now - t) // 60} 分钟且 CPU 无增长，杀进程重启")
                        notify_wechat(
                            "干涉停滞，已杀进程重启",
                            f"工作目录已 {int(now - t) // 60} 分钟无活动且 CPU 无增长，守护自动处理。",
                        )
                        run_hidden(
                            [
                                "powershell",
                                "-NoProfile",
                                "-Command",
                                "Stop-Process -Name envi_idl,main_sbas -Force -ErrorAction SilentlyContinue",
                            ]
                        )
                        time.sleep(5)
                        self.restart()
                    else:
                        # 进度变化检测
                        prog = parse_progress()
                        wc = work_file_count()
                        # 超参考 R_38 完成检测（进度从 R_38 变到其他参考 = 最慢阶段已过, 仅白天汇报）
                        if (
                            not self._reported_r38_done
                            and prog
                            and "R_38" not in prog
                            and "R_38" in self._last_progress
                        ):
                            self._reported_r38_done = True
                            if in_report_hours():
                                notify_wechat(
                                    "超参考 R_38 配准完成！",
                                    "最慢的参考景（10个副影像）已处理完，后续会加速。",
                                )
                        if prog != self._last_progress or wc != self._last_work_count:
                            self._last_progress = prog
                            self._last_work_count = wc
                            self._reported_slow = False  # 有推进则清除卡死警告

                    # ===== 强制周期体检（每30分钟; 只记日志, 微信额度有限不再推送）=====
                    if now - self.last_health >= HEALTH_CHECK_MIN * 60:
                        self.last_health = now
                        done_cnt = completed_pairs()
                        total = count_interf_pairs()
                        pct = done_cnt / total * 100 if total else 0
                        prog_now = parse_progress() or "读取中"
                        log(
                            f"[体检] {done_cnt}/{total} 对 ({pct:.1f}%), {output_size_gb()}, 进度: {prog_now}"
                        )

                # 隐藏 IDL 窗口（防弹窗）
                hide_idl_windows()

                # 磁盘检测
                free = disk_free_gb()
                if free < 20:
                    notify_wechat(
                        "磁盘空间不足！",
                        f"结果盘仅剩 {free:.0f}GB，SBAS 处理可能失败，请尽快处理。",
                    )
                    wake_ai(
                        f"磁盘空间不足：仅剩 {free:.0f}GB，实验可能失败。请诊断并给出处理方案"
                        f"（清理/扩容/暂停？）。",
                        etype="error",
                        stage=STEPS[stage][2] if stage is not None else None,
                    )

                # 微信进度汇报（白天 4 次，内容与邮件一致 = full_report；Server酱额度内）
                tm_now = time.localtime()
                for _hh, _mm in WECHAT_REPORT_TIMES:
                    if tm_now.tm_hour == _hh and tm_now.tm_min == _mm and in_report_hours():
                        if now - self.last_wechat >= 1800:  # 30 分钟节流防重复
                            self.last_wechat = now
                            notify_wechat("实验进度汇报", full_report())
                        break

                # 定时邮件汇报
                if mail_report_enabled() and now - self.last_report >= 7200 and in_report_hours():
                    self.last_report = now
                    send_mail(f"[SBAS] 定时进度汇报 {time.strftime('%H:%M')}", full_report())
                elif (
                    mail_report_enabled()
                    and time.localtime().tm_hour == 18
                    and time.localtime().tm_min == 0
                    and now - self.last_report >= 1800
                ):
                    self.last_report = now
                    send_mail("[SBAS] 18:00 最终进度汇报", full_report())
            except Exception as e:
                log(f"检查异常: {e}")
            time.sleep(POLL_SEC)


if __name__ == "__main__":
    Guardian().run()
