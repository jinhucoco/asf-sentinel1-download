"""ASF 稳健下载：逐文件下载 + 超时保护 + 自动重试 + 断点续传。

比 download.py 多了两样：
  1. 搜索后展示完整数据列表（含帧号、大小），保存到 inventory.txt
  2. Tkinter 桌面进度条（当前文件 + 总进度 + 百分比）

用法：
    python robust_download.py --aoi <kml/shp> --start YYYYMMDD --end YYYYMMDD \
        --pol VV+VH --out <dir> [--retry 3] [--no-gui]
"""

import os
import sys
import threading
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from download import aoi_to_wkt, iso_datetime, load_config, parse_polarization

DOWNLOAD_TIMEOUT = 120  # 单次读超时（秒）：网络挂起时快速中断并续传重试
RETRY_COUNT = 10  # 每个文件最大尝试次数（续传可无限逼近）
RETRY_WAIT = 5  # 重试间隔（秒）


MAX_FILE_SIZE = 12 * 1024**3  # 单文件上限 12GB（SLC 约 4.5GB，留裕量防磁盘耗尽）
ALLOWED_DOWNLOAD_HOSTS = (
    "asf.alaska.edu",
    "earthdata.nasa.gov",
    "amazonaws.com",
    "amazonaws.com.cn",
)

import socket

socket.setdefaulttimeout(60)  # 全局 socket 超时：任何网络操作 60s 无响应即中断


def sanitize_filename(fname):
    """只留 basename，拒绝路径分隔符/../绝对路径（防路径穿越）。

    平台一致性：Windows 上 os.path.basename 把 ":" 当路径分隔符（a:b.zip->b.zip），
    Linux 不会；这里先把 ":" 转成 "/" 再 basename，保证跨平台行为一致。"""
    fname = os.path.basename(str(fname or "").replace("\\", "/").replace(":", "/"))
    if (
        not fname
        or fname in (".", "..")
        or ":" in fname
        or "/" in fname
        or "\\" in fname
        or ".." in fname
    ):
        raise ValueError(f"非法文件名: {fname!r}")

    return fname


def check_download_url(url):
    """必须 HTTPS 且 host 在白名单内（防 token 泄露/SSRF）"""
    from urllib.parse import urlparse

    u = urlparse(url)
    if u.scheme != "https":
        raise ValueError(f"下载 URL 非 HTTPS: {url[:80]}")
    host = (u.hostname or "").lower()
    if not any(host.endswith("." + d) or host == d for d in ALLOWED_DOWNLOAD_HOSTS):
        raise ValueError(f"下载 URL host 不在白名单: {host}")


def format_inventory_rich(items):
    """详细清单（含帧号、大小）"""
    lines = [f"{'序号':<4}{'日期':<11}{'相对轨道':<8}{'方向':<12}{'极化':<8}{'帧号':<6}{'文件名'}"]
    for i, it in enumerate(items, 1):
        lines.append(
            f"{i:<4}{it['date']:<11}{it['orbit']:<8}{it['direction']:<12}"
            f"{it['pol']:<8}{it['frame']:<6}{it['file']}"
        )
    return "\n".join(lines)


def save_inventory(items, out_dir):
    """保存数据清单到 inventory.txt"""
    path = os.path.join(out_dir, "inventory.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# ASF Sentinel-1 下载清单\n")
        f.write(
            "# 轨道组: 方向/轨道 | 文件数: %d | 时相数: %d\n"
            % (len(items), len(set(it["date"] for it in items)))
        )
        f.write("# 字段: 序号,日期,相对轨道,方向,极化,帧号,文件名\n")
        f.writelines(
            f"{i},{it['date']},{it['orbit']},{it['direction']},{it['pol']},"
            f"{it['frame']},{it['file']}\n"
            for i, it in enumerate(items, 1)
        )
    print(f"[OK] 清单已保存: {path}")
    return path


