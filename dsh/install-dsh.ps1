# ============================================================================
# insar-genie — DSH (DeepSeek Harness) 插件一键安装脚本 (Windows)
#
# 安装内容：
#   SBAS-InSAR 全链路 agent preset（含 insar-genie 技能 + scripts + experiment）
#   安装到 $env:USERPROFILE\.dsh\.agent-presets\insar-genie\
#
# 用法：
#   本地源码：   powershell -ExecutionPolicy Bypass -File install-dsh.ps1
#   一键远程：   powershell -Command "irm https://raw.githubusercontent.com/jinhucoco/insar-genie/main/dsh/install-dsh.ps1 | iex"
#   预览模式：   powershell -ExecutionPolicy Bypass -File install-dsh.ps1 -DryRun
#
# 卸载：
#   Remove-Item "$env:USERPROFILE\.dsh\.agent-presets\insar-genie" -Recurse -Force
# ============================================================================
param(
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$Repo = 'jinhucoco/insar-genie'
$PresetId = 'insar-genie'
$DshHome = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' }
$Target = Join-Path $DshHome ".agent-presets\$PresetId"
$Source = Join-Path $PSScriptRoot $PresetId
$RawBase = "https://raw.githubusercontent.com/$Repo/main/dsh"

function Write-Step($msg) { Write-Host "[..] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "[!] $msg" -ForegroundColor Yellow }

if ($DryRun) {
  Write-Step "Dry-run: 将安装到 $Target"
  Write-Step "Dry-run: 从 $Source 复制预设目录"
  Write-Step "Dry-run: 如需远程安装: irm $RawBase/install-dsh.ps1 | iex"
  Write-Host ""
  Write-Host "====================================================="
  Write-Host "  --dry-run 完成（未做任何安装）"
  Write-Host "  在【宿主终端】执行完整安装："
  Write-Host "  powershell -Command `"irm $RawBase/install-dsh.ps1 | iex`""
  Write-Host "====================================================="
  exit 0
}

# ---------- 定位源码 ----------
if (-not (Test-Path (Join-Path $Source 'agent.cordis.yml'))) {
  Write-Warn2 "本地未找到预设源码，尝试远程下载..."
  $tmp = Join-Path $env:TEMP "insar-genie-dsh"
  Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Path $tmp -Force | Out-Null
  try {
    foreach ($f in @('preset.yml', 'agent.cordis.yml')) {
      Invoke-WebRequest -UseBasicParsing "$RawBase/$PresetId/$f" -OutFile (Join-Path $tmp $f)
    }
    # 技能目录（预设内 skills/insar-genie/）从 GitHub API 列目录逐个下载
    $api = "https://api.github.com/repos/$Repo/git/trees/main?recursive=1"
    $tree = (Invoke-RestMethod $api).tree
    $prefix = "dsh/$PresetId/skills/"
    $files = $tree | Where-Object { $_.type -eq 'blob' -and $_.path.StartsWith($prefix) } | Select-Object -ExpandProperty path
    foreach ($p in $files) {
      $rel = $p.Substring($prefix.Length)
      $out = Join-Path $tmp $rel
      New-Item -ItemType Directory -Path (Split-Path $out) -Force | Out-Null
      Invoke-WebRequest -UseBasicParsing "$RawBase/$PresetId/skills/$rel" -OutFile $out
    }
    $Source = $tmp
  } catch {
    Write-Host "[X] 远程下载失败: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "    请先克隆仓库再运行，或浏览器下载 zip 解压后本地执行" -ForegroundColor Red
    exit 1
  }
}

# ---------- 校验源码完整性 ----------
$mustHave = @("$Source\agent.cordis.yml", "$Source\preset.yml", "$Source\skills\insar-genie\SKILL.md", "$Source\skills\insar-genie\scripts\download.py")
foreach ($f in $mustHave) {
  if (-not (Test-Path $f)) { Write-Host "[X] 预设源码不完整，缺少: $f" -ForegroundColor Red; exit 1 }
}

# ---------- 安装 ----------
New-Item -ItemType Directory -Path $Target -Force | Out-Null
if (Get-ChildItem $Target -Force -ErrorAction SilentlyContinue) {
  Write-Warn2 "目标目录已有内容，覆盖更新: $Target"
  Remove-Item $Target -Recurse -Force
  New-Item -ItemType Directory -Path $Target -Force | Out-Null
}
Copy-Item "$Source\*" $Target -Recurse -Force
Write-Ok "DSH 插件已安装 → $Target"

# ---------- 完成 ----------
Write-Host ""
Write-Host "====================================================="
Write-Host "  ✅ insar-genie (DSH SBAS 全链路插件) 安装完成"
Write-Host "====================================================="
Write-Host ""
Write-Host "  📦 预设位置: $Target"
Write-Host ""
Write-Host "  🚀 使用方法（3 步）："
Write-Host "    1. 打开 DSH Web 界面，点击「新建会话」"
Write-Host "    2. 选择模式（preset）: SBAS 全链路"
Write-Host "    3. 在对话中说："
Write-Host "       ""配置 ASF 账号密码"" → 引导填写 Earthdata 凭证"
Write-Host "       ""从 ASF 下载哨兵数据，区域 研究区.shp，时间 20240101 至 20240630，VV+VH"""
Write-Host ""
Write-Host "  🔑 需要自行准备的账户/软件（按需）："
Write-Host "     [必需] NASA Earthdata 账号（免费: https://urs.earthdata.nasa.gov/）"
Write-Host "     [可选] 邮箱 IMAP 授权码（GACOS 大气延迟收件用）"
Write-Host "     [处理阶段] ENVI + SARscape（商业软件，需自己的 license）"
Write-Host ""
Write-Host "  🗑️ 卸载: Remove-Item '$Target' -Recurse -Force"
Write-Host "  📖 完整文档: https://github.com/$Repo"
Write-Host "====================================================="
