# R038 소스 적용 및 EXP19 실행

## 적용

`HCR_R038_EXP19_additive_source.zip`의 **내용물**을 기존 `hierarchical-convergence-circuit` 저장소 루트에 병합한다. 새 프로젝트를 따로 만드는 전체 소스 ZIP이 아니다.

기준 커밋은 `d25f4bd4e3bd8c8aae763e3ee6542dbfd590900f`다. 기존 `src/hcr`, R035/R036/R037 소스와 기존 evidence는 그대로 필요하다. 이 ZIP에는 신규 경로만 들어 있다. Git pull, checkout, reset, commit, push는 자동 수행하지 않는다.

루트 배치는 다음처럼 되어야 한다.

```text
hierarchical-convergence-circuit/
  src/hcr/                         ← 기존 엔진 유지
  tools/r037_online_selection/     ← 기존 R037 유지
  tools/r038_early_adoption/        ← 이번 추가 소스
  HCR-Evidence/exp18/r037-first/    ← 기존 결과 유지
  R038_MANIFEST.json
  R038_README.ko.md
  Run-HCR-R038.py
  Run-HCR-R038.bat
  scripts/r038_cli.py
  scripts/verify_r038.py
```

ZIP을 같은 경로에 두 번 적용하면서 수정한 새 파일을 덮어쓰지 않도록 주의한다. 실행기는 기존 실험/계획 파일을 덮어쓰지 않지만 일반 압축 프로그램의 덮어쓰기 동작까지 통제하지는 않는다.

## 한 번에 실행

저장소 루트의 `Run-HCR-R038.bat`를 실행한다. Python 3.12의 기본 사용자 설치 경로가 있으면 우선 사용하고, 없으면 PATH의 python을 사용한다. Python 3.12 이상과 기존 프로젝트가 필요하며 새 pip 설치나 외부 API 키는 필요하지 않다.

PowerShell에서 직접 실행하는 명령은 다음과 같다.

```powershell
python -X utf8 -B .\Run-HCR-R038.py
```

이 실행기는 순서대로 신규 배포/기준선 checksum, 신규 단위 테스트, 실제 R035 selector 연결 테스트, **기존 EXP18 전체 독립 재검증**, **기존 2개 입력으로 수행하는 실제 native 통합 테스트**, EXP19 계획 동결, 84개 본 실행, 독립 audit, verify, evidence ZIP 생성을 수행한다.

각 단계는 별도 프로세스다. 첫 오류에서 중단하며 import 오류나 evidence 누락을 skip·synthetic 결과로 바꾸지 않는다. stdout/stderr 및 종료 코드가 실행 로그에 보존된다.

Native 통합 self-test의 12개 session은 기존 2개 입력 × prior 2개 × 실험군 3개이며 본 EXP19 84개와 별개의 self-test다. 신규 6개 topology를 이 사전 검사에서 실행해 고르지 않는다.

## 검사만 실행

```powershell
python -X utf8 -B .\Run-HCR-R038.py --check-only
```

`--check-only`는 본 EXP19 계획/84개 실행을 하지 않는다. 다만 위의 실제 native 통합 self-test와 EXP18 재검증은 수행한다.

신규 ZIP 자체의 파일 checksum만 검사하려면 다음을 사용한다.

```powershell
python -X utf8 -B .\scripts\verify_r038.py --addon-only
```

## 결과 위치

기본값은 UTC 타임스탬프가 붙은 새 폴더다.

```text
HCR-Evidence/exp19/
  r038-<timestamp>.plan.json
  r038-<timestamp>/
    plan.json
    environment.json
    attempts.jsonl
    manifest.json
    source/                  실행에 사용한 기존/신규 소스 snapshot
    basis/exp18/             EXP18 계획·manifest·audit 출처 부분집합
    upstream/                원 학습 plan·seed·training
    raw/t0000.json ...       84개 실제 실행의 원문
    analysis/
      audit.json
      summary.ko.md
      summary.json
      paired.csv             28개 paired trio의 출력/기회/비용 비교
      trials.csv             84개 trial의 최종 출력·가정 수·비용
      records/               readout별 기회·frontier·proof·검산 기록
      manifest.json
    audit_failures/          audit 실패 시만 생성
  r038-<timestamp>_evidence.zip
  execution-logs/<timestamp>/
    01.log ...
    execution.json
```

성공하면 보고서와 evidence ZIP의 실제 경로를 마지막에 출력한다. 실패한 실행에는 `failure.json`과 부분 원문이 보존되며 완료 manifest를 만들지 않는다. 실행 전 사전 검사 실패는 `execution-logs`에서 확인한다. 외부 강제 종료에서는 `attempts.jsonl`만 남을 수 있으므로 완료 manifest가 없는 폴더를 성공으로 해석하지 않는다.

## 출처 또는 출력 폴더 지정

```powershell
python -X utf8 -B .\Run-HCR-R038.py `
  --source-run .\HCR-Evidence\exp18\r037-first `
  --out .\HCR-Evidence\exp19\r038-first
```

같은 `--out`에 다시 실행하지 않는다. 수동으로 재실행할 때는 새로운 이름을 지정하고 이전 실패 폴더를 보존한다.

## 단계별 실행

```powershell
python -X utf8 -B .\scripts\r038_cli.py prepare --source-run .\HCR-Evidence\exp18\r037-first --out .\HCR-Evidence\exp19\r038-first.plan.json
python -X utf8 -B .\scripts\r038_cli.py execute --plan .\HCR-Evidence\exp19\r038-first.plan.json --out .\HCR-Evidence\exp19\r038-first
python -X utf8 -B .\scripts\r038_cli.py audit --run .\HCR-Evidence\exp19\r038-first
python -X utf8 -B .\scripts\r038_cli.py verify --run .\HCR-Evidence\exp19\r038-first
python -X utf8 -B .\scripts\r038_cli.py bundle --run .\HCR-Evidence\exp19\r038-first --out .\HCR-Evidence\exp19\r038-first_evidence.zip
```

기존 `analysis/`가 있으면 `audit`로 덮어쓰지 않고 `verify`로 재계산 비교한다. 계획 동결 후 소스·입력·memory·config가 바뀌면 실행을 거부한다.

## EXP18 가정 수 정정 sidecar — 선택 사항

```powershell
python -X utf8 -B .\scripts\r038_cli.py errata-exp18 `
  --source-run .\HCR-Evidence\exp18\r037-first `
  --out .\HCR-Evidence\exp19\exp18-assumption-count-errata-r038.json
```

이 명령은 기존 EXP18 raw를 먼저 독립 재검증하고, 이전의 잘못 명명된 지원 가정 수와 새 검사/지원/비지원 수를 별도 파일로 저장한다. 원 EXP18 source/raw/analysis는 변경하지 않는다. 본 EXP19 실행에 필수인 명령은 아니며 정정 파일은 본 84개 결과와 별개다.

## 결과 읽기

`native`와 `posthoc_support`의 출력 차이는 선택 효과, `posthoc_support`와 `online_support`의 native 작업량 차이는 적용 시점 효과다. 차등 기회가 발생하지 않은 case를 삭제하거나 반증으로 단정하지 않는다. `saved_native_ticks`가 양수여도 paired prefix, 동일 지지 출력, 외부 정답이 함께 보존됐는지 확인한다.

지원된 오답의 빠른 종료는 정답 보존 절감과 다른 분류로 보고된다. Native ticks, selector 검사 수, proof 생성 수를 더해 총효율 숫자를 만들지 않는다.
