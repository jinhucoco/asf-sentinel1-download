#!/usr/bin/env bash
# ============================================================================
# pi-asf-sentinel1-slc — 一键安装脚本
#
# 支持所有 AI 工具（OpenAI Codex / Claude Code / Cursor / pi 等）：
#   1. 自动检测工具并复制技能到正确的 skills 目录
#   2. 安装 Python 依赖（asf_search/pyshp/shapely 等）
#   3. 初始化 Earthdata 凭证配置（config.json）
#
# 用法（一条命令）：
#   curl -fsSL https://raw.githubusercontent.com/jinhucoco/asf-sentinel1-download/main/install.sh | bash
#
# 或本地运行：
#   bash install.sh
# ============================================================================
set -euo pipefail

# ---------- 配置 ----------
SKILL_NAME="asf-sentinel1-download"
REPO_URL="https://github.com/jinhucoco/asf-sentinel1-download"
RAW_URL="https://raw.githubusercontent.com/jinhucoco/asf-sentinel1-download/main"
PYDEPS=(asf_search pyshp shapely defusedxml matplotlib)

# ---------- 颜色 ----------
C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'; C_CYAN='\033[0;36m'; C_RED='\033[0;31m'; C_NC='\033[0m'
ok()   { echo -e "${C_GREEN}[OK]${C_NC} $*"; }
warn() { echo -e "${C_YELLOW}[!]${C_NC} $*"; }
info() { echo -e "${C_CYAN}[..]${C_NC} $*"; }
die()  { echo -e "${C_RED}[X]${C_NC} $*" >&2; exit 1; }

# ---------- 定位技能源码 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 优先使用自包含的技能目录（含 SKILL.md + 脚本），否则回退仓库根目录
if [ -d "$SCRIPT_DIR/skills/$SKILL_NAME" ] && [ -f "$SCRIPT_DIR/skills/$SKILL_NAME/download.py" ]; then
  SRC="$SCRIPT_DIR/skills/$SKILL_NAME"
  info "使用自包含技能目录: $SRC"
elif [ -f "$SCRIPT_DIR/download.py" ] && [ -f "$SCRIPT_DIR/SKILL.md" ]; then
  SRC="$SCRIPT_DIR"
  info "使用仓库根目录技能: $SRC"
elif [ -d "$SCRIPT_DIR/skills/$SKILL_NAME" ]; then
  # 旧包结构：skills 子目录只有 SKILL.md，需从根目录补全
  warn "检测到旧包结构（skills 子目录不完整），使用仓库根目录"
  SRC="$SCRIPT_DIR"
else
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  info "下载技能包: $REPO_URL"
  git clone --depth 1 "$REPO_URL" "$TMP/repo" >/dev/null 2>&1 || die "无法克隆仓库，请检查网络"
  # 优先自包含技能目录，否则仓库根目录
  if [ -d "$TMP/repo/skills/$SKILL_NAME" ] && [ -f "$TMP/repo/skills/$SKILL_NAME/download.py" ]; then
    SRC="$TMP/repo/skills/$SKILL_NAME"
  else
    SRC="$TMP/repo"
  fi
fi
[ -f "$SRC/SKILL.md" ] || die "未找到 SKILL.md，技能源码无效: $SRC"

# ---------- 1. 检测目标工具并复制技能 ----------
detect_target() {
  if [ -d "$HOME/.codex" ]; then echo "codex"; return; fi
  if [ -d "$HOME/.claude" ]; then echo "claude"; return; fi
  if [ -d "$HOME/.pi" ]; then echo "pi"; return; fi
  echo "generic"
}

detect_all_targets() {
  local targets=""
  [ -d "$HOME/.codex" ] && targets="$targets codex"
  [ -d "$HOME/.claude" ] && targets="$targets claude"
  [ -d "$HOME/.pi" ] && targets="$targets pi"
  echo "$targets"
}

install_to() {
  local target="$1" dest=""
  case "$target" in
    codex)  dest="$HOME/.codex/skills/$SKILL_NAME" ;;
    claude) dest="$HOME/.claude/skills/$SKILL_NAME" ;;
    pi)     dest="$HOME/.pi/agent/skills/$SKILL_NAME" ;;
    *)      dest="$HOME/.agents/skills/$SKILL_NAME" ;;
  esac
  mkdir -p "$(dirname "$dest")"
  if [ -e "$dest" ]; then
    warn "$target: 技能已存在，覆盖更新: $dest"
    rm -rf "$dest"
  fi
  cp -r "$SRC" "$dest"
  ok "$target: 技能已安装 → $dest"
}

