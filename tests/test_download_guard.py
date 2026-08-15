# -*- coding: utf-8 -*-
"""download_guard 模块单元测试"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.download_guard import parse_progress, should_restart  # noqa: E402


def test_parse_progress(tmp_path):
    """日志解析：OK/FAIL/跳过/DL 计数与总数"""
    log = tmp_path / "multi_download.log"
    log.write_text(
        "[08-15 20:45:08] [1/85] [DL] S1A_xxx.zip 3.89GB\n"
        "[08-15 20:56:55] [1/85] [OK] S1A_xxx.zip 3.89GB\n"
        "[08-15 21:01:32] [2/85] 跳过(已完成): S1A_yyy\n"
        "[08-15 21:05:00] [3/85] [DL] S1A_zzz.zip 4.02GB\n"
        "[08-15 21:10:00] [3/85] [FAIL] S1A_zzz\n",
        encoding="utf-8",
    )
    p = parse_progress(str(log))
    assert p["total"] == 85
    assert p["ok"] == 1
    assert p["skip"] == 1
    assert p["fail"] == 1
    assert "S1A_zzz" in p["current"]


def test_parse_progress_missing_file(tmp_path):
    """日志不存在 → 全 0"""
    p = parse_progress(str(tmp_path / "nope.log"))
    assert p == {"ok": 0, "fail": 0, "skip": 0, "current": "", "total": 0}


def test_should_restart():
    """死亡即重启；卡死超阈值重启；正常下载不重启"""
    assert should_restart(alive=False, bytes_growing=False, stall_seconds=0, stall_min=40)
    assert should_restart(alive=True, bytes_growing=False, stall_seconds=40 * 60, stall_min=40)
    assert not should_restart(alive=True, bytes_growing=True, stall_seconds=9999, stall_min=40)
    assert not should_restart(alive=True, bytes_growing=False, stall_seconds=10 * 60, stall_min=40)


def test_next_report_time():
    """工作时段整点网格：9/11/13/15/17 推送；18 点后夜间静默"""
    from datetime import datetime

    from scripts.download_guard import next_report_time

    # 08:00 → 下一个 09:00
    t = next_report_time(9, 18, 2, datetime(2026, 8, 15, 8, 0))
    assert t.hour == 9
    # 10:30 → 下一个 11:00
    t = next_report_time(9, 18, 2, datetime(2026, 8, 15, 10, 30))
    assert t.hour == 11
    # 恰好整点 09:00 → 下一个 11:00（当前 >= 网格点才推送）
    t = next_report_time(9, 18, 2, datetime(2026, 8, 15, 9, 0))
    assert t.hour == 11
    # 17:30 已过全部网格点 → None（今天不再推）
    assert next_report_time(9, 18, 2, datetime(2026, 8, 15, 17, 30)) is None
    # 19:00 / 20:00（工作时段外启动）→ None，夜间静默
    assert next_report_time(9, 18, 2, datetime(2026, 8, 15, 19, 0)) is None
    assert next_report_time(9, 18, 2, datetime(2026, 8, 15, 20, 0)) is None