def robust_download(product, out_dir, session, progress=None, timeout=DOWNLOAD_TIMEOUT):
    """单文件下载：分块流式 + 断点续传（Range） + .part 标记 + 完整性校验。

    写入 <name>.part，校验字节数与 md5sum 后重命名为正式名（原子替换）。
    progress: DownloadProgress 实例（可选），更新 GUI 进度（线程安全）。
    返回 (成功?, 已下载字节数)。部分下载可下次续传。
    """
    import hashlib

    url = product.properties.get("url", "")
    fname = sanitize_filename(product.properties.get("fileName", ""))
    dest = os.path.join(out_dir, fname)

    part = dest + ".part"
    if not url:
        print(f"[!] {fname} 无下载 URL，跳过")
        return False, 0
    try:
        check_download_url(url)
    except ValueError as e:
        print(f"[!] {fname} {e}")
        return False, 0

    existing = os.path.getsize(part) if os.path.exists(part) else 0
    headers = {"Range": f"bytes={existing}-"} if existing > 0 else {}
    # 先探测真实总大小：ASF 的 Content-Length 不可靠，用 bytes=0-0 的 Content-Range
    total_size = 0
    try:
        probe = session.get(url, headers={"Range": "bytes=0-0"}, timeout=(30, 60))
        cr = probe.headers.get("Content-Range", "")

        probe.close()
        if cr and "/" in cr:
            total_size = int(cr.split("/")[-1])
    except Exception:
        pass
    try:
        with session.get(url, stream=True, timeout=(30, timeout), headers=headers) as resp:
            if resp.status_code not in (200, 206):
                print(f"[!] {fname} 状态码 {resp.status_code}")
                return False, existing
            if total_size <= 0:
                # 探测失败时回退 Content-Length
                total_size = existing + int(resp.headers.get("content-length", 0) or 0)
            if total_size > MAX_FILE_SIZE:
                print(f"[!] {fname} 超过大小上限 {MAX_FILE_SIZE // 1024**3}GB")
                return False, existing
            if progress:
                progress.update(fname, existing, total_size, 0, 1)
            mode = "ab" if existing > 0 and resp.status_code == 206 else "wb"
            with open(part, mode) as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        existing += len(chunk)
                        if progress:
                            progress.update(fname, existing, total_size, 0, 1)
        # 完整性校验：字节数 + asf_search 提供的 md5sum
        if os.path.getsize(part) > 0:
            size_ok = total_size > 0 and os.path.getsize(part) == total_size
            md5_expected = product.properties.get("md5sum")

            md5_ok = True
            if md5_expected:
                h = hashlib.md5()
                with open(part, "rb") as f:
                    for blk in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(blk)
                md5_ok = h.hexdigest().lower() == str(md5_expected).lower()
            if size_ok and md5_ok:
                # 完成：.part → 正式名（原子替换）
                os.replace(part, dest)
                return True, os.path.getsize(dest)
            print(f"[!] {fname} 完整性校验失败（size_ok={size_ok} md5_ok={md5_ok}），重新下载")

            os.remove(part)
            return False, 0
    except Exception as e:
        print(f"[!] {fname} 下载异常: {str(e)[:120]}")
        return False, os.path.getsize(part) if os.path.exists(part) else 0
    return False, existing


