"""NASADEM 30m DEM 官方源下载器（Earthdata / USGS e4ftl01）。
有 NASA Earthdata 账号即可用，无需百度网盘。

用法:
  python dem_download.py --aoi 研究区.shp --out ./dem
  python dem_download.py --lat 37.3 38.3 --lon 102.0 103.4 --out ./dem   # 或直接给范围

认证: 读取 ASF 技能的 config.json，或环境变量 EARTHDATA_USERNAME/PASSWORD
依赖: pip install earthaccess shapely pyshp
"""

import argparse
import glob
import math
import os
import zipfile


def get_creds():
    """Earthdata 凭证：优先环境变量，回退技能 config.json"""
    u = os.environ.get("EARTHDATA_USERNAME")
    p = os.environ.get("EARTHDATA_PASSWORD")
    if u and p:
        return u, p

    cfg_paths = [
        os.path.expanduser("~/.pi/agent/skills/insar-genie/config.json"),
        os.path.expanduser("~/.pi/agent/skills/asf-sentinel1-download/config.json"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"),
    ]
    for cp in cfg_paths:
        if os.path.exists(cp):
            import json

            cfg = json.load(open(cp, encoding="utf-8"))
            return cfg["username"], cfg["password"]
    return None, None


def aoi_to_bbox(aoi):
    """shp/kml → (lon_min, lat_min, lon_max, lat_max)"""

    if aoi.lower().endswith(".shp"):
        import shapefile

        r = shapefile.Reader(aoi)
        pts = [p for shape in r.shapes() for p in shape.points]
    else:  # kml（defusedxml 防 XXE + 大小限制）
        if os.path.getsize(aoi) > 10 * 1024 * 1024:
            raise ValueError(f"KML 文件过大: {aoi}")

        try:
            from defusedxml import ElementTree as ET
        except ImportError:
            raise ValueError("缺少 defusedxml（安全 XML 解析库），请 pip install defusedxml")
        ns = {"k": "http://www.opengis.net/kml/2.2"}
        tree = ET.parse(aoi)
        coords = tree.findall(".//k:coordinates", ns)
        pts = []
        for c in coords:
            for tok in (c.text or "").strip().split():
                parts = tok.split(",")
                pts.append((float(parts[0]), float(parts[1])))
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    return min(lons), min(lats), max(lons), max(lats)


def tiles_for_bbox(lon_min, lat_min, lon_max, lat_max):
    """推导 NASADEM 分幅（n37e102 覆盖 37-38N, 102-103E；南纬 s、西经 w）"""
    tiles = []
    for lat in range(math.floor(lat_min), math.ceil(lat_max)):
        for lon in range(math.floor(lon_min), math.ceil(lon_max)):
            ns = "s" if lat < 0 else "n"
            ew = "w" if lon < 0 else "e"
            tiles.append(f"{ns}{abs(lat):02d}{ew}{abs(lon):03d}")
    return sorted(tiles)


def main():
    ap = argparse.ArgumentParser(description="NASADEM 30m 官方下载")
    ap.add_argument("--aoi", help="研究区 shp/kml（自动推导分幅）")
    ap.add_argument("--lat", nargs=2, type=float, help="纬度范围 最小 最大")

    ap.add_argument("--lon", nargs=2, type=float, help="经度范围 最小 最大")
    ap.add_argument("--out", default="./dem", help="输出目录")
    args = ap.parse_args()

    if args.aoi:
        lon_min, lat_min, lon_max, lat_max = aoi_to_bbox(args.aoi)
        print(f"研究区范围: lon {lon_min:.3f}-{lon_max:.3f}, lat {lat_min:.3f}-{lat_max:.3f}")
    elif args.lat and args.lon:
        lon_min, lat_min, lon_max, lat_max = args.lon[0], args.lat[0], args.lon[1], args.lat[1]
    else:
        ap.error("需要 --aoi 或 --lat/--lon")

    tiles = tiles_for_bbox(lon_min, lat_min, lon_max, lat_max)
    print(f"需要的 NASADEM 分幅: {tiles}")

    u, p = get_creds()
    if not u:
        print("[!] 未找到 Earthdata 凭证（环境变量或 config.json）")
        return

    os.environ["EARTHDATA_USERNAME"] = u
    os.environ["EARTHDATA_PASSWORD"] = p

    import earthaccess

    earthaccess.login(strategy="environment")
    os.makedirs(args.out, exist_ok=True)

    want = set(f"NASADEM_HGT_{t}" for t in tiles)
    results = earthaccess.search_data(
        short_name="NASADEM_HGT",
        version="001",
        bounding_box=(lon_min - 0.5, lat_min - 0.5, lon_max + 0.5, lat_max + 0.5),
        count=50,
    )
    sel = [r for r in results if r["umm"]["GranuleUR"] in want]
    print(f"匹配 {len(sel)}/{len(tiles)} 个分幅")
    if not sel:
        print("[!] 搜索无结果，检查范围/账号权限")
        return

    _ = earthaccess.download(sel, args.out)  # 下载执行；解压用 glob 单独处理
    # 解压（防 zip 路径穿越）
    for z in glob.glob(os.path.join(args.out, "*.zip")):
        with zipfile.ZipFile(z) as zf:
            for m in zf.namelist():
                if m.startswith("/") or ".." in m.split("/") or (":" in m.split("/")[0]):
                    raise ValueError(f"不安全成员: {m}")
            zf.extractall(args.out)

        os.remove(z)
    hgts = sorted(glob.glob(os.path.join(args.out, "*.hgt")))
    print(f"完成: {len(hgts)} 个 hgt 就绪")
    for h in hgts:
        print(f"  {os.path.basename(h)} ({os.path.getsize(h) / 1e6:.1f}MB)")


if __name__ == "__main__":
    main()
