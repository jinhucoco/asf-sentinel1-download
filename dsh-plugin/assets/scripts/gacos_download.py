"""GACOS 大气延迟数据提交下载器（Python + Playwright）。

GACOS 无 API，只能网页表单提交（限制：每次 ≤20 日期）。本脚本自动填表，
结果邮件发送，用 gacos_fetch.py 收取。

依赖: pip install playwright && playwright install chromium

用法:
  python gacos_download.py --bbox "38.34 101.96 103.48 37.28" \
      --dates 20200104,20200209,... --time 23:10 --email you@xx.com --out ./gacos
  python gacos_download.py --bbox "N W E S" --list 日期清单.txt --time 23:10 --email ...

参数: --bbox "最大纬度N 最小经度W 最大经度E 最小纬度S"（GACOS 顺序 N W E S）
      --time  UTC 时刻 HH:MM（从 SLC 文件名提取，如 23:10）
      --dates 逗号分隔 YYYYMMDD 或 --list 每行一个日期
"""

import argparse
import os
import time


def split_batches(dates, max_per=20):
    return [dates[i : i + max_per] for i in range(0, len(dates), max_per)]


def submit_batch(page, bbox, hh, mm, dates, email):
    page.locator('input[name="N"]').fill(bbox["N"])
    page.locator('input[name="W"]').fill(bbox["W"])
    page.locator('input[name="E"]').fill(bbox["E"])

    page.locator('input[name="S"]').fill(bbox["S"])
    page.locator('select[name="H"]').select_option(hh)
    page.locator('select[name="M"]').select_option(mm)
    page.locator("textarea").fill("\n".join(dates))

    page.locator('input[type="radio"]').nth(1).check()  # Binary grid (ztd)
    page.locator('input[name="email"]').fill(email)
    page.get_by_role("button", name="Submit").click()
    # 轮询等待跳转（2026-08-17 民勤实测：wait_for_url 偶发捕获不到跳转，
    # 同样日期用轮询 10s 内成功；GACOS 服务端排队时响应慢，放宽到 180s）
    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(5)
        if "result.php" in page.url:
            return
    raise TimeoutError("GACOS 提交后 180s 未跳转 result.php")


def main():

    ap = argparse.ArgumentParser(description="GACOS 提交（≤20 日期/次，自动分批）")
    ap.add_argument(
        "--bbox", required=True, help='"N W E S"（最大纬度 最小经度 最大经度 最小纬度）'
    )
    ap.add_argument("--dates", help="逗号分隔 YYYYMMDD")
    ap.add_argument("--list", help="日期清单文件（每行一个 YYYYMMDD）")
    ap.add_argument("--time", default="23:10", help="UTC 时刻 HH:MM")
    ap.add_argument("--email", required=True, help="接收结果邮箱")

    ap.add_argument("--out", default="./gacos", help="输出目录（记录已提交批次）")
    ap.add_argument("--interval", type=int, default=60, help="批次间间隔秒（网站提示勿频繁提交）")
    args = ap.parse_args()
    if not args.dates and not args.list:
        ap.error("需要 --dates 或 --list")

    if args.dates:
        dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    else:
        dates = [l.strip() for l in open(args.list, encoding="utf-8") if l.strip()]

    import re as _re

    bad = [d for d in dates if not _re.fullmatch(r"\d{8}", d)]
    if bad:
        print(f"[!] 非法日期（需 YYYYMMDD）: {bad[:5]}")
        return
    if not dates:
        print("[!] 日期列表为空")
        return
    if not _re.fullmatch(r"\d{2}:\d{2}", args.time):
        print("[!] --time 需 HH:MM 格式（UTC）")
        return
    print(f"共 {len(dates)} 个日期，分 {len(split_batches(dates))} 批提交（每批 ≤20）")

    parts = args.bbox.split()
    if len(parts) != 4:
        print('[!] --bbox 需 4 个值: "N W E S"')
        return
    bbox = {"N": parts[0], "W": parts[1], "E": parts[2], "S": parts[3]}
    hh, mm = args.time.split(":")

    from playwright.sync_api import sync_playwright

    os.makedirs(args.out, exist_ok=True)
    done_file = os.path.join(args.out, "submitted.txt")
    done = set()
    if os.path.exists(done_file):
        done = set(l.strip() for l in open(done_file, encoding="utf-8"))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for i, batch in enumerate(split_batches(dates), 1):
            new = [d for d in batch if d not in done]
            if not new:
                print(f"批 {i}: 全部已提交，跳过")
                continue
            page = browser.new_page()
            page.goto(
                "http://www.gacos.net/index.html", wait_until="domcontentloaded", timeout=120000
            )

            page.wait_for_timeout(6000)
            ok = False
            for attempt in (1, 2):  # 每批最多重试一次（2026-08-17 民勤实测：偶发超时）
                try:
                    submit_batch(page, bbox, hh, mm, new, args.email)
                    print(f"批 {i}: {len(new)} 日期提交成功（{new[0]}...{new[-1]}）")
                    with open(done_file, "a", encoding="utf-8") as f:
                        f.write("\n".join(new) + "\n")
                    ok = True
                    break
                except Exception as e:
                    print(f"批 {i} 第 {attempt} 次失败: {str(e)[:80]}")
                    if attempt == 1:
                        print(f"  等待 {args.interval}s 后重试...")
                        time.sleep(args.interval)
            if not ok:
                print(f"批 {i} 重试后仍失败，本次跳过（下次运行自动补交）")
            page.close()
            if i < len(split_batches(dates)):
                print(f"  等待 {args.interval}s 再提交下一批...")
                time.sleep(args.interval)
        browser.close()
    print("=== GACOS 提交完成。结果将通过邮件发送，用 gacos_fetch.py 收取 ===")


if __name__ == "__main__":
    main()
