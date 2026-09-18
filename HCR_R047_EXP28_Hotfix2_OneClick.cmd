@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
set "HCR_R047_HF2_SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$s=[IO.File]::ReadAllText($env:HCR_R047_HF2_SELF);$m=[regex]::Match($s,'(?ms)^#HCR_HF2_PS_BEGIN\r?\n(.*?)^#HCR_HF2_PS_END');if(-not $m.Success){throw 'Missing HF2 launcher section'};& ([scriptblock]::Create($m.Groups[1].Value))"
set "RC=%ERRORLEVEL%"
echo.
echo Exit code: %RC%
pause
exit /b %RC%
#HCR_HF2_PS_BEGIN
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$code = 1
$journal = $null
try {
    $self = $env:HCR_R047_HF2_SELF
    $repo = [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($self))
    $protocol = Join-Path $repo 'tools\r047_state_ablation\protocol.py'
    $launcher = Join-Path $repo 'scripts\launch_r047.ps1'
    $runner = Join-Path $repo 'Run-HCR-R047.py'
    foreach ($required in @($protocol,$launcher,$runner)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw ('Required R047 file not found: ' + $required)
        }
    }

    $stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmss_fffffffZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
    $journal = Join-Path $repo ('HCR-Evidence\deployments\r047-hf2-' + $stamp)
    [IO.Directory]::CreateDirectory($journal) | Out-Null

    $utf8 = New-Object Text.UTF8Encoding($false)
    $beforeBytes = [IO.File]::ReadAllBytes($protocol)
    $beforeText = $utf8.GetString($beforeBytes)
    [IO.File]::WriteAllBytes((Join-Path $journal 'protocol.py.before'), $beforeBytes)

    $sha256 = [Security.Cryptography.SHA256]::Create()
    try { $beforeSha = ([BitConverter]::ToString($sha256.ComputeHash($beforeBytes))).Replace('-','').ToLowerInvariant() }
    finally { $sha256.Dispose() }

    $oldCmd = "            cmd=[sys.executable,'-X','utf8','-B','-m','unittest','discover','-s','tools/r047_state_ablation/tests','-p','test_*.py','-v','-f']"
    $oldRun = "                p=subprocess.run(cmd,cwd=repo,env=childenv,stdout=out,stderr=subprocess.STDOUT)"
    $markerHF1 = "            # HF1: run tests from repo/src so root-level hcr.py cannot shadow src/hcr package."
    $markerHF2 = "            # HF2: run tests from repo/src so root-level hcr.py cannot shadow src/hcr package."
    $newRun = "                p=subprocess.run(cmd,cwd=repo/'src',env=childenv,stdout=out,stderr=subprocess.STDOUT)"

    $already = (($beforeText.Contains($markerHF1) -or $beforeText.Contains($markerHF2)) -and $beforeText.Contains($newRun))
    if (-not $already) {
        $cmdCount = ([regex]::Matches($beforeText,[regex]::Escape($oldCmd))).Count
        $runCount = ([regex]::Matches($beforeText,[regex]::Escape($oldRun))).Count
        if ($cmdCount -ne 1 -or $runCount -ne 1) {
            throw ("R047 protocol.py does not match expected pre-hotfix source. cmd matches={0}, run matches={1}. No source file was changed." -f $cmdCount,$runCount)
        }

        $newline = if ($beforeText.Contains("`r`n")) { "`r`n" } else { "`n" }
        $newCmdLines = @(
            "            tests_dir=repo/'tools'/'r047_state_ablation'/'tests'",
            $markerHF2,
            "            cmd=[sys.executable,'-X','utf8','-B','-m','unittest','discover','-s',str(tests_dir),'-p','test_*.py','-v','-f']"
        )
        $replacementCmd = [string]::Join($newline,$newCmdLines)
        $afterText = $beforeText.Replace($oldCmd,$replacementCmd).Replace($oldRun,$newRun)
        if ($afterText -eq $beforeText) { throw 'HF2 produced no source change.' }

        $temp = $protocol + '.hf2-' + [Guid]::NewGuid().ToString('N') + '.tmp'
        try {
            [IO.File]::WriteAllText($temp,$afterText,$utf8)
            $check = [IO.File]::ReadAllText($temp,$utf8)
            if (-not $check.Contains($markerHF2) -or -not $check.Contains("cwd=repo/'src'")) {
                throw 'HF2 temp-file verification failed before overwrite.'
            }
            # Windows PowerShell/.NET Framework can reject File.Replace(...,$null).
            # Use the long-supported Copy(overwrite=true) API instead; the exact pre-image
            # is already preserved above in protocol.py.before.
            [IO.File]::Copy($temp,$protocol,$true)
            $post = [IO.File]::ReadAllText($protocol,$utf8)
            if ($post -ne $afterText) { throw 'HF2 destination verification failed after overwrite.' }
            [IO.File]::Delete($temp)
        } catch {
            if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Force }
            throw
        }
        $status = 'patched'
    } else {
        $status = 'already_patched'
    }

    $afterBytes = [IO.File]::ReadAllBytes($protocol)
    $sha256 = [Security.Cryptography.SHA256]::Create()
    try { $afterSha = ([BitConverter]::ToString($sha256.ComputeHash($afterBytes))).Replace('-','').ToLowerInvariant() }
    finally { $sha256.Dispose() }

    $record = [ordered]@{
        hotfix = 'R047-HF2'
        status = $status
        scope = 'self-test import resolution; HF1 installer write-method correction'
        protocol_path = $protocol
        before_sha256 = $beforeSha
        after_sha256 = $afterSha
        native_or_experiment_design_changed = $false
        prior_failed_runs_modified = $false
        automatic_retry = $false
        changes = @(
            'unittest discovery start path changed from relative to absolute repo/tools/.../tests',
            'unittest subprocess cwd changed from repo to repo/src',
            'patch installation uses File.Copy(overwrite=true), not File.Replace(..., null)'
        )
        created_utc = [DateTime]::UtcNow.ToString('o')
    }
    [IO.File]::WriteAllText((Join-Path $journal 'hotfix.json'),($record | ConvertTo-Json -Depth 5),$utf8)

    Write-Host ('HF2 status: ' + $status)
    Write-Host ('Journal: ' + $journal)
    Write-Host 'Launching a new R047 run. Previous failed runs are left untouched.'

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $launcher -Repo $repo
    $code = $LASTEXITCODE
    if ($null -eq $code) { $code = 1 }
    [IO.File]::WriteAllText((Join-Path $journal 'launch_result.json'),((@{returncode=$code; automatic_retry=$false; completed_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json)),$utf8)
} catch {
    $message = 'ERROR: ' + $_.Exception.Message
    Write-Host $message
    if ($journal) {
        try {
            $utf8 = New-Object Text.UTF8Encoding($false)
            [IO.File]::WriteAllText((Join-Path $journal 'failure.txt'),($_ | Out-String),$utf8)
        } catch {}
    }
    $code = 1
}
exit $code
#HCR_HF2_PS_END
