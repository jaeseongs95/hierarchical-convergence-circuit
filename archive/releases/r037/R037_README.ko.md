# R0.3.7 / EXP-18 — 온라인 proof 채택

기준선: `b6b57589e18cc4be97cea10515f90ffbf100218f`의 `hierarchical-convergence-circuit`.
기준 결과: `HCR-Evidence/exp17/r036-first`.

## 이번 변경

EXP-17은 native readout이 나온 뒤 선택기를 사후 비교했다. EXP-18에서는 **각 readout에 적용한 선택 결과가 실제 추가 전개 또는 종료를 결정**한다. 같은 기본 입력에 `legacy/route_only × native_saved/support_first`를 적용하여 32개의 fresh native session을 실행한다.

기존 `src/hcr`, R035/R036 소스, 과거 evidence는 수정하지 않는다. `capture_candidate`가 만든 원 native 판단을 보존하고, R035 선택기의 결과를 별도의 `adoption`으로 기록한다. 이것은 **온라인 실행 정책의 추가**이며 native kernel 내부 proof 생성기를 교체한 구현은 아니다. 원 native proof 생성과 추가 선택 비용을 모두 구분해서 기록한다.

## 적용 및 실행

ZIP 안의 파일과 폴더를 기존 저장소 **루트에 그대로 병합**한다. `Run-HCR-R037.py`가 기존 `Run-HCR-R036.py`와 같은 위치에 있어야 한다. 기존 파일을 삭제하거나 R036 파일로 대체하지 않는다. R037 파일이 이미 있으면 변경 내용을 먼저 확인한다.

Python 3.12 이상에서, 저장소 루트에서 실행한다.

```powershell
python -X utf8 -B Run-HCR-R037.py --out HCR-Evidence/exp18/r037-first
```

이 명령은 기존 회귀·배포 검사, EXP-17 재검증, 신규 단위·실제 selector·native 통합 검사를 통과한 뒤에만 EXP-18의 `prepare → execute → audit → verify`를 진행한다. 첫 실패에서 중단하며 자동 retry, Git commit/push, 모델 다운로드, 네트워크 작업은 하지 않는다.

`--out`을 생략하면 시각이 들어간 새 결과 폴더를 만든다. 이미 존재하는 계획이나 결과는 덮어쓰지 않는다. 검사만 실행하려면:

```powershell
python -X utf8 -B Run-HCR-R037.py --check-only
```

`--check-only`도 검사용 native session과 독립 재생을 실행할 수 있고 실행 로그를 남긴다. 본 EXP-18의 32회 실행과 계획 동결만 생략한다.

기준 결과가 다른 위치에 있으면 `--source-run "실제 EXP-17 결과 폴더"`를 지정한다. EXP-15 폴더를 직접 지정하는 옵션이 아니다.

## 산출물

| 위치 | 내용 |
|---|---|
| `HCR-Evidence/exp18/r037-first.plan.json` | 입력·조건·예산·소스·동결 memory 출처 |
| `.../r037-first/attempts.jsonl` | native 작업과 최초 판단·선택 결과의 즉시 기록 |
| `.../r037-first/raw/tXXXX.json` | 원 native packet, 모든 readout, 선택, terminal adoption |
| `.../r037-first/source/` | 재계산을 위한 소스 snapshot |
| `.../r037-first/upstream/` | EXP-17에 보존된 EXP-15 학습 출처 복사 |
| `.../r037-first/analysis/` | 독립 audit, summary, 조건 CSV, trial별 재계산 |
| `.../r037-first/failure.json` | 실행 실패 종류와 마지막 보존 상태. 실패 시에만 생성 |
| `.../r037-first/audit_failures/` | audit 실패 기록. 실패 시에만 생성 |
| `HCR-Evidence/exp18/execution-logs/` | 단계별 표준출력과 실행 상태 |

## 검증 상태

이 배포 환경에서 신규 단위 테스트 **93개**, 기존 R035 selector를 실제 호출한 연결 테스트 **16개**가 통과했다. 단위 테스트에는 고정 seed의 200개 synthetic 경계 조합이 포함된다. 연결 테스트의 Graph 상태 역시 synthetic이며, 실제 native engine 결과가 아니다.

**전체 native 통합·기존 전체 회귀·EXP-17 전체 재검증·본 EXP-18 실행은 이 배포 환경에서 수행하지 않았다.** 실행기에 이 검사들을 포함했으며 누락된 의존성을 skip으로 처리하지 않는다. 세부 기록은 `docs/R037_ACCEPTANCE.ko.md`와 `validation/r037/`에 있다.

설계: `docs/R037_DESIGN.ko.md` / 사용법: `docs/R037_USAGE.ko.md`.
