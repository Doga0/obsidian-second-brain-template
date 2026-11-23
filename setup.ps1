<#
.SYNOPSIS
  Second Brain vault setup (Windows). Safe to run more than once.

.DESCRIPTION
  1. Installs Obsidian and Python 3 with winget if they're missing
  2. Creates folders that empty-folder-unaware tools (zip, git) don't keep
  3. If this is a Git repo: disables line-ending conversion so notes stay byte-identical
  4. Records a hash baseline for protected folders (99 System/config.json), if any
  5. Registers the folder as an Obsidian vault and opens it
  6. Runs a health check

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File setup.ps1
  powershell -ExecutionPolicy Bypass -File setup.ps1 -RemoveExamples
  powershell -ExecutionPolicy Bypass -File setup.ps1 -SkipInstall -NoObsidian
#>
param(
  [switch]$SkipInstall,
  [switch]$NoObsidian,
  [switch]$RemoveExamples
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}
$Vault = $PSScriptRoot
Set-Location -LiteralPath $Vault
$Tool = Join-Path $Vault '99 System\scripts\vault_tool.py'

function Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "    OK  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "    !!  $m" -ForegroundColor Yellow }
function Refresh-Path { $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') }
function Has($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Get-Python {
  # The Microsoft Store alias "python.exe" exists but doesn't run; look for a real interpreter.
  foreach ($c in @('python', 'py')) {
    try { $v = & $c -c "import sys; print(sys.version_info[0])" 2>$null; if ($LASTEXITCODE -eq 0 -and "$v".Trim() -eq '3') { return $c } } catch {}
  }
  return $null
}
function Get-ObsidianExe {
  foreach ($p in @("$env:LOCALAPPDATA\Programs\Obsidian\Obsidian.exe", "$env:ProgramFiles\Obsidian\Obsidian.exe")) {
    if (Test-Path -LiteralPath $p) { return $p }
  }
  return $null
}
function Install-Pkg($id, $label) {
  if ($SkipInstall) { Warn "$label not found (-SkipInstall given)"; return }
  if (-not (Has 'winget')) { Warn "winget not available; install $label manually"; return }
  Write-Host "    ..  installing $label (winget: $id)"
  & winget install -e --id $id --accept-package-agreements --accept-source-agreements --silent | Out-Host
  Refresh-Path
}

# ------------------------------------------------------------------ 1. tools
Step 'Tools'
$py = Get-Python
if ($py) { Ok "Python 3 ($py)" } else {
  Install-Pkg 'Python.Python.3.12' 'Python 3'
  $py = Get-Python
  if ($py) { Ok 'Python installed' } else { Warn 'Python not found: the AI helper script (vault_tool.py) needs it. Get it from https://www.python.org/downloads/' }
}
if (-not $NoObsidian) {
  if (Get-ObsidianExe) { Ok 'Obsidian' } else {
    Install-Pkg 'Obsidian.Obsidian' 'Obsidian'
    if (Get-ObsidianExe) { Ok 'Obsidian installed' } else { Warn 'Obsidian not found: get it from https://obsidian.md' }
  }
}

# ------------------------------------------------------------------ 2. folders
Step 'Folders'
foreach ($d in @('00 Inbox', '15 Tasks', '60 Resources\Attachments', '70 Analyses', '90 Archive')) {
  $p = Join-Path $Vault $d
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p | Out-Null; Ok "created: $d" }
}
Ok 'Folder structure complete'

# ------------------------------------------------------------------ 3. git (optional)
if ((Test-Path -LiteralPath (Join-Path $Vault '.git')) -and (Has 'git')) {
  Step 'Git'
  & git config core.autocrlf false
  & git config core.quotepath false
  Ok 'Line-ending conversion off for this repo (notes stay byte-identical)'
}

# ------------------------------------------------------------------ 4. examples / protected folders
if ($py) {
  if ($RemoveExamples) {
    Step 'Example notes'
    & $py -X utf8 $Tool clean-examples --yes | Out-Host
  }
  $cfgFile = Join-Path $Vault '99 System\config.json'
  if (Test-Path -LiteralPath $cfgFile) {
    $cfg = Get-Content -LiteralPath $cfgFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($cfg.protected -and @($cfg.protected).Count -gt 0) {
      Step 'Protected folders'
      & $py -X utf8 $Tool protected-baseline | Out-Host
    }
  }
}

# ------------------------------------------------------------------ 5. Obsidian vault registration
if (-not $NoObsidian) {
  Step 'Obsidian'
  $cfgDir = Join-Path $env:APPDATA 'obsidian'
  $cfgPath = Join-Path $cfgDir 'obsidian.json'
  $running = [bool](Get-Process -Name 'Obsidian' -ErrorAction SilentlyContinue)
  $registered = $false
  $reg = $null
  if (Test-Path -LiteralPath $cfgPath) {
    $reg = Get-Content -LiteralPath $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($reg.vaults) {
      foreach ($prop in $reg.vaults.PSObject.Properties) {
        if ($prop.Value.path -and ($prop.Value.path.TrimEnd('\') -ieq $Vault.TrimEnd('\'))) { $registered = $true }
      }
    }
  }
  if ($registered) { Ok 'Vault already registered in Obsidian' }
  elseif ($running) { Warn 'Obsidian is running, so registration was skipped. In Obsidian choose "Open folder as vault" and pick this folder.' }
  else {
    if (-not (Test-Path -LiteralPath $cfgDir)) { New-Item -ItemType Directory -Path $cfgDir | Out-Null }
    if ($reg) { Copy-Item -LiteralPath $cfgPath -Destination "$cfgPath.bak" -Force } else { $reg = [pscustomobject]@{} }
    if (-not $reg.PSObject.Properties['vaults']) { $reg | Add-Member -NotePropertyName vaults -NotePropertyValue ([pscustomobject]@{}) }
    $id = -join ((1..16) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
    $ts = [int64]([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
    $reg.vaults | Add-Member -NotePropertyName $id -NotePropertyValue ([pscustomobject]@{ path = $Vault; ts = $ts; open = $true })
    [IO.File]::WriteAllText($cfgPath, ($reg | ConvertTo-Json -Depth 10), (New-Object Text.UTF8Encoding $false))
    Ok 'Vault registered in Obsidian (previous settings saved as obsidian.json.bak)'
  }
  if (Get-ObsidianExe) {
    Start-Process ('obsidian://open?path=' + [uri]::EscapeDataString($Vault))
    Ok 'Opening Obsidian. If it asks whether to trust this vault''s plugins, choose trust (needed for the board).'
  }
}

# ------------------------------------------------------------------ 6. health
Step 'Health check'
if ($py) { & $py -X utf8 $Tool lint | Select-Object -First 9 | Out-Host } else { Warn 'Python missing; health check skipped' }

Step 'Done'
Write-Host @"
    Vault: $Vault
    - Start at Home.md, then read 99 System/Second Brain Guide.md
    - AI commands (/sb-*): open this folder in Claude Code (https://claude.com/claude-code) and type /sb-
    - Remove the example notes: powershell -ExecutionPolicy Bypass -File setup.ps1 -RemoveExamples
"@
