# R067 결과: 같은 횟수의 관측도 새 정보인지에 따라 결과가 다르다

## 결론

e0를 고정한 이번 두-edge toy 조건에서, 현재 e1 관측을 한 번 제공하면 서로 다른 두 세계를 올바르게 구별했다. 낡은 관측을 한 번 더 제공하거나 과거 사실만 쓰면 두 세계에 같은 답을 냈다. 최초 conflict는 두 세계 모두에서 같았으므로 세계 변화의 충분한 신호가 아니었다.

회로 ON/OFF와 동일 정보를 받은 단순 baseline 모두에서 이 구분이 나타났다. 결과는 명시적 정보 갱신의 효과를 지지하며 native HCC의 자율 관측이나 고유 성능 이점을 입증하지 않는다.

## 관찰

실행: [r067-20260920T063020Z-db2c8e7392](../../HCR-Evidence/exp48/r067-20260920T063020Z-db2c8e7392/summary.json). 두 세계 × 세 군 × 두 gate의 12조건에서 최초·후속 판단을 각각 저장했다. 새 frozen native 실행 24회, 새 학습 0회다. 대응 조건이며 독립 표본 24개가 아니다.

e0 score는 모든 입력에서 +0.8이었다. e1 최초 score는 +0.8, 과거 사실은 False로 동일했다. 두 세계의 context·epoch·원관측·memory·config가 같았고 비공개 e1 truth만 달랐다. 최초 판단은 12조건 모두 True였으며 모든 최초·후속 readout은 채택됐다.

| 후속 처리군 | A: 현재 e1=False | B: 현재 e1=True | 실제 추가 관측 |
| --- | --- | --- | ---: |
| 과거 사실 | False, 정답 | False, 오답 | 0 |
| 낡은 관측 재제공 | True, 오답 | True, 정답 | 1 |
| 현재 관측 제공 | False, 정답 | True, 정답 | 1 |

표는 ON/OFF에서 같았다. 특히 stale/fresh는 같은 요청 edge와 한 번의 호출 조건이지만 결과가 달랐다. history도 예산 상한은 1이지만 호출은 0이므로 세 군의 실제 관측 비용이 모두 같다고 해석하지 않는다.

명시적 controller는 8개 응답을 소비했다. 이 중 현재 toy sensor 측정은 4개, stale 재제공은 4개다. 반복된 두 세계·gate 조건의 호출 수이며 독립 정보원 수가 아니다. 각 조건의 사실 조회·conflict 비교는 1회, fresh의 사실 값 기록은 1회였다. native observation request는 모든 실행에서 0회다.

fresh 입력은 새 사실표를 읽지 않고 응답에서 직접 만든다. 네 fresh 조건에서 사실표의 유효 시점 1과 응답 provenance를 저장했지만, 이 표를 다음 에피소드에 조회하는 유지 실험은 하지 않았다. 실제 시계 시간이 아닌 동결된 논리 시점 -1/0/1이다.

후속 판단의 대표 native 비용:

| e1 입력 | gate | expansion | circuit reuse | kernel ticks | binding checks |
| --- | --- | ---: | ---: | ---: | ---: |
| -1: history 및 A/fresh | OFF | 2 | 0 | 28 | 0 |
| -1: history 및 A/fresh | ON | 2 | 0 | 57 | 6 |
| +0.8: stale | OFF | 2 | 0 | 33 | 0 |
| +0.8: stale | ON | 1 | 1 | 68 | 4 |
| +1: B/fresh | OFF | 2 | 0 | 33 | 0 |
| +1: B/fresh | ON | 1 | 1 | 68 | 4 |

같은 입력의 단순 AND/sign baseline도 fresh 네 조건에서 모두 정답이었다. baseline은 두 edge 검사, native는 ticks·expansion·binding 등을 각각 기록했다. 단위가 다르므로 합산하지 않았고, energy·peak memory·정보 entropy는 측정하지 않았다.

## 해석

R066의 e0/e1 동시 변경 한계를 제거해, e0가 동일할 때 e1 입력만 바꿔도 이 과제의 교정과 세계 구별이 가능함을 관찰했다. 과거의 정확한 사실과 현재의 낡은 관측 사이의 conflict 자체는 어느 쪽이 현재 맞는지 알려주지 않았다. 새 관측이 양립 가능한 세계를 구별하는 입력을 제공했다.

음성 교정에서는 회로 reuse가 0이었고, 회로 ON은 OFF보다 ticks가 컸다. 양성 조건에서는 expansion이 감소했지만 ticks는 증가했다. 이번 결과에서도 계산 효율 개선을 주장할 수 없다.

## 대안 설명

fresh sensor의 정확성은 설계로 보장한 조건이다. 새로운 시점의 관측이라서 항상 참인 것은 아니며 센서 오류·지연·잘못된 provenance는 연구 조건으로 시험하지 않았다. 따라서 효과는 신뢰할 수 있는 정보의 명시적 입력 제공으로 설명되며, 학습이나 freshness 추론이 필요했다는 결론은 나오지 않는다.

controller는 요청 edge를 미리 알고 있었다. 관측 서비스는 응답을 사전 생성하고 worker가 최초 판단 저장 뒤 읽었다. 온라인 능동적 edge 선택이나 자율 conflict detection의 성능은 측정하지 않았다. 후속 판단도 최초 세션의 지속 실행이 아니라 같은 memory로 새로 시작한 native session이다.

## 판별 실험

다음 과제는 외부 controller가 요청을 정하지 않을 때 기존 native request 경로가 이 conflict를 관측 요구로 연결하는지 확인하는 것이다. 먼저 현재 API와 상태 전이를 조사하고, 정보가 native에 노출되는 조건을 맞춘 최소 비교를 동결한다. 상세 경계는 [NEXT.ko.md](NEXT.ko.md)에 적었다.

## 현재 주장 가능한 범위

- `observed`: 고정된 toy 조건에서 e1만의 현재 정보 갱신은 두 세계의 정답을 구별했고, 동일한 낡은 정보를 다시 제시하는 것은 구별하지 못했다.
- `partially-supported`: 충돌 이후 교정에는 사용할 수 있는 구별 정보가 중요하다는 설명을 지지한다. 모든 종류의 추론에 관한 일반적 필요조건은 아니다.
- `unsupported`: native 자율 정보 획득, sensor 신뢰 학습, 장기 기억 유지, 일반화, HCC 고유 우위 및 총 효율 향상.

24개 native 수식 replay, 합성 경계 검사 11개, 변조 16개 거부를 확인했다. 생산 코드와 분리된 검산 로직·프로세스이며 독립 연구자 감사는 아니다. 최종 회귀·bundle·기존 파일 보존은 [전달 검증](../../HCR-Evidence/r067-validation/delivery-verification.json)에서 확인한다.
