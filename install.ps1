param(
  [Parameter(Position = 0)]
  [ValidateSet("install", "uninstall", "help")]
  [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

function Find-Bash {
  $candidates = @(
    (Get-Command bash.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue),
    "$env:ProgramFiles\Git\bin\bash.exe",
    "$env:ProgramFiles\Git\usr\bin\bash.exe",
    "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe",
    "$env:LOCALAPPDATA\Programs\Git\usr\bin\bash.exe"
  ) | Where-Object { $_ -and (Test-Path $_) }

  if ($candidates.Count -gt 0) { return $candidates[0] }
  return $null
}

function Show-Usage {
  Write-Host "Usage:"
  Write-Host "  .\install.ps1 install    # Install or update"
  Write-Host "  .\install.ps1 uninstall  # Uninstall"
  Write-Host ""
  Write-Host "Notes (Windows):"
  Write-Host "  - Requires Git for Windows (Git Bash) OR WSL."
  Write-Host "  - If you already use WSL2, run install.sh from WSL instead."
}

if ($Command -eq "help") {
  Show-Usage
  exit 0
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$installSh = Join-Path $repoRoot "install.sh"
if (-not (Test-Path $installSh)) {
  throw "Missing install.sh next to install.ps1: $installSh"
}

$bash = Find-Bash
if (-not $bash) {
  Write-Host "❌ bash.exe not found."
  Write-Host "   Install Git for Windows (includes Git Bash): https://git-scm.com/download/win"
  Write-Host "   Or use WSL2 and run ./install.sh there."
  exit 1
}

& $bash $installSh $Command
