# EXP-44 / R063 결과

## 결론

기존 native 학습 규칙으로 세 경험 뒤 길이 2 회로 하나가 형성됐고, 새로운 분기 topology에서도 실제 재사용됐다. 회로 재사용은 세 평가 pair 모두 expansion을 줄이고 판단·관측 지지·채택을 보존했다. 그러나 native kernel ticks는 모두 늘었다. **회로 형성·재사용과 계산 효율 향상은 구별해야 한다.**

이 결과는 사전 정의된 경로 motif·컴파일 임계 규칙을 가진 toy 엔진의 관찰이다. 임의 graph 구조를 자율적으로 발견한 결과나 HCC 전체 가설의 입증은 아니다.

## 관찰

실행은 `HCR-Evidence/exp44/r063-20260920T020204Z-07096ed58b`다. 학습 3개와 frozen 평가 12개를 한 번씩 실행했다. 별도의 합성 training 3개/eval 8개는 연구 결과와 합산하지 않았다. 연구 실행과 core 회귀의 재실행은 없다.

학습의 각 inference 뒤 별도 reference 프로세스가 외부 toy truth, proof, 가정의 사실성을 검사하고 feedback을 만들었다. 그 feedback을 기존 native API가 소비했으며 host가 circuit이나 strength를 직접 쓰지 않았다. `training/01~03`에 inference/reference/learning packet을, `memory/0~3.json`에 전후 상태를 보존했다.

| 경험 완료 수 | 관측된 상태 |
|---:|---|
| 0 | 빈 memory |
| 1 | 길이 2 motif pending, 증거 1개 |
| 2 | 길이 2 pending 증거 2개, 길이 3 pending 증거 1개 |
| 3 | 길이 2 circuit 1개, strength 0.55; 길이 3은 증거 2개로 pending 유지 |

학습 입력은 각각 길이 2·3·4의 강한 양수 경로였고 세 feedback 모두 correct=True였다. 형성된 circuit의 증거는 train-1/2/3의 서로 다른 native proof와 feedback에 결속된다. strength 0.55는 기존 컴파일 규칙의 초기값이다. 아직 추가 강화나 오류 후 약화의 효과를 측정한 것은 아니다.

다음은 동일한 형성 후 memory에서 OFF→ON의 비교다. 모든 값은 최종 raw에서 다시 계산했다.

| 평가 입력 | 실제 circuit use | expansion OFF→ON | decision ticks OFF/ON | 추가 pool ticks | 전체 kernel ticks OFF→ON | 채택값 OFF/ON |
|---|---:|---:|---:|---:|---:|---|
| 길이 2 재명명 대조 | 1 | 2→1 | 33 / 33 | 35 | 33→68 | True / True |
| 길이 4 + 새 dead-end 분기, 열림 | 2 | 4→2 | 38 / 38 | 67 | 38→105 | True / True |
| 같은 분기 + 마지막 edge 닫힘 | 1 | 5→4 | 34 / 34 | 61 | 34→95 | False / False |

세 pair 모두 native/budget 실패 없이 사전 비용 예측의 평가 조건을 만족했다. 엄격한 expansion 감소는 3/3 지지, 엄격한 kernel ticks 감소는 3/3 반증, raw 판단·가정하 proof validity·support gap·채택 보존은 3/3 지지다. 이는 결정적 대조의 집계이며 독립 표본 세 개에 대한 통계 추론이 아니다.

12조건 모두 support gap=0이며 native gate가 판단을 채택했다. False 채택과 채택 거부는 다르다. D_DAG는 각 입력에서 2·4·2로 ON/OFF 동일했다. 회로 사용으로 expansion이 줄어도 primitive proof의 inferential dependency depth가 줄었다고 볼 수 없다.

`expansions`는 기존 native 정의에 따라 macro/primitive 적용뿐 아니라 dead-end frontier retirement도 포함한다. 닫힌 분기 입력의 OFF 5는 primitive 적용 4회와 dead-end 처리 1회다. 이 정의를 결과에 맞춰 새로 변경하지 않았다.

## 해석

형성 전 memory의 ON/OFF와 reuse OFF의 형성 전후 비교에서는 관측된 판단·채택과 시간 외 비용 계수가 모두 같았다. 형성 후 ON에서만 회로가 실제 적용됐다. 이 조건에서는 단순한 memory version 변경이나 빈 gate 활성화로 결과 차이를 설명할 수 없다.

