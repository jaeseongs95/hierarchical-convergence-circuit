# R072 / EXP-53: 고정 native 선택 경계의 입력 범위

## 문제와 이전 근거

R071은 e0=1.0/e1=0.8에서 threshold 0.9940565651611166을 쓰면 M0가 circuit, M1이 primitive를 선택했고, 네 평가 모두 True 오답과 kernel ticks 68을 유지했다. [후속 지정](../exp-52-native-selection-boundary/NEXT.ko.md)에 따라 새 메커니즘 대신 기존 경계의 입력 적용 범위를 확인한다.

## 동결 조건

R071 봉인 run의 config별 native M0(4.json)/M1(5.json)을 파일 hash로 고정한다. config, signature, strength, failures, version과 feedback 이력을 그대로 읽는다. 새 training, feedback, 재서명, 관측 요청·revision 전이는 하지 않는다. 같은 topology·identity·episode_id·revision=1·route_only·budget에서 e0=1.0을 고정하고 e1=0.6/0.8/1.0만 바꾼다. score×threshold×checkpoint 3×2×2의 12개 fresh session을 실행한다.

Threshold는 default=0.55, midpoint=0.9940565651611166이다. midpoint는 기존 R070 activation에서 사후 도출한 값이며 독립 발견으로 세지 않는다. M0/M1는 순수 strength가 아닌 checkpoint bundle이다. 정확한 원자료 hash, 셀·순서·예산과 예측은 [명세](frozen_spec.json)에 실행 전에 고정한다.

## 가설과 대안

범위 가설: midpoint의 M0/M1 선택 분리가 세 score 모두에서 유지된다. 적격 셀에서 선택이 같아지면 이 제한된 grid의 불변 분리 예측을 반증한다. 일반 연속구간의 강건성은 판정하지 않는다.

수식 방향에 따른 별도 prospective 예측은 default에서 모두 circuit, midpoint에서 0.6은 모두 primitive, 0.8은 M0 circuit/M1 primitive, 1.0은 모두 circuit이다. 즉 범위 불변 가설과 입력에 따른 경계 이동 설명을 구별한다. raw 판단 True/외부 정답 False를 별도 예측하며 ticks와 다른 정수 cost는 방향 예측 없이 기록한다. 가설 성공은 구현 수용의 조건이 아니다.

score 변화는 uncertainty prior, evidence drive와 decision 근거를 함께 바꾼다. score 사이 차이를 순수 threshold 효과라 부르지 않는다. threshold 효과는 같은 score/checkpoint에서 pool program·drive·수치 궤적·안정 상태가 대응하고 mismatch=0일 때 eligibility와 실제 선택의 차이로 판정한다. host가 자연 궤적을 일치시키지 않는다.

## 검증과 판정

봉인 parent bundle/source와 native 형성·약화 recipe를 별도 검산한다. 조건 동결 뒤 self-test, 12개 native 실행, 원자료 hash, 별도 packet/formula replay, 집계 검산과 변조 거부, 기존 core 회귀 1회, source/input 보존, bundle/ZIP 저장 순서다. score 0.8 네 셀은 R071의 수치·선택·readout·정수 비용 대응을 재확인하는 반복이며 새 발견·독립 표본으로 세지 않는다.

최초 실패·부분 원자료·traceback·로그를 보존하며 자동 retry는 없다. 후보 미완료·budget termination·parent construct 미충족·pool 불안정·mismatch 또는 대응 계산 불일치는 관련 예측을 not_evaluable로 둔다. 계약/hash/원자료 검산 오류는 연구 오답과 구분한 검증 실패다. 측정 불가를 성공으로 바꾸지 않는다.

## 주장 경계와 실행

결과는 단일 후보·짧은 toy 경로의 세 점 비교다. 회로 경쟁, 학습 우위, 자율 sensing, 인간/모델 내부 기제와 HCC 고유 우위를 판정하지 않는다. D_DAG, expansions, native ticks와 각각의 정수 counter를 구분한다. 실제 energy와 peak memory는 null이다.

`Run-HCR-R072.cmd`가 기존 Python 3.12+로 전체 실험을 실행한다. 설치·모델 변경·Git 조작은 원클릭에 넣지 않는다. 기존 evidence를 덮어쓰지 않고 `HCR-Evidence/exp53/r072-*`에 새 run을 보존한다. 기본 dispatcher는 그대로 유지한다.
