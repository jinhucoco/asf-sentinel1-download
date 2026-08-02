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
#   bash install.sh --dry-run   # 只打印将执行的操作与宿主终端手动命令，不实际安装
#
# 沙箱环境（如 Codex）说明：
#   Codex 沙箱默认关闭网络、HOME 目录只读，curl|bash 通常失败。
#   本脚本会探测目标目录可写性；不可写时输出降级指引
#   （宿主终端执行 / 浏览器下载 zip 解压），而不是静默失败。
# ============================================================================
set -euo pipefail

# ---------- 配置 ----------
SKILL_NAME="asf-sentinel1-download"
REPO_URL="https://github.com/jinhucoco/asf-sentinel1-download"
RAW_URL="https://raw.githubusercontent.com/jinhucoco/asf-sentinel1-download/main"
ZIP_URL="https://github.com/jinhucoco/asf-sentinel1-download/releases/latest/download/asf-sentinel1-download-skill.zip"
ZIP_FETCH_URL="https://codeload.github.com/jinhucoco/asf-sentinel1-download/zip/refs/heads/main"
PYDEPS=(asf_search pyshp shapely defusedxml matplotlib)

# ---------- 颜色 ----------
C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'; C_CYAN='\033[0;36m'; C_RED='\033[0;31m'; C_NC='\033[0m'
ok()   { echo -e "${C_GREEN}[OK]${C_NC} $*"; }
warn() { echo -e "${C_YELLOW}[!]${C_NC} $*"; }
info() { echo -e "${C_CYAN}[..]${C_NC} $*"; }
die()  { echo -e "${C_RED}[X]${C_NC} $*" >&2; exit 1; }

# ---------- 参数 ----------
DRY_RUN=0
SANDBOX_BLOCKED=0
case "${1:-}" in
  --dry-run) DRY_RUN=1 ;;
  -h|--help)
    echo "用法: bash install.sh [--dry-run]"
    echo "  --dry-run  仅打印将执行的操作与宿主终端手动命令，不实际安装"
    exit 0 ;;
esac

# ---------- 写权限探测（识别沙箱/只读环境） ----------
probe_write() {
  local dir="$1"
  if ! mkdir -p "$dir" 2>/dev/null; then return 1; fi
  if ! touch "$dir/.probe_$$" 2>/dev/null; then return 1; fi
  rm -f "$dir/.probe_$$"
  return 0
}

# ---------- zip 回退下载（git clone 不可用时） ----------
# 输出解压后的目录路径（仓库根目录）；失败返回非 0
download_repo_zip() {
  local dest_dir="$1" zip_path="$dest_dir/repo.zip" out_dir
  command -v unzip >/dev/null 2>&1 || return 1
  info "git clone 不可用，改用 zip 下载"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$ZIP_FETCH_URL" -o "$zip_path" || return 1
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$zip_path" "$ZIP_FETCH_URL" || return 1
  else
    return 1
  fi
  unzip -q "$zip_path" -d "$dest_dir" || return 1
  out_dir="$dest_dir/asf-sentinel1-download-main"
  [ -f "$out_dir/SKILL.md" ] || return 1
  echo "$out_dir"
}

# ---------- 定位技能源码 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC=""
if [ -d "$SCRIPT_DIR/skills/$SKILL_NAME" ] && [ -f "$SCRIPT_DIR/skills/$SKILL_NAME/download.py" ]; then
  SRC="$SCRIPT_DIR/skills/$SKILL_NAME"
  info "使用自包含技能目录: $SRC"
elif [ -f "$SCRIPT_DIR/download.py" ] && [ -f "$SCRIPT_DIR/SKILL.md" ]; then
  SRC="$SCRIPT_DIR"
  info "使用仓库根目录技能: $SRC"
elif [ -d "$SCRIPT_DIR/skills/$SKILL_NAME" ]; then
  warn "检测到旧包结构（skills 子目录不完整），使用仓库根目录"
  SRC="$SCRIPT_DIR"
else
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  if [ "$DRY_RUN" = 1 ]; then
    die "--dry-run 需本地源码；请先克隆仓库再运行，或浏览器下载: $ZIP_URL"
  fi
  info "下载技能包: $REPO_URL"
  REPO_DIR=""
  if git clone --depth 1 "$REPO_URL" "$TMP/repo" >/dev/null 2>&1; then
    REPO_DIR="$TMP/repo"
  elif REPO_DIR="$(download_repo_zip "$TMP")" && [ -n "$REPO_DIR" ]; then
    info "zip 方式下载成功"
  else
    die "无法下载仓库（git clone 与 zip 均失败）。请检查网络，或浏览器下载: $ZIP_URL"
  fi
  if [ -d "$REPO_DIR/skills/$SKILL_NAME" ] && [ -f "$REPO_DIR/skills/$SKILL_NAME/download.py" ]; then
    SRC="$REPO_DIR/skills/$SKILL_NAME"
  else
    SRC="$REPO_DIR"
  fi
fi
[ -f "$SRC/SKILL.md" ] || die "未找到 SKILL.md，技能源码无效: $SRC"

# ---------- 1. 检测目标工具并复制技能 ----------
detect_all_targets() {
  local targets=""
  [ -d "$HOME/.codex" ] && targets="$targets codex"
  [ -d "$HOME/.claude" ] && targets="$targets claude"
  [ -d "$HOME/.pi" ] && targets="$targets pi"
  echo "$targets"
}

target_dest() {
  case "$1" in
    codex)  echo "$HOME/.codex/skills/$SKILL_NAME" ;;
    claude) echo "$HOME/.claude/skills/$SKILL_NAME" ;;
    pi)     echo "$HOME/.pi/agent/skills/$SKILL_NAME" ;;
    *)      echo "$HOME/.agents/skills/$SKILL_NAME" ;;
  esac
}

