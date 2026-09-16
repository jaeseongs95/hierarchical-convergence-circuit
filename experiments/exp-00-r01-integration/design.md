# EXP-00 — R0.1 기능적 통합 검증

상태: **개발 fixture**, 코드의 실제 상태 전이를 확인하는 검사. 외부 성능 가설의 사전등록 평가가 아니다. 개발 중 반례를 보고 credit 정책을 수정했다. 뒤의 동일한 재현 실행은 독립 연구 표본으로 세지 않는다.

## 실행 순서

1. 빈 회로 메모리에서 서로 다른 인스턴스 이름의 통과 가능한 두 edge 경로 6개를 TRAIN한다. 처음 3개의 외부 검증된 기록에서 첫 회로가 생긴다.
2. 메모리를 파일로 저장하고 실제로 다시 읽는다. 이후 frozen 평가 조건마다 같은 snapshot을 복제한다.
3. full / graph_only / no_top_down / no_reexpansion을 각각 8개 공용 fixture에서 비교한다.
4. 같은 training snapshot에서 시작한 full과 no_reexpansion에 약한 반대 관측을 준다. 최초 오답을 기록한 뒤에만 correctness bit를 공개한다.
5. 허용한 조건은 낮은 관측의 edge를 추가 측정하고 그래프를 재전개한다. 수정된 판단과 새 학습 version을 별도로 저장한다.
6. 학습 후 memory를 저장·재로드하고 새 episode의 같은 약한 관측과 정상 관측을 다시 판단한다.

## 고정한 fixture

명확한 새 이름, 같은 관계의 반대 전제, 완전 모호 관측, 약한 반대 증거, 3edge 신규 경로, 두 갈래 신규 관계, 두 갈래 모두 막힘, edge 순서가 뒤집힌 새 인스턴스다. scenario label은 실행기 기록에만 있고 Observation에는 없다.

weak conflict는 실제 첫 edge가 막혔는데 공개 score는 -0.06, 두 번째는 열려 있고 +0.92다. 학습은 양성 예시로 편향돼 있으므로 강한 prior가 초기 상태를 왜곡할 수 있다. 정답을 알아낸 뒤 반대로 출력시키는 함수는 없다.

추가 측정은 요청한 edge의 실제 상태에 따라 +0.98 또는 -0.98을 공개한다. goal 정답이나 proof를 주지 않는다. 이 조건은 더 좋은 관측을 얻을 수 있는 경우의 수정 가능성만 검사한다. feedback만으로 항상 복구하는 능력을 시험하지 않는다.

## 성공/실패 보고

초기·수정·재방문은 별도 decision이다. 정답/오답/보류, 가정 아래 proof 유효성, 실제 assumption 진실성, 안정된 오답을 나눠 센다. 여러 조건에서 같은 fixture를 반복한 수를 고유 문제 수로 쓰지 않는다.

회로 재사용 때도 실제 group/edge 갱신이 수행되는지, 명확한 반대 전제를 넣으면 답이 바뀌는지, primitive D가 macro 호출 수로 치환되지 않는지 확인한다. graph_only는 저장된 회로 호출을 막고, no_top_down은 실제 feedback 링크 전달만 막는다. no_reexpansion은 오류 뒤 새 관측/재시도를 막으며 최초 memory와 kernel은 같다.

## 추가 유한 calibration

길이 1~4인 경로의 30개 binary world와 diamond의 16개 binary world, cold/warm와 입력 edge 순서 두 조건으로 184번 검사한다. 공개 측정은 신뢰도 ±0.92로 명확하다. 5개 topology의 합성 개발 점검이며 노이즈 분포·범용 일반화 실험이 아니다.

## 파일

각 run은 plan, events, episodes, memory 전후, summary, status, manifest를 갖는다. 실제 출처는 source hash로 가리킨다. 기존 가설의 Claim ID를 갱신하는 작업은 자동으로 수행하지 않는다. EXP-01~07의 넓은 평가를 이 실행으로 완료 처리하지 않는다.
