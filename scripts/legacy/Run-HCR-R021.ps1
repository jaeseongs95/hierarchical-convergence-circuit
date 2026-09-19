[CmdletBinding()]
param(
    [string]$PythonPath = 'python',
    [string]$Out = ''
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function Invoke-HcrPython {
    param([string[]]$Arguments)
    & $PythonPath -X utf8 -B @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed (exit $LASTEXITCODE): $($Arguments -join ' ')"
    }
}

Push-Location $Repo
try {
    if ([string]::IsNullOrWhiteSpace($Out)) {
        $Stamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
        $Out = Join-Path $Repo "HCR-Evidence\exp10\r021-$Stamp"
    } elseif (-not [System.IO.Path]::IsPathRooted($Out)) {
        $Out = Join-Path $Repo $Out
    }
    if (Test-Path -LiteralPath $Out) {
        throw "Output already exists. Keep it and choose a new path: $Out"
    }
    Invoke-HcrPython -Arguments @('scripts/verify_release.py')
    Invoke-HcrPython -Arguments @('hcr.py', 'check')
    Invoke-HcrPython -Arguments @('-m','unittest','discover','-s','tools/r02_baseline/tests','-p','test_*.py','-v')
    Invoke-HcrPython -Arguments @('-m','unittest','discover','-s','tools/r02_concepts/tests','-p','test_*.py','-v')
    Invoke-HcrPython -Arguments @('tools/r02_concepts/check.py','--repo',$Repo)
    Invoke-HcrPython -Arguments @('hcr.py','session','demo','--out',$Out)
    Invoke-HcrPython -Arguments @('hcr.py','session','verify','--run',$Out)
    Write-Host "Result directory: $Out"
    Get-Content -LiteralPath (Join-Path $Out 'summary.ko.md') -Encoding UTF8
} finally {
    Pop-Location
}
