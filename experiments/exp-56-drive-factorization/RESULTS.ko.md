# EXP-56 / R075 결과

## 결론

R074의 gain bundle 효과에는 e1 score drive 변화와 e0 배경 drive 변화가 모두 기여했다. 이번 prior0·M0·고정 program에서는 e1 scale 감소가 c:0의 score 반응을 약 29~79배 키웠고, e0 scale 감소는 약 1.3~2.3% 키웠다. 따라서 효과가 e0 배경 변화만으로 생겼다는 설명은 이 조건에서 지지되지 않는다. e0 기여를 무시한 e1 단독 설명도 불완전하다.

포화 관련 설명은 `partially-supported`를 유지한다. e0를 고정한 비교가 e1 drive 변화의 기여를 분리했지만, 재귀 연결을 포함한 전체 수식의 반응이므로 e1 자체 포화를 유일한 원인으로 확정하지 않는다. 이 toy 수식의 추가 분해는 여기서 마치고 다음에는 native 경쟁·선택을 별도 계약으로 질문한다.

## 관찰

원자료는 `HCR-Evidence/exp56/r075-20260930T230143Z-63f9346db8/`이다. 12 evaluator 조건 모두 stable_decision으로 수렴했다. e:1·c:0 방향 예측 24개, e1 scale 비교 예측 8개, e0 배경 비교 예측 4개가 모두 지지됐다. 가설의 지지 여부와 장치 검증 통과 여부는 별도로 판정했다.

아래 배수는 동일 배경·score에서 scale1의 절대 score0.8 대비 차이를 scale4의 차이로 나눈 값이다. 각 행에서 조작한 scale 외의 입력·config는 고정했다.

| 조작 | 고정한 다른 scale | score | e:1 반응 배수 | c:0 반응 배수 |
| --- | ---: | ---: | ---: | ---: |
| e1 scale 4→1 | e0=4 | 0.6 | 14.996 | 29.428 |
| e1 scale 4→1 | e0=4 | 1.0 | 49.943 | 78.691 |
| e1 scale 4→1 | e0=1 | 0.6 | 15.001 | 29.695 |
| e1 scale 4→1 | e0=1 | 1.0 | 49.953 | 78.764 |
| e0 scale 4→1 | e1=4 | 0.6 | 1.000170 | 1.013427 |
| e0 scale 4→1 | e1=4 | 1.0 | 1.000167 | 1.020885 |
| e0 scale 4→1 | e1=1 | 0.6 | 1.000525 | 1.022617 |
| e0 scale 4→1 | e1=1 | 1.0 | 1.000368 | 1.021831 |

e:0·e:1·p:0:0·p:0:1·c:0의 상태와 차이는 summary에 각각 보존했다. c:0의 최종 활성 범위는 약 0.993434~0.993807이며 계속 높은 영역에 있다. c:0의 signed score effect interaction은 score0.6에서 −3.3681368353e-6, score1.0에서 +1.7509607929e-6이다. 따라서 이 차이는 두 scale의 독립 효과를 단순히 더한 값과 정확히 같지 않다.

동시 scale 4/4와 1/1의 여섯 궤적은 R074 prior0/M0와 오차 0으로 대응했다. 혼합 scale 여섯 개만 새 개입이고, 모두 같은 봉인 자료의 계산이다. 별도 recurrence의 최대 오차는 1.7208456881689926e-15로 허용 오차 2e-12 이하다. raw 변조 9개와 summary 변조 5개를 모두 거부했다. 합성 장치 검사는 budget_exhausted의 차이·비율·상호작용을 null로 보존하고 stable_ambiguous를 별도 상태로 유지했다. 이 검사를 연구 표본에 합산하지 않았다.

evaluator iteration은 35~40이었다. native/kernel ticks 또는 실제 실행 비용으로 해석하지 않는다.

## 해석

e0 배경을 고정한 두 비교에서 모두 e1 scale 효과가 컸으므로, R074의 반응 증가를 e0 배경 변화에만 귀속할 수 없다. e1 scale을 고정한 비교에서도 e0가 c:0 반응을 바꾸므로, e0 배경과 downstream 비선형성의 기여도 남는다. 두 기여의 크기는 이 score 범위·초기 상태·program에 한정된 유한 차이다.

R073의 기존 gain4 조건에서 learned prior 감소가 evidence 증가보다 크게 작용했다는 결론은 바꾸지 않는다. 이번 prior0 개입은 그 prior 효과를 새 조건에서 재측정한 것이 아니다. R074의 포화 관련 설명을 제한적으로 더 분리했으며, evidence 반응의 증가가 실제 판단 변화나 학습 개선을 뜻하지는 않는다.

## 대안 설명

relation node, self excitation, inhibition, top_down 피드백과 damping이 함께 평형을 만든다. 재귀 경로의 구체적 기여, 다른 초기 상태·topology·prior, 여러 경쟁 후보의 선택은 이번 실험에서 분리하지 않았다. c:0의 높은 상태와 작은 절대 차이는 여전히 실제 선택에 대한 효과를 보장하지 않는다.

## 판별 실험

다음 후보는 같은 목표에 유효하게 binding된 두 native 회로를 구성하고, 한 경로의 공개 evidence score를 바꿀 때 최초 pool 상태·경쟁·선택·proof/readout·terminal adoption이 실제로 달라지는지 비교하는 것이다. 기존 단일 후보의 threshold 통과만으로 경쟁을 주장하지 않는다. 새 조건·memory provenance·예측·판정 기준은 실행 전에 별도로 동결한다. 이번 턴에는 그 native 실험을 구현하거나 실행하지 않았다.

## 현재 주장 가능한 범위

봉인된 authored pool 수식의 prior0·M0 조건에서 e0 배경과 e1 score drive가 candidate의 유한 score 반응에 각각 기여하며, 이 조건에서는 e1 scale 효과가 더 컸다고 말할 수 있다. 전역 안정성·학습·hidden state·인간 인지의 증거로 확장하지 않는다.

새 native 실행·training·feedback·독립 표본은 0이다. 기존 대응 여섯 조건도 새 독립 증거로 합산하지 않는다. counterfactual의 native 선택·expansion·decision cost와 실제 에너지·peak memory는 null이다. core 회귀·bundle 바이트 대응과 Git 전달의 최종 근거는 이 실험의 ORCHESTRATION 문서와 `HCR-Evidence/r075-validation/`에 연결한다.

최종 core 회귀는 1회 수행했고 602개 중 599개 통과, 기존 환경 skip 3개였다. 실패·오류·새 skip은 없다. 원본/복사 입력, 봉인 source, raw manifest, bundle과 ZIP 바이트 대응을 확인했다. 실행 후 EXP-56을 추가한 현재 색인은 봉인 source 안의 이전 색인과 구분해 검사했고, 계산 소스와 봉인 evidence는 변경하지 않았다. 최초 전달 검사에서 발견한 색인 차이와 원인 진단을 보존했다.
