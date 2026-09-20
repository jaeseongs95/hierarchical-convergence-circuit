# EXP-45 / R064 결과

## 결론

**오류 feedback은 회로를 약화했지만, 올바른 행동을 재노출까지 유지시키지는 못했다.** 같은 관측으로 재개하면 여전히 틀렸고, 요청한 관측을 참조 세계에 맞게 교정한 재개에서만 올바르게 판단했다. 교정 후에도 원래의 잘못된 관측을 다시 주면 같은 오류가 채택됐다.

회로 OFF에서도 그 오류가 발생했다. 따라서 최초 오류를 회로 재사용 때문에 생긴 오류라고 부를 수 없다. 이번 결과는 **memory 변경, 관측 교정에 따른 판단 수정, 이후 행동 유지가 서로 다른 사건**임을 보여준다. 고정된 toy 조건에서의 결과이며 HCC 전체 가설을 반증한 것은 아니다.

## 관찰

연구 실행은 [r064-20260920T024825Z-d995fcc733](../../HCR-Evidence/exp45/r064-20260920T024825Z-d995fcc733/summary.json)이다. 최초 ADAPT 1회, 동일 요청 packet에서 재개 2군, frozen 12조건을 한 pass로 실행했다. 연구 재실행이나 결과 이후 source/spec/metric 변경은 없었다. R063의 세 학습 episode와 memory provenance는 다시 검산했으며 새 연구 경험으로 세지 않았다.

실제 세계에서는 두 번째 edge가 닫혀 있다. 최초 관측 score는 (0.8, 0.8)로 세계와 다르다. native 판단을 먼저 끝낸 뒤 별도 참조 과정이 실제 truth로 feedback을 만들었다. 원본 요청은 e0/e1을 포함했고, same_observation에는 score를 그대로, corrected_observation에는 (1, −1)을 제공했다. 두 군 모두 원본 재개 정책에 따라 회로 사용이 꺼졌다.

| 단계 | 채택값 | 실제 정답 일치 | 회로 재사용 | expansion | pool / decision ticks |
|---|---|---|---:|---:|---:|
| 최초 ADAPT | True | False | 1 | 1 | 34 / 33 |
| 같은 관측 재개 | True | False | 0 | 2 | 0 / 33 |
| 교정 관측 재개 | False | True | 0 | 2 | 0 / 28 |

False 채택은 채택 거부가 아니다. 세 실행 모두 gate가 판단을 채택했고, 가정하 proof validity는 True, 관측에 대한 support gap은 0, D_DAG는 2였다. 최초와 같은 관측 재개는 외부 참조에서 assumption_correct=False와 wrong_stable=True였다. 관측 지지와 실제 세계의 정답 일치는 별도다.

| memory snapshot | memory version | 회로 strength | 회로 failures / version | active | 회로 내용 변경 |
|---|---:|---:|---:|---|---|
| before | 3 | 0.55 | 0 / 1 | True | R063 seed |
| after_feedback | 4 | 약 0.11 | 1 / 2 | True | 약화·오류 feedback 이력 |
| after_correction | 5 | 약 0.11 | 1 / 2 | True | 직전과 동일 |

0.11의 원자료 값은 부동소수점 표현상 `0.11000000000000001`이다. 교정 관측에서 올바른 False 판단을 feedback한 뒤 patch의 `changes=[]`였다. memory의 version·consumed_feedback·patch 이력만 추가됐고 circuit와 pending은 그대로였다. 같은 관측 대조군의 두 번째 오류 feedback은 평가만 했으며 소비하지 않았다.

frozen 재노출 결과는 다음과 같다. 세 snapshot 전체에서 misleading-repeat은 ON/OFF 모두 잘못된 True를, truthful-control은 ON/OFF 모두 올바른 False를 채택했다.

| 입력 | gate | before → after_feedback → after_correction의 전체 kernel ticks | 회로 재사용 | expansion |
|---|---|---|---:|---:|
| misleading-repeat (0.8, 0.8) | OFF | 33 → 33 → 33 | 모두 0 | 모두 2 |
| misleading-repeat (0.8, 0.8) | ON | 67 → 68 → 68 | 모두 1 | 모두 1 |
| truthful-control (1, −1) | OFF | 28 → 28 → 28 | 모두 0 | 모두 2 |
| truthful-control (1, −1) | ON | 57 → 57 → 57 | 모두 0 | 모두 2 |

ON의 추가 tick은 activation pool에서 발생했다. misleading-repeat의 pool prior는 0.165→0.033, activation은 약 0.995611→0.994221로 낮아졌으나 eligibility와 actual reuse는 유지됐다. `strength`와 activation threshold는 같은 값이 아니다. 이 항목은 같은 raw의 재분석이며 추가 연구 증거로 중복 계산하지 않는다.

