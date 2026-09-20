# EXP-40 / R059 사전 동결 설계

## 질문과 이전 근거

R057은 같은 입력에서도 초기 상태에 따라 low/high 종착점이 달라짐을 관찰했고,
R058은 이 분리가 512 tick까지 지속됨을 확인했다. 교란 없이 유지되는 상태가
작은 교란 후에도 대조 궤적으로 복원되는지는 아직 측정하지 않았다.
R058 결과 보고서의 다음 실험을 이번 실행 전에 구체화한다.

## 조건과 개입

R058 goal/full의 initial=.5와 .9에서 얻은 tick 512 상태 두 개를 사용한다.
R052 c001/start_edge의 원래 full program, 순서·link·bias, goal 방향 drive
`e:0=.08, e:1=4, goal=0`, default config 및 동기 갱신식은 유지한다.
anchor 원자료 자체가 명시적 시작 입력이며 숨겨진 host correction이 아니다.
최초 종료와 R058 궤적은 수정하지 않고 출처로 보존한다.

각 출발점에서 무교란 대조 1개 및 다섯 좌표 각각의 `±1e-4` 교란 10개,
합계 22 branch를 실행한다. 각 branch는 anchor의 새 복사본에서 시작한다.
교란은 tick 0에 한 좌표에 한 번만 가하며 clipping·정규화·상태 보정은 없다.
실행 전 읽기 전용 범위 확인에서 20개 교란 모두 [0,1] 안에 있음이 확인됐다.
stable counter는 모든 branch에서 0으로 재설정하고, 동일 tick 함수로 정확히
128 추가 tick을 계산한다. 중간 안정 조건을 충족해도 조기 종료하지 않는다.
counter 재설정은 수치 상태 갱신에 영향을 주지 않는 측정 bookkeeping이다.

## 측정과 사전 판정

같은 출발점의 무교란 대조와 같은 tick에서 전 좌표 최대 절대 차이(L-infinity)를
tick 0..128에 기록한다. 마지막 16 tick(113..128) 모두 거리가 `<=1e-8`이면
유한시간 복원 `true`, 아니면 `false`다. 대조 자체의 복원 판정은 `null`이다.
기준은 실용적인 사전 tolerance이며 수치 오차 상한·통계적 유의성을 뜻하지 않는다.
최종 거리만 작고 tail에 이탈이 있으면 복원으로 세지 않는다.

secondary는 checkpoint 1/16/32/64/128 거리, 최대 거리와 초기 거리 대비 증폭률,
그 이후 끝까지 tolerance 안에 남는 최초 tick, 최종 state/residual/stable_steps다.
그 최초 tick은 미래의 무한시간 유지가 아니라 관측한 suffix에 대한 기술량이다.
goal band는 `<.5-1e-6` low, `>.5+1e-6` high, 나머지 inconclusive이며
tick 0..128의 band 유지와 대조 궤적 복원을 구분한다.
단조 거리 감소나 모든 tick에서 수축할 것을 성공 조건으로 요구하지 않는다.
복원·비복원·일시 증폭 모두 유효한 연구 결과다.

비용은 이번 22 branch의 kernel_ticks, group_updates, normalization_ops,
signal_transmissions를 단위별로 보고한다. 이전 512 tick, anchor 재생,
synthetic 검사·smoke·수치 검산 비용은 연구 비용과 합산하지 않는다.
native packet/proof/support/raw decision/adoption/실제 에너지는 null이다.

## 출처·검증과 실행 계약

기준 main은 `6ef4f80e9917e71cbcaed742b17d68482fd35c1f`다.
spec은 R052의 10개 원자료 및 R058의 plan/source manifest/raw manifest/audit와
두 full raw(총 6개)를 byte hash로 묶는다. 검산기는 R052 network 출처를 재생하고,
두 R058 anchor의 최초 종료와 512 tick까지 전체 recurrence를 별도로 재계산한다.
그 뒤 R059의 정확한 1좌표 변화·fresh state·128개 tick·residual·counter·비용을
`independent_step`으로 매 관측 state에서 다음 tick을 별도 수식으로 재계산한다.
두 부동소수점 궤적의 누적 차이를 수치 구현 오류로 혼동하지 않도록 검증된 관측
state를 다음 한 단계 검산 입력으로 쓴다. 생산기·runtime·dynamics를
import하지 않는 별도 프로세스에서 검증하고 raw에서 대조 거리·집계를 산출한다.

`Run-HCR-R059.cmd`: 기준선/source/spec/parents/anchors 동결 → synthetic self-test →
별도 implementation smoke 6개(두 출발점의 대조 및 goal ±)와 수치 검산 →
최종 core regression 1회 → 연구 22개 1회 → 별도 수치 검산 → summary/bundle/ZIP.
개발 중 synthetic 검사와 결함 수정은 허용한다. 연구 실행 후 기준·조건 변경과
추가 연구 실행은 하지 않는다. 실패 시 최초 로그·traceback·부분 evidence를 보존하며
자동 retry나 기존 결과 덮어쓰기는 없다. 가설의 성공 여부로 audit 통과를 결정하지 않는다.

범위는 R059 add-on·진입점·EXP-40 문서/index·신규 evidence다.
기존 core/tests/releases/raw와 기본 EXP-30 dispatcher를 유지한다.
검증 후 커밋·로컬 main 병합·브랜치 정리·일반 push·원격 일치를 확인한다.

## 주장 범위와 종료

고정 synthetic recurrence의 두 상태·축 방향 20개 교란·128 tick에 한정한다.
유한한 좌표별 복원은 근방의 모든 방향, basin 경계, 수학적 attractor,
무한시간 안정성 또는 학습된 Circuit을 증명하지 않는다.
LLM 내부·인간 인지·HCC 전체 가설로 확장하지 않는다.
필수 검증이 끝나면 추가 epsilon/horizon/parameter 탐색은 후속 실험으로 남긴다.
