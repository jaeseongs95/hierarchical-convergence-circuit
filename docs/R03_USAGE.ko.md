# R0.3 적용·실행 — EXP-11

## 기준과 범위

기준 commit은 `309828118509340572b946dfa60e8cde1f16e452`이다. R0.2.1의 기존 API·수치 규칙·학습 규칙을 보존한다.
R0.3은 두 처리 정책, typed 경로 메시지, 고정/적응 interleaving, 보수적 통합을 추가한다.
사용자의 과거 EXP-09/10 결과는 수정하지 않으며 새 비교를 독립 폴더에 쌓는다.

## 적용부터 실행까지

ZIP은 프로젝트 바깥에 풀고 `apply_r03.py`가 있는 폴더 경로를 `$Patch`로 지정한다.
README는 로컬 본문 전체를 유지하고 R0.3 안내 머리말만 추가한다. 실행 소스의 실제 충돌은 계속 차단한다.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $Repo = 'D:\codex\진짜미친짓\hierarchical-convergence-circuit'
    $Patch = 'C:\Users\sjs95\Desktop\hcr-r03-update'
    $Installer = Join-Path $Patch 'apply_r03.py'
    if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) {
        throw "적용기 파일이 없음: $Installer"
    }
    & python -X utf8 -B $Installer --repo $Repo
    if ($LASTEXITCODE -ne 0) { throw 'R0.3 사전검사 실패' }
    & python -X utf8 -B $Installer --repo $Repo --apply
    if ($LASTEXITCODE -ne 0) { throw 'R0.3 적용 실패' }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Repo 'Run-HCR-R03.ps1') -Out 'HCR-Evidence\exp11\r03-first'
    if ($LASTEXITCODE -ne 0) { throw 'R0.3 시험 또는 EXP-11 실패. 첫 오류를 확인하세요.' }
}
```

적용기는 Git 작업·네트워크 접속·실험 실행을 하지 않는다. 기존 파일은 저장소 형제 폴더에 백업하며, 충돌 시 쓰기 전에 중단한다.
실행기는 release 검사 → core 시험 → baseline 도구 시험 → concept 도구 시험 → 개념 연결 → EXP-11 → 감사 순이다.
PowerShell 파일을 바로 `&`로 실행하지 않고 위처럼 별도 프로세스로 호출한다.

## 이미 적용한 뒤 실행만 하기

```powershell
$Repo = 'D:\codex\진짜미친짓\hierarchical-convergence-circuit'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$Repo\Run-HCR-R03.ps1" -Out 'HCR-Evidence\exp11\r03-first'
```

같은 결과 폴더가 이미 있으면 덮어쓰지 않는다. 재실행은 `r03-second`처럼 다른 이름을 사용한다.
실패 기록을 삭제하거나 동일 이름으로 자동 retry하지 않는다.

## 생성되는 실제 경로

```text
D:\codex\진짜미친짓\hierarchical-convergence-circuit\HCR-Evidence\exp11\r03-first
```

```text
r03-first/
├─ plan.json                # 시작 전에 동결한 입력/예산/방법/소스 hash
├─ source/src/hcr/          # 당시 공통 엔진과 독립 감사 소스
├─ seed.json                # 검증된 seed session
├─ training.json            # 6개 학습 episode와 외부 평가
├─ raw/                     # 각 비교 직후 보존한 원시 method record
├─ records/                 # 같은 기록 + 외부 assessment + 감사
├─ summary.json
├─ summary.ko.md
├─ audit.json
└─ manifest.json
```

84개 비교 run, 140개 worker attempt, seed 학습 6회가 예정되어 있다.
140은 독립 문제 수가 아니라 방법/예산 조건의 worker 계산 수다. 미완료 worker도 attempt 수에 들어가며 정답으로 세지 않는다.
`verified=true`는 기록 계약이 검산됐다는 뜻이지 모든 판단의 정답·효율 개선이 아니다.
원시 record는 worker별 전체 trace·generation·proof와 controller의 메시지/스케줄을 담는다.
분석을 전달할 때는 `r03-first` 폴더 전체를 ZIP으로 압축한다.

## 수동 명령

```powershell
Set-Location 'D:\codex\진짜미친짓\hierarchical-convergence-circuit'
python -X utf8 -B hcr.py methods demo --out 'HCR-Evidence\exp11\r03-first'
python -X utf8 -B hcr.py methods verify --run 'HCR-Evidence\exp11\r03-first'
```

선행 방법을 바꾸는 대조는 별도 폴더에 `--first-method sequential`을 지정한다. 기존 run을 새 조건으로 덮어쓰지 않는다.
외부 입력은 `hcr.py methods infer --help`를 참조한다. `infer`는 공개 관측만 받고 정답을 판정하지 않는다.
이전 EXP-10을 다시 실행할 필요는 없다. source hash가 달라진 과거 checkpoint는 과거 source와 함께 검산하며, 기존 hash를 갱신하지 않는다.
