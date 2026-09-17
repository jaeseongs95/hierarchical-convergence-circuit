# R0.2.1 적용·실행 안내

## 적용과 실행은 다르다

배포 ZIP은 기존 저장소에 추가할 변경분이다. ZIP을 저장소 밖에 압축 해제한다.
`apply_r021.py`는 기본적으로 읽기 전용이고 `--apply`가 있어야 백업 후 파일을 쓴다.
설치기에서 테스트·추론·git commit/push를 자동 실행하지 않는다.

아래 블록 전체를 한 번 실행하면 **검사 → 적용 → 파일 확인 → 시험 → EXP-10 → 검산** 순서로 진행한다.
하나가 실패하면 다음 명령을 수행하지 않는다. `$Patch`는 ZIP을 푼 실제 폴더다.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $Repo = 'D:\codex\진짜미친짓\hierarchical-convergence-circuit'
    $Patch = 'C:\Users\sjs95\Desktop\hcr-r021-update'
    $Installer = Join-Path $Patch 'apply_r021.py'
    if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) {
        throw "패치 적용기를 찾을 수 없음: $Installer"
    }
    & python -X utf8 -B $Installer --repo $Repo
    if ($LASTEXITCODE -ne 0) { throw '패치 사전 검사 실패' }
    & python -X utf8 -B $Installer --repo $Repo --apply
    if ($LASTEXITCODE -ne 0) { throw '패치 적용 실패' }
    $Launcher = Join-Path $Repo 'Run-HCR-R021.ps1'
    if (-not (Test-Path -LiteralPath $Launcher -PathType Leaf)) { throw '실행기 파일 누락' }
    & $Launcher -Out 'HCR-Evidence\exp10\r021-first'
}
```

결과 위치:
`D:\codex\진짜미친짓\hierarchical-convergence-circuit\HCR-Evidence\exp10\r021-first`

기존 폴더는 삭제하거나 덮어쓰지 않는다. 재실행은 `r021-second` 등 새 이름을 사용한다.
`Run-HCR-R021.ps1`에 Out을 생략하면 `HCR-Evidence/exp10/r021-실행시각`을 사용한다.
script 실행이 시스템 정책에 차단되는 경우 적용기와 아래 Python 명령을 PowerShell에서 직접 실행한다. 정책을 임의로 낮추지 않는다.

## 패치를 이미 적용했다면

프로젝트 루트에서:

```powershell
& {
    $ErrorActionPreference = 'Stop'
    Set-Location 'D:\codex\진짜미친짓\hierarchical-convergence-circuit'
    & .\Run-HCR-R021.ps1 -Out 'HCR-Evidence\exp10\r021-first'
}
```

실행기 내부 순서: release 파일 해시 검사, `hcr.py check`, baseline tools 시험, concept tools 시험,
concept registry 검사, session demo, session verify, 요약 출력.
기존 R0.1/R0.2 명령과 memory 형식은 유지된다. EXP-09를 다시 복구하거나 다시 추론할 필요 없다.

## 실행기 대신 직접 수행

```powershell
python -X utf8 -B hcr.py check
python -X utf8 -B hcr.py session demo --out HCR-Evidence/exp10/r021-first
python -X utf8 -B hcr.py session verify --run HCR-Evidence/exp10/r021-first
```

정상 EXP-10은 `state=complete`, `verified=true`, `equivalent=true`, 비교 추론 30회 + seed 학습 6회를 기록한다.
각 전이 뒤 실제 디스크 save/load를 수행하는 resumed 조건을 포함한다. 이는 개발 검증 실행이며 EXP-09 새 연구 표본이 아니다.
`wrong`가 정답으로 자동 수정되면 오히려 기존 동작 보존 실패일 수 있다. 결과 해석은 실험 명세를 따른다.

## 단일 관측의 실제 프로세스 간 중단·재개

```powershell
python -X utf8 -B hcr.py session start `
  --input configs/example_observation.json `
  --steps 1 `
  --out HCR-Evidence/session-manual/step-01.json

python -X utf8 -B hcr.py session resume `
  --checkpoint HCR-Evidence/session-manual/step-01.json `
  --complete `
  --out HCR-Evidence/session-manual/complete-01.json

python -X utf8 -B hcr.py session verify `
  --checkpoint HCR-Evidence/session-manual/complete-01.json
```

`start`/부분 resume은 readout_ready에서 자동 finish하지 않는다. `resume --complete`가 남은 계산과 finish를 수행한다.
완료되어 pending이 없는 snapshot은 재시작할 수 없다. `--steps 0`은 begin 직후 상태만 저장한다.
`--expect-sha256`를 사용하면 직전 명령이 출력한 checkpoint_sha256와 정확히 같은 파일인지 추가로 검사한다.
`start --memory`는 R0.2 AdaptiveMemory를 입력으로 받을 수 있지만 session checkpoint와 memory packet을 혼용하지 않는다.

## 결과 제출

`HCR-Evidence/exp10/r021-first` **폴더 전체를 ZIP**으로 보낸다. summary만 골라 보내면 원시 상태·hash 재검산이 불가능하다.
이 폴더에는 source snapshot, seed/training, 각 조건의 record, resumed checkpoint들, IO 계측, summary, audit, manifest가 들어 있다.
폴더 전체 이동/이름 변경은 가능하지만 내부 파일·상대경로·내용은 그대로 둔다.

## 남겨둔 범위

단일 dependency iteration 내부의 kernel tick까지 정지하는 기능, 자동 background 작업, A/M 전환,
negative exception memory, prior 정책 변경, pool 가속은 구현하지 않았다.
Windows 실제 결과는 사용자의 실행으로 확인한다. Linux에서는 PowerShell parser 시험을 skip하며 이 숫자를 통과로 세지 않는다.

## 소스 줄바꿈과 원시 증거 해시

R0.2.1 release manifest는 source/document의 raw 해시와 명시적인 LF 정규화 해시를 함께 둔다.
Windows checkout의 CRLF/LF 차이만 허용하고 실제 코드 변경은 거부한다. 기존 manifest에는 이 예외를 소급 적용하지 않는다.
`runs`, capture, recovery, EXP-10 원시 결과의 해시는 여전히 바이트 그대로 비교한다.
