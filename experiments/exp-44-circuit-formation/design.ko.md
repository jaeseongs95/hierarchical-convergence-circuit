# EXP-44 / R063: 회로 형성 전후와 새로운 입력의 재사용

## 질문과 이전 결과
EXP-43은 고정된 feedback 링크 개입이 특정 입력의 native 판단·관측 지지·채택을 바꿀 수 있음을 확인했다. 그때 memory는 비어 있었으며 학습하지 않았다. EXP-25는 이미 형성된 고정 seed의 ON/OFF 총 효과를 비교했다. 이번에는 빈 memory에서 사전 지정한 경험 3개를 거친 각 상태를 보존하고, 전후 snapshot의 재사용 기여를 구별한다. EXP-43의 링크 제거 변형은 채택하지 않고 원본 native source를 사용한다.

## 동결 조건
학습 3개는 각각 길이 2·3·4인 양수 경로다. 각각 다른 node·edge·episode이며 구조 길이도 다르다. 모델의 판단 뒤 별도 reference 프로세스가 proof와 사전 정의 toy truth를 검사하고, 그 feedback만 기존 AdaptiveSession.feedback에 전달한다. 정답 값·circuit·strength를 host가 직접 쓰지 않는다. 목표 결과가 나올 때까지 경험을 추가하지 않는다.

평가 입력은 새로운 ID를 가진 길이 2 경로 대조, 학습에서 없던 dead-end 분기가 붙은 길이 4 경로, 같은 분기 구조의 마지막 edge가 닫힌 입력이다. 점수의 부호가 실제 passability라는 외부 평가 계약을 사전에 고정한다. 이것은 authored toy world이며 현실 관측 실험이 아니다. 단순 재명명 대조와 구성 변화 조건을 구별한다.

각 입력에 대해 memory 0/3 × use_circuits OFF/ON, 총 12개를 실행한다. training=3, eval=12를 한 연구 실행에서 한 번만 수행한다. 양군의 관측·config·top_down=True·route_only prior·native input order·native 최초 ready readout과 dependency gate를 고정한다. ON/OFF는 회로 검색·binding·pool·macro 적용 분기 전체의 허용/차단이다. 개입 후 자연스럽게 달라지는 route·schedule·종료 시점은 강제로 일치시키지 않는다.

기존 kernel max_ticks=160, 최대 advance=16, 최대 kernel_ticks=5120. 각 advance 전 회로가 존재하고 gate가 ON이면 pool+decision의 320 ticks, 아니면 160 ticks를 예약한다. 검산기가 모든 generation에서 같은 예산 계약을 재확인한다. 예산 종료는 native 실패와 분리하고, training candidate가 없으면 feedback을 생략한 채 그 실패와 unchanged memory를 보존한다.

## 사전 예측과 반증
기존 규칙상 양성이고 외부 검증을 통과한 서로 다른 세 episode는 길이 2 motif의 pending→compiled 전이를 가능하게 한다. 길이 3은 두 episode의 증거만 가지므로 pending에 남는다. 이 예상은 이미 구현된 임계 규칙의 작동 예측이며 학습 법칙이 자발적으로 발견된다는 주장이 아니다.

형성, held-out 실제 circuit use, expansion 감소, kernel ticks 감소, 출력·채택 보존을 따로 판정한다. post ON의 실제 circuit use가 있고 양군이 budget/native failure로 중단되지 않은 pair만 엄격한 비용 감소 예측의 평가 대상이다. 같은 비용은 엄격한 감소를 반증한다. 품질이 달라진 pair의 비용을 동일 품질 효율로 해석하지 않는다. D_DAG·pool ticks·decision ticks·binding·group updates·신호 전달·학습 write 비용의 단위를 나눈다.

pre gate 및 OFF의 전후 비교는 memory metadata나 gate 호출만으로 생긴 효과를 점검한다. circuit이 없거나 적용되지 않으면 형성·노출·binding·pool eligibility를 원자료에서 구분하며 조건을 바꿔 성공을 만들지 않는다.

## 원클릭과 검증
Run-HCR-R063.cmd: source·spec 동결 → 별도 synthetic training 3개/eval 8개 및 변조 검출 → 최종 core 회귀 1회 → 연구 training/외부 reference/feedback 각각 별도 프로세스 → 연구 frozen eval 12개 → 독립 native 상태·학습·proof·support·채택 검산 → 집계·bundle·ZIP.

각 training의 inference, 외부 assessment/feedback, native memory patch와 post-feedback packet, memory 0~3을 별도로 남긴다. 평가 init/begin/advance/candidate와 최초 종료를 보존한다. 독립 검산은 생산 runtime/compiler/learning을 호출하지 않는 기존 replay 공식과 별도 프로세스를 사용한다. 별도 연구자 감사와 동일하지 않다. 이전 source/raw/manifest는 수정하지 않는다.

합성 검사와 연구를 합산하지 않으며 첫 구현 실패도 보존한다. 연구 시작 전에만 허용된 구현 수정을 수행한다. 연구 시작 뒤 결과에 따라 source·입력·metric·조건을 바꾸거나 재실행하지 않는다. 성공 조건은 증거와 검증의 완결성이며 가설 성공이 아니다.

## 주장 범위
서로 다른 길이의 세 authored toy experience와 세 held-out 입력이며 통계적 독립 표본으로 계산하지 않는다. 경로 motif는 사전 정의된 role grammar와 min_valid_episodes 규칙에 의존한다. 임의 graph 학습, 자율적 구조 발견, LLM·인간 인지, 에너지·hardware 이득으로 일반화하지 않는다. 오류 이후의 재확장·수정 유지, latent connectivity와 동적 edge 비교는 이번 연구가 끝난 뒤 별도 질문으로 남긴다.
