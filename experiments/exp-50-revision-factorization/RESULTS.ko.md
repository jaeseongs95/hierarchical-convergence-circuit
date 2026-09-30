# R069 결과: 회로 약화와 관측 교정을 나눠 확인했다

## 결론

고정된 이진 toy world에서 오답 피드백은 실제 사용된 회로를 약화했지만, 동일 관측을 받는 새 세션의 오답을 교정하지 못했다. 피드백 전후 checkpoint 모두 새 관측 e1=-1을 받으면 False 정답을 채택했다. 정상 revision도 같은 관측에서는 오답을 유지했고 새 관측에서는 정답을 채택했다.

이는 이번 조건의 checkpoint·전달 관측·revision 경로 비교다. 순수 피드백 정보 효과, 순수 세션 지속 효과와 자율 센싱의 증거는 아니다.

## 관찰

최초 donor 1개와 후속 분기 6개를 실행했다. [원자료 집계](../../HCR-Evidence/exp50/r069-20260930T120436Z-4ac297ded8/summary.json)와 [독립 검산](../../HCR-Evidence/exp50/r069-20260930T120436Z-4ac297ded8/verification.json)에 결과를 연결했다. 단일 donor와 공유 측정에 의존하는 paired 비교이며 독립 표본 7개로 세지 않는다.

최초 donor는 True를 채택했고 참조 세계에서 오답이었다. 독립 evaluator가 산출한 피드백 한 번으로 실제 재사용한 회로 strength가 0.11에서 0.022로 약화했다. native 요청은 e1 하나였다. 이상적인 toy-world 획득은 1회, fresh 전달은 3회, cached 전달은 3회였다. 물리 센서는 사용하지 않았다.

| 후속 경로 | memory | 관측 | 판단·채택 | 참조 정답 여부 | expansion / reuse / ticks |
| --- | --- | --- | --- | --- | --- |
| 새 세션 | M0 | stale +0.8 | True | 오답 | 1 / 1 / 68 |
| 새 세션 | M1 | stale +0.8 | True | 오답 | 1 / 1 / 68 |
| 새 세션 | M0 | fresh -1 | False | 정답 | 2 / 0 / 57 |
| 새 세션 | M1 | fresh -1 | False | 정답 | 2 / 0 / 57 |
| 정상 revision | M1 | stale +0.8 | True | 오답 | 2 / 0 / 33 |
| 정상 revision | M1 | fresh -1 | False | 정답 | 2 / 0 / 28 |

새 세션의 M0/M1 비교는 stale·fresh 각각에서 최종 숫자 상태와 정수 비용 카운터가 같았다. memory 문서가 변하지 않았다는 뜻은 아니다. M1 stale의 pool 결과에는 prior 0.0066, activation 약 0.993892와 eligible=True가 기록돼 있으며 약화된 회로가 다시 사용됐다.

7개 수식 재생과 16개 변조 거부를 통과했다. 원자료의 최초 판단·후속 proof/readout/adoption, 정확한 feedback/request prefix와 checkpoint를 보존했다. 합성 selftest는 참조·예측 경계 검사이며 native 연구 표본에 합산하지 않았다. 최종 회귀·source/부모/ZIP 바이트 확인은 [전달 검증](../../HCR-Evidence/r069-validation/delivery-verification.json)에 기록한다.

## 해석

실제 회로 약화가 있어도 이번 route_only·강한 관측·단일 후보 조건에서는 최종 판단을 바꾸지 않았다. 관측 score 내용 변화는 피드백 전후 checkpoint와 두 실행 경로에서 동일한 교정 결과를 냈다. “memory 변화가 있었다”와 “교정 행동이 유지됐다”를 구분해야 한다는 이전 결론을 지지한다.

정상 revision에서는 configured gate가 ON이어도 실제 회로 재사용이 비활성화된다. 새 세션보다 적은 ticks는 API 경로와 활성화 pool 차이가 함께 바뀐 결과다. 세션 이력 유지의 이점이나 총효율 우위로 일반화하지 않는다. expansion이 적은 stale 새 세션은 ticks가 오히려 더 많았다.

## 대안 설명

route_only는 학습 prior를 정답 근거로 사용하지 않는다. 회로 strength 약화가 후보 activation에 영향을 주더라도 eligibility 경계를 넘지 않아 같은 회로가 선택될 수 있다. 이번처럼 단일 후보와 강한 score를 쓰면 checkpoint 변화에 최종 readout이 민감하지 않을 수도 있다. 이 비교로 대안들의 상대 기여를 분리하지 않았다.

True 판단에 correct=False라는 이진 피드백은 이미 False라는 정답 정보를 제공한다. 따라서 fresh 관측 후 교정은 새 측정이 정답 정보를 최초로 제공했다거나 반드시 필요했다는 증거가 아니다. host는 피드백과 지정 score를 제공했으며 native가 과거 사실의 freshness conflict를 자율 비교하지 않았다.

## 판별 실험

[다음 판별 작업](NEXT.ko.md)은 먼저 같은 원자료에서 M0/M1의 pool drive·activation·eligibility·선택을 독립 재계산해 strength 변화가 어느 경계까지 전달됐는지 확인하는 것이다. 같은 원자료의 재분석을 새로운 독립 증거로 세지 않는다. 그 뒤 필요한 경우에만 후보 activation 경계를 가르는 최소 paired 조작을 별도 동결한다.

## 현재 주장 가능한 범위

- observed: 실제 사용된 회로가 오답 피드백으로 약화됐지만, 이번 동일 관측의 새 세션 판단과 비용은 유지됐다.
- observed: 피드백 전후 checkpoint 및 정상 revision에서 fresh score를 전달하면 False 정답이 채택됐다.
- observed: 동일 M1에서도 새 세션과 정상 revision은 reuse와 ticks가 달랐다. 이는 API 경로 묶음 차이다.
- unsupported: 학습 없는 자율 감지·센싱, 순수 persistence 효과, HCC 고유 우위, 일반적 기억 유지와 총효율 개선.

생산 코드와 분리된 로직·프로세스로 검산했으며 독립 연구자 실험 재현은 아니다. 설계 토론의 fresh Judge는 실행 전 정적 검토를 수행했다. 거버넌스 MCP 통합 실행은 호스트 증명 누락으로 시작되지 않았다.
