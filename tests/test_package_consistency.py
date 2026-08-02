# -*- coding: utf-8 -*-
"""发布一致性测试：skills/asf-sentinel1-download/（发布镜像）必须与仓库根目录源一致。

背景：仓库根目录是唯一编辑源；skills/ 子目录是自包含发布镜像
（npm 的 pi.skills 与 install.sh 都整体复制该目录）。镜像漂移
会导致发布出旧版/不一致版本。本测试在改一处忘另一处时立即报警。
比较时忽略行尾符（CRLF/LF 视为等价）。
"""
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIRROR = os.path.join(REPO, "skills", "asf-sentinel1-download")

# 必须在两处保持一致的镜像文件（相对仓库根目录）
MIRROR_FILES = [
    "SKILL.md",
    "download.py",
    "analyze.py",
    "analysis.py",
    "robust_download.py",
    "progress_gui.py",
    "requirements.txt",
    "config.example.json",
]


def _norm(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


@pytest.mark.parametrize("name", MIRROR_FILES)
def test_mirror_matches_root(name):
    src = os.path.join(REPO, name)
    dst = os.path.join(MIRROR, name)
    assert os.path.exists(src), f"根目录缺少 {name}"
    assert os.path.exists(dst), f"镜像缺少 {name}（skills/asf-sentinel1-download/）"
    assert _norm(open(src, "rb").read()) == _norm(open(dst, "rb").read()), (
        f"{name} 两处不一致！请同步 skills/asf-sentinel1-download/（镜像）或根目录（源）"
    )


def test_mirror_has_no_forbidden_files():
    """镜像不应包含 config.json（真实凭证）等意外文件"""
    forbidden = {"config.json", "__pycache__"}
    for f in os.listdir(MIRROR):
        assert f not in forbidden, f"镜像目录包含禁止文件: {f}"
