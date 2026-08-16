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
    for attempt in range(RETRIES):
        try:
            r = session.get(url, stream=True, headers=headers, timeout=(30, 120))
            if r.status_code in (200, 206):
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


def single_download(session, url, dest, total_size, logfile, expected_md5=""):
    """单连接整文件下载：断点续传 + 重试 + 大小/MD5 校验。

    网络极差时多线程连续作废会自动降级到这个模式。
    """
    part = dest + ".part"
    existing = os.path.getsize(part) if os.path.exists(part) else 0
    for attempt in range(RETRIES + 2):
        try:
            headers = {}
            if existing:
                headers["Range"] = f"bytes={existing}-"
            r = session.get(url, stream=True, headers=headers, timeout=(60, 300))
            if r.status_code in (200, 206):
                with open(part, "ab" if existing else "wb") as f:
                    f.writelines(r.iter_content(1 << 20))
                size = os.path.getsize(part)
                if size == total_size:
                    os.replace(part, dest)
                    if expected_md5:
                        log("  计算 MD5 校验中...", logfile)
                        got = md5_of(dest)

                        if got != expected_md5:
                            log("  [WARN] MD5 不匹配! 删除重下", logfile)
                            os.remove(dest)
                            return False, size
                    return True, size
                existing = size  # 未完成，继续
            else:
                log(f"  [单连接] HTTP {r.status_code}, 重试 {attempt + 1}", logfile)
        except Exception as e:
            log(f"  [单连接] 错误 {str(e)[:60]}, 重试 {attempt + 1}", logfile)
        time.sleep(8 * (attempt + 1))
    return False, existing


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
    with open(dest, "wb") as out:
        for i in range(n):
            if not results.get(i) or not results[i][0]:
                log(f"  [片{i}] 失败，文件作废（下次重下）", logfile)

                for p in parts:
                    try:
                        os.remove(p)
                    except OSError:
                        pass

                return False, 0
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


def read_mode(out_dir):
    """读取下载模式（multi=多线程分片 / single=单文件）。

    mode.flag 由守护/降级逻辑写入；不存在时默认 multi。
    首次运行必须不崩溃（2026-08-15 教训：曾因先 open 后判存在导致
    首跑 FileNotFoundError；修复后曾因镜像同步回旧版复发——故抽成纯函数+测试）。
    """
    mode_flag = os.path.join(out_dir, "mode.flag")
    if os.path.exists(mode_flag):
        try:
            with open(mode_flag, encoding="utf-8") as f:
                if f.read().strip() == "single":
                    return "single"
        except OSError:
            pass
    return "multi"


def maybe_downgrade(mode, fail_streak, threshold, args, logfile):
    """多线程连续 threshold 个文件作废 → 写 mode.flag 切单文件模式，返回是否已降级退出。

    与 maybe_upgrade 对称：两者都是 (mode, 状态数据, 阈值, args, logfile)，
    状态数据（失败计数 / 速率历史）由主循环维护并传入，阈值作参数而非隐式常量。
    2026-08-16 教训：原逻辑只在下载函数返回失败（[FAIL]）时累计 fail_streak，
    而网络断连（ConnectionReset 等）走 except 分支（[WARN]）不累计——
    网络越差越走 except，降级反而永远触发不了。故抽成纯函数，两条路径共用。
    """
    if mode == "multi" and fail_streak >= threshold:
        with open(os.path.join(args.out, "mode.flag"), "w", encoding="utf-8") as f:
            f.write("single")
        log(
            f"[DOWNGRADE] 多线程连续 {fail_streak} 文件作废，自动切换单文件模式，退出重启",
            logfile,
        )
        return True
    return False


UPGRADE_MIN_MBPS = 2.0    # 单文件模式速率 ≥ 此值视为网络已恢复（用户指定 2026-08-16）
UPGRADE_STREAK = 3        # 连续 N 个成功文件达到速率阈值才升级（防速率抖动）
UPGRADE_COOLDOWN_S = 20 * 60  # 降级后 20 分钟内禁止升级（防模式切换抖动）
DOWNGRADE_STREAK = 2      # 多线程连续 N 个文件作废才降级（网络极差的保底）


