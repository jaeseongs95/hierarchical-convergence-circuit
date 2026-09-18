# R044 / EXP-25 적용·실행

## 기본 실행

`HCR_R044_EXP25_OneClick.cmd` 하나를 기존 HCR 저장소 루트에 놓고 더블클릭한다. `src/hcr`, `tools`, `R043_MANIFEST.json`, `Run-HCR-R043.py`가 있는 위치다. 소스 ZIP은 CMD에 내장되어 있어 따로 압축을 풀지 않는다. 관리자 실행이나 패키지·모델 설치는 필요하지 않다.

설치된 Python 3.12 이상과 Windows PowerShell을 사용한다. 기존 환경을 검증하고, 조건을 바꾸는 자동 설치·업데이트·모델 다운로드·Git commit/push를 하지 않는다. PowerShell ExecutionPolicy Bypass는 해당 process 실행 인자이며 영구 정책을 변경하는 명령이 아니다.

기준선 commit: `6b8ff8ab4c4858a3ab8f1a24e82b9033372133fc`.
부모 evidence: `HCR-Evidence/exp22/r041-20260917T224012_261821Z`.
직전 evidence: `HCR-Evidence/exp24/r043-20260918T002524_574380Z`.

CMD는 ZIP SHA-256 확인 후 R043 manifest와 기존 의존 source를 검사한다. 새 R044 파일만 추가한다. 같은 내용의 R044 파일은 그대로 두고, 내용이 다른 기존 파일은 강제로 덮어쓰지 않는다. 기존 raw와 result는 삭제하지 않는다.

## 자동 진행 단계

1. 설치 전 R043 source 무결성·의존성 검증 → R044 additive 설치.
2. R044 source 검사와 100개 단위·오류 주입 검사.
3. EXP-24 기존 run 전체 verify.
4. 실제 native integration 4조건 실행과 독립 검산. 본 실험 population과 분리.
5. 24조건의 plan·source·input·memory·budget 동결.
6. native 24조건 최초 실행과 원문 저장.
7. 독립 native state/proof/control/scheduler/gate audit 및 EXP-22 부모 6조건 회귀.
8. 분석 파일 재계산 verify → evidence ZIP 생성.

검사 실패는 skip하지 않는다. 6개 부모 raw를 재검산하는 것은 새 native trial 6개를 추가 실행하는 것과 다르다. 신규 본 실험 24조건 중 ON/identity 6조건을 부모와 대조한다. native integration 4조건은 별도 self-test다.

## 결과 위치

`HCR-Evidence/exp25/r044-<UTC timestamp>/`

| 경로 | 내용 |
|---|---|
| plan.json, environment.json | 사전 조건, source hashes, 실행 환경 |
| attempts.jsonl | 최초 실행 스트림 |
| raw/tNNNN.json | 각 trial의 raw native run, 원 판단, readout, 선택, 채택 |
| source/ | 실행·검산 source capsule |
| upstream/, basis/ | 동결 학습 seed와 선택한 부모 raw, EXP-24 anchor |
| analysis/summary.ko.md | 한국어 결론·관찰·해석·대안·판별 실험·주장 범위 |
| analysis/audit.json | 실행 계약·검산 상태. 효율 가설의 성공 판정과 다름 |
| analysis/paired_reuse.csv | ON−OFF 12쌍, expansion/ticks/결과 보존의 개별 예측 |
| analysis/network_costs.csv | 실제 pool/decision network별 ticks와 관련 계수 |
| analysis/expansion_actions.csv | primitive/macro/retirement, 실제·역변환 ID, span |
| analysis/cost_differences.csv | 단위별 ON−OFF 비용 차이 |
| analysis/ID_controls.csv | 같은 gate·order에서 ID 재명명 대조 |
| analysis/trials.csv, readouts.csv, scheduler_decisions.csv | 상세 수치와 기록 |
| analysis/records/tNNNN.json | state를 포함하는 평가 투영과 추가 진단 |
| analysis/claims.json | 예측 상태 및 이번 실험이 측정하지 않은 주장 |

정상 완료 ZIP: `HCR-Evidence/exp25/r044-<timestamp>_evidence.zip`.
단계 로그: `HCR-Evidence/exp25/execution-logs/<timestamp>/`.
설치·bootstrap 로그: `HCR-Evidence/deployments/r044-*/`, `r044-bootstrap-*/`.

실패하면 최초 실패에서 중단하고 traceback·완료 raw·부분 evidence를 유지한다. 가능한 경우 별도의 `_forensic.zip`을 만든다. 이 ZIP은 성공 evidence로 표시하지 않는다. 디스크 쓰기 자체가 실패하면 파일 생성을 보장할 수 없으므로 콘솔 오류도 보존해야 한다.

## 코드 검토용 ZIP

`HCR_R044_EXP25_source.zip`은 위 CMD에 내장된 동일한 추가 파일이다. 검토용이며 필수 별도 설치 파일이 아니다. 기존 `tools` 폴더를 삭제하거나 교체하지 않는다.

## 생성 환경에서의 검증 범위

생성 환경은 Linux / Python 3.13이다. 단위·계약·오류 주입·패키지 검사는 수행했으나 전체 native 저장소 의존 소스가 없어 실제 HCR 통합 및 본 실험은 수행하지 못했다. Windows CMD/PowerShell도 이 환경에서 실행하지 않았다. 세부 최초 실패와 최종 검사 기록은 `validation/r044/`에 있다. 사용자의 저장소에서 native 통합 검사를 통과해야 24조건 본 실험에 진입한다.
