"""ASF 数据质量分析 CLI —— 搜索后先分析，不下载

用法：
    python analyze.py --aoi <kml/shp> --start YYYYMMDD --end YYYYMMDD --pol VV+VH \
        --out <目录> [--monthly] [--plot]
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analysis import (
    FREQUENCY_LABELS,
    analyze_frame_coverage,
    ask_frequency,
    ask_rule,
    check_orbit_consistency,
    check_per_date_coverage,
    check_satellite_consistency,
    export_list,
    plot_coverage,
    sample_by_frequency,
)
from download import aoi_to_wkt, iso_datetime, iso_datetime_end, load_config, parse_polarization


def main():
    import argparse

    ap = argparse.ArgumentParser(description="ASF Sentinel-1 数据分析（不下载）")
    ap.add_argument("--aoi", required=True, help="矢量文件路径 (.shp/.kml)")
    ap.add_argument("--start", required=True, help="开始日期 YYYYMMDD")
    ap.add_argument("--end", required=True, help="结束日期 YYYYMMDD")

    ap.add_argument("--pol", default="VV+VH,VV", help="极化（逗号分隔）")
    ap.add_argument("--out", default="./analysis_out", help="输出目录")
    ap.add_argument("--sample", action="store_true", help="按频率采样（会询问频率与时相规则）")
    ap.add_argument("--plot", action="store_true", help="生成覆盖图")
    args = ap.parse_args()

    pols = [p.strip() for p in args.pol.split(",") if p.strip()]
    for p in pols:
        parse_polarization(p)

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

    # 按 (方向, 轨道) 分组
    groups = {}

    for r in all_results:
        key = (r.properties.get("flightDirection", "?"), str(r.properties.get("pathNumber", "?")))
        groups.setdefault(key, []).append(r)

    print("\n=== 分析结果 ===")
    for (d, o), prods in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"\n--- {d} / 轨道 {o}: {len(prods)} 景 ---")

        # 轨道一致性
        ok_orb, paths, bad = check_orbit_consistency(prods)
        print(f"  轨道一致性: {'✅' if ok_orb else '❌'} {sorted(paths)}")
        if bad:
            print(
                f"    ⚠ 混入轨道: {sorted({p.properties.get('pathNumber') for p in bad})}"
                f"（{len(bad)} 景，应排除）"
            )

        # 卫星一致性
        ok_sat, sats = check_satellite_consistency(prods)
        print(f"  卫星一致性: {'✅' if ok_sat else '⚠ 多卫星'} {sorted(sats)}")

        # frame 覆盖分析
        print("  frame 覆盖分析:")

        for fr, info in analyze_frame_coverage(wkt, prods).items():
            print(
                f"    frame {fr}: {info['n_files']}景 "
                f"({info['first_date']} ~ {info['last_date']}) "
                f"覆盖面积比={info['cover_ratio']:.0%} "
                f"{'✅完全覆盖' if info['fully_covers'] else '❌部分覆盖'}"
            )

        # 逐时相覆盖检查
        ok_dates, bad_dates = check_per_date_coverage(wkt, prods)
        print(f"  逐时相覆盖: ✅有效时相 {len(ok_dates)} 个 / ❌无效时相 {len(bad_dates)} 个")
        if bad_dates:
            for date, frames, n in bad_dates[:5]:
                print(f"    ⚠ {date}: 帧{frames} 并集未覆盖研究区（{n}景）")

        # 导出清单
        txt, csv = export_list(
            prods, os.path.join(args.out, f"list_{d}_{o}.txt"), f"{d} / 轨道 {o}"
        )
        print(f"  清单已导出: {csv}")

        # 覆盖图
        if args.plot:
            img = plot_coverage(
                wkt,
                prods,
                os.path.join(args.out, f"coverage_{d}_{o}.png"),
                f"{d} / 轨道 {o} 覆盖 vs 研究区",
                orbit=o,
            )
            print(f"  覆盖图已生成: {img}")

        # 采样（仅对有效轨道组询问，无效组跳过）
        if args.sample and ok_dates:
            freq = ask_frequency()

            rule = ask_rule()
            sel = sample_by_frequency(prods, freq, rule)
            print(f"  {FREQUENCY_LABELS[freq]}采样({rule}时相): {len(sel)} 景")
            # 采样后再查一次卫星一致性
            ok_sat2, sats2 = check_satellite_consistency(sel)
            print(f"    采样后卫星: {sorted(sats2)} {'✅' if ok_sat2 else '⚠ 多卫星!'}")
            for s in sel[:3]:
                pp = s.properties
                print(
                    f"    {str(pp.get('startTime', ''))[:10]} frame{pp.get('frameNumber')} "
                    f"{pp.get('fileName', '')[:50]}"
                )
            txt2, csv2 = export_list(
                sel,
                os.path.join(args.out, f"sampled_{d}_{o}_{freq}.txt"),
                f"{d} / 轨道 {o} {FREQUENCY_LABELS[freq]}采样",
            )
            print(f"    采样清单: {csv2}")
        elif args.sample:
            print("  (该轨道组无有效时相，跳过采样)")

    print(f"\n=== 分析完成，输出目录: {args.out} ===")


if __name__ == "__main__":
    main()
