# EXP-43 / R062 결과

## 결론

단일 2-edge chain의 goalstrong 입력에서는 p:0:1→p:0:0 top_down 링크를 사전에 제거한 엔진 변형이 수치 수렴값뿐 아니라 native 판단·proof의 관측 지지·readout 채택을 바꿨다. full에서는 False와 support gap 1개로 채택이 거부됐고, drop에서는 True와 gap 0개로 채택됐다. startstrong 입력에서는 두 조건 모두 채택되지 않았다.

이 결과는 고정된 수치 recurrence 분석을 실제 엔진 출력까지 연결한다. 실험자가 사전에 정한 구조 개입의 효과이며, 경험으로 그 링크를 바꾸거나 회로를 형성한 학습 결과는 아니다.

## 관찰

연구 실행: `HCR-Evidence/exp43/r062-20260920T011305Z-1a61ac35ea`. 원자료는 `raw/<arm>/<case>/execution.json`, 개별 init/begin/advance packet과 candidate는 같은 디렉터리의 progress에 보존했다. `audit/full.json`, `audit/drop_P_prefix.json`이 별도 프로세스의 독립 공식 검산 결과다.

| 입력(edge score) | 링크 | goal 수렴값 | raw 판단 | 가정하 proof 유효 | support gap | 채택 | native ticks |
|---|---|---:|---|---|---:|---|---:|
| startstrong (1, 0.02) | full | 0.026117211347 | False | True | 1 | 보류 | 60 |
| startstrong (1, 0.02) | drop_P_prefix | 0.028676195816 | False | True | 1 | 보류 | 62 |
| goalstrong (0.02, 1) | full | 0.013283387009 | False | True | 1 | 보류 | 116 |
| goalstrong (0.02, 1) | drop_P_prefix | 0.986807809282 | True | True | 0 | True | 75 |

네 조건 모두 stable_decision이며 D_DAG=2, expansion=2다. full/startstrong와 drop/startstrong의 proof는 관측 점수 양수인 z-edge를 닫혔다고 가정한다. full/goalstrong는 a-edge를 닫혔다고 가정한다. drop/goalstrong는 두 edge 모두 열렸다고 가정하며 공개 관측 점수와 일치한다. 따라서 가정하 proof validity가 True라는 사실만으로 관측 지지나 채택이 보장되지 않는다.

signal transmissions는 startstrong 480→434, goalstrong 928→525다. group updates는 각각 300→310, 580→375다. 이 값들을 다른 단위의 검사 수와 합쳐 총 비용으로 만들지 않는다. goalstrong는 채택 품질도 달라졌으므로 116→75 ticks를 동일 품질의 효율 비교라고 부르지 않는다. 시간·에너지·hardware 이득은 입증하지 않았다.

## 해석

R054의 동일 네 조건과 전체 tick·network·최종 상태가 허용 오차 1e-12 이내로 일치했다. full 두 조건은 원 R052 native session을 다시 독립 검산하고 전체 수치 궤적과 terminal 결과가 같은지 확인했다. R054는 proof/support/adoption을 null로 남겼지만 이번에는 실제 session/candidate를 생성해 그 빈 부분을 측정했다. 같은 수치 결과를 새로운 독립 효과로 중복 계산하지 않는다.

실행 코드의 개입은 source 복사본 안의 링크 생성 규칙 한 곳이다. 별도 검산기 복사본의 예상 grammar도 이에 맞게 한 곳 변경했고 두 파일의 정확한 전후 hash와 patch를 보존했다. native 판단·proof 생성·support·readout 규칙과 원본 src/tests는 그대로다. 독립성은 공식과 프로세스의 분리이며 다른 연구자의 감사는 아니다.

## 대안 설명

이 paired 조작은 이 고정 조건에서 링크 제거의 총 효과를 분리한다. 하지만 그 효과는 선택한 feedback gain·초기값·입력 강도·threshold·작은 chain의 상호작용일 수 있다. 보편적인 개선, 의미적 이해, 최적 feedback 구조, 학습된 정책 또는 HCC 전체 이론의 입증으로 확장할 수 없다.

참조 True는 두 공개 edge 점수가 양수인 toy 조건의 evaluator 정의다. 외부 세계의 실제 passability를 새로 관측한 결과가 아니다. 부호가 다르거나 미지인 관측, 더 큰 topology, 다른 budget에 대한 일반화는 미검증이다. startstrong에서 gap이 그대로 남은 사실은 링크 제거가 일반적인 해결책이 아니라는 제한을 보여 준다.

## 판별 실험

다음은 [회로 형성 전후와 새 instance 재사용 대조](NEXT.ko.md)로 좁힌다. EXP-25의 기존 frozen seed ON/OFF 비교를 반복하는 것으로 끝내지 않고, 검증된 경험을 통한 pending→compiled 변화와 그 이후의 새 입력에서 실제 circuit 사용을 분리한다. 이번 링크 제거를 학습된 변화로 취급하거나 그대로 기본 엔진에 적용하지 않는다. 오류 후 재확장·수정 유지와 latent connectivity 비교는 그다음 단계다.

## 현재 주장 가능한 범위와 검증

- `observed`: native 엔진의 명시적 링크 개입이 goalstrong의 False/보류를 관측 지지를 가진 True 채택으로 바꿨다. startstrong에서는 바꾸지 못했다.
- `observed`: 수렴·가정하 proof 유효성·관측 지지·채택은 구별해야 하는 측정량이다.
- `hypothesis`: 반복 경험이 이런 구조·강도·binding을 형성하고 재사용 성능을 바꿀 수 있다. 이번 실험에서는 학습하지 않았다.
- `unsupported by this experiment`: 전체 Graph↔Circuit 순환, 계층적 수렴, LLM 내부 계산, 인간 인지·생물학·물리적 에너지 효율에 대한 직접 결론.

최종 구현의 별도 합성 입력 4개와 32개 변조 거부 검사가 통과했다. 원본 core 회귀는 1회, 602개 중 599개 통과·기존 Windows symlink skip 3개이며 새 skip과 실패는 없다. source·bundle의 1,440개 파일·ZIP bytes와 raw에서 재계산한 최종 측정값을 확인했다. 검산 영수증은 `HCR-Evidence/r062-validation/delivery-verification.json`이다.

원클릭 준비 중 `validation/native-smoke` 상위 폴더 생성 누락이 한 번 발생했다. `HCR-Evidence/exp43/r062-20260920T011242Z-6ad9516312/failure.json`과 당시 source를 보존했다. 연구 실행과 core 회귀가 시작되기 전에 폴더 생성만 수정했으며 연구 입력 재실행으로 결과를 골라내지 않았다. 별도의 개발 합성 실행은 `HCR-Evidence/r062-validation/r062-20260920T011208Z-7c991d51d9`에 보존했다.
