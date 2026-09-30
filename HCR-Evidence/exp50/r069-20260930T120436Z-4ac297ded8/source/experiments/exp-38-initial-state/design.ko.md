# EXP-38 / R057 사전 동결 설계

## 질문과 근거

R056은 initial=.5에서 두 입력의 low endpoint 및 P_prefix 삭제 효과를 확인했다.
이 결과만으로 같은 program·입력의 종착점이 초기 상태와 무관하다고 볼 수 없다.
이번에는 입력·program·config를 고정하고 전 좌표의 초기 활성도만 .1/.5/.9로 바꾼다.
비방향 대조이며 초기 상태 의존성이나 동일 결과를 실험 성공 조건으로 요구하지 않는다.

## 조건

| orientation | input pair | 실제 (e:0,e:1) drive | initial | condition ids |
|---|---|---|---|---|
| start | (1,.02) | (4,.08) | .1/.5/.9 | start_i01/start_i05/start_i09 |
| goal | (.02,1) | (.08,4) | .1/.5/.9 | goal_i01/goal_i05/goal_i09 |

각 조건에서 full/drop_P_prefix를 실행하여 12행을 만든다.
initial=.5인 4행은 R056 재현 control, 다른 initial의 8행은 새 대조다.
입력·goal drive=0·edge 총 drive=4.08은 orientation 안에서 불변이다.
orientation을 합치거나 대칭 구조로 가정하지 않는다.

R052 c001/start_edge의 공통 program을 쓰고 P_prefix(p:0:1→p:0:0)만 mask에 따라 삭제한다.
group/bias/support/link 순서·weight, default config, 동기 갱신, 최초 종료 규칙과
160 tick 예산을 보존한다. 모든 group 좌표를 같은 초기값으로 설정하며 매 분기를
새 상태에서 시작한다. 이전 분기의 최종값·history·stable counter를 전달하지 않는다.
이는 uniform 초기 상태의 단일 scalar 개입이며 좌표별 초기 상태의 역할은 분리하지 않는다.

## 측정과 판정

primary는 orientation·mask를 고정한 initial .1−.5, .9−.5의 goal/e:0/e:1 차이다.
원자료에 모든 tick의 전 좌표, residual, stable count, 종료 상태 및 단위별 cost를 보존한다.
secondary는 각 initial의 drop−full 좌표 차이와 low 술어에 대한 맥락적 링크 필요성이다.

stable_decision/stable_ambiguous이면서 goal<.5−1e-6이면 low,
goal>.5+1e-6이면 high, 나머지는 inconclusive다.
baseline과 변경 조건이 모두 low/high로 판정 가능하면 범주가 다를 때
different_stable_regimes=true, 같으면 false이며, 하나라도 inconclusive면 null이다.
nonstable 종료에서도 연속값을 보존하지만 안정 상태 간 차이라고 부르지 않는다.

full=low/drop=high일 때 low 술어에 대한 P_prefix 필요성 true,
둘 다 low면 false, 그 외에는 null이다. full이 high인 조건을 불필요성으로 처리하지 않는다.
1e-6은 공학적 판정보류 폭이지 고정점 오차·통계적 불확실성 보증이 아니다.
작은 endpoint 차이는 종료 오차와 양립하므로 별개의 고정점·attractor 증거가 아니다.
low/high 범주가 달라도 이번 유한시간 관측을 수학적 attractor 또는 basin 증명으로 확장하지 않는다.

## 출처·검증·실행 계약

spec은 R052 원본 10파일과 R056 anchor 8파일의 SHA-256을 포함한다.
anchor는 plan/source_manifest/raw_manifest/audit 및 startstrong/goalstrong의 full/drop 4 raw다.
source/spec/parents/anchors를 실행 전에 동결하고 R056 조건과 initial=.5를 결속한다.
bridge는 program·initial·drives·모든 tick/state/residual/stable·종료·counter를 비교한다.
수치 비교는 abs/rel 1e-12다. 검산기는 생성기·runtime/session/dynamics를 import하지 않고
별도 프로세스에서 independent_step으로 전 궤적·최초 종료·비용을 재계산한다.

Run-HCR-R057.cmd: 기준선·source 동결 → synthetic self-test → 별도 smoke 4행/4bridge →
최종 core regression 1회 → 연구 12행 → independent numerical audit → summary/bundle/ZIP.
R052 native replay·R056 4 trajectory replay·smoke는 연구 표본이나 연구 비용과 합산하지 않는다.
실제 연구는 한 번 실행하며 자동 retry·조건 추가·덮어쓰기는 없다.
구현 중 synthetic 검사·결함 수정은 허용하며 실제 연구 재시작은 하지 않는다.
실패하면 최초 log·traceback·부분 evidence를 보존한다.

R057 add-on·문서·index·신규 evidence만 추가한다. 기존 core/tests/manifests/raw와 기본
dispatcher EXP-30을 유지한다. 검증 후 커밋·main 병합·작업 브랜치 정리·push·원격 확인한다.

## 주장 범위

이 실험은 동일 입력·program에서 세 uniform 초기값의 유한시간 궤적과 endpoint를 비교한다.
독립 표본, basin 경계, 초기 공간 전체, 유일한 고정점, 전역 수렴, 수학적 attractor,
이력 의존적 hysteresis 또는 Circuit 학습·재사용을 입증하지 않는다.
native session/proof/support/raw decision/adoption/실제 에너지는 null이다.
외부 LLM 행동·hidden state·인간 인지·HCC 전체 가설의 직접 증거로 표현하지 않는다.
