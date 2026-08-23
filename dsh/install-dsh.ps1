# ============================================================================
# insar-genie-dsh — DSH (DeepSeek Harness) SBAS 插件一键安装脚本 (Windows)
#
# 安装内容：
#   cordis 插件 @dsh-custom/insar-genie-dsh（SBAS 全链路自包含插件：
#   host 工具 + client UI + 内嵌 insar-genie 技能与全套脚本，无需 agent preset）
#   安装到 DSH web profile（file: 依赖写入 ~/.dsh/profiles/web/package.json，
#   随后 pnpm install 完成真实安装）。
#   等效命令：dsh plugin --profile web add @dsh-custom/insar-genie-dsh -w
#
# 注意：本插件已自包含（skill + scripts + experiment 打包在 assets），
#   不需要 agent preset，也不再安装 .agent-presets/insar-genie。
#
# 用法：
#   本地源码：   powershell -ExecutionPolicy Bypass -File install-dsh.ps1
#   预览模式：   powershell -ExecutionPolicy Bypass -File install-dsh.ps1 -DryRun
#
# 卸载：
#   dsh plugin --profile web remove @dsh-custom/insar-genie-dsh
# ============================================================================
param(
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$Repo = 'jinhucoco/insar-genie'
$PluginName = '@dsh-custom/insar-genie-dsh'
$DshHome = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' }
$ProfileDir = Join-Path $DshHome 'profiles\web'
$PluginSource = Join-Path $PSScriptRoot '..\dsh-plugin'
$PackageJson = Join-Path $ProfileDir 'package.json'

function Write-Step($msg) { Write-Host "[..] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "[!] $msg" -ForegroundColor Yellow }

if ($DryRun) {
  Write-Step "Dry-run: 将把插件以 file: 依赖写入 $PackageJson"
  Write-Step "Dry-run: 插件源码目录: $PluginSource"
  Write-Step "Dry-run: 随后在 $ProfileDir 执行 pnpm install"
  Write-Host ""
  Write-Host "====================================================="
  Write-Host "  --dry-run 完成（未做任何安装）"
  Write-Host "====================================================="
  exit 0
}

# ---------- 定位插件源码 ----------
if (-not (Test-Path (Join-Path $PluginSource 'package.json'))) {
  Write-Host "[X] 未找到插件源码: $PluginSource（需先克隆仓库）" -ForegroundColor Red
  exit 1
}

# ---------- 写入 file: 依赖 ----------
if (-not (Test-Path $PackageJson)) {
  Write-Host "[X] 未找到 web profile package.json: $PackageJson" -ForegroundColor Red
  Write-Host "    请先用 dsh web 初始化 profile，或确认 DSH_HOME 正确" -ForegroundColor Red
  exit 1
}

# 用 npm pkg set 写入依赖（file: 绝对路径，同原装插件方式）
Write-Step "写入依赖 $PluginName → file:$PluginSource"
npm pkg set "dependencies.$PluginName=file:$($PluginSource -replace '\\','/')" --prefix $ProfileDir 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "[X] 写入依赖失败" -ForegroundColor Red; exit 1 }

# ---------- 安装 ----------
Write-Step "执行 pnpm install（$ProfileDir）..."
Push-Location $ProfileDir
try {
  pnpm install 2>&1 | Select-Object -Last 8
  if ($LASTEXITCODE -ne 0) { Write-Host "[X] pnpm install 失败" -ForegroundColor Red; exit 1 }
} finally {
  Pop-Location
}
Write-Ok "DSH 插件已安装 → $ProfileDir"

# ---------- 完成 ----------
Write-Host ""
Write-Host "====================================================="
Write-Host "  ✅ insar-genie-dsh (DSH SBAS 全链路插件) 安装完成"
Write-Host "====================================================="
Write-Host ""
Write-Host "  🚀 使用：重启 dsh web 后在任意会话说："
Write-Host "     \"跑 SBAS，区域 研究区.shp，20240101-20240630，VV+VH\""
Write-Host "     （插件内嵌 insar-genie 技能，AI 自动驱动全链路）"
Write-Host ""
Write-Host "  🔑 需要自行准备的账户/软件（按需）："
Write-Host "     [必需] NASA Earthdata 账号（免费: https://urs.earthdata.nasa.gov/）"
Write-Host "     [可选] 邮箱 IMAP 授权码（GACOS 大气延迟收件用）"
Write-Host "     [处理阶段] ENVI + SARscape（商业软件，需自己的 license）"
Write-Host ""
Write-Host "  🗑️ 卸载: dsh plugin --profile web remove $PluginName"
Write-Host "  📖 完整文档: https://github.com/$Repo"
Write-Host "====================================================="
