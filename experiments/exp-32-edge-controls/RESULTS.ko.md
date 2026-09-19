# EXP-32 / R051 본 실험 결과

## 결론

동결된 길이 2, 관계 ++, 강도 0.02 조건에서 조작 edge 위치를 맞춰도
top-down OFF/ON의 채택 차이가 남았다. OFF에서는 edge0 또는 edge1 중 하나를
1.0으로 강화하면 모두 synthetic reference truth=True에 맞게 채택했고,
ON에서는 어느 위치를 강화해도 raw False를 유지하고 support gate에서 보류했다.
EXP-31의 차이를 조작 위치 혼재만으로 설명하는 가설은 이 조건에서 지지되지 않는다.
특정 feedback link가 원인이라는 기제 결론이나 top-down의 일반적 유해성까지 입증한 것은 아니다.

## 원자료와 검증

- 실행: `HCR-Evidence/exp32/r051-20260919T133359Z-9c4b7efe66`
- 동결 checkout: `c6e57a32a817039c6ee1d54ab3ca65aadf394744`
- 원자료: 실행 경로의 `study/baselines`, `study/raw`, `study/interventions`, `study/progress`
- 독립 검산: `analysis/audit.json`, SHA-256 `decc81a7d0aed71b7baf0e133b0620369100427b49667c0b3e4eac451e0513af`
- 결과: `EXECUTED_AND_INDEPENDENTLY_VERIFIED`, purpose=`research`
- 자체 테스트 13개 통과. 별도 implementation-validation smoke 2기준선/8기록 검산 통과.
- 최종 core 회귀 1회: 602개 실행, 599개 통과, 기존 Windows symlink skip 3개, 실패/오류/새 skip 0개.
- ZIP CRC, inventory, 봉인 manifest의 481개 파일에 대한 ZIP 내부 및 로컬 SHA-256 확인.
- 자동 retry, 코드 수정, 추가 연구 arm, 측정 호출 없이 원클릭 실행 1회로 완료했다.

## 관찰

아래는 identity 2종을 묶은 결과다. 각 셀의 두 조건은 독립 확률 표본이 아니라 이름 배치 대조다.

| TD | arm | 정답 채택 | 오답 채택 | 보류 | 추가 ticks |
|---|---|---:|---:|---:|---:|
| OFF | hold | 0 | 0 | 2 | 0 |
| OFF | revision_only | 0 | 0 | 2 | 74 |
| OFF | edge0 | 2 | 0 | 0 | 94 |
| OFF | edge1 | 2 | 0 | 0 | 88 |
| ON | hold | 0 | 0 | 2 | 0 |
| ON | revision_only | 0 | 0 | 2 | 176 |
| ON | edge0 | 0 | 0 | 2 | 120 |
| ON | edge1 | 0 | 0 | 2 | 232 |

4개 기준선에서 hold/revision_only의 최종 수치 상태와 전체 수치 궤적은 같았다.
identity 반전 8개 arm 대비도 수치 상태·궤적·채택이 같았다(허용오차 1e-12).
반면 같은 TD에서 edge0/edge1은 최종 상태와 궤적이 모두 달랐다.
따라서 채택 결과의 위치 불변성과 내부 계산의 위치 불변성을 혼동하면 안 된다.
goal의 위치 대비(edge1−edge0)는 OFF에서 +0.200130870699,
ON에서 −0.012833824338이며 차이의 차이는 −0.212964695037이다.
이는 동일 kernel의 결정론적 수치 대비이지, 독립 표본에서 추정한 통계적 효과 크기가 아니다.

| TD | 입력 score | goal activation | 내부 edge 충돌 | proof 유효 | 선택 proof support gap | raw | 채택 |
|---|---|---:|---:|---|---:|---|---|
| OFF | (0.02, 0.02) | 0.017257 | 0 | 아니오 | 0 | False | 보류 |
| OFF | (1.0, 0.02) | 0.734164 | 0 | 예 | 0 | True | True |
| OFF | (0.02, 1.0) | 0.934295 | 0 | 예 | 0 | True | True |
| ON | (0.02, 0.02) | 0.011671 | 2 | 예 | 1 | False | 보류 |
| ON | (1.0, 0.02) | 0.026117 | 1 | 예 | 1 | False | 보류 |
| ON | (0.02, 1.0) | 0.013283 | 1 | 예 | 1 | False | 보류 |

ON에서 강화한 edge는 내부 값이 0.5 이상으로 이동하지만, 남은 약한 edge는 0.5 미만이다.
edge0 강화 후 선택 proof는 slot1=False를, edge1 강화 후에는 slot0=False를 가정한다.
공개 score는 둘 다 양수이므로 해당 가정은 `sign_conflict`다.
proof의 가정하 논리 유효성과 관측 근거 충족은 별개이며, 여기서는 후자가 채택을 막는다.
OFF 기준선의 support gap=0도 proof 생성 실패가 없다는 뜻이 아니다.

## 비용

기준선은 4회만 실행했고, 추가 session은 12회다. 16개 paired record를 독립 표본 16개로 세지 않는다.
고유 기준선은 250 kernel ticks, 1,704 signal transmissions이다.
추가 실행은 784 kernel ticks, 5,248 signal transmissions, proof node 재구성 34개다.
관측 요청·측정·학습·memory write·circuit reuse는 0이며 실제 에너지는 미측정이다.
단위가 다른 counter를 합쳐 총 계산량이나 에너지 효율로 부르지 않는다.

## 해석과 주장 범위

이 실행은 고정 입력에서 top-down 스위치의 계산적 개입 효과를 분리했다.
그러나 스위치는 여러 feedback link를 동시에 바꾸므로 어느 link가 차이를 매개하는지는 미확인이다.
ON에서 충돌이 2개에서 1개로 줄어도 support gap과 보류가 남는다는 것은
내부 상태의 부분 수정과 최종 채택을 별도로 측정해야 함을 보여 준다.
현재 측정은 새 session의 직접 score 개입이며, 상태 이어가기·자율 관측·학습된 회로 수정은 아니다.
전체 HCC 가설, 인간 인지, 현실 진실, 일반적 정확도에 대한 증거로 확장하지 않는다.

결과 토론과 다음 판별 질문은 `RESULTS_DISCUSSION.ko.md`에 별도로 기록한다.
