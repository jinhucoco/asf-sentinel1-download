# -*- coding: utf-8 -*-
"""multi_download 模块单元测试（回归：mode.flag 首次运行不崩溃）"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.multi_download import read_mode  # noqa: E402


def test_read_mode_missing_flag(tmp_path):
    """无 mode.flag（首次运行）→ 默认 multi，不崩溃（2026-08-15 回归案例）"""
    assert read_mode(str(tmp_path)) == "multi"


def test_read_mode_single(tmp_path):
    """mode.flag 内容 single → 返回 single"""
    (tmp_path / "mode.flag").write_text("single", encoding="utf-8")
    assert read_mode(str(tmp_path)) == "single"


def test_read_mode_multi_flag(tmp_path):
    """mode.flag 内容 multi → 返回 multi"""
    (tmp_path / "mode.flag").write_text("multi", encoding="utf-8")
    assert read_mode(str(tmp_path)) == "multi"


def test_read_mode_other(tmp_path):
    """mode.flag 内容未知 → 默认 multi"""
    (tmp_path / "mode.flag").write_text("weird\n", encoding="utf-8")
    assert read_mode(str(tmp_path)) == "multi"
