param([Parameter(Mandatory=$true)][string]$Repo,[string]$Archive='')
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
$OutputEncoding=[Console]::OutputEncoding
$code=1
try {
    $candidates=@()
    if($env:HCR_PYTHON -and (Test-Path -LiteralPath $env:HCR_PYTHON -PathType Leaf)) {
        $candidates+=@{Exe=$env:HCR_PYTHON;Prefix=@()}
    }
    if($env:LOCALAPPDATA) {
        $known=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
        if(Test-Path -LiteralPath $known -PathType Leaf){$candidates+=@{Exe=$known;Prefix=@()}}
    }
    $py=Get-Command py.exe -ErrorAction SilentlyContinue
    if($py){$candidates+=@{Exe=$py.Source;Prefix=@('-3.12')}}
    $python=Get-Command python.exe -ErrorAction SilentlyContinue
    if($python -and $python.Source -and $python.Source.IndexOf('\WindowsApps\',[StringComparison]::OrdinalIgnoreCase) -lt 0) {
        $candidates+=@{Exe=$python.Source;Prefix=@()}
    }
    $chosen=$null
    foreach($candidate in $candidates) {
        try {
            $pre=@($candidate.Prefix)
            & $candidate.Exe @pre -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 9)" 2>$null
            if($LASTEXITCODE -eq 0){$chosen=$candidate;break}
        } catch { }
    }
    if($null -eq $chosen){throw 'Python 3.12+ not found. No package or interpreter was installed.'}
    $prefix=@($chosen.Prefix)
    if($Archive) {
        $installer=Join-Path (Split-Path -Parent $Archive) 'install_r046.py'
        & $chosen.Exe @prefix -X utf8 -B $installer --repo $Repo --archive $Archive
        if($LASTEXITCODE -ne 0){throw 'Additive installation failed; no experiment was started.'}
    }
    $run=Join-Path $Repo 'Run-HCR-R046.py'
    & $chosen.Exe @prefix -X utf8 -B $run
    $code=$LASTEXITCODE
    if($null -eq $code){$code=1}
} catch {
    Write-Host ('ERROR: '+$_.Exception.Message)
    $code=1
}
exit $code
