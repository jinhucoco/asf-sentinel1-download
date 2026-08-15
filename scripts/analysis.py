"""ASF 数据质量分析与选择工具（独立分析函数）

沉淀的功能：
1. 逐时相覆盖检查 —— 同一时相（同一天）所有影像并集必须完全覆盖研究区
   （用户核心要求：不是整组并集，而是每个时相单独检查）
2. 轨道/卫星一致性 —— 同 frame 可能被不同轨道复用（如 frame468 混 62/135），
   不同轨道/卫星绝不能混入同一 SBAS 序列
3. frame 覆盖分析 —— 每个 frame 的覆盖面积比、时相范围、景数
4. 每月采样 —— 按月取代表时相（含该时相所有帧）
5. 覆盖图生成 —— 研究区 vs 各 frame 影像覆盖范围可视化
6. 清单导出 —— download_list.txt / CSV
"""

import os
from collections import defaultdict

# ==================== 逐时相覆盖检查 ====================


def check_per_date_coverage(wkt_aoi, products):
    """逐时相覆盖检查 → (有效时相, 无效时相)

    SBAS 要求每个有效时相（同一天）的所有帧 footprint 并集【完全覆盖】
    研究区。部分帧缺失的时相不能用——研究区其他地方那天没有数据。

    返回：
        ok_dates: [(date, [frame...], n_files)]
        bad_dates: [(date, [frame...], n_files)]
    """
    from shapely.geometry import shape
    from shapely.ops import unary_union
    from shapely.wkt import loads

    aoi = loads(wkt_aoi)
    by_date = defaultdict(list)
    for r in products:
        by_date[str(r.properties.get("startTime", ""))[:10]].append(r)

    ok_dates, bad_dates = [], []
    for date in sorted(by_date):
        prods = by_date[date]
        frames = sorted({p.properties.get("frameNumber") for p in prods})
        fps = [shape(p.geometry) for p in prods if p.geometry]

        if not fps:
            bad_dates.append((date, frames, len(prods)))
            continue
        union = unary_union(fps)
        if union.covers(aoi):
            ok_dates.append((date, frames, len(prods)))
        else:
            bad_dates.append((date, frames, len(prods)))
    return ok_dates, bad_dates


# ==================== 裁剪清单复检 ====================


def per_date_coverage_report(wkt_aoi, date_footprints):
    """逐时相并集覆盖率（纯函数，可离线测试）→ {date: {ratio, covers}}

    给定 {date: [GeoJSON footprint...]} 计算每个时相并集对研究区的覆盖率
    ratio（0~1）与是否完全覆盖 covers。用于对【裁剪/自定义下载清单】做
    逐时相覆盖复检——check_per_date_coverage 用的是搜索返回的【全部帧】，
    裁剪掉冗余帧（如省磁盘只留主覆盖帧）后必须按裁剪后的清单重新校验，
    否则单帧足迹偏位的时相会漏检（实测 2025-02-06：帧 463 单帧仅覆盖
    研究区 90.2%，补相邻帧 468 后并集才 100%）。
    """
    from shapely.geometry import shape
    from shapely.ops import unary_union
    from shapely.wkt import loads

    aoi = loads(wkt_aoi)
    report = {}
    for date, geoms in sorted(date_footprints.items()):
        fps = [shape(g) for g in geoms if g]
        if not fps:
            report[date] = {"ratio": 0.0, "covers": False}
            continue
        union = unary_union(fps)
        report[date] = {
            "ratio": union.intersection(aoi).area / aoi.area,
            "covers": bool(union.covers(aoi)),
        }
    return report


def verify_download_list(wkt_aoi, rows, search_fn=None, log=print):
    """下载清单（csv 行：date/file）逐时相覆盖复检 → (ok_dates, bad_dates)

    每个时相用清单内全部文件（granule_search 取真实 footprint）做并集
    覆盖检查；并集未完全覆盖或 granule 查询失败即未达标。裁剪/自定义
    清单在下载前必须跑本复检（配合 multi_download.py --verify-aoi）。
    search_fn 可注入（单元测试用假函数）；默认 asf_search.granule_search。

    返回:
        ok_dates:  [(date, ratio), ...]
        bad_dates: [(date, ratio), ...]
    """
    from collections import defaultdict

    if search_fn is None:
        import asf_search

        search_fn = asf_search.granule_search

    by_date = defaultdict(list)
    for row in rows:
        fn = (row.get("file") or "").strip()
        d = (row.get("date") or "").strip()
        if fn and d:
            by_date[d].append(fn)

    ok_dates, bad_dates = [], []
    for date in sorted(by_date):
        geoms, missing = [], []
        for fn in by_date[date]:
            try:
                prods = search_fn(fn.replace(".zip", ""))
            except Exception as e:  # 网络异常按未达标处理并记录
                missing.append(f"{fn} ({str(e)[:40]})")
                continue
            if not prods:
                missing.append(fn)
                continue
            geoms.append(prods[0].geometry)
        report = per_date_coverage_report(wkt_aoi, {date: geoms})
        info = report[date]
        if missing:
            log(f"  {date}: {len(missing)} 景查询失败（未达标）: {missing[0][:60]}")
        if info["covers"] and not missing:
            ok_dates.append((date, info["ratio"]))
        else:
            bad_dates.append((date, info["ratio"]))
    return ok_dates, bad_dates


