"""
ASF Sentinel-1 自动下载 —— asf_search 官方库实现。

搜索/认证/下载都走 asf_search：ASFSession.auth_with_creds() 拿 EDL token
和 asf-urs cookie，ASFProduct.download() 带认证下载。
"""

import json
import os
import re

# ==================== 辅助函数 ====================


def load_config(path=None):
    # config.json 默认和脚本同目录（安装后 = 技能目录）
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if not os.path.exists(p):
        raise FileNotFoundError(
            "未找到凭证文件 " + p + "。安装后请先配置 NASA Earthdata 账号："
            "在对话中说「配置 ASF 账号密码」，或手动编辑 config.json"
            "（免费注册 https://urs.earthdata.nasa.gov/）"
        )
    with open(p, encoding="utf-8") as f:
        cfg = json.load(f)
    if not cfg.get("username") or not cfg.get("password") or cfg["username"].startswith("your_"):
        raise ValueError(
            "config.json 仍是模板占位符 (" + p + ")。请填入真实的 NASA Earthdata 账号密码后再运行。"
        )
    return cfg


def parse_polarization(s):
    s = s.strip().upper().replace(" ", "+")
    if s in ("VV", "VH", "HH", "HV", "VV+VH", "HH+HV"):
        return s
    raise ValueError(f"不支持的极化参数: {s}（支持 VV/VH/HH/HV/VV+VH/HH+HV）")


def ymd_to_mdy(s):
    """YYYYMMDD → MM/DD/YYYY

    >>> ymd_to_mdy('20240101')
    '01/01/2024'
    """
    s = str(s).strip()
    if not re.fullmatch(r"\d{8}", s):
        raise ValueError(f"日期格式应为 YYYYMMDD（8 位数字）: {s!r}")
    return f"{s[4:6]}/{s[6:8]}/{s[0:4]}"


def iso_datetime_end(s):
    """结束日期取闭区间：+1 天 00:00。S1 夜间过境 ~23:10 UTC，
    直接传 end 00:00 会把结束日全天丢掉。"""
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    d = _dt.strptime(str(s).strip(), "%Y%m%d")
    return (d + _td(days=1)).strftime("%Y-%m-%dT00:00:00Z")


def iso_datetime(s):
    """YYYYMMDD → YYYY-MM-DDT00:00:00Z（asf_search 的 ISO 格式）

    >>> iso_datetime('20240101')
    '2024-01-01T00:00:00Z'
    """
    s = str(s).strip()
    if not re.fullmatch(r"\d{8}", s):
        raise ValueError(f"日期格式应为 YYYYMMDD（8 位数字）: {s!r}")
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}T00:00:00Z"


def parse_direction(s):
    """asc/desc → ASCENDING/DESCENDING（asf_search flightDirection）

    >>> parse_direction('asc')
    'ASCENDING'
    >>> parse_direction('desc')
    'DESCENDING'
    """
    s = str(s).strip().lower()
    mapping = {
        "asc": "ASCENDING",
        "ascending": "ASCENDING",
        "升轨": "ASCENDING",
        "desc": "DESCENDING",
        "descending": "DESCENDING",
        "降轨": "DESCENDING",
    }
    if s not in mapping:
        raise ValueError(f"不支持的方向: {s}（支持 asc/升轨 或 desc/降轨）")
    return mapping[s]


def shp_to_kml(shp_path):
    """shp 第一要素外环（假设 WGS84）→ KML Polygon 字符串"""
    import shapefile

    with shapefile.Reader(shp_path) as r:
        shape = r.shape(0)
        pts = shape.points
    coords = ",".join(f"{x},{y}" for x, y in pts)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document><Placemark><Polygon><outerBoundaryIs><LinearRing><coordinates>{coords}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></Document>
