"""pytest 全局配置：把 scripts/ 加入 sys.path，使测试能 import 技能脚本。"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))


def pytest_configure(config):
    """CI 无头环境兜底：强制 Agg 后端（避免 DISPLAY 缺失报错）。"""
    import os

    os.environ.setdefault("MPLBACKEND", "Agg")
