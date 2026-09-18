@echo off
setlocal DisableDelayedExpansion
chcp 65001 >nul
set "HCR_R047_HF1_SELF=%~f0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$s=[IO.File]::ReadAllText($env:HCR_R047_HF1_SELF);$m=[regex]::Match($s,'(?ms)^#HCR_HF1_PS_BEGIN\r?\n(.*?)^#HCR_HF1_PS_END');if(-not $m.Success){throw 'Missing HF1 launcher section'};& ([scriptblock]::Create($m.Groups[1].Value))"
set "RC=%ERRORLEVEL%"
echo.
echo Exit code: %RC%
pause
exit /b %RC%
#HCR_HF1_PS_BEGIN
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$code = 1
$journal = $null
try {
    $self = $env:HCR_R047_HF1_SELF
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
    $journal = Join-Path $repo ('HCR-Evidence\deployments\r047-hf1-' + $stamp)
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
    $marker = "            # HF1: run tests from repo/src so root-level hcr.py cannot shadow src/hcr package."
    $newCmd = "            tests_dir=repo/'tools'/'r047_state_ablation'/'tests'`r`n$marker`r`n            cmd=[sys.executable,'-X','utf8','-B','-m','unittest','discover','-s',str(tests_dir),'-p','test_*.py','-v','-f']"
    $newRun = "                p=subprocess.run(cmd,cwd=repo/'src',env=childenv,stdout=out,stderr=subprocess.STDOUT)"

    $already = $beforeText.Contains($marker) -and $beforeText.Contains($newRun)
    if (-not $already) {
        $cmdCount = ([regex]::Matches($beforeText,[regex]::Escape($oldCmd))).Count
        $runCount = ([regex]::Matches($beforeText,[regex]::Escape($oldRun))).Count
        if ($cmdCount -ne 1 -or $runCount -ne 1) {
            throw ("R047 protocol.py does not match the expected pre-HF1 source. cmd matches={0}, run matches={1}. No source file was changed." -f $cmdCount,$runCount)
        }
        $newline = if ($beforeText.Contains("`r`n")) { "`r`n" } else { "`n" }
        $replacementCmd = $newCmd.Replace("`r`n",$newline)
        $afterText = $beforeText.Replace($oldCmd,$replacementCmd).Replace($oldRun,$newRun)
        if ($afterText -eq $beforeText) { throw 'HF1 produced no source change.' }

        $temp = $protocol + '.hf1-' + [Guid]::NewGuid().ToString('N') + '.tmp'
        try {
            [IO.File]::WriteAllText($temp,$afterText,$utf8)
            $check = [IO.File]::ReadAllText($temp,$utf8)
            if (-not $check.Contains($marker) -or -not $check.Contains("cwd=repo/'src'")) {
                throw 'HF1 post-write verification failed before replacement.'
            }
            [IO.File]::Replace($temp,$protocol,$null)
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
        hotfix = 'R047-HF1'
        status = $status
        scope = 'self-test import resolution only'
        protocol_path = $protocol
        before_sha256 = $beforeSha
        after_sha256 = $afterSha
        native_or_experiment_design_changed = $false
        prior_failed_run_modified = $false
        automatic_retry = $false
        change = @(
            'unittest discovery start path changed from relative to absolute repo/tools/.../tests',
            'unittest subprocess cwd changed from repo to repo/src'
        )
        created_utc = [DateTime]::UtcNow.ToString('o')
    }
    [IO.File]::WriteAllText((Join-Path $journal 'hotfix.json'),($record | ConvertTo-Json -Depth 5),$utf8)

    Write-Host ('HF1 status: ' + $status)
    Write-Host ('Journal: ' + $journal)
    Write-Host 'Launching a new R047 run. The previous failed run is left untouched.'

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
#HCR_HF1_PS_END