# ==================== 轨道 / 卫星一致性 ====================


def check_orbit_consistency(products):
    """组内 pathNumber 是否完全一致 → (一致?, 轨道集合, 违规影像列表)

    背景：ASF 中同一 frame 编号可能被不同轨道复用（实测 frame 468 混 62/135），
    不同轨道绝不能混入同一 SBAS 序列。
    """
    from collections import Counter

    cnt = Counter(p.properties.get("pathNumber", "?") for p in products)
    paths = set(cnt)
    if len(paths) <= 1:
        return True, paths, []
    # 取最多的轨道为主，其余为违规
    main_path = cnt.most_common(1)[0][0]
    bad = [p for p in products if p.properties.get("pathNumber", "?") != main_path]
    return False, paths, bad


def check_satellite_consistency(products):
    """组内卫星（platform）是否一致 → (一致?, 卫星集合)

    Sentinel-1 从 S1A/S1B 过渡到 S1C，不同卫星传感器特性有差异，
    混入同一 SBAS 序列需谨慎。
    """

    sats = {str(p.properties.get("platform", "?")) for p in products}
    return len(sats) <= 1, sats


# ==================== frame 覆盖分析 ====================


def analyze_frame_coverage(wkt_aoi, products):
    """每个 frame 的研究区覆盖分析 → {frame: {...}}

    每项含 n_files / first_date / last_date / cover_ratio（面积比 0~1）
    / fully_covers（单帧是否 100% 覆盖）。
    """
    from shapely.geometry import shape
    from shapely.wkt import loads

    aoi = loads(wkt_aoi)
    by_frame = defaultdict(list)
    for p in products:
        by_frame[p.properties.get("frameNumber", "?")].append(p)

    result = {}
    for fr, prods in sorted(by_frame.items(), key=lambda kv: -len(kv[1])):
        dates = sorted(str(p.properties.get("startTime", ""))[:10] for p in prods)

        fp = shape(prods[0].geometry) if prods[0].geometry else None
        ratio = aoi.intersection(fp).area / aoi.area if fp else 0.0
        result[fr] = {
            "n_files": len(prods),
            "first_date": dates[0] if dates else "?",
            "last_date": dates[-1] if dates else "?",
            "cover_ratio": ratio,
            "fully_covers": bool(fp and fp.covers(aoi)),
        }
    return result


# ==================== 每月采样 ====================


def monthly_sample(products, rule="first"):
    """每月取一个代表时相（含该时相所有帧）。rule: first/middle/last"""
    return sample_by_frequency(products, "monthly", rule)


