# -*- coding: utf-8 -*-
"""download_guard 模块单元测试"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.download_guard import parse_progress, should_restart


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


def test_parse_progress_ignores_auth_lines(tmp_path):
    """重启时写的 '[OK] 认证成功' 行（无 [n/total] 前缀）不计入 ok"""
    log = tmp_path / "multi_download.log"
    log.write_text(
        "[08-15 20:43:32] [OK] 认证成功: jinhu | 线程=8\n"
        "[08-15 20:56:55] [1/85] [OK] S1A_xxx.zip 3.89GB\n"
        "[08-16 10:06:46] [OK] 认证成功: jinhu | 线程=8\n"
        "[08-16 10:10:09] [OK] 认证成功: jinhu | 线程=8\n",
        encoding="utf-8",
    )
    p = parse_progress(str(log))
    assert p["total"] == 85
    assert p["ok"] == 1
    assert p["fail"] == 0
    assert p["skip"] == 0


def test_should_restart():
    """死亡即重启；卡死超阈值重启；正常下载不重启"""
    assert should_restart(alive=False, bytes_growing=False, stall_seconds=0, stall_min=40)
    assert should_restart(alive=True, bytes_growing=False, stall_seconds=40 * 60, stall_min=40)
    assert not should_restart(alive=True, bytes_growing=True, stall_seconds=9999, stall_min=40)
    assert not should_restart(alive=True, bytes_growing=False, stall_seconds=10 * 60, stall_min=40)


def test_health_body(tmp_path):
    """体检报告包含进度/状态/速度/重启数/日志尾部"""
    from scripts.download_guard import health_body

    log = tmp_path / "multi_download.log"
    log.write_text("[1/85] [OK] xxx\n[2/85] [DL] yyy\n", encoding="utf-8")
    prog = {"ok": 1, "fail": 0, "skip": 0, "current": "yyy", "total": 85}
    body = health_body(
        str(log), prog, str(tmp_path), alive=True, restarts=2, note="", speed_mbps=7.5
    )
    assert "1/85" in body
    assert "✅ 正常" in body
    assert "7.5 MB/s" in body
    assert "重启次数: 2" in body
    assert "yyy" in body

    body2 = health_body(
        str(log),
        prog,
        str(tmp_path),
        alive=False,
        restarts=2,
        note="⚠ 已介入处理: 进程死亡",
        speed_mbps=None,
    )
    assert "❌ 进程不在" in body2
    assert "⚠ 已介入处理" in body2