TARGETS="$(detect_all_targets)"
if [ -z "$TARGETS" ]; then
  info "未检测到 Codex/Claude/pi，将安装到通用位置 ~/.agents/skills/"
  install_to generic
else
  for t in $TARGETS; do
    install_to "$t"
  done
fi

# ---------- 2. 安装 Python 依赖 ----------
info "安装 Python 依赖: ${PYDEPS[*]}"
if command -v pip3 >/dev/null 2>&1; then
  PIP="pip3"
elif command -v pip >/dev/null 2>&1; then
  PIP="pip"
elif command -v python3 >/dev/null 2>&1; then
  PIP="python3 -m pip"
else
  warn "未找到 pip，请手动安装: pip install ${PYDEPS[*]}"
  PIP=""
fi
if [ -n "$PIP" ]; then
  # 优先使用技能自带的 requirements.txt
  if [ -f "$SRC/requirements.txt" ]; then
    # shellcheck disable=SC2086
    $PIP install -r "$SRC/requirements.txt" || warn "依赖安装失败，请手动执行: pip install -r requirements.txt"
  else
    # shellcheck disable=SC2086
    $PIP install ${PYDEPS[*]} || warn "依赖安装失败，请手动执行: pip install ${PYDEPS[*]}"
  fi
fi

# ---------- 3. 初始化凭证配置 ----------
CONFIG_TARGET="$HOME/.pi/agent/skills/$SKILL_NAME/config.json"
# 找到第一个安装位置的 config
for t in codex claude pi generic; do
  case "$t" in
    codex)  cand="$HOME/.codex/skills/$SKILL_NAME/config.json" ;;
    claude) cand="$HOME/.claude/skills/$SKILL_NAME/config.json" ;;
    pi)     cand="$HOME/.pi/agent/skills/$SKILL_NAME/config.json" ;;
    *)      cand="$HOME/.agents/skills/$SKILL_NAME/config.json" ;;
  esac
  if [ -f "$cand" ]; then CONFIG_TARGET="$cand"; break; fi
done

if [ ! -f "$CONFIG_TARGET" ]; then
  cp "$SRC/config.example.json" "$CONFIG_TARGET" 2>/dev/null || \
    printf '{\n  "username": "your_earthdata_username",\n  "password": "your_earthdata_password"\n}\n' > "$CONFIG_TARGET"
  warn "已生成凭证模板: $CONFIG_TARGET"
  warn "请编辑该文件，填入你的 NASA Earthdata 账号密码（免费注册: https://urs.earthdata.nasa.gov/）"
else
  ok "凭证配置已存在: $CONFIG_TARGET"
fi

# ---------- 4. 完成 ----------
echo ""
echo "====================================================="
echo "  ✅ pi-asf-sentinel1-slc 安装完成"
echo "====================================================="
echo ""
echo "  📦 技能位置:"
for t in codex claude pi generic; do
  case "$t" in
    codex)  d="$HOME/.codex/skills/$SKILL_NAME" ;;
    claude) d="$HOME/.claude/skills/$SKILL_NAME" ;;
    pi)     d="$HOME/.pi/agent/skills/$SKILL_NAME" ;;
    *)      d="$HOME/.agents/skills/$SKILL_NAME" ;;
  esac
  [ -d "$d" ] && echo "     - $d"
done
echo ""
echo "  🚀 使用方法（在 AI 工具对话中直接说）:"
echo "     \"从 ASF 下载哨兵数据，区域 研究区.shp，时间 20240101 至 20240630，VV+VH\""
echo ""
echo "  📖 完整文档: $REPO_URL"
echo "  💡 确保 config.json 已填入 Earthdata 账号密码"
echo ""
echo "====================================================="
