# EXP-46 / R065: 기억 정보 경계 재분석

R064는 관측을 교정하면 False를 올바르게 채택했지만, 새 세션에서 잘못된 원래 관측을 다시 주면 True로 돌아갔다. 다음 과제는 학습 횟수 추가가 아니라 교정 정보가 어디까지 보존되고 다음 판단에서 어디에 쓰이는지 확인하는 것이다.

이 작업은 R064의 기존 원자료 재분석이다. native 연구 실행, 학습, 독립 표본은 모두 0이다. `Run-HCR-R065.cmd`가 입력 hash 확인 → 조건·source 복사 → 합성 self-test → 기존 packet 재평가 → 별도 로직·프로세스 검산 → 최종 core 회귀 1회 → hash·ZIP 묶음을 수행한다. 원자료는 참조만 하며 수정하지 않는다. bundle에는 이번 분석 source와 결과가 들어가며, 재현에는 고정된 R064 부모 evidence도 필요하다.

## 동결 조건과 판정

- before / after_feedback / after_correction × ON/OFF × misleading-repeat / truthful-control의 기존 frozen packet 12개를 모두 사용한다.
- 각 packet의 관측, memory, config, 판단, proof, readout을 그대로 두고 참조 truth만 open=(True,True), closed=(True,False)로 바꾼다. 한 packet에 대한 두 참조 채점이며 새 실행 두 개가 아니다.
- 해당 두-edge chain에서 정답은 각각 True와 False다. 같은 채택값으로 양쪽을 모두 맞힐 수 없다는 논리 명제를 검사한다. 채택 거부나 None은 성공으로 세지 않는다. 불일치가 나오면 checker/construct 오류로 남긴다.
- **구조 재사용 유지**는 저장 pattern의 동일성 및 기존 misleading-repeat ON의 actual circuit reuse로 판단한다. **세계 사실 교정 유지**는 교정 뒤 fresh misleading-repeat에서 closed truth에 맞는 False를 채택하는지로 판단한다. memory version 증가만으로 어느 쪽도 통과시키지 않는다.
- 올바른 False feedback 전후의 circuit/pending와 patch를 비교하고, persistent memory와 full session packet을 구분한다. source에서 학습 분기, 새 session 생성, activation, 무결성 guard까지 추적한다.

원자료 hash와 위 조건은 실행 전에 frozen_spec에 고정한다. 이전 R064 결과는 이미 알려져 있으므로 이번 검산을 새로운 사전 예측 검증이나 독립 재현 실험으로 부르지 않는다. 분석 결과를 보고 조건을 바꾸거나 유리한 행을 고르지 않는다.

## 해석 경계

open 참조는 closed 세계에서 만들어진 memory를 그대로 붙여 채점한다. 두 참조가 같은 실제 학습 이력과 동시에 양립한다고 주장하지 않는다. 알려지지 않은 세계 변화 또는 반사실적 label 부착에 대한 조건부 정보 한계이며, 실제 세계를 바꿔 얻은 인과 실험이 아니다. 12/24 행의 비율을 일반 정확도나 통계 표본으로 해석하지 않는다.

오류 True 판단에 대한 신뢰할 수 있는 binary feedback은 그 episode의 도달 불가능성을 알려줄 수 있다. 그러나 어느 edge가 닫혔는지는 그것만으로 특정되지 않는다. 요청 후 수정 관측은 edge별 추가 정보다. 이 정보가 full session에 있는지와 persistent memory가 다음 fresh 판단에서 사용할 수 있게 저장하는지는 별개다.

새 사실 memory, 음성 회로 학습, 반복 feedback, 자동 관측 교정, core 수정은 이번 범위에 없다. 독립성은 생산 도구와 다른 채점 로직·프로세스에 한정하며 독립 연구자 감사는 아니다.
