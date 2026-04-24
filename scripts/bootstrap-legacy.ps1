param(
    [string]$LegacyPath = "C:\Users\Ling\.codex\memories\persistent_memory"
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "Initializing codex-mem..."
powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\codex-mem.ps1") init

Write-Host "Importing legacy memories from $LegacyPath ..."
powershell -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\codex-mem.ps1") import-legacy --path $LegacyPath

Write-Host "Done."
