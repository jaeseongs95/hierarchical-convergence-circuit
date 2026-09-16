[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [string]$OutDir = "",
    [string]$PythonPath = ""
)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
if (-not $PythonPath) {
    $Known = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
    if (Test-Path -LiteralPath $Known) { $PythonPath = $Known }
    else {
        $Command = Get-Command python -ErrorAction SilentlyContinue
        if ($Command) { $PythonPath = $Command.Source }
        else { throw "Python 3.12+ not found. Use -PythonPath with an existing python.exe." }
    }
}
$Entry = Join-Path $Root "hcr.py"
& $PythonPath -X utf8 -B $Entry check
if ($LASTEXITCODE -ne 0) { throw "Selftest failed; no demo started." }
if ($CheckOnly) { Write-Output "Check complete. No LLM/model/server request."; exit 0 }
if (-not $OutDir) {
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss_fffffff"
    $OutDir = Join-Path $Root ("runs\r01_" + $Stamp)
}
& $PythonPath -X utf8 -B $Entry demo --config (Join-Path $Root "configs\r01.toml") --out $OutDir
if ($LASTEXITCODE -ne 0) { throw "Demo stopped. Existing output is preserved. No automatic retry." }
& $PythonPath -X utf8 -B $Entry verify --run $OutDir
if ($LASTEXITCODE -ne 0) { throw "Verification failed. Output is preserved." }
Write-Output ("Completed: " + $OutDir)
