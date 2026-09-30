# EXP-45 / R064: 오류 교정과 재노출 유지의 분리

## 문제와 이전 근거

R063은 원본 TRAIN 규칙이 세 개의 유효한 양성 episode 뒤 길이 2 회로를 만들고, frozen 평가에서 재사용함을 확인했다. 이는 오류 뒤 판단 수정이나 수정된 행동의 유지를 증명하지 않는다. 이번에는 R063의 memory/3.json을 그대로 가져와 오류 feedback, 재개, 추가 관측, memory의 영향을 분리한다. 부모의 세 학습 episode는 독립 검산하되 새 연구 표본으로 합산하지 않는다.

## 동결 조건

원본 src/tests, route_only, top_down=true, ADAPT, 기본 config를 유지한다. public 입력은 두 edge 직렬 경로이며 최초 score는 모두 0.8이다. 별도 봉인 파일 reference_worlds.json이 실제 passability를 정한다. 관측 점수와 실제 세계는 서로 다른 변수다. worker는 그 파일이나 reference evaluator를 읽지 않는다. 이는 과정과 데이터 흐름의 분리이며 파일 접근 권한 격리를 주장하지 않는다.

최초 native ADAPT 한 번의 첫 readout을 외부 truth로 평가한다. 완료 candidate가 없으면 feedback을 생략한다. feedback.correct=false일 때만 원본 request_revision을 한 번 호출한다. 요청이 없으면 재개 두 군을 not_run으로 기록한다. 조건을 충족하도록 ID·proof·memory·판단을 host가 보정하지 않는다.

요청이 있으면 동일한 요청 packet에서 두 가지 가지를 각각 한 번 실행한다. same_observation은 score를 그대로 두고 요청 revision만 사용한다. corrected_observation은 요청받은 edge의 score만 참조 과정에서 truth에 맞는 ±1로 측정하여 전달한다. 두 군 모두 원본 재개 정책에 따라 회로 사용이 비활성화된다. 따라서 두 군의 차이는 추가 관측 효과를 구별하고, 같은 관측의 재개는 재시작·정책 변화 효과의 대조군이다. 두 군을 외부 평가하되 corrected_observation의 feedback만 최종 memory에 반영한다.

세 memory(before, after_feedback, after_correction) × circuit gate OFF/ON × 두 입력(misleading-repeat, truthful-control)을 fresh FROZEN_EVAL로 평가한다. 두 입력은 같은 topology·ID·순서·세계이고 score만 다르다. memory와 gate 비교에서는 관측 전체를 고정한다. 각 조건은 한 번이며 재노출은 추가 학습을 하지 않는다. 연구 실행은 최초 1회와 조건부 재개 2회, frozen 12조건이 상한이다.

## 예측과 판정

예측은 (1) 오류 feedback 이후 memory 변화, (2) 같은 관측 재개로 올바른 채택, (3) 교정 관측 재개로 올바른 채택, (4) 교정이 성공한 뒤 misleading-repeat에서 올바른 채택 유지다. 각각 supported/falsified/not_evaluable로 기록한다. 최초 오류 채택과 원본 요청이 있어야 재개 예측을 판정하며, 유지 예측은 교정 관측에서 올바른 채택이 실제로 있어야 판정한다. hypothesis 성공은 실행 검증의 통과 조건이 아니다. 최초 오류가 회로 때문에 발생했다고 전제하지 않는다.

raw judgment, dependency gate, adopted value, 실제 정답 일치, proof 유효성, 관측에 대한 support gap, D_DAG를 분리한다. 관측에 의해 지지되는 proof가 실제 세계에도 맞는다고 보지 않는다. memory strength·version·failures·feedback 이력과 actual reuse, expansion, native kernel tick을 별도로 기록한다. 비용의 단위를 합치지 않는다. 에너지와 peak memory는 미측정이다.

## 검증과 중단

먼저 score 0.7의 요청 분기와 0.95의 요청 없음 분기를 synthetic으로 검사한다. 각 분기에서 frozen 6조건과 source·proof·판단·support·memory·adoption 변조 검사를 수행하고 추가로 feedback·request·revision 기록 변조를 거부하는지 확인한다. 첫 실패는 보존하며 연구 시작 전 구현만 수정할 수 있다. 완성 후 core regression은 한 번 수행하고 연구는 한 pass만 실행한다. 결과를 본 뒤 source/spec/metric 의미를 바꾸거나 연구를 재실행하지 않는다.

생산 코드와 별도 프로세스에서 기존 독립 수식 검산기를 사용해 native session/learning/revision을 재계산한다. 참조 truth와 관측 수정, 동일 packet prefix, budget 사전 예약, 최종 memory와 frozen input을 검증한다. 독립 연구자 검증을 수행했다고 주장하지 않는다. 원클릭 Run-HCR-R064.cmd는 source/plan 동결→합성 검사→core 회귀→연구→audit→raw/bundle/ZIP 순서이며 Git 조작은 포함하지 않는다.

## 주장 경계

고정된 toy world와 원본 계산 규칙의 한 번의 실패·재개·재노출 사례다. 장기 유지, 일반화, 학습 최적성, 내부 LLM 사고, 인간 인지나 생물학적 circuit의 증거로 일반화하지 않는다. 어떤 분리된 단계가 실패했는지에 따라 다음 질문을 정하며 새 학습 메커니즘을 이번 턴에 추가하지 않는다.
