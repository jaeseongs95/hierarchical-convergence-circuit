# EXP-43 / R062: feedback에서 native 판단까지

## 결론을 열어 둔 사전 설계
R054의 수치 결과가 native proof·관측 지지·채택으로 이어지는지를 처음 측정한다. 학습 효과나 일반 능력 향상이 성공 기준은 아니다. 기존 R052의 top_down ON, 입력 배열 path, identity 0에서 startstrong와 goalstrong를 가져와 각각 full과 drop_P_prefix로 실행한다. 4개 결정적 실행을 독립 표본으로 계산하지 않는다.

## 개입과 고정 조건
관측 ID·revision·점수·배열·topology·config·빈 frozen memory·예산을 paired arm 사이에 고정한다. 기존 AdaptiveSession을 사용하고 native readout을 그대로 기록한다. 세션 식별자는 기존 R050 helper의 prefix를 보존하며 case와 arm으로 구별한다.

현재 src/tests는 수정하지 않는다. 실행 전 원본 source를 복사하고, drop 복사본에서 workspace.make_program의 p:0:1→p:0:0 top_down 생성만 제외한다. 별도 검산기의 chain_program에서도 독립적인 인덱스 조건으로 해당 링크만 제외한다. 두 소스 변경은 pre/post hash와 정확한 텍스트로 봉인한다. 이는 명시적 엔진 변형이며, 변경 없는 원본 엔진 결과로 부르지 않는다. 상태·proof·지원 진단·readout 규칙은 수정하지 않는다. 실험 도메인은 2-edge 단일 chain이며 다른 topology로 일반화하지 않는다.

## 예측과 판정
기존 R054에 따르면 goalstrong는 링크 제거 시 goal 수렴값의 쪽이 바뀌고 startstrong는 양쪽에서 낮다. 실제 proof의 유효성·support gap·채택은 이번 측정 대상이다. 수렴과 raw decision, proof under-assumptions validity, 관측 지지, native readout adoption을 분리한다. evaluator의 양수 edge 기준은 이 toy 입력의 참조이며 외부 세계 정답이 아니다. 높은 수렴값만으로 정답을 선언하지 않는다.

## 검증과 중단
원클릭: source·입력·spec 동결 → 별도 합성 open/blocked 4개 및 변조 검출 → core 최종 회귀 1회 → 연구 native 4개 → 각 변형의 독립 과정·공식 검산 → R054 전체 tick / 원본 full R052 native bridge → summary·bundle·ZIP. 최초 실패와 부분 기록을 보존하고 자동 retry하지 않는다. 구현 오류는 연구 시작 전에만 수정하며 이전 실패 evidence를 남긴다.

R054 수치 bridge의 허용 오차는 절대/상대 1e-12이다. 독립 검산은 별도 공식·프로세스이며 별도 연구자 검토와 동일하지 않다. 과거 source와 evidence를 재봉인하지 않는다. 계산 counter의 단위를 합치지 않고 에너지·메모리 측정은 unknown으로 둔다. 실행시간은 성능 벤치마크로 해석하지 않는다.

## 다음 단계의 조건
native 결과와 검산을 먼저 확인한 뒤, 기존 학습 장치로 형성한 동일 memory snapshot에 대한 reuse ON/OFF의 새 instance paired 비교를 설계한다. 고정 feedback의 수치 분석을 추가 확장하는 대신 학습·재사용·실패 후 재확장을 각각 구별한다. latent connectivity와 동적 edge 생성 비교는 그 뒤의 별도 실험이다.
