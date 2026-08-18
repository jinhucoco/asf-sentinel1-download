"""SARscape 连接图可视化 v2 - 复刻 SARscape GUI 风格的两张标准图
用法: python plot_connection_graph.py <CG报告目录>
输出: Time-Baseline 图 + Time-Position 图 (与 SARscape GUI 弹窗一致)
"""

import datetime
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def to_dt(s):
    return datetime.datetime.strptime(s, "%Y%m%d")


def parse_cg(cg_dir):
    """解析 connection_graph 目录, 返回 (acq列表, pairs列表)"""
    rep = os.path.join(cg_dir, "CG_report.txt")
    if not os.path.exists(rep):
        raise FileNotFoundError(f"找不到 CG_report.txt: {rep}")
    content = open(rep, encoding="utf-8", errors="replace").read()

    # 时相: id, date, position, valid
    acq = []
    in_images = False
    for line in content.split("\n"):
        if "Number of images" in line:
            in_images = True
            continue
        if in_images:
            m = re.search(
                r"sentinel1_135_(\d{8})_\S+.*?ID : \[(\d+)\].*?Valid : \[(\w+)\].*?Position : \[([-\d.]+)\]",
                line,
            )
            if m:
                acq.append(
                    {
                        "date": m.group(1),
                        "id": int(m.group(2)),
                        "valid": m.group(3) == "YES",
                        "pos": float(m.group(4)),
                    }
                )
            elif line.strip().startswith("*") and "images" not in line:
                break
    acq = sorted(acq, key=lambda a: a["date"])
    sr = min(acq, key=lambda a: abs(a["pos"]))

    # 干涉对: (ref_date, sec_date, normal_b, temp_b)
    pairs = []
    ref_date = None
    for line in content.split("\n"):
        rm = re.search(r"REFERENCE : \d+ .*sentinel1_135_(\d{8})_", line)
        if rm:
            ref_date = rm.group(1)
            continue
        sm = re.search(
            r"SECONDARY : \d+ .*sentinel1_135_(\d{8})_.*?NormalBaseline = \[([-\d.]+)\].*?TemporalBaseline = \[(-?\d+)\]",
            line,
        )
        if sm and ref_date:
            pairs.append(
                {
                    "ref": ref_date,
                    "sec": sm.group(1),
                    "nb": float(sm.group(2)),
                    "tb": int(sm.group(3)),
                }
            )
    return acq, pairs, sr


def style_ax(ax, xlabel, ylabel, title):
    ax.set_xlabel(xlabel, fontsize=13, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=13, fontweight="bold")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.grid(True, axis="x", alpha=0.3, linestyle="--", linewidth=0.5)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_minor_locator(mdates.MonthLocator())
    ax.tick_params(labelsize=11)
    for spine in ax.spines.values():
        spine.set_linewidth(1.2)


def plot_time_baseline(acq, pairs, sr, out_png):
    """Time-Baseline Plot: X=日期, Y=空间基线, 每对连接线+菱形点"""
    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fafafa")

    # 干涉对连线 (线在基线高度)
    for p in pairs:
        d1, d2 = to_dt(p["ref"]), to_dt(p["sec"])
        ax.plot(
            [d1, d2], [p["nb"], p["nb"]], "-", color="#4472C4", linewidth=0.9, alpha=0.35, zorder=2
        )

    # 每个时相: 菱形
    for a in acq:
        d = to_dt(a["date"])
        if a["date"] == sr["date"]:
            color, ec, size = "#FFC000", "black", 14  # 超参考: 黄色
            zorder = 6
        elif a["valid"]:
            color, ec, size = "#00B050", "black", 12  # 有效: 绿色
            zorder = 5
        else:
            color, ec, size = "#FF0000", "black", 12  # 无效: 红色
            zorder = 5
        ax.plot(
            [d],
            [0],
            marker="D",
            markersize=size,
            color=color,
            markeredgecolor=ec,
            markeredgewidth=0.9,
            zorder=zorder,
        )
        ax.annotate(
            str(a["id"]),
            (d, 0),
            textcoords="offset points",
            xytext=(0, -19),
            ha="center",
            fontsize=7.5,
            color="#555555",
            zorder=7,
        )

    ax.axhline(0, color="#999999", linewidth=1.0)
    # 基线范围: 数据集中在±60m, 显示±150m
    ax.set_ylim(-150, 150)
    style_ax(
        ax,
        "Acquisition Date",
        "Normal Baseline [m]",
        f"Time-Baseline Plot  (Super Reference: {sr['date']})",
    )

    # 图例 (右上角避免遮挡)
    legend_elems = [
        Line2D(
            [0],
            [0],
            marker="D",
            color="w",
            markerfacecolor="#FFC000",
            markeredgecolor="black",
            markersize=11,
            label=f"Super Reference ({sr['date']})",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            color="w",
            markerfacecolor="#00B050",
            markeredgecolor="black",
            markersize=11,
            label="Valid Acquisition",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            color="w",
            markerfacecolor="#FF0000",
            markeredgecolor="black",
            markersize=11,
            label="Discarded Acquisition",
        ),
        Line2D(
            [0], [0], color="#4472C4", linewidth=1.5, label=f"Interferometric Pair ({len(pairs)})"
        ),
    ]
    ax.legend(
        handles=legend_elems,
        loc="upper center",
        fontsize=10,
        framealpha=0.92,
        edgecolor="#cccccc",
        ncol=4,
        bbox_to_anchor=(0.5, 1.10),
    )
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_png, dpi=180, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {os.path.basename(out_png)}")