def maybe_upgrade(mode, speed_history, streak, args, logfile):
    """单文件模式速率连续达标 → 清 mode.flag 切回多线程，返回是否已升级退出。

    与 maybe_downgrade 对称：两者都是 (mode, 状态数据, 阈值, args, logfile)，
    状态数据（速率历史 / 失败计数）由主循环维护并传入，阈值作参数而非隐式常量。
    2026-08-16 新增：原设计只有降级（multi→single）没有升级（single→multi），
    夜间/带宽恢复后仍用单连接浪费带宽。此函数在 single 模式下统计近期成功文件
    的速率（speed_history 由主循环维护，已含本次），连续 streak 个
    ≥ UPGRADE_MIN_MBPS 就恢复多线程并退出重启。

    防抖双层：
    - 速率滞回：升级阈值（2MB/s，用户指定 2026-08-16）远高于降级触发（网络极差才降级）；
    - 切换冷却：降级后 UPGRADE_COOLDOWN_S 内不升级（mode.flag 的 mtime 是
      降级时刻），防止"升级→波动→降级→又升级"反复退出重启。
    """
    if mode != "single":
        return False
    recent = speed_history[-streak:] if speed_history else []
    if len(recent) < streak or not all(s >= UPGRADE_MIN_MBPS for s in recent):
        return False
    # 冷却检查：刚降级不久（mode.flag mtime 新）不升级
    flag = os.path.join(args.out, "mode.flag")
    if os.path.exists(flag):
        try:
            age = time.time() - os.path.getmtime(flag)
            if age < UPGRADE_COOLDOWN_S:
                log(
                    f"[UPGRADE] 跳过：{age / 60:.0f} 分钟前刚降级（冷却 {UPGRADE_COOLDOWN_S // 60} 分钟），暂不升级",
                    logfile,
                )
                return False
        except OSError:
            pass
    try:
        os.remove(flag)
    except OSError:
        pass
    log(
        f"[UPGRADE] 单文件模式连续 {streak} 个文件速率 ≥ {UPGRADE_MIN_MBPS:.0f}MB/s"
        f"（近期 {[round(s,1) for s in recent]}），恢复多线程模式，退出重启",
        logfile,
    )
    return True


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

    ok = fail = skip = fail_streak = 0
    completed = True  # 完整跑完清单才写 complete.flag（降级/中断不写）
    speed_history = []  # single 模式下近期成功文件速率（MB/s），供自动升级判断
    # 新任务开始：清掉旧 complete.flag（守护/遥控据此恢复工作）
    cf_old = os.path.join(args.out, "complete.flag")
    if os.path.exists(cf_old):
        try:
            os.remove(cf_old)
            log("[START] 新任务开始，清除旧 complete.flag", logfile)
        except OSError:
            pass
    # 下载模式：multi=多线程分片，single=单文件（自动降级后，标记存输出目录）
    mode = read_mode(args.out)
    md5_cache = load_md5_done(args.out)  # 已校验通过的 md5 缓存（避免重启全量重算）
    log(f"[MODE] 下载模式: {mode}{'（已自动降级）' if mode == 'single' else ''}", logfile)
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
                    log(f"[{i}/{len(rows)}] [WARN] 已存在文件 MD5 不匹配，删除重下: {fname[:45]}", logfile)
                    os.remove(dest)
                else:
                    skip += 1
                    log(f"[{i}/{len(rows)}] 跳过(已完成, 无 md5 仅大小): {fname[:45]}", logfile)
                    continue

            total = get_total_size(session, url)
            log(f"[{i}/{len(rows)}] [DL] {fname[:40]}... {total / 1e9:.2f}GB", logfile)

            t0 = time.time()
            if mode == "multi":
                ok_flag, size = multi_download(
                    session, url, dest, total, args.threads, logfile, expected_md5
                )
            else:
                ok_flag, size = single_download(session, url, dest, total, logfile, expected_md5)
            dt = time.time() - t0
            if ok_flag:
                ok += 1
                fail_streak = 0
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
                # 单文件模式速率连续达标 → 自动升级回多线程（网络恢复的保优）
                if mode == "single":
                    speed_history.append(speed_mbps)
                    # 只保留最近一小段，防无界增长（2026-08-16 审查修复）
                    if len(speed_history) > UPGRADE_STREAK * 4:
                        del speed_history[:-UPGRADE_STREAK * 4]
                    if maybe_upgrade(mode, speed_history, UPGRADE_STREAK, args, logfile):
                        mode = "multi"  # 语义更新：本进程内后续（如有）按 multi 看待
                        completed = False
                        break
            else:
                fail += 1
                fail_streak += 1
                # 失败中断"连续成功"序列：清空速率历史，防止非连续成功触发升级
                speed_history.clear()
                log(f"[{i}/{len(rows)}] [FAIL] {fname[:45]}", logfile)
                # 自动降级：多线程连续 2 个文件作废 → 切单文件模式（网络极差的保底）
                if maybe_downgrade(mode, fail_streak, DOWNGRADE_STREAK, args, logfile):
                    completed = False
                    break
        except Exception as e:
            fail += 1
            fail_streak += 1
            # 失败中断"连续成功"序列：清空速率历史（同 FAIL 分支）
            speed_history.clear()
            log(f"[{i}/{len(rows)}] [WARN] {fname[:45]} :: {str(e)[:80]}", logfile)
            # 网络断连（ConnectionReset 等）同样累计连续失败，触发自动降级
            if maybe_downgrade(mode, fail_streak, DOWNGRADE_STREAK, args, logfile):
                completed = False
                break

        time.sleep(2)

    log(f"=== 完成: 成功 {ok} / 失败 {fail} / 跳过 {skip} ===", logfile)
    # 任务完成标记（配合守护脚本防无限重启；仅完整跑完清单时写）
    if completed:
        try:
            cf = os.path.join(args.out, "complete.flag")
            with open(cf, "w", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
            log(f"[DONE] 任务完成，写入标记: {cf}", logfile)
        except Exception:
            pass


if __name__ == "__main__":
    main()
