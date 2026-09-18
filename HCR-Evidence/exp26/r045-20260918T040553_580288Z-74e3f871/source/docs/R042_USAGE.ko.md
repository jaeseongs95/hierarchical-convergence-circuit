# R042 적용 및 실행 안내

## 적용 위치

먼저 기준선 commit `11f43790c0cb1b4732199ae4fb17c5bbbed4cd5b`와 EXP-22 실행 결과가 있는 저장소를 사용한다. ZIP의 내용물을 저장소 루트에 **병합**한다. ZIP 전체를 새 프로젝트로 실행하거나 tools 폴더를 통째로 교체하지 않는다.

```text
hierarchical-convergence-circuit/
├─ Run-HCR-R041.py                    # 기존 파일 유지
├─ Run-HCR-R042.py                    # 추가
├─ Run-HCR-R042.bat                   # 추가
├─ R042_MANIFEST.json                 # 추가
├─ src/hcr/                          # 기존 파일 유지
├─ tools/r041_scheduler_direction/    # 기존 파일 유지
└─ tools/r042_id_role_isolation/      # 추가
```

원래 `tools/`, `scripts/`, `docs/`, `experiments/`, `validation/` 폴더 안에 R042 파일이 추가되는 방식이다. 기존 버전 파일은 ZIP에 포함하지 않는다.

## 가장 간단한 실행

`Run-HCR-R042.bat`를 더블클릭한다. 로컬 Python 3.12 설치 경로를 우선 사용하고, 없으면 PATH의 Python 3.12 이상을 사용한다. 설치/업데이트/다운로드는 하지 않는다.

명령행에서는 다음과 같다.

```powershell
python -X utf8 -B Run-HCR-R042.py
```

기본 parent 경로는 다음이며, 경로 이름만 믿지 않고 manifest SHA-256을 검사한다.

```text
HCR-Evidence/exp22/r041-20260917T224012_261821Z
```

다른 위치에 같은 원자료를 둔 경우:

```powershell
python -X utf8 -B Run-HCR-R042.py --source-run "D:\research\exp22\r041-20260917T224012_261821Z"
```

## 검증만 실행

```powershell
python -X utf8 -B Run-HCR-R042.py --check-only
```

이 옵션은 신규 24조건 실험을 만들지 않는다. 패키지 검사, unit tests, 기존 EXP-22 전체 재검산, 실제 native integration smoke **4조건**은 실행한다. 따라서 단순 syntax check만 수행하는 옵션은 아니다. smoke 원문은 execution-logs에 별도로 저장하며 본 연구 24조건에 합산하지 않는다.

신규 파일만 검사하고 native에 접근하지 않는 명령:

```powershell
python -X utf8 -B scripts/verify_r042.py --addon-only
```

## 수동 단계 실행

전체 launcher가 이 순서를 자동 처리하므로 일반적인 사용에서는 따로 입력할 필요가 없다. 아래 명령의 `MANUAL_RUN`은 매번 새 이름이어야 한다.

```powershell
python -X utf8 -B scripts/r042_cli.py prepare --source-run "HCR-Evidence/exp22/r041-20260917T224012_261821Z" --out "HCR-Evidence/exp23/MANUAL_RUN.plan.json"
python -X utf8 -B scripts/r042_cli.py execute --plan "HCR-Evidence/exp23/MANUAL_RUN.plan.json" --out "HCR-Evidence/exp23/MANUAL_RUN"
python -X utf8 -B scripts/r042_cli.py audit --run "HCR-Evidence/exp23/MANUAL_RUN"
python -X utf8 -B scripts/r042_cli.py verify --run "HCR-Evidence/exp23/MANUAL_RUN"
python -X utf8 -B scripts/r042_cli.py bundle --run "HCR-Evidence/exp23/MANUAL_RUN" --out "HCR-Evidence/exp23/MANUAL_RUN_evidence.zip"
```

수동 단계 실행은 launcher의 EXP-22 전체 preflight를 자동 대체하지 않는다. 필요한 parent 전체 재검산 명령은 아래다.

```powershell
python -X utf8 -B scripts/r041_cli.py verify --run "HCR-Evidence/exp22/r041-20260917T224012_261821Z"
```

## 생성되는 자료

```text
HCR-Evidence/exp23/
├─ execution-logs/<UTC timestamp>/
│  ├─ 01.log ...
│  ├─ native-selftest/               # 실제 native smoke 4조건, 본 실험 아님
│  └─ execution.json
├─ r042-<UTC timestamp>.plan.json
├─ r042-<UTC timestamp>/
│  ├─ plan.json
│  ├─ environment.json
│  ├─ source/                        # 동결된 코드 전체
│  ├─ upstream/                      # seed 및 훈련 계보
│  ├─ basis/exp22/                   # parent 고정 자료 + 회귀 raw 12개
│  ├─ attempts.jsonl                 # 첫 시도부터 append-only
│  ├─ raw/t0000.json ... t0023.json
│  ├─ manifest.json
│  └─ analysis/
│     ├─ audit.json
│     ├─ summary.json
│     ├─ summary.ko.md
│     ├─ trials.csv
│     ├─ groups.csv
│     ├─ id_role_reversal.csv
│     ├─ comparisons.csv
│     ├─ readouts.csv
│     ├─ scheduler_decisions.csv
│     ├─ records/
│     └─ manifest.json
└─ r042-<UTC timestamp>_evidence.zip
```

## 오류가 발생했을 때

최초 실패에서 중단한다. `execution-logs/.../execution.json`과 실패한 단계 로그를 먼저 확인한다. 본 실행 도중 실패했다면 `failure.json`, `attempts.jsonl`, 이미 완료된 raw가 남는다. 독립 검산 실패는 `audit_failures/`에 따로 남는다.

기존 실행을 지우고 같은 이름으로 다시 실행하지 않는다. 수정/새 실행을 해야 한다면 이전 실패 자료를 보존하고 새 실행 ID를 사용한다. 실패 폴더도 `bundle` 명령으로 묶을 수 있으며, 그 ZIP은 완료 연구 결과가 아니라 forensic evidence다.

`source hash`, `parent manifest`, `미등록 ID` 오류는 파일을 자동으로 교체하거나 reference를 추측해 고쳐 해결하지 않는다. 다른 코드/자료를 섞었는지 원인을 확인한다.

## 실행 이후

스크립트가 출력한 run 폴더와 execution log를 보존한다. Git commit/push는 실행기에서 하지 않는다. 다음 분석에서 실제 24조건 raw와 audit/verify 결과를 기준으로 판단한다.
