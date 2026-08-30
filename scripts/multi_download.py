"""ASF Sentinel-1 多线程分片下载器。

两种用法：
  1. 清单驱动（配合 analyze.py 生成的清单）：
     python multi_download.py --list 清单.csv --out 下载目录 [--threads 8]
  2. 搜索驱动（指定轨道直接下载，跳过交互选择）：
     python multi_download.py --aoi 区域.shp --start 20200101 --end 20251231 \
       --pol VV+VH --track 135 --out 下载目录 [--threads 8]

N 线程 Range 分片并发、分片级断点续传 + 重试 + 失败片循环补下、
大小 + MD5 双校验（坏数据自动删除重下）、已完成文件跳过。
"""

import argparse
import csv
import glob
import hashlib
import json
import os
import shutil
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asf_search as asf
from asf_search import ASFSession
from download import aoi_to_wkt, iso_datetime, load_config, parse_polarization

DEFAULT_THREADS = 8
RETRIES = 6
EXTRA_ROUNDS = 3


def log(msg, logfile):

    line = f"[{time.strftime('%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    if logfile:
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def _refresh_proxy(session, logfile):
    """每个文件下载前调用：动态读 Windows 系统代理，开关代理即时生效。

    2026-08-16 改进：原实现只在启动时读环境变量（进程生命周期内固化），
    用户开/关代理后必须重启下载器才生效。改为每次下载前读注册表
    ProxyEnable/ProxyServer——开代理自动走代理，关代理自动直连，
    全程无需重启。环境变量（HTTPS_PROXY）优先级更高，兼容外部注入。
    """
    proxy = (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("ALL_PROXY")
    )
    if not proxy and os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            ) as key:
                enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                server, _ = winreg.QueryValueEx(key, "ProxyServer")
            if enable and server:
                proxy = server if "://" in server else "http://" + server
        except OSError:
            pass
    # 仅在状态变化时更新并记日志（避免每个文件刷屏）
    current = dict(session.proxies or {}).get("https") or dict(session.proxies or {}).get("http")
    if (proxy or None) != (current or None):
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
            log(f"[PROXY] 使用代理: {proxy}", logfile)
        else:
            session.proxies = {}
            log("[PROXY] 未使用代理（直连）", logfile)


def download_chunk(session, url, start, end, part_path, idx, logfile):
    """下载一个分片；已下载部分跳过，失败重试"""
    existing = os.path.getsize(part_path) if os.path.exists(part_path) else 0
    # 2026-08-16 修复：.part 大小必须等于分片偏移（start），否则是旧 range 残留
    # （total_size 波动导致 chunk 变化时），续传会错位。不匹配则清空重下。
    if existing > 0 and existing != start:
        log(f"  [片{idx}] 续传错位（part={existing}B 期望偏移={start}B），清空重下", logfile)
        try:
            os.remove(part_path)
        except OSError:
            pass
        existing = 0
    if existing >= (end - start + 1):
        return True, existing  # 该片已完成
    start += existing

    headers = {"Range": f"bytes={start}-{end}"}
    # D7-①: 读超时 120s → 30s,断连立即重连,不挂死(ASF CDN 对慢连接会踢)
    for attempt in range(RETRIES):
        try:
            r = session.get(url, stream=True, headers=headers, timeout=(30, 30))
            if r.status_code in (200, 206):
                enable_tcp_keepalive(r)  # D7-④: TCP keep-alive 保活
                mode = "ab" if existing else "wb"
                with open(part_path, mode) as f:
                    f.writelines(r.iter_content(1 << 20))
                return True, os.path.getsize(part_path)
            log(f"  [片{idx}] HTTP {r.status_code}, 重试 {attempt + 1}/{RETRIES}", logfile)
        except Exception as e:
            log(f"  [片{idx}] 错误 {str(e)[:60]}, 重试 {attempt + 1}/{RETRIES}", logfile)
        time.sleep(5 * (attempt + 1))
    return False, 0


