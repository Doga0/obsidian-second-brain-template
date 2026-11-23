<#
.SYNOPSIS
  Second Brain vault setup (Windows). Safe to run more than once.

.DESCRIPTION
  1. Installs Obsidian, Python 3 and Git with winget if they're missing
  2. Creates folders that zip/git don't keep when empty
  3. Git: initializes the repository, first commit, line endings off; pushes and enables
     automatic sync in the Obsidian Git plugin when a remote exists (-Remote <url>)
  4. Records a hash baseline for protected folders (99 System/config.json), if any
  5. Registers the folder as an Obsidian vault and opens it
  6. Runs a health check

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File setup.ps1
  powershell -ExecutionPolicy Bypass -File setup.ps1 -RemoveExamples
  powershell -ExecutionPolicy Bypass -File setup.ps1 -Remote https://github.com/<you>/<private-repo>.git
  powershell -ExecutionPolicy Bypass -File setup.ps1 -SkipInstall -NoObsidian -NoGit
#>
param(
  [switch]$SkipInstall,
  [switch]$NoObsidian,
  [switch]$RemoveExamples,
  [switch]$NoGit,
  [string]$Remote = '',
  [string]$GitName = '',
  [string]$GitEmail = ''
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
foreach ($d in @('Personal\00 Inbox', 'Personal\15 Tasks', 'Personal\60 Resources\Attachments', 'Personal\70 Analyses', 'Personal\90 Archive',
                 'Work\00 Inbox', 'Work\10 Projects', 'Work\20 Meetings', 'Work\30 Organizations & People', 'Work\40 Systems & APIs',
                 'Work\50 Tasks', 'Work\60 Attachments', 'Work\70 Analyses', 'Work\90 Archive')) {
  $p = Join-Path $Vault $d
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Path $p | Out-Null; Ok "created: $d" }
}
Ok 'Folder structure complete'
# MCP server definition for Claude Code: point it at the Python found on this machine
$mcpFile = Join-Path $Vault '.mcp.json'
if ($py -and $py -ne 'python' -and (Test-Path -LiteralPath $mcpFile)) {
  $mcpText = [IO.File]::ReadAllText($mcpFile)
  $mcpNew = $mcpText.Replace('"command": "python"', '"command": "' + $py + '"')
  if ($mcpNew -ne $mcpText) { [IO.File]::WriteAllText($mcpFile, $mcpNew, (New-Object Text.UTF8Encoding $false)); Ok "MCP server set to use '$py'" }
}
if ($RemoveExamples -and $py) {
  Step 'Example notes'
  & $py -X utf8 $Tool clean-examples --yes | Out-Host
}

# ------------------------------------------------------------------ 3. git: version history for the Obsidian Git plugin
if (-not $NoGit) {
  Step 'Git (version history)'
  if (-not (Has 'git')) { Install-Pkg 'Git.Git' 'Git' }
  if (-not (Has 'git')) {
    Warn 'Git not found: version history is off. Install Git (https://git-scm.com) and run setup again, or disable the Git plugin in Obsidian.'
  } else {
    # git writes progress to stderr; in Windows PowerShell 5.1 that would trip 'Stop', so rely on exit codes here.
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $placeholder = $false
    if (-not (Test-Path -LiteralPath (Join-Path $Vault '.git'))) {
      & git init -b main -q
      if ($LASTEXITCODE -ne 0) { $ErrorActionPreference = $prevEAP; throw 'git init failed' }
      Ok 'Initialized a Git repository'
    } else { Ok 'Git repository found' }
    & git config core.autocrlf false
    & git config core.quotepath false
    if ($GitName) { & git config user.name $GitName }
    if ($GitEmail) { & git config user.email $GitEmail }
    if (-not (& git config user.name)) { & git config user.name 'Second Brain'; $placeholder = $true }
    if (-not (& git config user.email)) { & git config user.email 'second-brain@localhost'; $placeholder = $true }
    if ($placeholder) { Warn 'No Git identity found; using "Second Brain <second-brain@localhost>" for this vault. Change it with -GitName/-GitEmail.' }
    # Cloned the template itself? Detach so nobody tries to push to the template repository.
    $origin = (& git remote get-url origin 2>$null)
    if ($origin -and ($origin -match 'Doga0/obsidian-second-brain-template(\.git)?/?$')) {
      & git remote remove origin
      $origin = $null
      Warn 'This copy was cloned from the template repository; detached it. Use -Remote <your-repo-url> to connect your own.'
    }
    if ($Remote) {
      if ($origin) { & git remote set-url origin $Remote } else { & git remote add origin $Remote }
      $origin = $Remote
      Ok "Remote set: $Remote"
    }
    if (-not (& git rev-parse --verify HEAD 2>$null)) {
      & git add -A
      & git commit -q -m 'Initial vault from obsidian-second-brain-template' 2>&1 | Out-Null
      if ($LASTEXITCODE -eq 0) { Ok 'First commit created' } else { Warn 'First commit failed; run "git commit" manually' }
    }
    $gitCfg = Join-Path $Vault '.obsidian\plugins\obsidian-git\data.json'
    $pushOn = $false
    if ($origin) {
      $branch = (& git rev-parse --abbrev-ref HEAD)
      & git push -q -u origin $branch 2>&1 | Out-Null
      if ($LASTEXITCODE -eq 0) { $pushOn = $true; Ok "Pushed to $origin; automatic sync enabled" }
      else { Warn "Push to $origin failed (sign in or check the URL). Keeping local-only history; run setup again after fixing." }
    } else { Ok 'No remote: the Git plugin keeps local history only (auto-commit every 10 minutes)' }
    if (Test-Path -LiteralPath $gitCfg) {
      $gc = Get-Content -LiteralPath $gitCfg -Raw -Encoding UTF8 | ConvertFrom-Json
      if (($gc.disablePush -ne (-not $pushOn)) -or ($gc.autoPullOnBoot -ne $pushOn)) {
        $gc.disablePush = -not $pushOn
        $gc.autoPullOnBoot = $pushOn
        [IO.File]::WriteAllText($gitCfg, ($gc | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding $false))
        & git add -- $gitCfg
        & git commit -q -m ('Git plugin: ' + $(if ($pushOn) { 'enable automatic sync' } else { 'local history only' })) 2>&1 | Out-Null
        if ($pushOn) { & git push -q 2>&1 | Out-Null }
      }
    }
    $ErrorActionPreference = $prevEAP
  }
}

# ------------------------------------------------------------------ 4. examples / protected folders
if ($py) {
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
if ($py) { & $py -X utf8 $Tool lint --no-write | Select-Object -First 9 | Out-Host } else { Warn 'Python missing; health check skipped' }

Step 'Done'
Write-Host @"
    Vault: $Vault
    - Start at Home.md, then read 99 System/Second Brain Guide.md
    - AI commands (/sb-*): open this folder in Claude Code (https://claude.com/claude-code) and type /sb-
    - Remove the example notes: powershell -ExecutionPolicy Bypass -File setup.ps1 -RemoveExamples
    - Back up to your own private repo: powershell -ExecutionPolicy Bypass -File setup.ps1 -Remote <repo-url>
"@
