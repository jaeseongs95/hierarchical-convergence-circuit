# EXP-14 — 계산 부족·정보 부족·판단 정책의 판별

## 동결 조건

기본은 학습 6회 memory, 8개 EXP-13 유래 입력, 초기 prior 정책 legacy/route_only, 5개 review 정책이다.
16개 최초 추론을 공유한다. main 130개 rollout과 통제 12개(무변화 센서 2, 관측 불가 2, 추가 예산 0인 조건 4, 1-step 조건 4), 합계 142개다.
같은 공개 관측에 두 hidden world가 있는 경우 최초 추론을 다시 생성하지 않는다. 관측에 의해 입력이 달라진 뒤의 재계산은 실제 신규 session으로 센다.
학습 3/6/9 시점 비교는 `--training-counts 3 6 9`로 **실행 전에** 명시적으로 선택한다. 기본 결과만으로 rigidity/강도 효과를 주장하지 않는다.

## 가설 및 반증/미지지 조건

| 가설 | 주요 대조 | 예측과 판정 |
|---|---|---|
| H-C 계산 부족 | hold vs expand_only / irrelevant_missing | 새 관측 없이 지지되는 readout을 얻으면 지지. 경로만 늘고 같은 약한 proof를 선택하면 미지지 |
| H-P 선택 정책 장벽 | expand_only vs route_review | 전개만으로 실패하지만 prior 분리 재계산으로 회복하면 정책 영향 설명에 부합. 두 조건은 재사용/재계산 비용이 달라 분리 보고 |
| H-I 실제 정보 부족 | route_review vs 관측 조건 / critical_missing, critical_zero | 같은 정보 재계산은 두 world를 식별하지 못해야 한다. 요청 응답이 분기한 뒤에만 결론이 갈리는지 확인 |
| H-Q 계산 우선의 질의 절감 | observe_first vs expand_then_observe | 지지 출력·정확도를 유지하며 질의를 줄이는가. 더 계산하고 같은 질의를 하면 실패로 기록 |
| H-S 불필요한 재검토 억제 | known_cut_missing, two_branch_cut, strong_positive | 지지되는 최초 출력이면 추가 전개/질의 없이 유지하는가 |
| H-L 센서 계약의 한계 | misleading_direction | 관측 방향이 잘못됐을 때 지지 통과와 외부 오답을 혼동하지 않는가 |

관측 provider는 모의 환경이다. perfect 조건에서는 요청 edge만 숨은 세계에서 ±0.98 score로 응답한다. 이는 선택적 관측 제어를 시험하는 명시적인 sensor-oracle 대조이며 실제 센서·LLM의 연구 결과가 아니다.

## 필수 지표

정답·오답·보류, 지지 출력 회복, 실제 결론 변경, 추가 정보 여부, 추가 advance/tick, 질의 feature 수, 정상 입력에 불필요하게 요청한 수, proof 생성량, branch reference와 끝난 이유를 보존한다.
`recovered_supported_output`은 gate 뒤의 출력 회복이지 항상 정답 개선이라는 뜻이 아니다. 최초 오답은 결과에서 삭제하지 않는다.

## 실행 순서

계획과 source hash 동결 → seed 학습 → 최초 추론/ready packet 저장 → paired controller 개입 → raw 저장 → 독립 감사/외부 채점 → 요약/manifest.
수작업 소형 fixture이므로 넓은 일반화나 wall-time 가속을 주장하지 않는다. 기본 학습/메모리는 frozen이고 수정 후 다음 episode 학습 유지 효과는 이 실험의 대상이 아니다.