사전 예측 판정은 memory 변화 supported, 같은 관측 재개의 정답 교정 falsified, 교정 관측 재개의 정답 교정 supported, 교정 행동의 재노출 유지 falsified다. 네 예측 모두 이번 실행에서 판정 가능했다. 모두 결정적 조건 비교이며 표본 비율에 대한 통계적 추론이 아니다.

## 해석

같은 요청·memory·재개 정책에서 관측 score만 바꾼 두 군의 결과가 달랐다. 이 조건에서 관찰된 교정은 추가 관측과 연결되며, 회로 비활성화와 재시작만으로 설명되지 않는다. 교정된 관측을 이미 학습 전 memory에 주어도 맞았으므로, 교정 성공을 새로운 기억 형성의 증거로 볼 수 없다.

원본 `update_adaptive`는 틀린 판단에 사용된 회로를 약화하고, 올바른 True proof에서 양성 경로 motif를 학습한다. 올바른 False 판단에서는 이력 기록 외 구조 학습 분기가 없다. 관측된 빈 changes와 일치한다. 따라서 이번 구현에서 관측 교정 정보가 재사용 가능한 사실 기억으로 저장됐다고 주장할 근거가 없다. 저장된 회로가 여러 상황에 재사용하는 경로 계산이라는 점과, 특정 edge의 실제 passability를 기억하는 일도 구별해야 한다.

R063에서 관찰한 형성·재사용은 유지된다. 다만 이를 곧바로 “실패 후 재확장하면 수정된 circuit이 남고 다음 행동이 개선된다”로 확장할 수 없다. 수정된 관측의 일시적 이용까지와 지속 가능한 교정 사이의 연결은 아직 성립하지 않았다.

## 대안 설명

관측 자체가 잘못됐기 때문에 primitive 계산도 틀릴 수 있으며 OFF 대조군이 이를 직접 뒷받침한다. 약화된 회로가 여전히 activation 임계값을 넘었다는 사실은 재사용 지속과 양립하지만, 그것만이 재노출 오류의 원인이라고 할 수 없다.

현재 learner는 상황별 사실이나 음성 proof를 보존하는 계약이 없어, 이번 유지 예측이 구현의 표현 범위를 넘어섰을 가능성이 있다. 또한 고정된 하나의 오류 사례에서 한 번의 feedback만 제공했다. 반복 feedback, 다른 강도·topology·세계, 회로 비활성화 이후의 결과, 장기 유지와 다른 유형의 오류는 측정하지 않았다. 그 미측정 조건이 더 낫다고 추정해 이번 실패를 지우지 않는다.

## 판별 실험

다음에는 메커니즘을 늘리기 전에 **구조 재사용 기억과 상황별 사실 기억의 정보 경계**를 먼저 검증한다. 현재 memory와 같은 public input으로 서로 다른 실제 세계를 구별할 정보가 전달되는지, 올바른 False proof 이후 어떤 필드가 판단에 재사용되는지 확인한다. 같은 입력·memory에 서로 다른 참조 truth만 붙이는 반사실 대조는 새 native 경험 없이 가능한 정보 한계를 판정할 수 있다. 구체적 다음 작업은 [NEXT.ko.md](NEXT.ko.md)에 기록했다.

## 현재 주장 가능한 범위

기존 API는 native 오류 feedback, 회로 약화, 요청 기반 재개와 관측 교정을 분리해 실행·검산할 수 있다(`observed`). 이번 조건에서 교정된 행동이 frozen 재노출까지 유지된다는 예측은 `falsified`다. 일반적인 Graph↔Circuit의 학습·수정·장기 유지 순환은 여전히 `hypothesis`이며, 이번 장치에서 완전하게 구현·검증됐다고 말할 수 없다.

검증은 원본 core 602개 중 599개 통과와 기존 Windows 환경 skip 3개, 합성 ADAPT 4회/frozen 12조건, 변조 거부 90건이다. 별도 수식·프로세스로 부모 provenance, session, learning, 요청과 관측, proof·채택·memory를 검산했다. [전달 검증](../../HCR-Evidence/r064-validation/delivery-verification.json)은 bundle 1,418개 파일의 hash, source/raw manifest, ZIP, raw 비용 집계와 결과 일치를 확인했다. source manifest SHA-256은 `6765aea4758b69dde657b4fb51cee460919d4bf109b69d6a8c4248dbef0574df`다. 합성 실행은 연구 결과에 합산하지 않았고 독립 연구자 감사·에너지·peak memory·LLM/인간 인지 효과는 측정하지 않았다.
