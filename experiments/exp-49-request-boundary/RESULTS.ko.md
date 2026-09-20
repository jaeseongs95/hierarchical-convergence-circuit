# R068 결과: 기존 native 요청은 외부 오답 피드백에 의존한다

## 결론

현재 구현은 R067의 과거 사실–현재 관측 conflict만으로 관측을 요청하는 경로를 제공하지 않는다. 같은 입력·memory에서 frozen_eval/adapt와 circuit OFF/ON 네 조건 모두 자동 요청이 없었으며, 피드백 없이 request_revision을 호출하면 계약 오류로 거부됐다.

이는 현재 API의 진입 조건을 확인한 결과다. 과거 사실과 freshness 정보가 native에 노출되지 않으므로, controller와 동일 정보를 가진 자율 관측 정책의 성능 비교는 **측정 불가**다. HCC 전체 이론의 반증이나 자율 능력 점수 0을 뜻하지 않는다.

## 관찰

실행: [원자료와 집계](../../HCR-Evidence/exp49/r068-20260920T091750Z-4ee71c2983/summary.json). 네 native 세션을 두 참조 세계에 각각 채점했다. 참조 세계 A/B를 별도 실행이나 독립 표본으로 세지 않았다.

| mode | circuit | 최초 판단 / 채택 | 자동 요청 | 명시적 API 결과 | expansion / reuse / ticks |
| --- | --- | --- | ---: | --- | --- |
| frozen_eval | OFF | True / 채택 | 0 | 외부 오답 피드백 없음으로 거부 | 2 / 0 / 33 |
| frozen_eval | ON | True / 채택 | 0 | 외부 오답 피드백 없음으로 거부 | 1 / 1 / 68 |
| adapt | OFF | True / 채택 | 0 | 외부 오답 피드백 없음으로 거부 | 2 / 0 / 33 |
| adapt | ON | True / 채택 | 0 | 외부 오답 피드백 없음으로 거부 | 1 / 1 / 68 |

연구 조건에서 API 호출은 4회, 실제 observation request·측정·피드백·학습은 각각 0회였다. 거부 전후 packet은 완전히 같았다. 네 판단은 A(e1=False)에서는 오답, B(e1=True)에서는 정답이다. 관측이 같은 두 세계에 같은 판단을 내린 결과이며 새로운 세계 식별 증거가 아니다.

별도 합성 검사 10개를 수행했다. 오답 피드백과 약한 두 edge를 주면 e0/e1 모두 요청했다. e0=1로 고정한 단일 후보 fixture에서는 e1을 요청했고, e1=-1 응답 뒤 같은 세션 revision이 True에서 False로 바뀌었다. 이 조건은 외부 피드백으로 memory도 갱신하며 연구 네 조건에 합산하지 않았다. frozen 피드백, correct 피드백 후 요청, 중복 pending, 미요청 edge 변경의 거부도 확인했다. strong edge·train mode·재전개 비활성에서는 요청이 없었다. 예산 0은 runtime 조건이 아니라 설정 단계에서 거부됐다.

첫 원클릭 실행은 합성 예산 0을 유효 설정으로 가정한 테스트 오류로 중단됐다. [첫 실패](../../HCR-Evidence/exp49/r068-20260920T091701Z-a6d286bb1c/failure.json)와 부분 packet을 보존했다. 해당 fixture를 설정 거부 검사로 고쳤으며 이 실패에서 연구 native 실행과 회귀시험은 시작되지 않았다. 새 실행에서 네 연구 조건·10개 합성 검사·11개 변조 거부를 검산했다. source·부모 evidence·bundle 및 최종 회귀는 [전달 검증](../../HCR-Evidence/r068-validation/delivery-verification.json)에 연결한다.

## 해석

R067의 explicit controller 요청과 기존 native request_revision은 다른 정보 계약이다. 전자는 host가 과거 사실과 현재 관측을 비교하고 e1을 미리 지정했다. 후자는 외부가 최초 판단이 틀렸다고 알려 준 뒤 약한 edge 집합을 반환한다. API를 host가 호출해야 하므로 여기서 반환된 요청도 자체 실행되는 sensing loop의 증거는 아니다.

합성 revision은 이미 구현된 교정 경로의 작동 확인이다. 외부 error feedback이 추가 정보와 학습 개입을 제공하므로, 이 결과로 자율 conflict detection이나 학습 없는 정보 획득을 주장할 수 없다. 회로 ON의 expansion 감소와 ticks 증가는 비용 단위를 나눠 해석해야 한다.

## 대안 설명

요청 부재는 관측 정책이 올바른 edge 선택에 실패해서가 아니라, 선행 피드백이 없어 API가 실행을 거부한 것으로 설명된다. native 입력에 과거 사실과 valid_at이 없는 표현 경계도 독립된 제한이다. 이 실험으로 두 제한의 상대적 기여를 정량 분해하지 않았다.

약한 edge 요청은 abs(score)<0.9라는 고정 규칙으로 설명된다. 필요한 edge의 의미적 선택, 최적 관측 정책, 일반적인 정보 이득 계산의 증거는 없다. 단일 후보 성공은 선택 문제 자체가 없는 조건이다.

## 판별 실험

[다음 최소 비교](NEXT.ko.md)는 외부 정보·학습·세션 지속 효과를 분리하는 것이다. 자율 conflict 입력을 새로 설계하는 작업은 별도 계약으로 다룬다.

## 현재 주장 가능한 범위

- `observed`: 현재 native API는 외부 오답 피드백 없이 관측 요청을 허용하지 않으며, 네 고정 조건에서 자동 요청이 없었다.
- `observed` — 합성 구현 검사: 외부 피드백 이후 약한 edge 요청과 단일 후보의 같은 세션 revision이 작동했다.
- `unsupported`: native 자율 conflict detection, 정보 가치에 따른 edge 선택, HCC 고유 우위, 총 효율 개선, 장기 기억 유지.
- `not measurable` — 측정 상태: R067 controller와 동일 정보를 가진 native 자율 요청 정책의 성능은 현재 표현 계약으로 직접 비교할 수 없다.

검산은 생산 코드와 분리된 로직·프로세스로 수행했으며 독립 연구자 감사는 아니다.
