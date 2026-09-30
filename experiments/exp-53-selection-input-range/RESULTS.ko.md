# R072 결과: 선택 분리는 두 점에서 유지됐고 완전 양의 입력에서는 사라졌다

## 결론

고정된 R071 memory와 threshold에서 e1=0.6/0.8은 midpoint의 M0 circuit/M1 primitive 선택 분리를 유지했다. e1=1.0에서는 M0/M1 모두 primitive를 선택해 세 점의 불변 분리 가설이 반증됐다. 모든 12개 평가에서 route_only 판단·채택은 True 오답이고 native kernel ticks는 68이었다. 선택 변화가 판단 교정이나 ticks 감소로 연결되지 않았다.

## 관찰

[동결 원자료 집계](../../HCR-Evidence/exp53/r072-20260930T140801Z-ba41410e23/summary.json), [별도 검산](../../HCR-Evidence/exp53/r072-20260930T140801Z-ba41410e23/verification.json)을 기준으로 한다. R071 config별 native M0/M1 파일·signature를 그대로 읽었으며 새 training과 feedback은 0이다. e0=1.0, topology·identity·episode_id·revision=1·route_only·budget을 고정했다.

| e1 | M0 / M1 activation | M0 / M1 prior | default 선택 M0 / M1 | midpoint 선택 M0 / M1 |
| --- | --- | --- | --- | --- |
| 0.6 | 0.9946031190005065 / 0.9939711377690879 | 0.066 / 0.0132 | circuit / circuit | circuit / primitive |
| 0.8 | 0.9942212668099926 / 0.9938918635122408 | 0.033 / 0.0066 | circuit / circuit | circuit / primitive |
| 1.0 | 0.9938074999629096 / 0.9938074999629096 | 0 / 0 | circuit / circuit | primitive / primitive |

threshold는 default 0.55와 midpoint 0.9940565651611166이다. 같은 score/checkpoint의 두 threshold에서 pool program·drive·수치 궤적·안정 상태가 대응했고 mismatch는 모두 0이었다. 여섯 threshold pair가 모두 evaluable이다. score 1.0의 M0/M1는 pool program·drive·수치 궤적까지 같았다. 다른 score의 checkpoint pair는 같은 program에서 prior와 drive·궤적이 달랐다.

circuit 선택은 expansion 1회, primitive 선택은 [0]→[1]의 2회였다. pool/decision ticks는 전 조건 35/33, 합계 68이었다. 다른 정수 counter는 집계에 따로 남겼으며 expansion 차이를 총 비용·시간·에너지 차이로 바꾸지 않는다. proof의 D_DAG는 2이고 under-assumptions-valid=True였지만, 외부 world의 e1=False와 맞지 않아 raw/adopted 정답은 아니었다.

새 native 평가는 12회로, 그중 0.8의 네 셀은 R071 반복이며 pool·decision 수치, 선택·readout·정수 비용이 모두 대응했다. 새 score 조건 평가는 8회다. 결정적 toy 조건의 반복 실행 수이며 독립 표본·독립 경계 발견으로 세지 않는다.

## 해석

기존 코드와 독립 검산의 prior 식은 `prior_gain × strength × balance × max(1−|score|)`다. 이번 두 edge에서는 e0=1.0이므로 uncertainty=1−e1이고 balance는 3/4다. e1=1.0에서 두 prior가 0이 되어 checkpoint strength 차이를 수치 drive로 전달하는 이 항이 사라졌다. 동일 pool 궤적 관찰은 이 코드 경로와 맞는다. [별도 수식 대조](../../HCR-Evidence/r072-validation/post-execution-formula-explanation.json)는 같은 원자료에 대한 후속 설명이며 새 연구 표본이 아니다.

실행 전에 기록한 'e1 증가로 circuit activation이 증가한다'는 단순 방향 예측은 틀렸다. prospective 선택 예측 중 0.6-midpoint-M0와 1.0-midpoint-M0/M1가 falsified다. observation score가 커지면 evidence drive는 커지지만 uncertainty prior는 작아진다는 두 입력의 결합을 동결 예측이 충분히 고려하지 못했다. 예측·명세를 결과에 맞춰 고치지 않았고 core 오류로 간주하지 않는다. 세 점의 불변 분리 가설도 falsified다. 한편 12개 raw 판단 True/오답 예측은 supported다.

## 대안 설명

score는 evidence drive·uncertainty prior·decision 근거를 함께 바꾸므로 score 사이 activation 감소의 순수 원인을 이번 native 조건만으로 분리하지 못했다. 동일 score의 threshold pair에서만 threshold eligibility 효과를 말한다. M0/M1는 strength·version·failures와 이력을 포함하는 checkpoint bundle이다. 단일 후보·짧은 경로·route_only가 선택 변화에도 판단·ticks가 같았던 결과와 양립한다.

## 판별 실험

[다음 작업](NEXT.ko.md)은 이 원자료의 같은 pool program에서 evidence drive와 prior를 수식 replay에서 별도로 고정하는 분해를 제안한다. native 실행, 학습 결과와 counterfactual 계산을 구분하며 새 runtime 메커니즘은 추가하지 않는다. score 1.0에서 정보 전달 항이 사라지는 설명을 먼저 검산한 뒤 새 native 실험의 필요성을 판정한다.

## 현재 주장 가능한 범위

observed: 세 사전 선택 점 중 0.6/0.8에서는 midpoint 선택 분리가 유지되고 1.0에서는 사라졌다. 모든 조건의 True 오답과 68 native ticks는 유지됐다. partially-supported: 완전 양의 입력에서 uncertainty prior가 0이 되어 checkpoint 수치 차이가 pool 입력에서 사라지는 코드 설명과 원자료가 맞는다. falsified: 이번 grid의 불변 선택 분리 및 세 prospective cell의 방향 예측. unsupported: 연속구간의 일반 강건성, 순수 strength 효과, 독립 경계 발견, 회로 경쟁·학습 우위·행동 교정 충분성·자율 sensing과 HCC 고유 우위. HCC 전체 이론의 반증으로 일반화하지 않는다.

별도 프로세스에서 생산 runtime을 import하지 않는 규칙·수식 검산을 수행했다. 독립 연구자의 외부 재현은 아니다. wall-time 효율과 실제 에너지·peak memory는 이번 실험에서 판정하지 않았다.

## 검증과 실행

원클릭 `Run-HCR-R072.cmd`에서 조건 동결, parent native lineage·config self-test, native 12회, raw hash, 독립 replay, 별도 집계 검산, core 회귀 1회와 bundle 저장을 완료했다. raw packet 변조 7종과 summary 변조 6종, cross-config load 4개를 거부했다. 기존 core 602개 중 599개가 통과했고 3개 환경 skip을 보존했다. 신규 fail/error/skip은 없다. 최종 전달의 byte·ZIP·scope·수용 검사는 [전달 검증](../../HCR-Evidence/r072-validation/delivery-verification.json)에 기록한다. 최초 연구 실행 실패와 retry는 없었으며 준비 단계의 CLI 인자 오류는 validation에 별도 보존했다.
