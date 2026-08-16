"""multi_download 模块单元测试（回归：mode.flag 首次运行不崩溃）"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.multi_download import (
    DOWNGRADE_STREAK,
    UPGRADE_COOLDOWN_S,
    maybe_downgrade,
    maybe_upgrade,
    read_mode,
)


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


def test_maybe_downgrade_multi_streak(tmp_path):
    """multi 模式连续 2 文件作废 → 写 mode.flag=single 并返回 True（2026-08-16 回归）"""
    args = type("Args", (), {"out": str(tmp_path)})()
    logfile = str(tmp_path / "x.log")
    assert maybe_downgrade("multi", 1, DOWNGRADE_STREAK, args, logfile) is False
    assert not (tmp_path / "mode.flag").exists()
    assert maybe_downgrade("multi", 2, DOWNGRADE_STREAK, args, logfile) is True
    assert (tmp_path / "mode.flag").read_text(encoding="utf-8").strip() == "single"


def test_maybe_downgrade_single_mode(tmp_path):
    """single 模式不降级、不写 flag"""
    args = type("Args", (), {"out": str(tmp_path)})()
    logfile = str(tmp_path / "x.log")
    assert maybe_downgrade("single", 5, DOWNGRADE_STREAK, args, logfile) is False
    assert not (tmp_path / "mode.flag").exists()


def test_maybe_upgrade_multi_noop(tmp_path):
    """multi 模式不触发升级（2026-08-16 新增）"""
    args = type("Args", (), {"out": str(tmp_path)})()
    logfile = str(tmp_path / "x.log")
    assert maybe_upgrade("multi", [2.5, 2.4, 2.3], 3, args, logfile) is False


def test_maybe_upgrade_slow_noop(tmp_path):
    """single 模式但速率低于阈值 → 不升级"""
    args = type("Args", (), {"out": str(tmp_path)})()
    logfile = str(tmp_path / "x.log")
    assert maybe_upgrade("single", [1.9, 1.8, 1.7], 3, args, logfile) is False


def test_maybe_upgrade_fast(tmp_path):
    """single 模式连续 3 个达标速率 → 升级并删除 mode.flag"""
    args = type("Args", (), {"out": str(tmp_path)})()
    logfile = str(tmp_path / "x.log")
    assert maybe_upgrade("single", [2.5, 2.4, 2.3], 3, args, logfile) is True
    assert not (tmp_path / "mode.flag").exists()


def test_maybe_upgrade_cooldown(tmp_path):
    """降级后冷却期内不升级（防模式切换抖动）"""
    args = type("Args", (), {"out": str(tmp_path)})()
    logfile = str(tmp_path / "x.log")
    (tmp_path / "mode.flag").write_text("single", encoding="utf-8")  # mtime=now
    assert maybe_upgrade("single", [2.5, 2.4, 2.3], 3, args, logfile) is False


def test_maybe_upgrade_cooldown_expired(tmp_path):
    """冷却期过后 → 升级并删除 mode.flag"""
    args = type("Args", (), {"out": str(tmp_path)})()
    logfile = str(tmp_path / "x.log")
    flag = tmp_path / "mode.flag"
    flag.write_text("single", encoding="utf-8")
    past = time.time() - UPGRADE_COOLDOWN_S - 5
    os.utime(flag, (past, past))
    assert maybe_upgrade("single", [2.5, 2.4, 2.3], 3, args, logfile) is True
    assert not flag.exists()
