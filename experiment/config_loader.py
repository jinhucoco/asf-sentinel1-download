"""从 config.env 读取实验配置（KEY=VALUE）。

bat 脚本用 for /f 读同一文件；python 用 load_config() 读。
config.env 在本机目录（gitignore），config.example.env 是模板。
"""

import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.env")


def load_config(path=None):
    """返回 {KEY: value}，缺失或文件不存在返回 {}"""
    p = path or CONFIG_FILE
    cfg = {}
    if not os.path.exists(p):
        return cfg
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def get(key, default=""):
    """便捷取配置值"""
    return load_config().get(key, default)
