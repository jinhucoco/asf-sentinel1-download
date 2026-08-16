"""multi_download 模块单元测试（2026-08-16 简化后：固定多线程 + MD5 缓存）"""

import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.multi_download import (
    MD5_DONE_FILE,
    get_total_size,
    load_md5_done,
    md5_of,
    save_md5_done,
)


def test_load_md5_done_missing(tmp_path):
    """无缓存文件 → 空 dict（首次运行不崩溃）"""
    assert load_md5_done(str(tmp_path)) == {}


def test_save_and_load_md5_done(tmp_path):
    """写缓存 → 读回一致"""
    save_md5_done(str(tmp_path), {"a.zip": "abc123"})
    assert load_md5_done(str(tmp_path)) == {"a.zip": "abc123"}


def test_load_md5_done_corrupt(tmp_path):
    """缓存文件损坏 → 空 dict（容错）"""
    (tmp_path / MD5_DONE_FILE).write_text("{bad json", encoding="utf-8")
    assert load_md5_done(str(tmp_path)) == {}


def test_md5_of_small_file(tmp_path):
    """md5_of 能计算文件 MD5"""
    p = tmp_path / "f.bin"
    p.write_bytes(b"hello world")
    assert len(md5_of(str(p))) == 32


def test_get_total_size_stream_and_close():
    """get_total_size 使用 stream=True 且显式 close（连接释放）"""
    src = inspect.getsource(get_total_size)
    assert "stream=True" in src
    assert "r.close()" in src


def test_no_single_mode_remnants():
    """2026-08-16 简化：模块不应再有 single/降级/升级机制残留"""
    import scripts.multi_download as md

    src = inspect.getsource(md)
    assert "single_download" not in src
    assert "maybe_downgrade" not in src
    assert "maybe_upgrade" not in src
    assert "read_mode" not in src
