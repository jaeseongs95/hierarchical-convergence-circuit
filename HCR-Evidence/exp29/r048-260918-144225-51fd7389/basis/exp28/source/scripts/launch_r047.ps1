param(
    [Parameter(Mandatory=$true)][string]$Repo,
    [string]$Archive = '',
    [string]$VerifyRun = ''
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$code = 1
try {
    $choices = @()
    if ($env:HCR_PYTHON) {
        if (-not (Test-Path -LiteralPath $env:HCR_PYTHON -PathType Leaf)) { throw 'HCR_PYTHON does not name an existing interpreter.' }
        $choices += ,@($env:HCR_PYTHON)
    } else {
        $py = Get-Command 'py.exe' -ErrorAction SilentlyContinue
        if ($py) { $choices += ,@($py.Source, '-3.12'); $choices += ,@($py.Source, '-3') }
        foreach ($name in @('python.exe','python3.exe')) {
            $candidate = Get-Command $name -ErrorAction SilentlyContinue
            if ($candidate -and $candidate.Source.IndexOf('\WindowsApps\',[StringComparison]::OrdinalIgnoreCase) -lt 0) {
                $choices += ,@($candidate.Source)
            }
        }
    }
    $exe = $null
    foreach ($candidate in $choices) {
        $command = $candidate[0]
        $prefix = @()
        if ($candidate.Count -gt 1) { $prefix = @($candidate[1..($candidate.Count-1)]) }
        $probe = @($prefix) + @('-c','import sys; print(sys.executable); sys.exit(0 if sys.version_info >= (3,12) else 2)')
        $savedPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            $found = & $command @probe 2>$null
            $probeCode = $LASTEXITCODE
        } finally { $ErrorActionPreference = $savedPreference }
        if ($probeCode -eq 0 -and $found) { $exe = [string]($found | Select-Object -Last 1); break }
    }
    if (-not $exe) { throw 'No existing Python 3.12+ found. Nothing was installed or downloaded.' }
    Write-Host ('Python: ' + $exe)
    if ($Archive) {
        $installer = Join-Path $PSScriptRoot 'install_r047.py'
        & $exe -X utf8 -B $installer --repo $Repo --archive $Archive --launch
    } elseif ($VerifyRun) {
        $cli = Join-Path $Repo 'scripts\r047_cli.py'
        & $exe -X utf8 -B $cli verify --run $VerifyRun
    } else {
        & $exe -X utf8 -B (Join-Path $Repo 'Run-HCR-R047.py')
    }
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 1 }
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message)
    $code = 1
}
exit $code
