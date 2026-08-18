"""发布一致性测试：skills/insar-genie/（发布镜像）必须与仓库根目录源一致。

背景：仓库根目录是唯一编辑源；skills/ 子目录是自包含发布镜像
（npm 的 pi.skills 与 install.sh 都整体复制该目录）。镜像漂移
会导致发布出旧版/不一致版本。本测试在改一处忘另一处时立即报警。

重构后结构（2026-08-09）：脚本统一在 scripts/ 子目录，镜像与根
保持同构——SKILL.md / config.example.json / scripts/*（脚本+依赖清单）。
比较时忽略行尾符（CRLF/LF 视为等价）。

DSH 预设（2026-08-14）：dsh/insar-genie/skills/insar-genie/ 是 DSH 插件
自带的技能副本（随预设安装分发），同样必须与根目录源一致。
"""

import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIRROR = os.path.join(REPO, "skills", "insar-genie")
DSH_PRESET = os.path.join(REPO, "dsh", "insar-genie", "skills", "insar-genie")

# 必须在两处保持一致的镜像文件（相对仓库根目录，scripts/ 自动展开）
MIRROR_FILES = ["SKILL.md", "config.example.json"]


def _norm(b: bytes) -> bytes:
    return b.replace(b"\r\n", b"\n")


def _mirror_files():
    """根目录与镜像 scripts/ 下的全部文件（一致性全集，排除缓存与仓库级工具）"""
    # verify_clone.py 是仓库级验证工具，不随技能安装（不进镜像）
    REPO_ONLY = {"verify_clone.py"}

    def clean(names):
        return sorted(
            n for n in names if not n.startswith("__") and n != "__pycache__" and n not in REPO_ONLY
        )

    root_scripts = clean(os.listdir(os.path.join(REPO, "scripts")))
    mirror_scripts = clean(os.listdir(os.path.join(MIRROR, "scripts")))
    assert root_scripts == mirror_scripts, (
        f"scripts/ 文件集合不一致！根: {root_scripts} vs 镜像: {mirror_scripts}"
    )
    return [f"scripts/{f}" for f in root_scripts]


def _all_pairs():
    yield from ((f, f) for f in MIRROR_FILES)
    yield from ((f, f) for f in _mirror_files())


@pytest.mark.parametrize("name", MIRROR_FILES)
def test_mirror_matches_root(name):
    _assert_same(os.path.join(REPO, name), os.path.join(MIRROR, name), name)


@pytest.mark.parametrize("name", _mirror_files())
def test_scripts_match(name):
    _assert_same(os.path.join(REPO, name), os.path.join(MIRROR, name), name)


def _assert_same(src, dst, name, label="镜像"):
    assert os.path.exists(src), f"根目录缺少 {name}"
    assert os.path.exists(dst), f"{label}缺少 {name}（{dst}）"
    assert _norm(open(src, "rb").read()) == _norm(open(dst, "rb").read()), (
        f"{name} 两处不一致！请同步 {label} 或根目录（源）"
    )


def test_mirror_has_no_forbidden_files():
    """镜像不应包含 config.json（真实凭证）等意外文件，且根目录无残留旧脚本"""
    forbidden = {"config.json", "__pycache__", "install.sh"}
    for f in os.listdir(MIRROR):
        assert f not in forbidden, f"镜像目录包含禁止文件: {f}"
    root = os.listdir(REPO)
    stale = [f for f in root if f.endswith(".py") and not f.startswith("scripts")]
    assert not stale, f"根目录残留旧版脚本（应在 scripts/ 下）: {stale}"


# ── DSH 预设技能副本一致性（2026-08-14）──────────────────────────────
# dsh/insar-genie/skills/insar-genie/ 随 DSH 插件安装分发，同样必须与根一致。
# 覆盖：SKILL.md / config.example.json / scripts/*；experiment/ 为运行资产，
# 其一致性由 verify_clone.py 覆盖，此处只守护分发关键文件与禁止项。


def _preset_pairs():
    for f in MIRROR_FILES:
        yield f
    for f in _mirror_files():
        yield f


@pytest.mark.parametrize("name", list(_preset_pairs()))
def test_dsh_preset_skill_matches_root(name):
    _assert_same(
        os.path.join(REPO, name),
        os.path.join(DSH_PRESET, name),
        name,
        label="DSH 预设技能副本（dsh/insar-genie/skills/insar-genie/）",
    )


def test_dsh_preset_has_no_forbidden_files():
    """DSH 预设技能副本不应包含真实凭证/本机配置"""
    forbidden = {
        "config.json",
        "__pycache__",
        "install.sh",
        "config.env",
        "notify_config.json",
        "mail_config.json",
    }
    for f in os.listdir(DSH_PRESET):
        assert f not in forbidden, f"DSH 预设技能目录包含禁止文件: {f}"
    for sub in ("scripts", "experiment"):
        subdir = os.path.join(DSH_PRESET, sub)
        if os.path.isdir(subdir):
            for f in os.listdir(subdir):
                assert f not in forbidden, f"DSH 预设 {sub}/ 包含禁止文件: {f}"
    # experiment 下深层禁止项
    guard_dir = os.path.join(DSH_PRESET, "experiment", "asf_experiment")
    if os.path.isdir(guard_dir):
        for f in os.listdir(guard_dir):
            assert f not in {"notify_config.json", "mail_config.json"}, (
                f"DSH 预设 asf_experiment/ 包含禁止文件: {f}"
            )