최종 decision network의 program과 매 tick의 state·residual·stable_steps는 형성 후 ON/OFF에서 모두 같았다. ON의 drives 기록에는 일부 prefix의 명시적 0 항목이 더 있어 원문 딕셔너리는 다르지만, 각 group에 실제로 적용되는 drive는 같다. `route_only`에서 완성 경로의 primitive 수치 network를 다시 만들기 때문에, 이번 재사용은 전개 경로를 묶었을 뿐 최종 수치 판정을 생략하지 않았다. 추가 kernel ticks는 원자료에서 정확히 pool의 35·67·61 ticks로 분해된다.

binding checks도 OFF의 0에서 ON의 4·20·20으로 늘었다. 이 검사는 ticks와 단위가 달라 합산하지 않는다. 시간·에너지·peak memory·hardware 효율을 새로 측정하지 않았으며, 비용 감소라고 주장하지 않는다.

EXP-25의 기존 학습 seed 재사용 대조와 양립하는 비용 구조다. 이번에 추가한 증거는 빈 memory에서 각 경험을 통해 형성되는 전이와 그 snapshot에 결속된 새 입력 평가다. 과거 raw나 이번 raw의 재분석을 새로운 독립 실험으로 중복 계산하지 않는다. EXP-43의 feedback 링크 제거는 이번 엔진에 적용하지 않았다.

## 대안 설명

형성 시점은 `min_valid_episodes=3`과 사전 정의된 role grammar의 결과다. 일반적 학습 법칙이나 emergent 회로 발견의 직접 증거가 아니다. 학습에도 길이 4 경로가 있었으므로 새 분기 입력의 성공을 보지 못한 길이·primitive 종류로의 일반화로 해석할 수 없다. 새로 조합된 것은 dead-end 분기 topology이며 재명명 대조는 별도다.

이번 강한 관측, route_only, 작은 경로, 현재 pool 구현에서는 검색·경쟁 overhead가 재사용의 전개 이득을 상회했다. 더 큰 문제나 다른 관측에서 같은 tradeoff가 유지되는지는 미검증이다. 반대로 성능이 좋아질 조건을 찾을 때까지 구조·gain·입력을 바꾸는 것도 이번 결과의 해석이 아니다.

## 판별 실험

다음은 [오류 feedback 이후의 수정과 유지](NEXT.ko.md)를 별도로 검증한다. circuit 형성은 확인했으므로, 오류 뒤 memory가 바뀌는 것과 이후 판단·재확장 행동이 바뀌는 것을 구별해야 한다. 비용을 줄이기 위한 새 cache·scheduler·압축 장치를 이번 결과에 덧붙이지 않는다. latent connectivity 비교는 이 과정의 분리 측정 뒤로 둔다.

## 현재 주장 가능한 범위와 검증

- `observed`: 명시된 규칙하에서 경험·외부 검증·pending→compiled·새 분기 입력의 실제 reuse가 연결됐다.
- `observed`: 세 pair의 expansion 감소와 판단·지지·채택 보존.
- `falsified in these conditions`: 재사용 ON이 native kernel ticks를 엄격히 줄인다는 사전 예측.
- `unmeasured/hypothesis`: 오류 후 장기 수정 유지, 자율 구조 발견, 일반 graph 학습, 전체 Graph↔Circuit 순환과 계층적 수렴.

별도 공식·프로세스로 native state/learning/proof/support/readout을 검산했고, 합성 평가 8개에서 변조 56개를 거부했다. core 회귀 1회는 602개 중 599개 통과, 기존 Windows symlink skip 3개, 새 skip·실패 0개다. source·raw manifest·bundle 952개 파일과 ZIP bytes를 검증했다. 별도 연구자 감사나 LLM·인간 인지 실험은 수행하지 않았다.

연구 뒤 추가한 delivery 집계 검사에서 dead-end가 native expansions에 포함된다는 점을 빠뜨려 최초 비교가 한 번 실패했다. 기존 native 검산·raw·summary·예측은 변경하지 않았다. 해당 검사만 원래 정의대로 수정했으며 최초 검사 소스와 원인은 `HCR-Evidence/r063-validation/verify-delivery-initial.py`, `delivery-checker-correction.json`에 보존했다. 최종 검산은 `delivery-verification.json`, decision 궤적의 추가 분석은 `decision-trajectory-details.json`을 따른다.
