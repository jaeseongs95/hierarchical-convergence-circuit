# R037 실행·보존 안내

## 권장 실행

기준 저장소의 기존 파일은 유지하고 신규 ZIP의 폴더를 루트에 병합한다. 루트에는 `src`, `tools`, `scripts`, `HCR-Evidence`, 기존 R036 실행기와 새 R037 실행기가 함께 있어야 한다.

```powershell
python -X utf8 -B Run-HCR-R037.py --out HCR-Evidence/exp18/r037-first
```

자동으로 수행하는 단계는 기존 release/R034/R035/R036 배포 검증, 기존 회귀 검사, 기존 EXP-17 전체 독립 재검증, R037의 단위 검사·기존 selector 연결 검사·실제 native 통합 검사, 마지막으로 본 EXP-18의 동결/실행/audit/verify다. 검사용 native 실행은 본 실험 32회와 다른 단계이며 본 summary에 합산하지 않는다.

이미 `r037-first` 또는 `r037-first.plan.json`이 존재하면 중단한다. 최초 실행이 실패했어도 지우거나 덮어쓰지 말고 원자료와 실행 로그를 보존한다. 수정 후 새 이름을 사용한다. `--out`을 생략하면 매번 고유 시각 이름을 사용한다. 이는 사용자가 새 실행을 요청하는 것이며 프로그램의 자동 retry가 아니다.

```powershell
python -X utf8 -B Run-HCR-R037.py --check-only
python -X utf8 -B Run-HCR-R037.py --source-run "D:\실제저장위치\exp17\r036-first"
```

`--check-only`는 무계산 dry-run이 아니다. 회귀·native self-test·독립 replay를 수행하고 로그를 남기되 본 EXP-18의 계획 생성과 32회 실험만 하지 않는다.

## 단계별 수동 실행

아래는 동결과 실제 실행을 분리해서 진행할 때의 명령이다. 권장 통합 실행기는 사전 회귀 검사를 강제하지만, 이 개별 명령들은 이전 단계 전체를 대신하지 않는다.

```powershell
python -X utf8 -B scripts/verify_r037.py
python -X utf8 -B scripts/r037_cli.py prepare --source-run HCR-Evidence/exp17/r036-first --out HCR-Evidence/exp18/r037-first.plan.json
python -X utf8 -B scripts/r037_cli.py execute --plan HCR-Evidence/exp18/r037-first.plan.json --out HCR-Evidence/exp18/r037-first
python -X utf8 -B scripts/r037_cli.py audit --run HCR-Evidence/exp18/r037-first
python -X utf8 -B scripts/r037_cli.py verify --run HCR-Evidence/exp18/r037-first
```

`prepare`는 입력·예산·소스 hash·memory 출처를 동결한다. `execute`는 원자료만 만들고 독립 검증 완료라고 판정하지 않는다. `audit`는 원자료 전체로 analysis를 새로 만든다. `verify`는 다시 계산해 저장된 analysis 및 manifest와 일치하는지 확인한다.

이미 analysis가 있으면 `audit`로 덮어쓰지 않는다. 같은 결과 재검산은 `verify`를 사용한다. 본 소스나 의존성이 동결 이후 바뀌면 실행/검산이 중단된다. 과거 결과는 당시 commit 및 보존된 source snapshot 기준으로 검산해야 한다.

## 결과에서 먼저 볼 항목

`analysis/summary.ko.md`에서 terminal adoption과 최초/마지막 readout을 구분한다. `analysis/summary.json`의 paired 비교에는 첫 view 일치, 공통 readout prefix, 정책별 채택값·종료 사유·native ticks가 있다. trial별 상세 records에는 원 native 값, 선택값, 두 proof의 D_DAG와 가정, 지지 경로 및 활성화 적격 여부가 있다.

`stop_supported_policy`는 관측 지지 계약을 만족하는 출력을 채택했다는 뜻이지 외부 정답의 보증이 아니다. `stop_frontier_exhausted`도 단순 성공/오답 대신 보류 원인과 함께 해석한다. `stop_initial_budget`, `stop_compute_budget`, `stop_selection_budget`, `stop_engine_failure`는 별개로 보존된다.

커밋할 결과의 기본 범위는 새 plan, 새 run의 raw/manifest/source/upstream/basis/analysis와 해당 execution-logs다. 저장소의 ignore 규칙 때문에 일부가 빠질 수 있으므로 `git status`에서 실제 추적 대상을 확인한다. 이 프로그램은 Git index나 설정을 수정하지 않는다.

## 파일 역할

| 경로 | 역할 |
|---|---|
| `runtime.py` / `backend.py` | 기존 native session에 온라인 채택 제어 연결 |
| `contracts.py` / `spec.py` | 허용 입력, 예산, 32회 실험 조건 |
| `sources.py` / `protocol.py` / `io.py` | 기준선 검사, 조건 동결, 단회 실행, 원문·실패 보존 |
| `control_audit.py` | 생산 제어기를 호출하지 않는 action/예산 재계산 |
| `audit.py` | 기존 native/선택기 auditor 연결, 외부 평가, 원자료·분석 검증 |
| `reporting.py` | 표본·시점·비용 단위를 분리한 보고 |
| `tests/` | 의존성 없이 실행 가능한 단위·synthetic 계약 검사 |
| `selector_tests/` | 실제 기존 R035 selector와 신규 제어기의 연결 검사. Graph는 synthetic |
| `native_tests/` | 저장소의 실제 native engine + EXP-17 기준선 통합 검사 |
| `validation/r037/` | 이 배포 환경에서 실제 수행한 검사 로그 |
