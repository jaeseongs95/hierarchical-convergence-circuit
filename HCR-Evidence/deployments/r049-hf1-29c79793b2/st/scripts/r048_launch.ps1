param([Parameter(Mandatory=$true)][string]$Repo,[string]$Archive='',[string]$VerifyRun='')
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
$env:PYTHONUTF8='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$code=1
try {
    $python=$null
    if ($env:HCR_PYTHON) {
        if (-not (Test-Path -LiteralPath $env:HCR_PYTHON -PathType Leaf)) { throw 'HCR_PYTHON is not an existing executable.' }
        $choices=@();$choices+=,@($env:HCR_PYTHON)
    } else {
        $choices=@()
        $p=Get-Command py.exe -ErrorAction SilentlyContinue
        if ($p) { $choices+=,@($p.Source,'-3.12'); $choices+=,@($p.Source,'-3') }
        foreach($name in @('python.exe','python3.exe')) {
            $p=Get-Command $name -ErrorAction SilentlyContinue
            if ($p -and $p.Source.IndexOf('\WindowsApps\',[StringComparison]::OrdinalIgnoreCase) -lt 0) { $choices+=,@($p.Source) }
        }
    }
    foreach($choice in $choices) {
        $exe=$choice[0];$prefix=@()
        if($choice.Count -gt 1){$prefix=@($choice[1..($choice.Count-1)])}
        $args=@($prefix)+@('-c','import sys; print(sys.executable); sys.exit(0 if sys.version_info >= (3,12) else 2)')
        $saved=$ErrorActionPreference
        try {$ErrorActionPreference='Continue';$found=& $exe @args 2>$null;$rc=$LASTEXITCODE}
        finally {$ErrorActionPreference=$saved}
        if($rc -eq 0 -and $found){$python=[string]($found|Select-Object -Last 1);break}
    }
    if(-not $python){throw 'Existing Python 3.12+ not found. No software was installed.'}
    Write-Host ('Python: '+$python)
    if($Archive){
        & $python -X utf8 -B (Join-Path $PSScriptRoot 'r048_install.py') --repo $Repo --archive $Archive --launch
    }elseif($VerifyRun){
        & $python -X utf8 -B (Join-Path $Repo 'scripts\r048_cli.py') verify --run $VerifyRun
    }else{
        & $python -X utf8 -B (Join-Path $Repo 'Run-HCR-R048.py')
    }
    $code=$LASTEXITCODE
    if($null -eq $code){$code=1}
}catch{
    Write-Host ('ERROR: '+$_.Exception.Message)
    $code=1
}
exit $code