</kml>"""


# 历史兼容：ASF 网页下拉选项文本映射（测试引用）
FILE_TYPE_LABEL = {
    "SLC": "Single Look Complex",
    "GRD": "Detected",
    "OCN": "Ocean",
    "RAW": "Raw Data",
}


def format_inventory(items):
    """items: [{date, orbit, pol, size, file}] → 表格字符串"""
    lines = [f"{'序号':<4}{'日期':<10}{'相对轨道':<10}{'方向':<12}{'极化':<8}{'文件名'}"]
    for i, it in enumerate(items, 1):
        lines.append(
            f"{i:<4}{it['date']:<10}{it['orbit']:<10}{it.get('direction', ''):<12}{it['pol']:<8}{it['file']}"
        )
    return "\n".join(lines)


def _confirm(items=None):
    """交互确认下载（测试引用）。

    返回：
        'all'      — 确认下载全部结果
        轨道号字符串 — 只下载该轨道的结果
        None       — 取消
    """
    orbits = sorted({str(it["orbit"]) for it in (items or []) if str(it["orbit"]) != "?"})
    hint = (
        (
            "，或输入轨道号只下载该轨道（可选: "
            + "/".join(orbits[:10])
            + ("…" if len(orbits) > 10 else "")
            + "）"
        )
        if orbits
        else "，或输入轨道号只下载该轨道"
    )
    while True:
        ans = input(f"输入 y 全部下载，n 取消{hint}: ").strip().lower()

        if ans in ("y", "yes"):
            return "all"
        if ans in ("n", "no", "q", "quit", ""):
            return None
        if ans.isdigit():
            return ans
        print(f"无法识别「{ans}」，请输入 y / n / 轨道号。")


# ==================== 矢量 → WKT ====================


def shp_to_wkt(shp_path):
    """shp 第一要素外环 → WKT POLYGON（ASF intersectsWith 格式）。

    防 DoS：限制文件 100MB / 坐标点 100 万。
    """
    MAX_SHP_SIZE = 100 * 1024 * 1024  # 100 MB
    MAX_COORDS = 1_000_000  # 坐标点数上限
    if os.path.getsize(shp_path) > MAX_SHP_SIZE:
        raise ValueError(f"shp 文件过大（>{MAX_SHP_SIZE // 1024 // 1024}MB）: {shp_path}")
    import shapefile

    with shapefile.Reader(shp_path) as r:
        if len(r) == 0:
            raise ValueError(f"shp 无要素: {shp_path}")
        shape = r.shape(0)
        pts = shape.points

    if not pts:
        raise ValueError(f"shp 无坐标: {shp_path}")
    if len(pts) > MAX_COORDS:
        raise ValueError(f"shp 坐标点数超过上限（{MAX_COORDS}）: {shp_path}")
    coords = ", ".join(f"{x} {y}" for x, y in pts)
    return f"POLYGON(({coords}))"


def kml_to_wkt(kml_path):
    """kml 第一个 Polygon 的坐标 → WKT POLYGON。

    兼容 opengis/earth.google 命名空间；坐标 'lon,lat[,alt]' 自动忽略海拔。
    防 DoS：限制 10MB / 100 万点。
    """

    MAX_KML_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_COORDS = 1_000_000  # 坐标点数上限
    if os.path.getsize(kml_path) > MAX_KML_SIZE:
        raise ValueError(f"KML 文件过大（>{MAX_KML_SIZE // 1024 // 1024}MB）: {kml_path}")
    try:
        # defusedxml 不展开外部实体，防 XXE
        from defusedxml import ElementTree as SafeET

        tree = SafeET.parse(kml_path)
    except ImportError:
        # fail-closed：缺 defusedxml 直接报错，不退回不安全的 ElementTree
        raise ValueError("缺少 defusedxml（安全 XML 解析库），请执行 pip install defusedxml")
    root = tree.getroot()

    # 按本地名匹配，兼容任意命名空间
    coords_el = None
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]  # 去掉命名空间前缀
        if tag == "coordinates" and (el.text or "").strip():
            coords_el = el
            break
    if coords_el is None:
        raise ValueError(f"无法从 KML 解析 Polygon 坐标: {kml_path}")

    pts = []
    for tok in coords_el.text.strip().split():
        if len(pts) >= MAX_COORDS:
            raise ValueError(f"KML 坐标点数超过上限（{MAX_COORDS}）: {kml_path}")

        parts = tok.split(",")

        if len(parts) >= 2:
            lon, lat = parts[0].strip(), parts[1].strip()

            if lon and lat:
                pts.append(f"{lon} {lat}")

    if not pts:
        raise ValueError(f"KML 坐标为空: {kml_path}")
    return f"POLYGON(({', '.join(pts)}))"


def aoi_to_wkt(path):
    """按扩展名分发：.shp / .kml → WKT"""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".shp":
        return shp_to_wkt(path)

    if ext == ".kml":
        return kml_to_wkt(path)
    raise ValueError(f"不支持的矢量格式: {ext}（支持 .shp / .kml）")


def footprint_contains(wkt_aoi, footprint_geojson):
    """影像 footprint 是否完全包含研究区（SBAS 要求全包含，不只是相交）"""
    try:
        from shapely.geometry import shape as shapely_shape
        from shapely.wkt import loads as wkt_loads

        aoi = wkt_loads(wkt_aoi)

        fp = shapely_shape(footprint_geojson)
        if aoi is None or aoi.is_empty or fp is None or fp.is_empty:
            return False
        return fp.covers(aoi)
    except Exception:
        return False


def group_union_covers(wkt_aoi, products):
    """一组影像的 footprint 并集是否覆盖研究区。

    研究区压在上下两景边界时，单景都不够，但同帧对并集可以。
    """
    try:
        from shapely.geometry import shape as shapely_shape
        from shapely.ops import unary_union
        from shapely.wkt import loads as wkt_loads

        aoi = wkt_loads(wkt_aoi)
        if aoi is None or aoi.is_empty:
            return False
        polys = []

        for r in products:
            fp = getattr(r, "geometry", None)
            if fp:
                polys.append(shapely_shape(fp))
        if not polys:
            return False
        union = unary_union(polys)
        return union.covers(aoi)
    except Exception:
        return False


def group_by_frame(products):
    """按 (日期, frameNumber) 分组 → {date: {frame: [products]}}"""

    result = {}
    for r in products:
        p = r.properties
        date = str(p.get("startTime", ""))[:10]
        frame = str(p.get("frameNumber", "?"))
        result.setdefault(date, {}).setdefault(frame, []).append(r)
    return result


def group_by_orbit(results):
    """按相对轨道号 pathNumber 分组 → {orbit: [products]}"""
    groups = {}
    for r in results:
        orb = str(r.properties.get("pathNumber", "?"))
        groups.setdefault(orb, []).append(r)
    return groups


# ==================== 主流程 ====================


def run_download(aoi_path, start, end, polarizations, out_dir, max_results=None, config=None):
    """兼容包装：委托 DownloadSession（v2 重构，见 download_session.py）。
    原 v1 长流程逻辑已封装为 DownloadSession 类（认证/搜索/选择/校验/下载拆成方法）。"""
    from download_session import DownloadSession

    return DownloadSession(config=config).run(
        aoi_path, start, end, polarizations, out_dir, max_results=max_results
    )


# ==================== 历史 v1 实现（保留供参考/回退）====================
def _run_download_v1(aoi_path, start, end, polarizations, out_dir, max_results=None, config=None):
    """AOI→WKT → 认证 → 搜索全部方向 → (方向,轨道)分组 → 覆盖过滤 →
    用户选轨道组 → 清单 → 确认 → 批量下载。

    SBAS 要求同轨道同方向且完全覆盖研究区；方向不预设，由用户根据
    各组景数选。polarizations: 如 ['VV+VH', 'VV']，逐组搜索后合并。
    """
    import asf_search
    from asf_search import ASFSession

    cfg = config or load_config()
    os.makedirs(out_dir, exist_ok=True)

    # AOI → WKT
    wkt = aoi_to_wkt(aoi_path)
    print(f"[OK] AOI → WKT: {wkt[:90]}{'...' if len(wkt) > 90 else ''}")

    # 认证（EDL token + asf-urs cookie）
    session = ASFSession()
    session.auth_with_creds(cfg["username"], cfg["password"])
    print("[OK] Earthdata 认证成功")

    # 逐极化搜索（不限定方向），合并结果
    all_results = []
    for pol in polarizations:
        kwargs = dict(
            platform="SENTINEL-1",
            processingLevel="SLC",
            beamMode="IW",
            polarization=pol,
            start=iso_datetime(start),
            end=iso_datetime_end(end),
            intersectsWith=wkt,
        )
        if max_results:
            kwargs["maxResults"] = max_results
        r = asf_search.geo_search(**kwargs)
        print(f"[OK] 极化 {pol}: 搜索到 {len(r)} 个结果")
        all_results.extend(r)
    if not all_results:
        print(f"[!] 未搜索到数据（{start}~{end}），请调整时间范围或 AOI。")
        return []

    # 按 (方向, 相对轨道) 分组
    groups = {}
    for r in all_results:
        key = (r.properties.get("flightDirection", "?"), str(r.properties.get("pathNumber", "?")))
        groups.setdefault(key, []).append(r)
    print(f"[OK] 共 {len(groups)} 个 (方向,轨道) 组")

    # 覆盖判断：单景完全覆盖优先，不行再看组内并集（跨帧场景）
    covering = {}
    cross_frame = {}  # 记录有上下景的轨道组
    for key, prods in groups.items():
        # 同轨道同 frame 的 footprint 一致，取第一景试单景覆盖
        fp = prods[0].geometry if hasattr(prods[0], "geometry") else None
        single_ok = fp is not None and footprint_contains(wkt, fp)
        if single_ok:
            covering[key] = prods
            continue

        # 单景不够就试并集：研究区可能跨上下两景边界
        union_ok = group_union_covers(wkt, prods)

        if union_ok:
            covering[key] = prods
            cross_frame[key] = True
            # 同一时相是否有多个 frame
            frames = group_by_frame(prods)
            multi = sum(1 for d in frames if len(frames[d]) > 1)
            print(
                f"[!] 轨道组 {key[0]}/{key[1]}: 单景不覆盖但并集覆盖"
                f"（研究区跨帧边界，{multi} 个时相需下载上下景）"
            )
    if covering:
        print(f"[OK] 覆盖研究区的轨道组: {', '.join(f'{d}/{o}' for d, o in covering)}")
    else:
        print("[!] 没有轨道覆盖研究区，将按相交结果处理（可能边缘缺景）。")
        covering = groups

    # 展示各组景数，让用户选择
    print("\n=== 可选轨道组（按景数排序） ===")
    ranked = sorted(covering.items(), key=lambda kv: -len(kv[1]))
    for i, ((d, o), prods) in enumerate(ranked, 1):
        print(f"  [{i}] {d} / 轨道 {o}: {len(prods)} 景")
    if len(ranked) == 1:
        print(f"\n仅一个轨道组可用，自动选择: {ranked[0][0][0]} / 轨道 {ranked[0][0][1]}")
        chosen = ranked[0][0]
    else:
        while True:
            try:
                sel = input("\n选择要使用的轨道组编号（回车选默认第 1 个）: ").strip()
                if sel == "":
                    sel = "1"
                idx = int(sel)
                if 1 <= idx <= len(ranked):
                    chosen = ranked[idx - 1][0]
                    break
                print(f"编号 {idx} 超出范围（1-{len(ranked)}）")
            except ValueError:
                print("请输入数字编号")
    results = covering[chosen]
    print(f"[OK] 已选择: {chosen[0]} / 轨道 {chosen[1]}（{len(results)} 景）")

    # 生成清单
    items = []
    for r in results:
        p = r.properties
        start_time = str(p.get("startTime", ""))

        items.append(
            {
                "date": start_time[:10].replace("-", ""),
                "orbit": p.get("pathNumber", "?"),
                "direction": p.get("flightDirection", "?"),
                "pol": p.get("polarization", "?"),
                "file": p.get("fileName", "?"),
            }
        )

    print("\n" + format_inventory(items))

    # 确认（轨道号过滤基于已选轨道，可取消）
    choice = _confirm(items)
    if choice is None:
        print("已取消下载。")
        return []
    if choice != "all":
        keep = [i for i, it in enumerate(items) if str(it["orbit"]) == choice]
        results = [results[i] for i in keep]
        items = [items[i] for i in keep]

        if not items:
            print(f"[!] 没有轨道号为 {choice} 的结果，取消下载。")
            return []
        print(f"将下载轨道 {choice} 的 {len(items)} 个结果。")

    # 轨道一致性校验：组内 pathNumber 必须完全一致
    # （防同 frame 被不同轨道复用导致轨道混杂，如 frame 468 含轨道 62/135）
    path_set = {r.properties.get("pathNumber", "?") for r in results}
    if len(path_set) != 1:
        print(
            f"[!] 严重: 选中的 {len(results)} 景包含多个轨道号 {sorted(map(str, path_set))}，"
            f"不能用于 SBAS。请重新选择轨道组。"
        )
        return []
    path_final = list(path_set)[0]
    print(f"[OK] 轨道一致性校验通过: 全部 {len(results)} 景均为轨道 {path_final}")

    # 卫星一致性检查（S1A/S1B/S1C 不混用提示）
    sats = {str(r.properties.get("platform", "?")) for r in results}
    if len(sats) > 1:
        print(
            f"[!] 警告: 选中数据含多颗卫星 {sorted(sats)}，不同卫星混入同一 SBAS"
            f"序列可能影响结果，请确认。"
        )

    # 逐时相覆盖检查：每个时相（同一天）的并集必须完全覆盖研究区
    # （用户核心要求：不是整组并集，而是每个时相单独检查）
    try:
        from analysis import check_per_date_coverage

        ok_dates, bad_dates = check_per_date_coverage(wkt, results)
        print(
            f"[OK] 逐时相覆盖检查: {len(ok_dates)} 个有效时相"
            f"（并集完全覆盖研究区），{len(bad_dates)} 个无效时相"
        )
        if bad_dates:
            print(
                f"[!] 警告: {len(bad_dates)} 个时相影像未完全覆盖研究区，"
                f"将自动排除（示例: {bad_dates[0][0]} 帧{bad_dates[0][1]}）"
            )
            bad_set = {d for d, _, _ in bad_dates}
            results = [
                r for r in results if str(r.properties.get("startTime", ""))[:10] not in bad_set
            ]
            print(f"[OK] 排除无效时相后剩余 {len(results)} 景")
    except ImportError:
        pass  # analysis 缺失时跳过，不影响核心流程

    # 批量下载（官方库自动带认证；URL 白名单 + HTTPS 校验）
    saved = 0
    saved_paths = []
    for r in results:
        fname = r.properties.get("fileName", "?")
        try:
            url = r.properties.get("url", "")

            if url:
                from urllib.parse import urlparse

                u = urlparse(url)
                if u.scheme != "https":
                    raise ValueError(f"下载 URL 非 HTTPS: {url[:60]}")
                host = (u.hostname or "").lower()
                allowed = (
                    "asf.alaska.edu",
                    "earthdata.nasa.gov",
                    "amazonaws.com",
                    "amazonaws.com.cn",
                )
                if not any(host.endswith("." + d) or host == d for d in allowed):
                    raise ValueError(f"下载 URL host 不在白名单: {host}")
            r.download(path=out_dir, session=session)

            dest = os.path.join(out_dir, fname)
            if os.path.exists(dest) and os.path.getsize(dest) > 0:
                saved += 1
                saved_paths.append(dest)
                print(f"[OK] 已保存: {dest} ({os.path.getsize(dest)} bytes)")
            else:
                print(f"[!] 文件为空或未落盘: {dest}")
        except Exception as e:
            print(f"[X] 下载失败 {fname}: {e}")

    print(f"完成。成功下载 {saved}/{len(results)} 个文件，保存在: {out_dir}")
    return saved_paths


def main():

    import argparse

    ap = argparse.ArgumentParser(description="ASF Sentinel-1 自动下载")
    ap.add_argument("--aoi", required=True, help="矢量文件路径 (.shp 或 .kml)")
    ap.add_argument("--start", required=True, help="开始日期 YYYYMMDD")
    ap.add_argument("--end", required=True, help="结束日期 YYYYMMDD")
    ap.add_argument("--pol", default="VV+VH,VV", help="极化（逗号分隔，可多个，如 VV+VH,VV）")
    ap.add_argument("--out", default=os.path.join(os.getcwd(), "sentinel1_data"), help="下载目录")
    ap.add_argument("--max", type=int, default=None, help="每个极化的结果上限（默认不限）")
    args = ap.parse_args()
    if args.max is not None and args.max < 1:
        ap.error("--max 必须 ≥ 1")
    # VV+VH,VV → ['VV+VH', 'VV']
    pols = [p.strip() for p in args.pol.split(",") if p.strip()]
    for p in pols:
        parse_polarization(p)  # 校验

    run_download(args.aoi, args.start, args.end, pols, args.out, max_results=args.max)


if __name__ == "__main__":
    main()
