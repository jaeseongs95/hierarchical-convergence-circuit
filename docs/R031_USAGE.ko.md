# R0.3.1 적용·실행

기존 R0.3에 추가하는 EXP-12 패치다. 기존 실험 결과를 이동·삭제하거나 다시 복구할 필요는 없다.

## 패치 적용

ZIP을 저장소 **밖**에 풀고 `apply_r031.py`가 있는 폴더를 지정한다. payload 수동 덮어쓰기는 하지 않는다.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $Repo = 'D:\codex\진짜미친짓\hierarchical-convergence-circuit'
    $Patch = 'C:\Users\sjs95\Desktop\hcr-r031-update'
    $Installer = Join-Path $Patch 'apply_r031.py'

    if (-not (Test-Path -LiteralPath $Installer -PathType Leaf)) {
        throw "적용기 파일이 없음: $Installer"
    }

    & python -X utf8 -B $Installer --repo $Repo
    if ($LASTEXITCODE -ne 0) { throw 'R0.3.1 사전검사 실패' }

    & python -X utf8 -B $Installer --repo $Repo --apply
    if ($LASTEXITCODE -ne 0) { throw 'R0.3.1 적용 실패' }

    $Launcher = Join-Path $Repo 'Run-HCR-R031.py'
    if (-not (Test-Path -LiteralPath $Launcher -PathType Leaf)) {
        throw "실행기 파일이 없음: $Launcher"
    }

    & python -X utf8 -B $Launcher --out 'HCR-Evidence\exp12\r031-first'
    if ($LASTEXITCODE -ne 0) { throw '시험 또는 EXP-12 실패. 출력된 첫 오류를 확인하세요.' }
}
```

실행기 자체가 Python이므로 PowerShell ExecutionPolicy를 변경하지 않는다. 기존 Python 3.12 이상을 사용한다. pip 설치·모델 다운로드·네트워크 호출·commit·push는 없다.

적용기는 기존 source/test/config와 수정 대상 내용을 검사한다. README는 로컬 본문을 보존하고 R0.3.1 안내만 앞에 추가하며 release manifest도 해당 바이트를 기준으로 갱신한다. README 이외의 코드 충돌은 차단한다. 변경 전 백업은 프로젝트의 형제 폴더에 둔다.

## 실행 순서

`Run-HCR-R031.py`는 release 검사 → core selftest → baseline 90개 도구시험 → concept 39개 도구시험 → 개념 연결 검사 → EXP-12 → 결과 감사 순으로 수행한다. 어느 단계가 실패하면 이후 작업을 시작하지 않는다. core selftest의 신규 prior 시험에도 개발 검증용 작은 전체 EXP-12 실행이 포함되며 임시 폴더에서 수행된다. 이것은 정식 결과 폴더의 표본과 섞지 않는다.

같은 위치에 결과가 있으면 자동으로 이름을 바꾸거나 덮어쓰지 않는다. 최초 실패도 보존하고 다음 실행은 `r031-second`처럼 명시적으로 새 이름을 사용한다.

## 결과 위치

```text
D:\codex\진짜미친짓\hierarchical-convergence-circuit\
└─ HCR-Evidence\exp12\r031-first\
   ├─ plan.json
   ├─ source\
   ├─ seed\3.json, 6.json, 9.json
   ├─ training.json
   ├─ raw\<학습량>\<사례>\<arm>.json
   ├─ records\<학습량>\<사례>\<arm>.json
   ├─ fixed\<학습량>\<사례>\legacy.json, route_only.json
   ├─ costs.csv
   ├─ summary.json
   ├─ summary.ko.md
   ├─ audit.json
   └─ manifest.json
```

정상 완료의 작업 수는 `task_inferences=117`, `training_inferences=9`, `fixed_network_pairs=39`, `fixed_network_replays=78`이다. `verified=true`는 기록·조작 계약의 검산을 뜻하며, route_only가 우수하다는 통과 기준은 없다.

출력의 `new_task_inferences` 등은 generator의 새 계산 수이고 `audit_new_inferences=0`은 검산 중 추론을 다시 하지 않았다는 뜻이다. 저장된 audit의 `new_inferences=0`을 전체 실험이 실행되지 않았다는 뜻으로 해석하지 않는다.

분석을 요청할 때는 **`r031-first` 폴더 전체**를 ZIP으로 전달한다. 파일 일부만 선택하지 않는다. 원본 run 내부에 추가 보고서나 ZIP을 넣으면 manifest 검사가 실패하므로 별도 위치에 압축한다.

## 개별 명령

프로젝트 루트에서 다음 명령을 쓸 수 있다.

```powershell
# 계획만 읽기: 새 추론 없음
python -X utf8 -B hcr.py priors plan

# 새 실험만 실행: 이미 launcher를 완료했다면 중복 실행하지 않음
python -X utf8 -B hcr.py priors demo --out 'HCR-Evidence\exp12\r031-second'

# 기존 결과 재검산: 원본 변경 및 새 추론 없음
python -X utf8 -B hcr.py priors verify --run 'HCR-Evidence\exp12\r031-first'

# 신규 시험만 올바른 import 경로로 실행
python -X utf8 -B -m unittest discover -s tests -p 'test_r031_prior_scope.py' -v
```

비기본 policy의 개별 session 시작은 `hcr.py session start ... --judgment-prior route_only`를 사용한다. resume은 packet에 기록된 정책을 따른다. resume 중 다른 정책으로 바꾸는 옵션은 없다. 일반 `hcr.py methods demo`는 기존 legacy 정책 그대로이며 EXP-12의 prior 비교와 혼합하지 않았다.
