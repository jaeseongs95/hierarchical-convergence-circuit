# EXP-31 / R050 실행 결과

실행: `r050-20260919T125611Z-1b3aab6370`  
구현: `r050-source-implementation-3-proof-audit`  
상태: `EXECUTED_AND_INDEPENDENTLY_VERIFIED`

## 결론

이번 동결 조건에서 동일 입력 재시작과 revision-only 개입은 실패를 회복하지 못했다.
선택된 관측 하나의 강도를 높이면 거부된 4조건 중 2조건에서 정답 채택으로 바뀌었다.
이는 실제 AdaptiveSession 경로에서 관찰한 결과이며, 독립 센서 측정이나 학습의 효과는 아니다.

## 관찰

| 개입 | 정답 채택 | 오답 채택 | 보류 | 추가 kernel ticks |
|---|---:|---:|---:|---:|
| hold | 20 | 0 | 4 | 0 |
| 동일 입력 재시작 | 20 | 0 | 4 | 250 |
| revision-only | 20 | 0 | 4 | 250 |
| 관측 강도 변경 | 22 | 0 | 2 | 326 |

24개 기준선을 공유하는 96개 분기 기록이다. 이미 채택된 20조건에서는 재시작하지 않았다.
실제로 비교한 4조건에서 P1(기준선 대 동일 입력), P2(동일 입력 대 revision-only)는
최종 상태와 tick 궤적이 모두 허용오차 1e-12 안에서 같았다.
P3(revision-only 대 강도 변경)는 4조건 모두 상태와 궤적이 달랐다.

모든 최초 거부 조건은 강도 0.02, 관계 ++였다.
top-down OFF의 c000/c002는 최초 proof 구성 실패였고 강도 변경 후 정답 채택으로 회복했다.
top-down ON의 c001/c003는 강도 변경 후에도 내부 edge 부호 충돌 1개와 support 거부가 남았다.
따라서 상태·궤적 변화 자체를 회복으로 세면 안 된다.
기존 observe_first 선택기는 최초 거부 4조건 모두 stop_no_measurement_target이었다.

## 해석과 범위

이 조건에서는 새 입력 없는 재계산이나 revision bookkeeping보다 관측 강도 변경이 결과 차이를 설명한다.
다만 하나의 고정된 chain, 빈 memory, 고정 config와 목표 선택 정책의 paired 실험이다.
네 분기는 독립 표본이 아니며 다른 문제군·초기 상태·관측 대상 정책으로 일반화하지 않는다.
같은 관측 강도 변경에도 top-down 설정에 따라 회복 여부가 달랐다는 점이 다음 판별 대상이다.
후속 실험에서 관측 대상 edge나 개입 범위를 바꾸려면 새로운 조건을 먼저 동결해야 한다.

## 구현 검증

- R050 self-test: 117개 통과, 실패·오류·skip 0.
- native smoke: 2개 기준선·8개 분기 독립 검산 통과. 연구 결과와 별도 집계.
- core regression: 602개 실행, 599개 통과, 기존 Windows symlink skip 3개, 실패·오류 0. 전체 회귀 실행은 1회.
- 본실험: 24개 기준선·96개 분기와 원자료의 독립 검산 통과.
- audit/summary/CSV/Markdown 일치 검사 통과.
- 최초 실패 evidence 193개 파일의 목록·SHA-256 동일 확인. core와 R048/R049 계약 유지.

## 근거

- [실행 결과](../../HCR-Evidence/exp31/r050-20260919T125611Z-1b3aab6370/result.json)
- [독립 검산](../../HCR-Evidence/exp31/r050-20260919T125611Z-1b3aab6370/analysis/audit.json)
- [조건별 CSV](../../HCR-Evidence/exp31/r050-20260919T125611Z-1b3aab6370/analysis/trials.csv)
- [자동 집계 보고서](../../HCR-Evidence/exp31/r050-20260919T125611Z-1b3aab6370/analysis/summary.ko.md)
- [수정 근거](HF2.ko.md)

실행 도중 커밋·push는 수행하지 않았으며, 실행 소스는 run 안에 동결돼 있다.
이후 로컬 커밋은 해당 실행의 source_manifest를 소급 변경하지 않는다.
