# EXP-55 / R074 결과

## 결론

고정 prior 아래 gain을 4에서 1로 낮추면 score 0.8 대비 반응이 evidence node `e:1`과 candidate node `c:0`에서 모두 커졌다. 두 node를 따로 판정한 gain 비교 예측 16개가 모두 지지됐다. 기존 evidence-only 효과가 작은 현상을 낮은 gain에서도 그대로 유지한다는 대안은 이번 gain bundle에서 지지되지 않았다. 양의 evidence 포화와 관련된 설명은 `partially-supported`로 올리되, 포화를 유일한 원인으로 확정하지 않는다.

`c:0`의 최종 상태는 여전히 약 0.9934~0.9942이며, gain1의 score 효과도 절대값 0.000072~0.000155 수준이다. evidence 반응이 커지는 것과 후보 판단이 크게 바뀌는 것을 구분해야 한다.

## 관찰

성공 근거는 `HCR-Evidence/exp55/r074-20260930T221337Z-87c1ca1866/`이다. 24개 evaluator 계산 모두 stable_decision으로 수렴했다. score 0.8 기준 차이의 부호는 두 node 모두 0.6에서 음수, 1.0에서 양수였고 baseline에서는 0이었다. 방향 예측 48개가 모두 지지됐다.

아래 배수는 동일 prior·checkpoint·score 조건에서 `|gain1 차이| / |gain4 차이|`다. M0/M1의 prior 0 조건은 숫자 입력이 같아 중복 계산이며 독립 표본이 아니다.

| prior | checkpoint | score | e:1 반응 배수 | c:0 반응 배수 | gain1의 c:0 차이 |
| --- | --- | ---: | ---: | ---: | ---: |
| 기존 고정값 0.033 | M0 | 0.6 | 14.985 | 29.892 | -0.0001342655 |
| 기존 고정값 0.033 | M0 | 1.0 | 49.925 | 80.094 | +0.0000718768 |
| 기존 고정값 0.0066 | M1 | 0.6 | 15.000 | 30.064 | -0.0001509880 |
| 기존 고정값 0.0066 | M1 | 1.0 | 49.954 | 80.334 | +0.0000806038 |
| 0 | M0 | 0.6 | 15.004 | 30.094 | -0.0001554237 |
| 0 | M0 | 1.0 | 49.961 | 80.409 | +0.0000829662 |
| 0 | M1 | 0.6 | 15.004 | 30.094 | -0.0001554237 |
| 0 | M1 | 1.0 | 49.961 | 80.409 | +0.0000829662 |

gain4에서 `e:1`은 약 0.99737~0.99989였고, gain1에서는 약 0.90422~0.95688이었다. prior 0의 여섯 checkpoint 비교에서 숫자 입력과 전체 결과·궤적이 정확히 같았다. gain4/기존 prior 고정 여섯 궤적은 R073 evidence-only 결과와 오차 0으로 대응했다.

별도 recurrence의 최대 수치 오차는 `1.4432899320127035e-15`로 동결 허용 오차 `2e-12` 이하다. raw 변조 9개와 summary 변조 5개를 모두 거부했다. 합성 장치 검사는 budget_exhausted를 측정불가로, stable_ambiguous를 별도 상태로 보존했다. 실제 계산은 gain4에서 35 evaluator iteration, gain1에서 37~40 iteration이었다. native/kernel 비용으로 해석하지 않는다.

## 해석

prior를 제거한 조건에서도 반응 배수가 커졌으므로, gain 효과를 기존 learned prior의 존재만으로 설명할 수는 없다. R073의 기존 gain4 조건에서 prior 감소가 evidence 증가보다 크게 작용했다는 결론은 그대로 보존된다. 이번 연구는 다른 gain에서 joint prior 변화의 상대 크기를 측정하지 않았으므로 그 결론을 새 조건으로 확장하지 않는다.

e:1 반응만 커지고 c:0 반응은 그대로일 것이라는 downstream 대안은 이번 조건에서 지지되지 않았다. 동시에 c:0의 절대 차이는 e:1보다 훨씬 작고 높은 활성 상태를 유지한다. 따라서 gain 감소는 점수 민감도를 높였지만, 후보 상태를 낮은 활성 영역으로 옮기는 조작으로 검증된 것은 아니다.

## 대안 설명

gain 조작은 e:1뿐 아니라 고정 score 1인 e:0의 drive도 4에서 1로 바꾼다. e0 배경, relation 입력, top_down 피드백과 각 node의 비선형 응답이 함께 새 평형을 만든다. 현재 결과는 이 gain bundle의 효과이며 e:1 자체 포화의 단독 인과 증거가 아니다.

짧은 단일 후보 toy program과 고정 초기 상태·budget만 검사했다. 여러 경쟁 후보, 다른 topology, 실제 선택·proof·정답, memory 형성·약화·학습, 안정 영역의 범위는 검증하지 않았다. checkpoint 비교도 이 prior 경로의 숫자 전달에 한정된다.

## 판별 실험

원인 분리가 연구 판단에 필요하면 e0 drive scale과 e1 drive scale을 각각 4/1로 고정한 2×2 비교를 별도 계약으로 설계할 수 있다. prior 0·동일 program·top_down·한 checkpoint·동일 initial에서 e1 score 세 점을 비교하면, 기존 동시 gain 조건과 두 혼합 조건을 분리할 수 있다. 현재 결과를 새 독립 증거로 반복 합산하지 않으며 이번 턴에는 실행하지 않았다.

## 현재 주장 가능한 범위

봉인된 authored pool 수식의 고정 prior 조건에서 evidence gain bundle 감소가 evidence·candidate node의 유한 score 반응을 키웠다고 말할 수 있다. 포화 관련 설명은 제한적으로 지지된다. 새 native 실행·학습·feedback·독립 표본은 0이고, 기존 R073 대응 6개를 새 발견 표본으로 세지 않는다. counterfactual에 native 선택·expansion·decision cost를 부여하지 않았고 에너지·peak memory는 null이다.

최초 self-test 실패는 JSON key 순서를 조건 배열 순서로 사용한 검증기 오류였다. 후속 입력 점검에서는 존재하지 않는 goal 직접 drive를 요구한 오류를 확인했다. 점검 실패 뒤 이어간 두 번째 실행은 source hash gate에서 중단됐다. 두 실패 run과 로그를 그대로 보존했으며, 장치 코드만 수정했다. 동결 설계·예측·연구 config와 부모 자료는 바꾸지 않았다. 성공 실행에서만 24개 연구 수식 계산과 최종 회귀를 수행했다.

최종 core 회귀는 성공 실행에서 정확히 1회 수행했다. 602개 중 599개 통과, 기존 symlink 환경 skip 3개이며 실패·오류·새 skip은 없다. 원본 입력·복사본·source·raw manifest·bundle·ZIP의 전체 바이트 대응도 직접 확인했다.
