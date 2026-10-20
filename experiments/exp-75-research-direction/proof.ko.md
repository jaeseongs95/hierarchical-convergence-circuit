# A-0의 충분조건과 한계

대상은 SHA가 고정된 `dynamics.tick`의 동기 갱신이다. cfg는 모든 group에 같고, 외부 callback·실행 중 program/config/drive 변경은 없다. 같은 class의 두 group은 level/goal 역할과 bias·실제 drive·초기 state의 binary64 bit가 같아야 한다. 원래 link 목록에서 top_down flag로 활성화한 incoming 행을 순서대로 추출한다. 대응 위치의 weight bit·kind가 같고 source가 같은 class에 있어야 한다. 중복 link는 제거하거나 weight를 합치지 않는다.

초기 state는 class 안에서 bit가 같다. 어느 tick의 class 안 state가 bit 동일하다고 가정하자. 대응 incoming source class의 state도 같고, bias+drive와 각 weight·연산 순서가 같다. 따라서 totals의 누적 결과가 bit 동일하다. 같은 cfg와 자기 state로 같은 positive/negative/z/exp 분기·damping 갱신을 수행하므로 다음 state도 bit 동일하다. 귀납적으로 이 닫힌 관계는 경계 feedback을 포함한 모든 tick에 유지된다. 서로 다른 source의 숫자가 우연히 같은 한 시점만 보고 경계를 생략하는 R19의 반례와 다르다.

이는 올바르게 작성된 대표 갱신·복원 구현의 근거다. A-0은 그 runtime을 구현하거나 실행하지 않는다. 실제 복원 dictionary 순서·residual·history·종료 controller·readout·비용의 보존은 A-1에서 별도로 대조해야 한다. 현재 source의 충분조건 확인을 존재하지 않는 runtime의 실측 동치로 표현하지 않는다.

producer는 local label에서 시작해 기존 color와 ordered source color 행으로 반복 분할한다. 기존 color를 key에 남겨 합쳐진 class를 다시 합치지 않는다. 각 유효 분할은 class 수를 늘리므로 유한 group 수에서 멈춘다. 별도 verifier는 처음 label이 같은 모든 ordered node pair를 만든 뒤, incoming 대응이 맞지 않거나 source pair가 제거된 pair를 반복 제거한다. producer의 refinement를 호출하지 않는다. 최종 pair 관계와 출력 class 전체를 대조해 closure뿐 아니라 **이 보수적 ordered-row 규칙 안의 maximality**를 확인한다. singleton만 반환하는 거짓 음성도 검출한다.

이 충분조건은 필요조건이 아니다. 서로 다른 연산 순서의 우연한 수치 일치, 다른 level의 동치, 특정 고정점 값, 일반 수학식 변환을 추가로 탐색하지 않는다. signed zero도 다른 label로 취급한다. 따라서 0기회는 이 규칙·네 Program·고정 입력의 음성 결과다.

ledger의 생략 group/normalization/link 수는 대표 행만 계산하는 가상 한 tick의 **투영량**이다. 실제 group/link 계산량은0이다. 전체 state 출력 slot과 alias 복원 slot도 따로 적어 복원비용을 숨기지 않는다. partition 생성·검증의 선언한 작업 수와 실험 process 자원은 분석 비용이며 native 추론 비용이나 최적화 속도 측정이 아니다.

양성이어도 학습 호출은0이다. 현 query의 drive/initial에 결속된 공유 class가 새 query에서도 유효하다는 보장은 없으며, 미래 재사용에는 다시 binding·조건 검증과 그 비용이 필요하다. 학습된 회로 압축·미래 품질·실제 성능은 별도의 주장이다.
