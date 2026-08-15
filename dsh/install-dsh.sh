#!/usr/bin/env bash
# ============================================================================
# insar-genie — DSH (DeepSeek Harness) 插件一键安装脚本 (macOS / Linux)
#
# 安装内容：
#   SBAS-InSAR 全链路 agent preset（含 insar-genie 技能 + scripts + experiment）
#   安装到 ${DSH_HOME:-$HOME/.dsh}/.agent-presets/insar-genie/
#
# 用法：
#   本地源码：   bash install-dsh.sh
#   一键远程：   curl -fsSL https://raw.githubusercontent.com/jinhucoco/insar-genie/main/dsh/install-dsh.sh | bash
#   预览模式：   bash install-dsh.sh --dry-run
#
# 卸载：
#   rm -rf "${DSH_HOME:-$HOME/.dsh}/.agent-presets/insar-genie"
# ============================================================================
set -euo pipefail

REPO="jinhucoco/insar-genie"
PRESET_ID="insar-genie"
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
TARGET="$DSH_HOME/.agent-presets/$PRESET_ID"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SCRIPT_DIR/$PRESET_ID"
RAW_BASE="https://raw.githubusercontent.com/$REPO/main/dsh"

C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'; C_CYAN='\033[0;36m'; C_RED='\033[0;31m'; C_NC='\033[0m'
ok()   { echo -e "${C_GREEN}[OK]${C_NC} $*"; }
warn() { echo -e "${C_YELLOW}[!]${C_NC} $*"; }
info() { echo -e "${C_CYAN}[..]${C_NC} $*"; }
die()  { echo -e "${C_RED}[X]${C_NC} $*" >&2; exit 1; }

DRY_RUN=0
case "${1:-}" in
  --dry-run) DRY_RUN=1 ;;
  -h|--help)
    echo "用法: bash install-dsh.sh [--dry-run]"
    echo "  --dry-run  仅打印将执行的操作，不实际安装"
    exit 0 ;;
esac

if [ "$DRY_RUN" = 1 ]; then
  info "Dry-run: 将安装到 $TARGET"
  info "Dry-run: 从 $SOURCE 复制预设目录"
  info "Dry-run: 远程安装: curl -fsSL $RAW_BASE/install-dsh.sh | bash"
  echo ""
  echo "====================================================="
  echo "  --dry-run 完成（未做任何安装）"
  echo "  在【宿主终端】执行完整安装："
  echo "  curl -fsSL $RAW_BASE/install-dsh.sh | bash"
  echo "====================================================="
  exit 0
fi

# ---------- 定位源码 ----------
if [ ! -f "$SOURCE/agent.cordis.yml" ]; then
  warn "本地未找到预设源码，尝试远程下载..."
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  for f in preset.yml agent.cordis.yml; do
    curl -fsSL "$RAW_BASE/$PRESET_ID/$f" -o "$TMP/$f" || die "下载 $f 失败"
  done
  # 技能目录：从 GitHub API 列目录逐个下载
  API="https://api.github.com/repos/$REPO/git/trees/main?recursive=1"
  PREFIX="dsh/$PRESET_ID/skills/"
  FILES="$(curl -fsSL "$API" | python3 -c "import sys,json; print('\n'.join(t['path'] for t in json.load(sys.stdin)['tree'] if t['type']=='blob' and t['path'].startswith('$PREFIX')))")"
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    rel="${p#"$PREFIX"}"
    mkdir -p "$TMP/$(dirname "$rel")"
    curl -fsSL "$RAW_BASE/$PRESET_ID/skills/$rel" -o "$TMP/$rel" || die "下载 skills/$rel 失败"
  done <<< "$FILES"
  SOURCE="$TMP"
fi

# ---------- 校验源码完整性 ----------
for f in agent.cordis.yml preset.yml skills/$PRESET_ID/SKILL.md skills/$PRESET_ID/scripts/download.py; do
  [ -f "$SOURCE/$f" ] || die "预设源码不完整，缺少: $f"
done

# ---------- 安装 ----------
mkdir -p "$TARGET"
if [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
  warn "目标目录已有内容，覆盖更新: $TARGET"
  rm -rf "$TARGET"
  mkdir -p "$TARGET"
fi
cp -r "$SOURCE/." "$TARGET/"
ok "DSH 插件已安装 → $TARGET"

# ---------- 完成 ----------
echo ""
echo "====================================================="
echo "  ✅ insar-genie (DSH SBAS 全链路插件) 安装完成"
echo "====================================================="
echo ""
echo "  📦 预设位置: $TARGET"
echo ""
echo "  🚀 使用方法（3 步）："
echo "    1. 打开 DSH Web 界面，点击「新建会话」"
echo "    2. 选择模式（preset）: SBAS 全链路"
echo "    3. 在对话中说："
echo "       \"配置 ASF 账号密码\" → 引导填写 Earthdata 凭证"
echo "       \"从 ASF 下载哨兵数据，区域 研究区.shp，时间 20240101 至 20240630，VV+VH\""
echo ""
echo "  🔑 需要自行准备的账户/软件（按需）："
echo "     [必需] NASA Earthdata 账号（免费: https://urs.earthdata.nasa.gov/）"
echo "     [可选] 邮箱 IMAP 授权码（GACOS 大气延迟收件用）"
echo "     [处理阶段] ENVI + SARscape（商业软件，需自己的 license）"
echo ""
echo "  🗑️ 卸载: rm -rf '$TARGET'"
echo "  📖 完整文档: https://github.com/$REPO"
echo "====================================================="
