# EXP-47 / R066: 명시적 사실 저장·조회 baseline

R064의 교정된 관측은 False 채택을 만들었지만 fresh misleading 입력에서는 유지되지 않았다. R065는 현재 persistent memory에 edge별 사실 조회 경로가 없음을 확인했다. R066은 요청 교정 관측을 작은 사실표에 저장하고 다시 조회하는 정보 경로를 검사한다.

## 동결 조건

R064의 봉인된 request·measurements·memory를 입력으로 재사용하고 새 frozen native 평가 60개를 실행한다. 새 학습이나 독립 표본은 없다. binary_feedback는 after_feedback memory, edge_correction은 after_correction memory를 받는다. **인과 비교는 같은 정보 channel 안의 current / record_only / lookup 사이**로 제한한다. channel 사이에는 memory 이력 차이가 있으므로 정보 bit 하나만의 효과라고 해석하지 않는다.

교정 channel의 세 군 모두 같은 요청 교정 정보에 노출된 이력을 가진다. current는 native memory만 전달하고, record_only는 사실표를 보존하되 조회하지 않으며, lookup은 같은 표를 조회해 일치한 edge의 score를 ±1로 바꾼다. native memory, config, topology, 원래 관측, 예산과 gate를 맞추고 gate ON/OFF를 별도로 비교한다. 조회 후 내부 trajectory가 자연스럽게 달라지는 것은 그대로 둔다. binary correctness에서 닫힌 edge를 추론하지 않는다.

사실표는 `(context, epoch, edge_id, source, target, value, provenance)`다. toy-A/epoch 0은 과거 ID에서 발견한 사실이 아니라 **이번 baseline에서 명시적으로 부여한 상황 범위**다. edge ID는 이 범위와 endpoint가 같을 때만 같은 사실이다. native API에는 context/epoch가 없고, baseline 조회기에만 이 추가 metadata를 준다. 저장 시점은 R064 요청 교정 관측 revision 1이며 epoch는 관측 revision과 다르다. 범위의 유효성은 외부의 명시적 epoch 계약에 의존한다.

| case | 노출 scope | private truth e1 | 원래 관측 | 목적 |
|---|---|---|---|---|
| same | toy-A / 0 | False | 두 score +0.8 | 고정 세계 재노출 |
| other_context | toy-B / 0 | True | 두 score +0.8 | 같은 edge ID의 다른 세계 |
| new_epoch | toy-A / 1 | True | 두 score +0.8 | 알려준 유효기간 변경 |
| silent_change | toy-A / 0 | True | 두 score +0.8 | 알리지 않은 세계 변화 |
| truthful | toy-A / 0 | False | +1, -1 | 정확 관측의 별도 통제 |

모든 세계의 e0는 True이고 정답은 두 edge의 conjunction이다. same과 silent_change는 외부에 보이는 정보가 같고 참조 세계만 다르다. 이를 시간에 따른 실제 세계변화 추적이나 서로 독립적인 표본으로 부르지 않는다. native 실행자는 private truth 파일을 읽지 않는다. 별도 검산 프로세스가 결과를 채점한다.

## 기록·비용·판정

원래 관측, 제공/저장 사실, 조회 결과·출처, 실제 native 입력, 최초 판단, proof, readout, tick/expansion/reuse를 모두 보존한다. score 덮어쓰기는 명시적 입력 개입이며 native 능력에 합산하지 않는다. missing/conflict 조회는 None 상태로 기록하고 원래 score를 유지한다. 이는 False 사실을 새로 얻었다는 뜻이 아니다. readout 거부·미완료는 올바른 False로 세지 않는다.

Boolean payload 개수, scope 일치 조회 개수, 표의 UTF-8 직렬화 bytes, 조회 query 수·record 비교 수, 이전 측정 edge 수, 새 측정 호출 수를 별도 단위로 기록한다. 일치한 기록이 미통지 변화 뒤에도 실제로 유효하다고 보장하지 않는다. 정보 entropy/정보 이득, 실제 에너지, peak memory는 측정하지 않아 null이다. binary_correctness_payload_bits는 이전 오류 판정 1개만 뜻하며 교정 channel memory에는 후속 정답 feedback metadata도 있다.

동결된 예측은 matching lookup 교정, binary의 edge 비추론, context/epoch 불일치 시 입력 보존, silent change에서 lookup 오류, truthful 입력의 충분성이다. 예측이 실패해도 해당 구현·조건의 반증으로 보고하고 유리한 조건으로 재실행하지 않는다.

## 실행과 검증

`Run-HCR-R066.cmd`가 source·부모 입력·조건 동결 → 합성 경계 검사 → native 평가 60개 → 별도 사실 join 재계산과 native 수식 replay·변조 거부 → 최종 core 회귀 1회 → hash·ZIP 보존을 수행한다. 자동 설치·Git 조작·retry가 없으며 기존 결과를 덮어쓰지 않는다. source snapshot과 필요한 부모 파일이 bundle 안에 들어간다.

표 자체는 두 record의 선형 조회다. 학습 규칙, native schema, 장기 memory, 자동 freshness 판단을 추가하지 않는다. 성공하면 해당 정보 경로로 이 toy 과제를 해결할 수 있다고만 말한다. Circuit 학습, 일반화, HCC의 독자적 우위와 효율은 별도 검증 대상이다.
