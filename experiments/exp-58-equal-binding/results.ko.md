# EXP-58 / R077 결과: prior 없는 두 완결 binding의 native 선택 전환

## 결론

길이2 회로 하나를 native feedback으로 형성한 뒤, 같은 길이의 두 목표 완결 binding 사이에서 최초 circuit 선택과 최종 proof가 바뀌었다. e3 score가 0·0.6일 때는 S→A→G, 1일 때는 S→B→G를 선택했다. 모든 pool의 prior와 mismatch는 0이고 prefix 후보는 없었다. 따라서 **길이 차이·prefix·비영 prior 없이도 이 고정 조건에서 score가 native 경로 선택을 바꿀 수 있음이 observed**다.

여섯 평가의 정답·채택은 모두 True, `D_DAG`는 모두 2였다. ON은 expansion을 줄였지만 전체 kernel tick을 늘렸다. 정답률 향상·깊이 감소·계산 비용 감소로 해석하지 않는다.

## 관찰

원자료: `HCR-Evidence/exp58/r077-20261001T004751Z-b3e726c9fa`. native train 3회와 evaluation 6회, feedback 3회다. 첫 두 feedback 뒤 pattern은 pending, 세 번째 뒤 길이2 pattern 하나가 compile됐다. strength 0.55·version 1·failures 0·active True였다. 평가 memory는 동일하며 추가 학습·feedback·관측 교정은 없었다.

최초 pool은 같은 circuit ID의 두 완결 binding [0,1]과 [2,3]만 포함했다. 모든 후보 상태·eligibility와 두 방향 inhibition link를 검산했다. 모든 최초 pool은 stable_decision이었다. score=0에서 [2,3] activation은 0.0282763008402952로 ineligible, 나머지 다섯 ON 후보는 eligible이었다.

| e3 score | ON 최초 선택·최종 proof | OFF 최종 proof | ON/OFF expansion | ON pool/decision tick | OFF 전체 tick |
| --- | --- | --- | --- | --- | ---: |
| 0 | [e0,e1] | [e0,e1] | 1 / 2 | 34 / 33 | 33 |
| 0.6 | [e0,e1] | [e0,e1] | 1 / 2 | 32 / 33 | 33 |
| 1 | [e2,e3] | [e0,e1] | 1 / 2 | 32 / 33 | 33 |

ON 전체 tick은 67·65·65, OFF는 모두 33이다. 이들은 측정 단위가 같은 kernel tick 비교이며 wall time·전력·총 계산 효율을 대신하지 않는다. native 비용의 `candidate_circuits=2`는 두 binding 후보 검사량이다. 저장 회로 개수 1과 구분한다.

score=0.6에서는 두 activation이 정확히 같은 0.9918157251346338이고 [0,1]을 선택했다. score=1에서는 [0,1]이 0.9918156846804936, [2,3]이 0.9918239266121338로 차이는 약 8.24e-6이다. 이는 포화 구간의 작은 상태 차이이며 정답의 큰 차이나 일반적인 선택 강도로 해석하지 않는다.

## 해석

동결한 최초 선택 전환·양 끝 score의 경로 선호 예측은 이 조건에서 supported다. 하나의 저장 pattern이 다른 role/node/edge binding으로 재사용되고 그 후보 상태가 실제 expansion과 proof에 연결되는 것을 확인했다. 같은 정답과 같은 `D_DAG`에서도 proof 경로와 계산 궤적·비용은 달랐다.

EXP-57의 추가 prefix·길이 차이·prior 혼합 문제를 제거한 새 계산이다. 다만 학습/config/topology가 달라 이번 결과를 EXP-57 전환의 원인 분해로 소급하지 않는다. 이번 실험은 서로 다른 저장 회로 사이의 경쟁 검증도 아니다.

## 대안 설명

inhibition과 top-down recurrence, 고정 binding 순서·selector·scheduler가 함께 작동한다. ON/OFF는 pool·binding·reuse 전체 개입이라 inhibition의 독립 효과를 분리하지 못한다. 동률에서 앞선 binding을 선택한 한 사례만으로 순서 정책의 최적성·학습 여부를 판정할 수 없다. authored score는 센서 노이즈나 의미 이해의 측정이 아니다.

## 판별 실험

다음은 같은 memory/config·물리 graph·edge ID와 score를 유지하고 입력 edge 배열 순서만 바꾸는 paired 실험이다. 선택은 slot 번호뿐 아니라 실제 edge ID 경로로 대응한다. 동률과 비동률에서 순서 민감도가 같은지 분리하며, 이번 원자료를 변경하거나 추가 native 실행을 이번 표본으로 합산하지 않는다. 구체적 배열·예측·예산은 아직 동결하지 않았다.

## 현재 주장 가능한 범위

이 deterministic toy world에서 하나의 native 저장 pattern·두 완결 binding·prior/mismatch 0·score 개입에 따른 최초 선택과 proof 경로 변화는 observed다. 일반 HCC 우위·학습 효율·inhibition 필요성·인간/생물학적 메커니즘은 hypothesis 또는 unsupported 범위로 남는다. 독립 발견 표본은 0, energy·peak memory는 null이다.

독립 검산은 journal 9개·feedback 3개를 재생했으며 pool recurrence 최대 오차는 5.551115123125783e-16이다. 원자료 변조 7종과 집계 변조 10종을 거부했다. synthetic grammar self-test는 native 연구 실행에 포함하지 않았다. 최종 회귀와 전달 근거는 `HCR-Evidence/r077-validation/delivery-verification.json`에서 확인한다.