def sample_by_frequency(products, frequency="monthly", rule="first"):
    """按采样频率取代表时相，返回选中的影像列表。

    frequency: all（不采样）/ monthly / quarterly / semiyearly / yearly
    rule: first（最早时相）/ middle / last
    每个采样区间选中的时相包含该时相的所有帧（跨帧上下景都保留）。
    """
    if frequency == "all":
        return list(products)

    # 区间分桶：monthly→YYYY-MM, quarterly→YYYY-Qn, semiyearly→YYYY-Hn, yearly→YYYY
    def bucket(ymd):
        y, m = ymd[:4], int(ymd[5:7])
        if frequency == "monthly":
            return f"{y}-{ymd[5:7]}"
        if frequency == "quarterly":
            return f"{y}-Q{(m - 1) // 3 + 1}"
        if frequency == "semiyearly":
            return f"{y}-H{1 if m <= 6 else 2}"
        if frequency == "yearly":
            return y
        return ymd  # 未知频率 → 按天

    buckets = defaultdict(list)
    for p in products:
        ymd = str(p.properties.get("startTime", ""))[:10]
        buckets[bucket(ymd)].append(p)

    selected = []
    for key in sorted(buckets):
        prods = buckets[key]
        dates = sorted(set(str(p.properties.get("startTime", ""))[:10] for p in prods))
        if not dates:
            continue
        if rule == "first":
            target = dates[0]
        elif rule == "last":
            target = dates[-1]
        else:  # middle
            target = dates[len(dates) // 2]
        day_prods = [p for p in prods if str(p.properties.get("startTime", ""))[:10] == target]
        selected.extend(day_prods)
    return selected


FREQUENCY_CHOICES = ["all", "monthly", "quarterly", "semiyearly", "yearly"]
FREQUENCY_LABELS = {
    "all": "全部（不采样）",
    "monthly": "每月",
    "quarterly": "每季度",
    "semiyearly": "每半年",
    "yearly": "每年",
}


def ask_frequency():
    """交互询问采样频率 → 频率字符串"""
    print("\n请选择取景频率:")
    for i, f in enumerate(FREQUENCY_CHOICES, 1):
        print(f"  [{i}] {FREQUENCY_LABELS[f]}")
    while True:
        ans = input("输入编号（回车默认每月 [2]）: ").strip()
        if ans == "":
            return "monthly"
        try:
            idx = int(ans)

            if 1 <= idx <= len(FREQUENCY_CHOICES):
                return FREQUENCY_CHOICES[idx - 1]
        except ValueError:
            pass
        print("请输入有效编号")


def ask_rule():
    """交互询问时相选择规则 → 'first'/'middle'/'last'"""
    print("\n每个区间取哪个时相？")
    print("  [1] 最早时相")
    print("  [2] 中间时相")
    print("  [3] 最晚时相")

    while True:
        ans = input("输入编号（回车默认最早 [1]）: ").strip()
        if ans == "":
            return "first"
        try:
            idx = int(ans)
            if idx == 1:
                return "first"
            if idx == 2:
                return "middle"
            if idx == 3:
                return "last"
        except ValueError:
            pass

        print("请输入有效编号")


# ==================== 清单导出 ====================


def export_list(products, out_path, title="ASF 下载清单"):
    """导出下载清单（TXT + CSV）。每项：日期, 帧号, 轨道号, 卫星, 文件名"""

    import csv

    rows = []
    for p in sorted(products, key=lambda x: str(x.properties.get("startTime", ""))):
        pp = p.properties
        rows.append(
            {
                "date": str(pp.get("startTime", ""))[:10],
                "frame": pp.get("frameNumber", "?"),
                "orbit": pp.get("pathNumber", "?"),
                "satellite": pp.get("platform", "?"),
                "file": pp.get("fileName", "?"),
            }
        )

    # TXT
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# {title} ({len(rows)} 个文件)\n")
        f.write("# 字段: 日期,帧号,轨道号,卫星,文件名\n")
        f.writelines(
            f"{r['date']},{r['frame']},{r['orbit']},{r['satellite']},{r['file']}\n" for r in rows
        )
    # CSV
    csv_path = os.path.splitext(out_path)[0] + ".csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "frame", "orbit", "satellite", "file"])
        w.writeheader()
        w.writerows(rows)
    return out_path, csv_path


# ==================== 覆盖图 ====================


def plot_coverage(wkt_aoi, products, out_path, title="影像覆盖 vs 研究区", orbit=None):
    """研究区 vs 各 frame 影像覆盖范围的可视化图。

    按 (轨道号, frame) 组合分组绘制——同一 frame 编号可能被不同轨道复用
    （如 frame 468 在轨道 135 与 62 下 footprint 完全不同），必须按轨道
    严格区分，避免画错/漏画。orbit 指定时只画该轨道。
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from shapely.geometry import shape
    from shapely.wkt import loads

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False

    aoi = loads(wkt_aoi)
    # 按 (轨道, frame) 分组；轨道号统一转 str 比较（int/str 兼容）
    combos = defaultdict(list)
    for p in products:
        path = str(p.properties.get("pathNumber", "?"))
        if orbit is not None and path != str(orbit):
            continue  # 只画指定轨道

        combos[(path, str(p.properties.get("frameNumber", "?")))].append(p)

    fig, ax = plt.subplots(1, 1, figsize=(12, 10), dpi=120)
    colors = cm.tab10.colors
    combo_list = sorted(combos.items(), key=lambda kv: -len(kv[1]))

    for i, ((path, fr), prods) in enumerate(combo_list):
        fp = shape(prods[0].geometry)
        x, y = fp.exterior.xy
        col = colors[i % len(colors)]
        label = f"轨道{path} / frame{fr}: {len(prods)}景"
        ax.fill(x, y, alpha=0.22, color=col, edgecolor=col, linewidth=1.5, label=label)
        cx, cy = fp.centroid.x, fp.centroid.y
        ax.text(
            cx, cy, f"{fr}", fontsize=12, ha="center", va="center", color=col, fontweight="bold"
        )

    ax_x, ax_y = aoi.exterior.xy
    ax.plot(ax_x, ax_y, color="red", linewidth=3.5, label="研究区 (kml)")

    ax.fill(ax_x, ax_y, color="red", alpha=0.3)

    ax.set_xlabel("经度 Longitude (°E)", fontsize=13)
    ax.set_ylabel("纬度 Latitude (°N)", fontsize=13)
    ax.set_title(title, fontsize=15, fontweight="bold")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path)
    plt.close(fig)
    return out_path
