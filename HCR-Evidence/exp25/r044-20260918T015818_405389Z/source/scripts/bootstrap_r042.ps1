param([Parameter(Mandatory=$true)][string]$Repo, [string]$InstallArchive = '')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$exitCode = 1
$tempInstaller = $null
try {
    $Repo = [IO.Path]::GetFullPath($Repo)
    if (-not (Test-Path -LiteralPath (Join-Path $Repo 'src\hcr') -PathType Container)) { throw 'Place the launcher in the HCR project root.' }
    $candidates = @()
    foreach ($version in @('312','313','314')) {
        $exe = Join-Path $env:LOCALAPPDATA ('Programs\Python\Python' + $version + '\python.exe')
        if (Test-Path -LiteralPath $exe -PathType Leaf) { $candidates += [pscustomobject]@{Exe=$exe; Args=@()} }
    }
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) { $candidates += [pscustomobject]@{Exe=$py.Source; Args=@('-3.12')} }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { $candidates += [pscustomobject]@{Exe=$python.Source; Args=@()} }
    $chosen = $null
    foreach ($item in $candidates) {
        $prefix = @($item.Args)
        & ($item.Exe) @prefix -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' *> $null
        if ($LASTEXITCODE -eq 0) { $chosen=$item; break }
    }
    if ($null -eq $chosen) { throw 'Python 3.12 or newer was not found.' }
    $exe=$chosen.Exe; $prefix=@($chosen.Args)
    $env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'; $env:PYTHONDONTWRITEBYTECODE='1'
    Write-Host ('Python: '+$exe)
    if ($InstallArchive) {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $archive = [IO.Compression.ZipFile]::OpenRead($InstallArchive)
        try {
            $entry=$archive.GetEntry('scripts/install_r042.py')
            if ($null -eq $entry) { throw 'Installer payload is missing.' }
            $tempInstaller=Join-Path ([IO.Path]::GetTempPath()) ('hcr-r042-'+[Guid]::NewGuid().ToString('N')+'.py')
            $reader=New-Object IO.StreamReader($entry.Open(),[Text.Encoding]::UTF8)
            try { [IO.File]::WriteAllText($tempInstaller,$reader.ReadToEnd(),(New-Object Text.UTF8Encoding($false))) }
            finally { $reader.Dispose() }
        } finally { $archive.Dispose() }
        & $exe @prefix -X utf8 -B $tempInstaller --repo $Repo --archive $InstallArchive
        if ($LASTEXITCODE -ne 0) { $exitCode=$LASTEXITCODE; throw 'Installation stopped. Existing files were not force-overwritten.' }
    }
    & $exe @prefix -X utf8 -B -u (Join-Path $Repo 'Run-HCR-R042.py')
    $exitCode=$LASTEXITCODE
} catch { Write-Host ('ERROR: '+$_.Exception.Message) -ForegroundColor Red }
finally { if ($tempInstaller -and (Test-Path -LiteralPath $tempInstaller)) { Remove-Item -LiteralPath $tempInstaller -Force } }
exit $exitCode