install_to() {
  local target="$1" dest parent
  dest="$(target_dest "$target")"
  parent="$(dirname "$dest")"
  if [ "$DRY_RUN" = 1 ]; then
    echo "  [dry-run] mkdir -p $parent"
    echo "  [dry-run] [ -e $dest ] && rm -rf $dest"
    echo "  [dry-run] cp -r $SRC $dest"
    return 0
  fi
  if ! probe_write "$parent"; then
    SANDBOX_BLOCKED=1
    warn "$target: 目录不可写（疑似沙箱/只读环境）: $parent"
    return 1
  fi
  mkdir -p "$parent"
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
  install_to generic || true
else
  for t in $TARGETS; do
    install_to "$t" || true
  done
fi

# ---------- dry-run 汇总 ----------
if [ "$DRY_RUN" = 1 ]; then
  echo ""
  echo "====================================================="
  echo "  --dry-run 完成（未做任何安装）"
  echo "  在【宿主终端】执行等价的完整命令："
  echo "====================================================="
  echo "  curl -fsSL $RAW_URL/install.sh | bash"
  echo ""
  echo "  或浏览器下载 zip，解压后把 asf-sentinel1-download 文件夹"
  echo "  放入对应 skills 目录（~/.codex/skills/ 等）："
  echo "  $ZIP_URL"
  echo "====================================================="
  exit 0
fi

# ---------- 沙箱降级指引 ----------
if [ "$SANDBOX_BLOCKED" = 1 ]; then
  echo ""
  echo "====================================================="
  echo "  ⚠️ 检测到沙箱/只读环境，技能未能安装到目标目录"
  echo "  （常见于 Codex：默认关闭网络 + HOME 目录只读）"
  echo ""
  echo "  解决办法（任选其一）："
  echo "  1) 在【宿主终端】（非 AI 沙箱）执行:"
  echo "     curl -fsSL $RAW_URL/install.sh | bash"
  echo "  2) 浏览器下载 zip，解压后把 asf-sentinel1-download 文件夹"
  echo "     放入 ~/.codex/skills/（或 ~/.claude/skills/、~/.pi/agent/skills/）:"
  echo "     $ZIP_URL"
  echo "  3) 若确需在沙箱内安装，请为 Codex 配置:"
  echo "     network_access=true，并将 ~/.codex 加入可写目录"
  echo "====================================================="
  exit 1
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
for t in codex claude pi generic; do
  cand="$(target_dest "$t")/config.json"
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
  d="$(target_dest "$t")"
  [ -d "$d" ] && echo "     - $d"
done
echo ""
echo "  🚀 使用方法（在 AI 工具对话中直接说）:"
echo "     \"从 ASF 下载哨兵数据，区域 研究区.shp，时间 20240101 至 20240630，VV+VH\""
echo ""
echo "  📖 完整文档: $REPO_URL"
echo "  📦 手动安装 zip: $ZIP_URL"
echo "  💡 确保 config.json 已填入 Earthdata 账号密码"
echo ""
echo "====================================================="
