param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$stateHome = Join-Path $repoRoot "state"
$env:PYTHONUTF8 = "1"

function Resolve-PythonCommand {
    if ($env:CODEX_MEM_PYTHON) {
        return @($env:CODEX_MEM_PYTHON)
    }

    $commonPaths = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"),
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe"
    )
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            return @($path)
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return @($pythonCmd.Source)
    }

    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        return @($pyCmd.Source, "-3")
    }

    throw "No usable Python interpreter found. Set CODEX_MEM_PYTHON to python.exe."
}

Push-Location $repoRoot
try {
    $python = @(Resolve-PythonCommand)
    if ($python.Length -gt 1) {
        & $python[0] $python[1..($python.Length - 1)] -m codex_mem --home $stateHome @CliArgs
    }
    else {
        & $python[0] -m codex_mem --home $stateHome @CliArgs
    }
}
finally {
    Pop-Location
}
