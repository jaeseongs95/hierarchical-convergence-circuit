# EXP-57 / R076 결과: native 선택은 바뀌지만 두 완결 경로의 전환은 아니다

## 결론

세 번의 native train과 독립 feedback 뒤 길이2·길이3 저장 pattern이 각각 형성됐고, 두 완결 경로와 추가 prefix가 최초 pool에 들어갔다. 공개 score 변화에 따라 최초 선택은 긴 완결 경로와 짧은 prefix 사이에서 바뀌었다. 짧은 완결 경로 [0,1]가 최초 선택된 조건은 없었다. 따라서 **다중 후보의 native 상태·선택 변화는 observed지만, 두 완결 경로 사이의 선택 전환은 아직 관찰되지 않았다.**

최종 정답과 채택은 여덟 평가에서 모두 True였으며 독립 world에서 정확했다. 회로 ON은 proof와 계산 궤적을 바꿨지만 kernel tick을 모든 대응 조건에서 늘렸다. 이는 이 조건의 계산 비용 감소나 일반 HCC 우위의 근거가 아니다.

## 관찰

원자료: `HCR-Evidence/exp57/r076-20261001T001633Z-cac62c3eb7`. 새 native 실행 11회는 train 3회와 evaluation 8회이고, feedback은 3회다. 1·2회 뒤 두 pattern은 pending, 3회 뒤 둘 다 strength 0.55·version 1·failures 0·active True로 compile됐다. 모든 평가의 memory는 동일하며 추가 learning·feedback·observation correction은 없었다.

최초 pool의 후보는 [0,1](길이2 완결), [2,3](길이2 prefix), [2,3,4](길이3 완결)다. 세 후보 사이의 방향성 inhibition link 여섯 개와 모든 tick/state·prior·mismatch·eligibility를 독립적으로 재계산했다. 최초 pool은 모두 stable_decision이었다. e4=-1에서 긴 완결 후보의 mismatch는 1이고 eligibility는 False였다. 다른 세 score에서는 세 후보 모두 eligible이었다.

| e4 score | ON 최초 선택 | ON proof D_DAG | OFF proof D_DAG | ON/OFF expansion | ON pool tick | ON decision tick | OFF 전체 tick |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |
| -1 | circuit prefix [2,3] | 2 | 2 | 3 / 2 | 32 | 65 | 33 |
| 0 | circuit 완결 [2,3,4] | 2 | 2 | 2 / 2 | 47 | 135 | 33 |
| 0.6 | circuit 완결 [2,3,4] | 3 | 2 | 1 / 2 | 32 | 36 | 33 |
| 1 | circuit prefix [2,3] | 3 | 2 | 2 / 2 | 35 | 36 | 33 |

OFF의 최초 선택은 모두 primitive [0]이며 최종 proof는 [0,1]였다. ON의 -1·0 조건에서는 [2,3,4]와 [0,1]을 모두 전개한 뒤 [0,1] proof를 채택했다. ON의 0.6·1 조건에서는 [2,3,4] proof를 채택했다. 최초 선택·최종 proof·terminal adoption은 다른 단계다. D_DAG의 변화는 이 외부 proof DAG의 변화이며 runtime 깊이나 사람의 사고 깊이가 아니다.

최초 pool에서 긴 완결 후보의 activation은 score -1/0/0.6/1에 각각 0.013497963562251105 / 0.9977956407311622 / 0.9944747008172594 / 0.9890539604943791이다. prior는 각각 0 / 0.8250000000000001 / 0.33000000000000007 / 0이다. score가 커질수록 선택이 단조롭게 강화된다는 관찰은 아니다. score 1에서 prefix activation은 0.9890556281224341로 긴 완결보다 약 1.67e-6 높았다.

## 해석

R071·R072의 단일 후보 threshold 구분과 R073~R075의 수식 분해를 넘어, 이번에는 새 native 형성·binding·세 후보 pool·실제 expansion을 확인했다. “score를 바꾸면 최초 선택이 바뀐다”는 동결 예측은 이 조건에서 supported다. 다만 그 선택은 prefix와 완결의 전환이므로 두 목표 완결 경로의 전환이라는 더 강한 주장으로 바꾸지 않는다.

score 0에서 긴 후보가 가장 높게 활성화되는 현상은 native uncertainty prior 증가와 양립한다. prior/evidence를 분리하지 않았으므로 prior가 유일한 원인이라고 확정하지 않는다. 정답과 채택이 같아도 중간 그래프와 proof 깊이·비용은 같지 않다는 분리는 이 장치에서 관찰됐다.

## 대안 설명

공개 score는 evidence drive·uncertainty prior를 함께 바꾸며 음수에서는 mismatch gate도 바꾼다. 길이가 다른 두 pattern, 긴 완결과 공유 edge를 가진 prefix, top-down 경로와 inhibition이 함께 작동한다. ON/OFF는 binding·pool·reuse 전체의 변화여서 inhibition의 필요성이나 독립 인과 효과를 분리하지 못한다. 결정적 slot·순서 정책도 고정했으므로 다른 배열이나 topology에 일반화할 수 없다.

## 판별 실험

다음은 같은 길이의 두 완결 경로에서 prefix 혼합을 제거하고, native config의 prior_gain을 처음부터 0으로 정해 score 효과를 묻는 별도 최소 계약이다. 동일 길이 pattern은 하나로 저장되므로 “서로 다른 저장 회로 두 개”와 “같은 저장 회로의 두 binding 후보”를 구분해야 한다. 이번 원자료의 조건이나 memory를 수정해서 그 실험으로 바꾸지 않는다. 구체적 설계·score·예측은 아직 동결·구현·실행하지 않았다.

## 현재 주장 가능한 범위

이 authored deterministic toy world에서 두 저장 pattern의 native 형성과 두 목표 완결 후보·추가 prefix의 pool 진입, joint score 개입에 따른 최초 선택·최종 proof 변화가 observed다. 여덟 조건은 통계적으로 독립된 발견 표본 여덟 개가 아니며 새 독립 표본 수는 0이다. multi-candidate inhibition의 연결과 연산은 검산했지만 인과적 필요성은 hypothesis다. 일반 학습 성능·정답률 향상·계산 효율·사람의 직관·생물학적 메커니즘은 이 결과로 주장하지 않는다. energy와 peak memory는 null이다.

독립 검산은 native journal 11개와 feedback 3개를 재생하고 pool recurrence 최대 오차 8.881784197001252e-16을 확인했다. 원자료 변조 7종과 집계 변조 8종을 거부했다. 합성 self-test는 후보 문법과 paired 입력 확인용으로 별도 보존했다. 최종 회귀·전달 결과는 `HCR-Evidence/r076-validation/delivery-verification.json`에서 확인한다.