def md5_of(path):
    """文件 MD5（分块读，适合大文件）"""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def enable_tcp_keepalive(r):
    """D7-④: 对响应连接启用 TCP keep-alive,防 CDN/运营商 NAT 掐空闲连接。
    requests stream 连接在 r.raw._connection.sock;失败静默(不影响下载)。"""
    try:
        sock = r.raw._connection.sock
        if sock is None:
            return
        sock.setsockopt(getattr(socket, "SOL_SOCKET", 1), getattr(socket, "SO_KEEPALIVE", 8), 1)
        # 每 30s 探测,3 次失败断开
        for name, val in (("TCP_KEEPIDLE", 30), ("TCP_KEEPINTVL", 30), ("TCP_KEEPCNT", 3)):
            opt = getattr(socket, name, None)
            if opt is not None:
                try:
                    sock.setsockopt(getattr(socket, "IPPROTO_TCP", 6), opt, val)
                except OSError:
                    pass
    except Exception:
        pass


MD5_DONE_FILE = "md5_done.json"  # 输出目录下：已通过校验的文件名 → md5 缓存


def load_md5_done(out):
    """读 MD5 校验缓存（防每次重启对全部已完成文件重算，3.7GB×49 ≈ 20 分钟）。"""
    try:
        with open(os.path.join(out, MD5_DONE_FILE), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_md5_done(out, cache):
    """写 MD5 校验缓存（增量更新，失败静默）。"""
    try:
        with open(os.path.join(out, MD5_DONE_FILE), "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except OSError:
        pass


def get_total_size(session, url):
    """Range 探测真实大小（ASF 的 HEAD 不可靠）"""
    r = session.get(url, headers={"Range": "bytes=0-0"}, timeout=(30, 60), stream=True)
    cr = r.headers.get("Content-Range", "")
    r.close()  # stream=True 时必须显式关闭，否则连接不复用（2026-08-16 修复）
    if cr and "/" in cr:
        return int(cr.split("/")[-1])
    raise ValueError(f"无法获取文件大小: {url[:60]}")


def multi_download(session, url, dest, total_size, threads, logfile, expected_md5=""):

    n = threads if total_size >= 300 * 1024 * 1024 else 4
    chunk = total_size // n
    ranges = [(i * chunk, (i + 1) * chunk - 1) for i in range(n)]
    ranges[-1] = (ranges[-1][0], total_size - 1)

    parts = [dest + f".part{i}" for i in range(n)]
    for p in glob.glob(dest + ".part*"):
        if p not in parts:
            try:
                os.remove(p)
            except OSError:
                pass

    results = {}
    with ThreadPoolExecutor(max_workers=n) as ex:
        futs = {
            ex.submit(download_chunk, session, url, s, e, parts[i], i, logfile): i
            for i, (s, e) in enumerate(ranges)
        }
        for fut in as_completed(futs):
            i = futs[fut]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = (False, 0)
                log(f"  [片{i}] 异常: {str(e)[:60]}", logfile)

    # 合并前对失败分片循环补下：网络差时别急着作废整个文件
    for round_no in range(EXTRA_ROUNDS):
        failed = [i for i in range(n) if not results.get(i) or not results[i][0]]
        if not failed:
            break
        log(f"  [补下轮{round_no + 1}] 失败分片 {failed}，重试中...", logfile)
        with ThreadPoolExecutor(max_workers=len(failed)) as ex:
            futs = {
                ex.submit(
                    download_chunk, session, url, ranges[i][0], ranges[i][1], parts[i], i, logfile
                ): i
                for i in failed
            }
            for fut in as_completed(futs):
                i = futs[fut]
                try:
                    results[i] = fut.result()
                except Exception:
                    results[i] = (False, 0)

    # 合并分片
    # D7-②: 失败分片不再整文件作废——保留已完成分片(.part),让外层/下次续传继续补下。
    # 原逻辑: 任一失败 → 删所有 parts 作废整个文件,网络差时反复重下首部浪费大量带宽。
    done_parts = []
    failed_parts = []
    for i in range(n):
        if not results.get(i) or not results[i][0]:
            failed_parts.append(i)
            continue
        done_parts.append(parts[i])
    if failed_parts:
        log(f"  [片{failed_parts} 失败] 保留 {len(done_parts)} 个已完成分片,下次续传补下(不整文件作废)", logfile)
        # 已成功分片仍可合并? 不——缺片则整文件不完整;保持 .part 供续传,
        # 但为不占额外空间且续传快,把已完成部分尝试合并到 dest 的临时区? 保持简单:
        # 直接返回失败,dest 不存在,parts 保留(断点续传靠 download_chunk 的 existing>0 跳过)。
        return False, 0
    with open(dest, "wb") as out:
        for i in range(n):
            with open(parts[i], "rb") as f:
                shutil.copyfileobj(f, out)
    for p in parts:
        os.remove(p)
    size = os.path.getsize(dest)
    if size != total_size:
        log(f"  大小不匹配 {size} != {total_size}，作废重下", logfile)
        os.remove(dest)
        return False, size

    # MD5 校验（ASF 官方 md5sum）
    if expected_md5:
        log("  计算 MD5 校验中...", logfile)
        got = md5_of(dest)

        if got != expected_md5:
            log(f"  [WARN] MD5 不匹配! 期望 {expected_md5} 实得 {got}，删除重下", logfile)
            os.remove(dest)
            return False, size
        log(f"  MD5 校验通过: {got[:16]}...", logfile)

    return True, size


def search_and_group(aoi, start, end, pols):
    wkt = aoi_to_wkt(aoi)
    results = []
    for pol in pols:
        r = asf.geo_search(
            platform="SENTINEL-1",
            processingLevel="SLC",
            beamMode="IW",
            polarization=pol,
            start=iso_datetime(start),
            end=iso_datetime_end(end),
            intersectsWith=wkt,
        )
        results.extend(r)
    groups = {}
    for r in results:
        key = (r.properties.get("flightDirection"), str(r.properties.get("pathNumber")))
        groups.setdefault(key, []).append(r)
    return groups, results


def main():
    ap = argparse.ArgumentParser(description="ASF 多线程分片下载")
    ap.add_argument("--list", help="清单 CSV（date,frame,orbit,satellite,file 列），优先于搜索路径")
    ap.add_argument("--aoi", help="区域 shp/kml（搜索路径用）")

    ap.add_argument("--start", help="起始 YYYYMMDD")
    ap.add_argument("--end", help="结束 YYYYMMDD")
    ap.add_argument("--pol", default="VV+VH,VV", help="极化，逗号分隔")
    ap.add_argument("--track", type=int, help="指定轨道号（跳过交互选择）")
    ap.add_argument("--out", default="./sentinel1_data", help="下载目录")
    ap.add_argument("--threads", type=int, default=DEFAULT_THREADS, help="分片线程数")
    ap.add_argument(
        "--verify-aoi",
        help="清单驱动模式：下载前用该 shp/kml 对清单做逐时相覆盖复检"
        "（裁剪/自定义清单必用，防单帧覆盖不足时相漏检）",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="配合 --verify-aoi：存在未达标时相时终止下载（默认仅告警）",
    )
    args = ap.parse_args()

    if not args.list and not (args.aoi and args.start and args.end):
        ap.error("需要 --list 或 --aoi/--start/--end 之一")

    skill_dir = os.path.dirname(os.path.abspath(__file__))

    cfg = load_config(os.path.join(skill_dir, "config.json"))

    session = ASFSession()
    session.auth_with_creds(cfg["username"], cfg["password"])
    os.makedirs(args.out, exist_ok=True)
    logfile = os.path.join(args.out, "multi_download.log")
    # 代理：启动时应用一次（环境变量优先），此后每个文件前动态刷新（见 _refresh_proxy）
    proxy_url = (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("ALL_PROXY")
    )
    if proxy_url:
        session.proxies = {"http": proxy_url, "https": proxy_url}
        log(f"[PROXY] 使用代理: {proxy_url}", logfile)
    log(f"[OK] 认证成功: {cfg['username']} | 线程={args.threads}", logfile)

    rows = []
    if args.list:
        with open(args.list, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        log(f"清单驱动: {len(rows)} 条", logfile)
        # 逐时相覆盖复检：裁剪/自定义清单必须下载前复核（2025-02-06 案例：
        # analyze 全量校验用搜索全部帧，裁剪掉冗余帧后单帧不足时相会漏检）
        if args.verify_aoi:
            from analysis import verify_download_list

            wkt = aoi_to_wkt(args.verify_aoi)
            log(f"[VERIFY] 逐时相覆盖复检开始: {args.verify_aoi}（{len(rows)} 文件）", logfile)
            ok_dates, bad_dates = verify_download_list(wkt, rows, log=lambda m: log(m, logfile))
            log(f"[VERIFY] 通过 {len(ok_dates)} 时相 / 未达标 {len(bad_dates)} 时相", logfile)
            for date, ratio in bad_dates:
                log(f"[VERIFY]  ⚠ {date}: 并集覆盖 {ratio:.2%} —— 需补帧后重下", logfile)
            if bad_dates and args.strict:
                log("[VERIFY] strict 模式：存在未达标时相，终止下载", logfile)
                sys.exit(1)
    else:
        pols = [parse_polarization(p) for p in args.pol.split(",")]
        groups, _ = search_and_group(args.aoi, args.start, args.end, pols)
        if not groups:
            log("[!] 未搜索到数据", logfile)

            return
        ranked = sorted(groups.items(), key=lambda kv: -len(kv[1]))
        if args.track:
            sel = None
            for (d, p), prods in ranked:
                if int(p) == args.track:
                    sel = prods
                    log(f"已指定轨道 {args.track}（{d}，{len(prods)} 景）", logfile)
                    break
            if sel is None:
                log(
                    f"[!] 轨道 {args.track} 不在结果中，可用组："
                    + " ".join(f"{d}/轨道{p}({len(pr)})" for (d, p), pr in ranked),
                    logfile,
                )
                return
        else:
            print("可用 (方向,轨道) 组：")
            for i, ((d, p), prods) in enumerate(ranked, 1):
                print(f"  [{i}] {d} / 轨道 {p}: {len(prods)} 景")
            idx = input("选择编号（回车默认 1）: ").strip() or "1"
            try:
                sel = ranked[int(idx) - 1][1]
            except (ValueError, IndexError):
                sel = ranked[0][1]
                log("编号无效，使用第 1 组", logfile)
        for r in sel:
            rows.append({"file": r.properties.get("fileName", "")})

        log(f"搜索路径: {len(rows)} 景", logfile)

    ok = fail = skip = 0
    consec_fail = 0  # D7-③: 连续失败计数(触发渐进降并发)
    completed = True  # 完整跑完清单才写 complete.flag（中断不写）
    # 2026-08-17 修复：不再在启动时删除 complete.flag。
    # 原逻辑每次启动删 flag → 扫描清单期间 flag 缺失 → run_dl（每5分钟）误判
    # "任务未完成"再次拉起下载器 → 双下载器 + 守护反复重启的无限循环。
    # complete.flag 只在"发现待下载文件"时删除（见下），全部完成后保持存在。
    md5_cache = load_md5_done(args.out)  # 已校验通过的 md5 缓存（避免重启全量重算）
    log("[MODE] 下载模式: multi（固定多线程）", logfile)
    for i, r in enumerate(rows, 1):
        fname = r.get("file", "").strip()

        if not fname:
            fail += 1
            continue
        # 文件名消毒（防路径穿越）
        if (
            fname.startswith("/")
            or ".." in fname.split("/")
            or (":" in fname.split("/")[0])
            or fname in (".", "..")
        ):
            log(f"[{i}/{len(rows)}] [WARN] 非法文件名，跳过: {fname[:50]}", logfile)
            continue
        dest = os.path.join(args.out, fname)
        try:
            # 每个文件前动态刷新代理（用户开/关代理即时生效，无需重启）
            _refresh_proxy(session, logfile)
            prod = asf.granule_search(fname.replace(".zip", ""))
            if not prod:
                log(f"[{i}/{len(rows)}] [FAIL] 未找到: {fname[:45]}", logfile)
                fail += 1
                continue
            url = prod[0].properties["url"]
            expected_md5 = prod[0].properties.get("md5sum", "")

            # 已完成判断（2026-08-16 修复）：有 md5 时校验，防残次文件被永久跳过。
            # 校验结果写入 md5_done.json 缓存，重启后不再全量重算（3.7GB×49≈20分钟）。
            if os.path.exists(dest) and os.path.getsize(dest) > 1024:
                if expected_md5:
                    if md5_cache.get(fname) == expected_md5:
                        skip += 1
                        log(f"[{i}/{len(rows)}] 跳过(已完成, MD5缓存): {fname[:45]}", logfile)
                        continue
                    got = md5_of(dest)
                    if got == expected_md5:
                        md5_cache[fname] = got
                        save_md5_done(args.out, md5_cache)
                        skip += 1
                        log(f"[{i}/{len(rows)}] 跳过(已完成, MD5 校验通过): {fname[:45]}", logfile)
                        continue
                    # MD5 不匹配 → 残次文件，删除重下
                    log(
                        f"[{i}/{len(rows)}] [WARN] 已存在文件 MD5 不匹配，删除重下: {fname[:45]}",
                        logfile,
                    )
                    os.remove(dest)
                else:
                    skip += 1
                    log(f"[{i}/{len(rows)}] 跳过(已完成, 无 md5 仅大小): {fname[:45]}", logfile)
                    continue

            total = get_total_size(session, url)
            # 发现待下载文件 → 任务未完成，清除 complete.flag（让守护/run_dl 知道在干活）
            cf_old = os.path.join(args.out, "complete.flag")
            if os.path.exists(cf_old):
                try:
                    os.remove(cf_old)
                    log(f"[{i}/{len(rows)}] [START] 有待下载文件，清除旧 complete.flag", logfile)
                except OSError:
                    pass
            log(f"[{i}/{len(rows)}] [DL] {fname[:40]}... {total / 1e9:.2f}GB", logfile)

            t0 = time.time()
            # D7-③: 渐进降并发——连续失败时线程 8→4→2→1(网络极差降载,避免被 CDN 限流/超时踢掉)。
            # 修复 2026-08-16 简化为"始终固定多线程": 固定高并发在弱网下每条连接都被拖慢/断连,
            # 降并发后单连接更稳(配合分片重试+保活)。成功后恢复满并发(夜间网速提升自动提速)。
            eff_threads = args.threads
            if consec_fail >= 2:
                eff_threads = max(1, args.threads // (2 ** min(consec_fail // 2, 3)))
            if eff_threads != args.threads:
                log(f"[DEGRADE] 连续失败 {consec_fail} 次，线程 {args.threads}→{eff_threads}", logfile)
            ok_flag, size = multi_download(
                session, url, dest, total, eff_threads, logfile, expected_md5
            )
            dt = time.time() - t0
            if ok_flag:
                ok += 1
                consec_fail = 0  # 成功即恢复计数
                # 下载成功且校验过 → 写 md5 缓存（防下次重启重算）
                if expected_md5:
                    try:
                        md5_cache[fname] = expected_md5
                        save_md5_done(args.out, md5_cache)
                    except OSError:
                        pass
                speed_mbps = size / max(dt, 1) / 1e6
                log(
                    f"[{i}/{len(rows)}] [OK] {fname[:35]}... {size / 1e9:.2f}GB ({dt / 60:.1f}min, {speed_mbps:.1f}MB/s)",
                    logfile,
                )
            else:
                fail += 1
                consec_fail += 1  # D7-③: 连续失败递增(触发降并发)
                log(f"[{i}/{len(rows)}] [FAIL] {fname[:45]}", logfile)
        except Exception as e:
            fail += 1
            consec_fail += 1  # D7-③
            log(f"[{i}/{len(rows)}] [WARN] {fname[:45]} :: {str(e)[:80]}", logfile)

        time.sleep(2)

    log(f"=== 完成: 成功 {ok} / 失败 {fail} / 跳过 {skip} ===", logfile)
    # 任务完成标记（配合守护脚本防无限重启；仅完整跑完清单【且无失败】才写）
    # 2026-08-30 D1 修复：原逻辑 `if completed:` 只看"是否跑完整张清单"，
    # 网络差时大量 FAIL 也写 complete.flag → run_dl/守护误判"全部完成"停止拉取，
    # 实际丢文件（实测 成功3/失败131 也写 flag，131 景丢失）。
    # 正确语义：有失败文件 = 任务未真正完成，不写 flag，让守护/run_dl 继续补下。
    if completed and fail == 0:
        try:
            cf = os.path.join(args.out, "complete.flag")
            with open(cf, "w", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
            log(f"[DONE] 任务完成，写入标记: {cf}", logfile)
        except Exception:
            pass
    elif fail > 0:
        log(
            f"[NOTE] 存在 {fail} 个失败文件，不写 complete.flag（待守护/run_dl 续跑补下）",
            logfile,
        )


if __name__ == "__main__":
    main()