def plot_time_position(acq, pairs, sr, out_png):
    """Time-Position Plot: X=日期, Y=垂直轨道位置, 菱形点"""
    fig, ax = plt.subplots(figsize=(16, 8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fafafa")

    for a in acq:
        d = to_dt(a["date"])
        if a["date"] == sr["date"]:
            color, ec, size = "#FFC000", "black", 13
            zorder = 6
        elif a["valid"]:
            color, ec, size = "#00B050", "black", 11
            zorder = 5
        else:
            color, ec, size = "#FF0000", "black", 11
            zorder = 5
        ax.plot(
            [d],
            [a["pos"]],
            marker="D",
            markersize=size,
            color=color,
            markeredgecolor=ec,
            markeredgewidth=0.9,
            zorder=zorder,
        )
        ax.annotate(
            str(a["id"]),
            (d, a["pos"]),
            textcoords="offset points",
            xytext=(0, -20),
            ha="center",
            fontsize=8,
            fontweight="bold",
            color="#333333",
            zorder=7,
        )

    # 超参考位置虚线
    ax.axhline(sr["pos"], color="#FFC000", linewidth=1.2, linestyle="--", alpha=0.7)
    style_ax(
        ax,
        "Acquisition Date",
        "Relative Position [m]",
        f"Time-Position Plot  (Super Reference: {sr['date']}, position {sr['pos']:.1f} m)",
    )

    legend_elems = [
        Line2D(
            [0],
            [0],
            marker="D",
            color="w",
            markerfacecolor="#FFC000",
            markeredgecolor="black",
            markersize=11,
            label=f"Super Reference ({sr['date']})",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            color="w",
            markerfacecolor="#00B050",
            markeredgecolor="black",
            markersize=11,
            label="Valid Acquisition",
        ),
        Line2D(
            [0],
            [0],
            marker="D",
            color="w",
            markerfacecolor="#FF0000",
            markeredgecolor="black",
            markersize=11,
            label="Discarded Acquisition",
        ),
    ]
    ax.legend(
        handles=legend_elems,
        loc="upper center",
        fontsize=10,
        framealpha=0.92,
        edgecolor="#cccccc",
        ncol=4,
        bbox_to_anchor=(0.5, 1.10),
    )
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_png, dpi=180, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {os.path.basename(out_png)}")


def main():
    if len(sys.argv) < 2:
        print("用法: python plot_connection_graph.py <connection_graph目录>")
        sys.exit(1)
    cg_dir = sys.argv[1]
    acq, pairs, sr = parse_cg(cg_dir)
    print(f"解析: {len(acq)} 时相, {len(pairs)} 干涉对, 超参考 {sr['date']}")
    plot_dir = os.path.join(cg_dir, "plot")
    os.makedirs(plot_dir, exist_ok=True)
    plot_time_baseline(acq, pairs, sr, os.path.join(plot_dir, "Time-Baseline_Plot.png"))
    plot_time_position(acq, pairs, sr, os.path.join(plot_dir, "Time-Position_Plot.png"))


if __name__ == "__main__":
    main()
