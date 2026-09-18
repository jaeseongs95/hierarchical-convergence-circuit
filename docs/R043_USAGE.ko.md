# R043 실행 및 파일 안내

## 일반 실행

`HCR_R043_EXP24_OneClick.cmd`를 기존 저장소 루트( `src`, `tools`, `R042_MANIFEST.json`이 있는 곳)에
저장한 뒤 더블클릭한다. 자체 포함 ZIP을 검증하고 새 R043 파일만 설치한 다음 전체 파이프라인을 실행한다.
검토용 ZIP을 따로 받을 필요는 없다. 설치 후에는 `Run-HCR-R043.cmd`도 전체 실행 진입점이다.

설치된 R043 파일이 같은 내용이면 재사용한다. 사용자 수정과 충돌하면 덮어쓰지 않는다.
이전 R042 및 그 의존 소스의 checksum이 다르면 어느 버전으로 고쳐야 할지 추측하지 않고 중단한다.
Git HEAD가 추가 문서/결과 commit으로 움직여도 동결 소스가 같으면 실행할 수 있다.
실제 HEAD는 environment.json에 기록되며, 이 도구가 git 상태를 바꾸지 않는다.

## 자동 탐색하는 이전 결과

EXP22: `HCR-Evidence/exp22/r041-20260917T224012_261821Z`
EXP23: `HCR-Evidence/exp23/r042-20260917T233524_872976Z`

둘 다 동결된 manifest hash를 검사한다. 임의의 최신 run을 골라 대체하지 않는다.
폴더를 다른 곳에 보관한 경우에만 설치 후 Python 진입점에 경로를 명시할 수 있다.
일반 실행에는 아래 옵션을 직접 입력할 필요가 없다.

```powershell
python -X utf8 -B Run-HCR-R043.py --source-run "<EXP22 folder>" --prior-run "<EXP23 folder>"
```

`--check-only`는 기존 raw 검산과 native self-test까지 수행하며 본 실험을 실행하지 않는다.
명시적 `--out`은 이전 evidence나 execution-log 폴더와 겹칠 수 없고 기존 폴더를 덮어쓸 수 없다.

## 보고서 읽기

`paired_ID_control.csv`: 6쌍의 tick/궤적/지원 signature/최초 divergence 및 판정.
`cost_differences.csv`: 단위별 count 차이. 미측정값은 null/빈 cell이며 0으로 대체하지 않는다.
`trials.csv`: 12조건 결과, 채택 여부, classification, D_DAG, 개별 비용, 실제 wall time.
`readouts.csv`: readout별 native 판단과 policy 채택, 지원 경로의 출현 시점.
`scheduler_decisions.csv`: 선두 slot 결정, native ID와 evaluator canonical ID, 실제 ID 읽기 count.
`records/*.json`: 상태 투영까지 포함한 검산 record. CSV는 이를 요약한 보조 자료다.
`audit.json`: 입력 분리, seed/state/proof 검산, identity 회귀 상태.

## 실패

종료 코드 0만 전체 파이프라인 완료다. 불변성 예측이 실패해도 실행·검산이 정상이라면 종료 코드는 0이다.
반대로 환경·schema·reference·runtime·audit가 실패하면 비영 종료 코드와 최초 failure를 남긴다.
`execution-logs`의 단계 로그 및 execution.json, run의 failure.json/audit_failures를 확인한다.
실패를 skip하거나 자동 재시도하지 않는다. `_forensic.zip`은 불완전 상태 보존용이고 정상 evidence와 별개다.
설치 단계 오류는 `HCR-Evidence/deployments/r043-*`에 기록된다.

## 구현 구조

`tools/r043_input_order_control/spec.py`, `transform.py`: 생산 입력/조건 구성.
`input_audit.py`, `policy_audit.py`, `audit.py`, `baseline_audit.py`: 독립 검산 및 회귀.
`runtime.py`: 기존 native worker에 공개 입력만 전달하는 어댑터.
`protocol.py`, `sources.py`, `storage.py`: 동결/계보/원문 보존/단회 실행.
`trajectory.py`, `reporting.py`: evaluator-only 투영과 조건별 결과 집계.
`scripts/install_r043.py`, `bootstrap_r043.ps1`, `Run-HCR-R043.py`: 원클릭 설치/실행.
`tests`, `native_tests`: synthetic 단위 검사와 실제 native 연동 검사를 분리한다.