def main():
    import argparse

    ap = argparse.ArgumentParser(description="ASF Sentinel-1 稳健下载")
    ap.add_argument("--aoi", required=True)
    ap.add_argument("--start", required=True)

    ap.add_argument("--end", required=True)

    ap.add_argument("--pol", default="VV+VH,VV")
    ap.add_argument("--out", default=os.path.join(os.getcwd(), "sentinel1_data"))

    ap.add_argument("--retry", type=int, default=RETRY_COUNT)
    ap.add_argument("--no-gui", action="store_true", help="不显示桌面进度条")

    args = ap.parse_args()

    pols = [p.strip() for p in args.pol.split(",") if p.strip()]
    for p in pols:
        parse_polarization(p)

    # 认证 + 搜索
    import asf_search
    from asf_search import ASFSession

    cfg = load_config()
    os.makedirs(args.out, exist_ok=True)

    wkt = aoi_to_wkt(args.aoi)
    session = ASFSession()
    session.auth_with_creds(cfg["username"], cfg["password"])

    print("[OK] 认证成功")

    all_results = []
    for pol in pols:
        r = asf_search.geo_search(
            platform="SENTINEL-1",
            processingLevel="SLC",
            beamMode="IW",
            polarization=pol,
            start=iso_datetime(args.start),
            end=iso_datetime_end(args.end),
            intersectsWith=wkt,
        )
        print(f"[OK] 极化 {pol}: {len(r)} 个结果")

        all_results.extend(r)

    if not all_results:
        print("[!] 未搜索到数据")
        return

    # 分组 + 选轨道
    groups = {}
    for r in all_results:
        key = (r.properties.get("flightDirection", "?"), str(r.properties.get("pathNumber", "?")))
        groups.setdefault(key, []).append(r)
    print(f"\n[OK] 共 {len(groups)} 个 (方向,轨道) 组:")
    ranked = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    for i, ((d, o), prods) in enumerate(ranked, 1):
        print(f"  [{i}] {d} / 轨道 {o}: {len(prods)} 景")
    sel = input("\n选择轨道组编号（回车选默认第 1 个）: ").strip() or "1"
    try:
        sel_idx = int(sel)
        if not (1 <= sel_idx <= len(ranked)):
            raise ValueError
    except ValueError:
        print(f"[!] 编号 {sel} 无效，自动使用第 1 组")
        sel_idx = 1
    results = ranked[sel_idx - 1][1]
    print(
        f"[OK] 已选择: {ranked[sel_idx - 1][0][0]} / 轨道 {ranked[sel_idx - 1][0][1]}（{len(results)} 景）"
    )

    # 展示完整数据列表 + 保存清单
    items = []
    for r in results:
        p = r.properties
        items.append(
            {
                "date": str(p.get("startTime", ""))[:10].replace("-", ""),
                "orbit": p.get("pathNumber", "?"),
                "direction": p.get("flightDirection", "?"),
                "pol": p.get("polarization", "?"),
                "frame": p.get("frameNumber", "?"),
                "file": p.get("fileName", "?"),
            }
        )
    print("\n" + format_inventory_rich(items))

    save_inventory(items, args.out)

    choice = input("\n输入 y 全部下载，n 取消: ").strip().lower()
    if choice not in ("y", "yes"):
        print("已取消")
        return

    # 桌面进度条：Tk 主循环必须在主线程，所以 GUI 放后台线程跑其主循环，
    # 下载线程经 queue 更新（progress_gui 已做线程安全封装）。Windows 可用，
    # 非 Windows 或启动失败自动降级（--no-gui 可强制关闭）。
    progress = None
    if not args.no_gui:
        try:
            from progress_gui import DownloadProgress

            progress = DownloadProgress()
            progress.set_total(len(results))
            gui_thread = threading.Thread(target=progress.launch, daemon=True)
            gui_thread.start()
            time.sleep(0.8)  # 等 GUI 窗口出现
        except Exception as e:
            print(f"[!] 进度条启动失败（继续下载）: {str(e)[:80]}")

            progress = None

    # 逐文件下载 + 重试
    ok, fail = 0, []
    for idx, r in enumerate(results, 1):
        fname = sanitize_filename(r.properties.get("fileName", ""))
        dest = os.path.join(args.out, fname)
        part = dest + ".part"

        # 已完整下载（正式名存在且无 .part）则跳过
        if os.path.exists(dest) and not os.path.exists(part):
            print(f"[SKIP] {fname} 已完整下载 ({os.path.getsize(dest)} bytes)")
            ok += 1
            if progress:
                progress.file_done()
            continue
        if os.path.exists(part):
            print(f"[续传] {fname} 已有部分 {os.path.getsize(part)} bytes，继续")
        success = False
        for attempt in range(1, args.retry + 1):
            print(f"[下载] {fname} 第 {attempt}/{args.retry} 次尝试...", flush=True)
            t0 = time.time()
            success, _ = robust_download(r, args.out, session, progress=progress)
            if success:
                size = os.path.getsize(dest)
                print(f"[OK] {fname} 完成 ({size} bytes, {time.time() - t0:.0f}s)")

                ok += 1
                if progress:
                    progress.file_done()
                break
            print(f"[!] 尝试 {attempt} 失败，{RETRY_WAIT}s 后重试（已下载部分将续传）")
            time.sleep(RETRY_WAIT)
        if not success:
            fail.append(fname)
            print(f"[X] {fname} 下载失败（已重试 {args.retry} 次）")

    if progress:
        progress.close()
    print(f"\n=== 完成：成功 {ok}/{len(results)}，失败 {len(fail)} ===")
    if fail:
        print("失败文件:")

        for f in fail:
            print("  ", f)


if __name__ == "__main__":
    main()
