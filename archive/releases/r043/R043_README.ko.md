# R0.4.3 / EXP-24 — input_order ID 재명명 음성대조

기준 commit: `eedb04f90f02cf3c55693d493d33db18f96a23b5` (`main` 조회 시점).
R042 release Git blob: `3e1447a50b2e0938a10468ce428b6b76a8d28d86`.
기존 native 엔진·R041 scheduler/selector·R042·이전 evidence는 수정하지 않는 추가 패치다.

## 실행

**배포받은 `HCR_R043_EXP24_OneClick.cmd` 하나를 기존 저장소 루트에 놓고 더블클릭한다.**
압축을 수동으로 풀거나 패치/실행/집계 명령을 차례로 입력할 필요가 없다.
설치 이후 재실행 진입점은 `Run-HCR-R043.cmd`다. 명시적 재실행은 별도 timestamp로 저장된다.
`HCR_R043_EXP24_source.zip`은 검토·보관용으로 같은 소스와 검증 기록을 담는다.

Python 3.12 이상과 기존 R042 저장소·EXP22/23 evidence가 필요하다. Python 또는 패키지 설치,
모델 다운로드·변경, Ollama/LLM 호출, git fetch/pull/commit/push는 실행하지 않는다.
PowerShell ExecutionPolicy Bypass는 실행 프로세스에만 적용하며 영구 정책은 변경하지 않는다.

## 무엇을 구분하는가

EXP23에서는 ID–역할 연결을 바꾸자 min/max 비용과 측정된 궤적이 교환됐다.
이번에는 **동일 배열 순서에서 `input_order`를 고정하고 ID만 재명명**한다.
ID 배치 2 × 배열 순열 6 × scheduler 1 = **12 native 조건, 6 paired 비교**다.
서로 다른 여섯 배열 순서 사이의 불변성을 요구하는 실험이 아니다.

기존 `input_order`는 frontier의 첫 slot을 선택한다. ID로 순위를 매기지는 않지만,
view의 ID inventory 검사와 선택 결과 로그를 위한 ID 읽기는 남아 있다.
따라서 “ID를 전혀 읽지 않는 실행”으로 명명하거나 읽기 비용을 0으로 바꾸지 않는다.

주 예측은 같은 순열에서 native ticks와 측정된 canonical readout 궤적의 동일성이다.
차이가 나타나면 `falsified_in_pair`로 기록하며, **불변성·정답을 audit 통과 조건으로 강제하지 않는다.**
readout이 부족하면 `not_evaluable`로 기록한다. 이미 측정된 tick 차이는 readout 부족으로 숨기지 않는다.

## 자동 파이프라인

패키지/기준선 확인 → 충돌 없는 추가 설치 → 신규 소스 검증 → 60개 단위 검사
→ EXP22 및 EXP23 기존 raw 재검산 → native 통합 self-test 4조건
→ plan 동결 → 본 실험 12조건 → 독립 audit → 독립 재계산 verify → evidence ZIP.

native self-test 4조건과 EXP22 identity 회귀 6조건은 연구 모집단에 합산하지 않는다.
EXP23 24조건을 다시 읽는 것도 새 독립 증거로 세지 않는다.
기준 소스나 이전 raw가 다르면 자동 수정·갱신하지 않고 중단한다.

## 결과 위치

`HCR-Evidence/exp24/r043-<UTC timestamp>/analysis/summary.ko.md`

같은 run의 `paired_ID_control.csv`, `cost_differences.csv`, `trials.csv`, `readouts.csv`,
`scheduler_decisions.csv`, `audit.json`, `records/*.json`을 함께 보존한다.
원문은 `raw/*.json`, 최초 action stream은 `attempts.jsonl`에 저장된다.
전체 run을 담은 `<run>_evidence.zip`이 run 폴더 옆에 생성된다.
실행 단계 로그는 `HCR-Evidence/exp24/execution-logs/<timestamp>/`에 남는다.

오류가 나면 최초 실패에서 중단한다. `failure.json`/`audit_failures` 및 부분 raw를 유지하고,
실행 기록과 부분 evidence를 별도 `_forensic.zip`으로 묶는다. 불완전 ZIP은 성공 결과가 아니다.
기존 raw/result와 사용자 수정 파일을 덮어쓰거나 자동 retry/repair하지 않는다.

## 실제 검증 범위

이 패키지의 생성 환경에서 수행한 검사와 수행하지 못한 native 검사는
`validation/r043/검증보고서.md` 및 로그에 분리해 기록했다.
단위 fixture·오류 주입 검사는 EXP24 결과가 아니다.
