# R45 / EXP-91 사전 판별 및 결과별 처리 계약

1. **유한 채택 조건 (`FINITE_FULL_COVERAGE_AND_STAGE_TRANSFER_ACCEPTED`)**:
   - 1,024개 native 조건과 128개 exact 조건의 `kind`·`selected_index`·`value`·`reason` 및 역할(`12,288/12,288`)·AST(`4,096/4,096`) 중간값이 독립 집합 oracle과 100% 일치하고, 896개 non-identity→identity 대응이 후보 identity 기준으로 896/896 불변이다.
   - 128개 모든 base에서 제한 대응 수가 `[8]`(무변경 0/896, 변경 896/896)이고, 각 코드북이 64/64 ordered 코드쌍을 모두 소비한다.
   - 64개 역할 입력이 4개 Hamming 동치류($d \in \{0,1,2,3\}$)로 정확히 분할되고, 384개 `expr` 전수 전이와 80개 `feasible2`/`query2` 극값 경계가 모두 기대 진릿값·분류·사유와 일치하며, 21개 표적 변조가 모두 거부된다.
2. **음성 종결 조건 (`NOT_ADOPTED`)**:
   - 위 조건 중 하나라도 실패하면 임계값·입력·코드북 사후 수정이나 native 재실행 없이 실패 원자료와 최초 반례를 그대로 보존하고 음성으로 닫는다.
3. **해석 한계 고정**:
   - 채택되더라도 authored 3-bit codebook과 고정 `Config`/`initial=0.5`/`n=2` 파이프라인 및 `role->expr` 전수 전이·`feasible2/query2` 극값 경계의 유한 결과로만 기록하며, $64^n$ 전체 열거·학습된 표현·H03 구조 재사용·원계산 대체·속도 우위·일반 AI·운영 도입으로 확대하지 않는다.
