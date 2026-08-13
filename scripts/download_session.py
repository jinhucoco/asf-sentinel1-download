"""ASF Sentinel-1 下载会话类（v2 重构，2026-08-13）。

把 download.py 的 run_download() 长流程（认证 → 搜索 → 分组 → 覆盖过滤 →
选择 → 校验 → 下载）封装为 DownloadSession 类，拆成可复用、可测试的实例方法。

纯工具函数（aoi_to_wkt / footprint_contains / group_union_covers / format_inventory
/ _confirm / parse_polarization / iso_datetime 等）仍由 download.py 提供（模块级），
本模块只 import 复用，不做重复实现。
"""

import os

from download import (
    _confirm,
    aoi_to_wkt,
    footprint_contains,
    format_inventory,
    group_union_covers,
    iso_datetime,
    iso_datetime_end,
    load_config,
)


class DownloadSession:
    """ASF Sentinel-1 下载会话：认证 → 搜索 → 分组 → 覆盖过滤 → 选择 → 校验 → 下载。"""

    def __init__(self, config=None):
        self.config = config or load_config()
        self.session = None

    # ---------- 认证 ----------
    def auth(self):
        from asf_search import ASFSession

        self.session = ASFSession()
        self.session.auth_with_creds(self.config["username"], self.config["password"])
        return self.session

    # ---------- 搜索 ----------
    def search(self, wkt, start, end, polarizations, max_results=None):
        """逐极化搜索（不限定方向），合并后按 (方向,轨道) 分组。"""
        import asf_search

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
            return {}
        groups = {}
        for r in all_results:
            key = (
                r.properties.get("flightDirection", "?"),
                str(r.properties.get("pathNumber", "?")),
            )
            groups.setdefault(key, []).append(r)
        print(f"[OK] 共 {len(groups)} 个 (方向,轨道) 组")
        return groups

    # ---------- 覆盖过滤 ----------
    def covering_groups(self, wkt, groups):
        """只保留完全覆盖研究区的轨道组（单景覆盖或跨帧并集覆盖）。"""
        covering = {}
        for key, prods in groups.items():
            fp = prods[0].geometry if hasattr(prods[0], "geometry") else None
            if fp is not None and footprint_contains(wkt, fp):
                covering[key] = prods
                continue
            if group_union_covers(wkt, prods):
                covering[key] = prods
        if covering:
            print(f"[OK] 覆盖研究区的轨道组: {', '.join(f'{d}/{o}' for d, o in covering)}")
        else:
            print("[!] 没有轨道覆盖研究区，将按相交结果处理（可能边缘缺景）。")
            covering = groups
        return covering

    # ---------- 选择轨道组 ----------
    def select_group(self, covering):
        """展示可选轨道组，用户选择（单组自动选，多组交互）。"""
        ranked = sorted(covering.items(), key=lambda kv: -len(kv[1]))
        print("\n=== 可选轨道组（按景数排序） ===")
        for i, ((d, o), prods) in enumerate(ranked, 1):
            print(f"  [{i}] {d} / 轨道 {o}: {len(prods)} 景")
        if len(ranked) == 1:
            print(f"\n仅一个轨道组可用，自动选择: {ranked[0][0][0]} / 轨道 {ranked[0][0][1]}")
            return ranked[0][0]
        while True:
            try:
                sel = input("\n选择要使用的轨道组编号（回车选默认第 1 个）: ").strip()
                idx = int(sel) if sel else 1
                if 1 <= idx <= len(ranked):
                    return ranked[idx - 1][0]
                print(f"编号 {idx} 超出范围（1-{len(ranked)}）")
            except ValueError:
                print("请输入数字编号")

    # ---------- 校验 ----------
    def validate(self, wkt, results):
        """轨道一致性 + 卫星检查 + 逐时相覆盖校验，返回过滤后的结果。"""
        path_set = {r.properties.get("pathNumber", "?") for r in results}
        if len(path_set) != 1:
            print(
                f"[!] 严重: 选中的 {len(results)} 景包含多个轨道号 {sorted(map(str, path_set))}，"
                f"不能用于 SBAS。请重新选择轨道组。"
            )
            return []
        print(f"[OK] 轨道一致性校验通过: 全部 {len(results)} 景均为轨道 {list(path_set)[0]}")

        sats = {str(r.properties.get("platform", "?")) for r in results}
        if len(sats) > 1:
            print(f"[!] 警告: 选中数据含多颗卫星 {sorted(sats)}，请确认。")

        try:
            from analysis import check_per_date_coverage

            ok_dates, bad_dates = check_per_date_coverage(wkt, results)
            print(f"[OK] 逐时相覆盖检查: {len(ok_dates)} 个有效时相，{len(bad_dates)} 个无效时相")
            if bad_dates:
                bad_set = {d for d, _, _ in bad_dates}
                results = [
                    r for r in results if str(r.properties.get("startTime", ""))[:10] not in bad_set
                ]
                print(f"[OK] 排除无效时相后剩余 {len(results)} 景")
        except ImportError:
            pass
        return results

    # ---------- 下载 ----------
    def download(self, results, out_dir):
        """批量下载（HTTPS + host 白名单校验，防 token 泄露/SSRF）。"""
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
                r.download(path=out_dir, session=self.session)
                dest = os.path.join(out_dir, fname)
                if os.path.exists(dest) and os.path.getsize(dest) > 0:
                    saved_paths.append(dest)
                    print(f"[OK] 已保存: {dest} ({os.path.getsize(dest)} bytes)")
                else:
                    print(f"[!] 文件为空或未落盘: {dest}")
            except Exception as e:
                print(f"[X] 下载失败 {fname}: {e}")
        print(f"完成。成功下载 {len(saved_paths)}/{len(results)} 个文件，保存在: {out_dir}")
        return saved_paths

    # ---------- 编排（门面） ----------
    def run(self, aoi_path, start, end, polarizations, out_dir, max_results=None):
        """AOI→WKT → 认证 → 搜索 → 覆盖过滤 → 用户选轨道组 → 校验 → 下载。"""
        os.makedirs(out_dir, exist_ok=True)

        wkt = aoi_to_wkt(aoi_path)
        print(f"[OK] AOI → WKT: {wkt[:90]}{'...' if len(wkt) > 90 else ''}")

        self.auth()
        print("[OK] Earthdata 认证成功")

        groups = self.search(wkt, start, end, polarizations, max_results)
        if not groups:
            print(f"[!] 未搜索到数据（{start}~{end}），请调整时间范围或 AOI。")
            return []

        covering = self.covering_groups(wkt, groups)
        chosen = self.select_group(covering)
        results = covering[chosen]
        print(f"[OK] 已选择: {chosen[0]} / 轨道 {chosen[1]}（{len(results)} 景）")

        # 生成清单
        items = []
        for r in results:
            p = r.properties
            items.append(
                {
                    "date": str(p.get("startTime", ""))[:10].replace("-", ""),
                    "orbit": p.get("pathNumber", "?"),
                    "direction": p.get("flightDirection", "?"),
                    "pol": p.get("polarization", "?"),
                    "file": p.get("fileName", "?"),
                }
            )
        print("\n" + format_inventory(items))

        # 确认
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

        # 校验 + 下载
        results = self.validate(wkt, results)
        if not results:
            return []
        return self.download(results, out_dir)
