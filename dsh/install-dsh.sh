#!/usr/bin/env bash
# ============================================================================
# insar-genie-dsh — DSH (DeepSeek Harness) SBAS 插件一键安装脚本 (macOS / Linux)
#
# 安装内容：
#   cordis 插件 @dsh-custom/insar-genie-dsh（SBAS 全链路自包含插件：
#   host 工具 + client UI + 内嵌 insar-genie 技能与全套脚本，无需 agent preset）
#   安装到 DSH web profile（file: 依赖写入 ${DSH_HOME:-$HOME/.dsh}/profiles/web/package.json，
#   随后 pnpm install 完成真实安装）。
#
# 注意：本插件已自包含（skill + scripts + experiment 打包在 assets），
#   不需要 agent preset，也不再安装 .agent-presets/insar-genie。
#
# 用法：
#   本地源码：   bash install-dsh.sh
#   预览模式：   bash install-dsh.sh --dry-run
#
# 卸载：
#   dsh plugin --profile web remove @dsh-custom/insar-genie-dsh
# ============================================================================
set -euo pipefail

REPO="jinhucoco/insar-genie"
PLUGIN_NAME="@dsh-custom/insar-genie-dsh"
DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
PROFILE_DIR="$DSH_HOME/profiles/web"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_SOURCE="$SCRIPT_DIR/../dsh-plugin"
PACKAGE_JSON="$PROFILE_DIR/package.json"

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
  info "Dry-run: 将把插件以 file: 依赖写入 $PACKAGE_JSON"
  info "Dry-run: 插件源码目录: $PLUGIN_SOURCE"
  info "Dry-run: 随后在 $PROFILE_DIR 执行 pnpm install"
  echo ""
  echo "====================================================="
  echo "  --dry-run 完成（未做任何安装）"
  echo "====================================================="
  exit 0
fi

# ---------- 定位插件源码 ----------
[ -f "$PLUGIN_SOURCE/package.json" ] || die "未找到插件源码: $PLUGIN_SOURCE（需先克隆仓库）"

# ---------- 写入 file: 依赖 ----------
[ -f "$PACKAGE_JSON" ] || die "未找到 web profile package.json: $PACKAGE_JSON（请先 dsh web 初始化 profile）"

info "写入依赖 $PLUGIN_NAME → file:$PLUGIN_SOURCE"
npm pkg set "dependencies.$PLUGIN_NAME=file:$PLUGIN_SOURCE" --prefix "$PROFILE_DIR" >/dev/null 2>&1 || die "写入依赖失败"

# ---------- 安装 ----------
info "执行 pnpm install（$PROFILE_DIR）..."
( cd "$PROFILE_DIR" && pnpm install 2>&1 | tail -8 ) || die "pnpm install 失败"
ok "DSH 插件已安装 → $PROFILE_DIR"

# ---------- 完成 ----------
echo ""
echo "====================================================="
echo "  ✅ insar-genie-dsh (DSH SBAS 全链路插件) 安装完成"
echo "====================================================="
echo ""
echo "  🚀 使用：重启 dsh web 后在任意会话说："
echo "     \"跑 SBAS，区域 研究区.shp，20240101-20240630，VV+VH\""
echo "     （插件内嵌 insar-genie 技能，AI 自动驱动全链路）"
echo ""
echo "  🔑 需要自行准备的账户/软件（按需）："
echo "     [必需] NASA Earthdata 账号（免费: https://urs.earthdata.nasa.gov/）"
echo "     [可选] 邮箱 IMAP 授权码（GACOS 大气延迟收件用）"
echo "     [处理阶段] ENVI + SARscape（商业软件，需自己的 license）"
echo ""
echo "  🗑️ 卸载: dsh plugin --profile web remove $PLUGIN_NAME"
echo "  📖 完整文档: https://github.com/$REPO"
echo "====================================================="
