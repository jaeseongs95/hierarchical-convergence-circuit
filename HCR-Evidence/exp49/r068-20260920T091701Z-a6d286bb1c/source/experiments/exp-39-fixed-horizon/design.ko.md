# EXP-39 / R058 사전 동결 설계

## 질문과 근거

R057은 동일 입력·program에서 initial=.1/.5와 .9가 서로 다른 안정 low/high 범주로
종료되는 세 대조를 확인했다. 이 분리가 최초 종료 뒤에도 유지되는지 아직 측정하지 않았다.
이번에는 같은 12조건을 tick 512까지 계산해 유한시간 지속성을 조사한다.
분리의 유지와 소멸 모두 결과이며, 특정 방향을 구현 검증 성공 조건으로 요구하지 않는다.

## 조건과 개입

R057의 start=(4,.08), goal=(.08,4) drive, uniform initial=.1/.5/.9,
full/drop_P_prefix의 12조건을 그대로 쓴다. 공통 program은 R052 c001/start_edge다.
program·bias·link 순서/weight·drives·initial·default config·동기 갱신식은 불변이다.
config.max_ticks=160도 기존 최초 종료 판정을 위해 유지한다.

먼저 기존 settle로 최초 종료를 얻고 전 궤적·상태·종료 이유·counter를 marker로 보존한다.
그다음 같은 상태·stable counter에서 tick 함수를 이어 실행해 총 512 tick에 도달한다.
상태와 안정 counter를 재설정하지 않는다. core 코드를 바꾸지 않고 add-on에서 중단만 해제한다.
원래 oscillator 또는 budget termination이더라도 최초 이유는 그대로 보존한다.
연장 후 상태를 새로운 native decision 또는 최초 성공으로 바꾸지 않는다.

연장은 명시적 intervention이며 기존 160 tick 예산 실험과 구분한다.
12개 branch의 최초 종료까지가 재현 prefix이고 이후 tick만 새 continuation 관측이다.
한 branch를 prefix와 suffix 두 독립 표본으로 세지 않는다.

## 사전 측정과 판정

primary는 marker와 tick 160/512의 전 좌표·goal·residual·stable_steps 및 goal 범주다.
marker는 원래 종료 상태가 stable_decision/stable_ambiguous일 때만 안정 범주를 판정한다.
고정 tick의 stable_at_checkpoint는 누적 stable_steps>=patience로 판정하며,
이를 새로운 first termination 또는 native outcome으로 부르지 않는다.
goal<.5−1e-6은 low, goal>.5+1e-6은 high, 그 사이는 inconclusive다.
checkpoint가 안정 조건을 충족하지 않으면 stable_regime은 inconclusive다.

marker가 안정 low/high인 경우 marker 직후부터 512까지 모든 tick의 goal band를 비교한다.
같은 band를 유지하면 postmarker_band_preserved=true, 한 번이라도 벗어나면 false다.
marker가 판정 불가면 null이다. 불일치 tick 수와 최초 불일치 tick도 보존한다.
이 band 검사는 매 tick의 안정성 주장과 구분한다. 연장 구간의 최대 residual,
marker 대비 전 좌표 최대 절대 변화량, 최소 stable_steps를 함께 보고한다.

secondary는 marker/160/512 각각에서 initial .1−.5, .9−.5의 goal/e:0/e:1 차이와
각 initial의 drop−full 차이다. 두 orientation을 합치지 않는다.
필요성은 full low/drop high일 때 true, 둘 다 low면 false, 나머지 null인 기존 맥락적 술어다.
1e-6은 판정보류 폭이며 오차 보증이나 통계 한계가 아니다. 종료 뒤의 작은 움직임을
고정점 차이나 새 attractor로 해석하지 않는다.

비용은 최초 종료 cost, 추가 continuation cost, total cost를 분리한다.
단위별 counter만 각각 합산하며 host 처리·wall time·실제 에너지를 kernel ticks로 대체하지 않는다.
tick 512 이후를 추정하거나 결과를 본 뒤 horizon을 늘리지 않는다.

## 출처·검증·실행 계약

spec에 R052 원본 10파일 및 R057 anchor 16파일(plan/source/raw manifest/audit와 12 raw)을 동결한다.
생산기는 anchor 결과를 실행 입력으로 사용하지 않으며 R052 network와 사전 조건만 읽는다.
검산기는 R057 verify_record로 원래 최초 종료까지 독립 재계산한 뒤,
independent_step으로 연장 구간의 모든 tick/state/residual/stable count·cost를 재계산한다.
생산기/runtime/session/dynamics import는 audit 프로세스에서 금지한다.
전체 재구성 prefix packet을 R057 anchor와 abs/rel 1e-12로 비교한다.
기존 source·manifest·원자료를 재봉인하거나 수정하지 않는다.

Run-HCR-R058.cmd: 기준선·source/spec/parents/anchors 동결 → synthetic 검사 →
initial=.5 두 방향×두 mask의 별도 smoke 4행/4bridge → 최종 core regression 1회 →
연구 12행/12bridge → 수치 audit → summary/bundle/ZIP.
R052 및 R057 출처 replay와 smoke는 연구 증거·비용에 합산하지 않는다.
개발 중 synthetic 검사·결함 수정은 허용하며 실제 연구는 한 번만 실행한다.
자동 retry·기존 파일 덮어쓰기·조건 추가는 없다. 실패하면 최초 log·traceback·부분 evidence를 보존한다.

변경 범위는 R058 add-on·진입점·EXP-39 문서/index·신규 evidence다.
기존 core/tests/manifest/raw와 기본 dispatcher EXP-30을 유지한다.
검증 후 커밋·main 병합·작업 브랜치 정리·origin/main push·원격 확인을 수행한다.

## 주장 범위

tick 512까지의 상태 지속성은 무한시간 안정성, 수학적 attractor, basin 경계 또는
hysteresis의 증명이 아니다. native packet/proof/support/raw decision/adoption/실제 에너지는 null이다.
LLM 내부·인간 인지·학습된 Circuit 형성·재사용·HCC 전체 가설의 직접 증거로 확장하지 않는다.
