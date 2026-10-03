# EXP-59 / R078: 같은 memory에서 edge 배열 순서의 native 선택 영향

## 이전 확인과 이번 질문

R077은 native feedback 3회로 길이2 pattern 하나를 형성했고 두 완결 binding S→A→G와 S→B→G에 적용했다. prior/mismatch와 prefix는 0이었다. e3 score 0·0.6에서는 [e0,e1], 1에서는 [e2,e3]를 최초 선택하고 최종 proof로 사용했다. 동률에서 앞선 binding을 택했으나 topology·공개 ID를 고정한 배열 교환에서도 비동률 선호가 유지되는지는 미해결이었다. 과거 9회 실행과 재분석은 이번 새 표본에 합산하지 않는다.

## 동결 개입

`frozen_spec.json`은 R077의 봉인 최종 memory 문서, config, world truth, episode/revision, 공개 node/edge ID, edge별 score, session budget을 고정한다. score 0·0.6·1 각각에서 원래 배열 [e0,e1,e2,e3]와 경로 블록 교환 [e2,e3,e0,e1], ON/OFF를 paired 평가한다. 새 native 평가 12회, train·feedback 0회, 독립 발견 표본 0이다. score=0의 방향성 중립 계약을 유지한다. budget은 advance 16·kernel tick 5120이며 core의 실제 자원 상한도 R077과 같다.

각 score/gate의 배열 pair에서 바뀌는 입력은 edge 배열 순서뿐이다. score 수준 간 비교는 기존 score 조건을 유지한 별도 대응이다. 관측 digest·내부 binding ID·native 후보/group 순서는 자연히 달라질 수 있으며 host가 동일하게 고치지 않는다. ON/OFF는 회로 pool·binding·reuse 전체 개입이며 inhibition의 독립 효과를 뜻하지 않는다.

## 실행 전 예측과 판정

1. 비동률 score 0·1: ON 최초 circuit 선택과 최종 proof의 실제 edge ID 경로는 배열 교환에도 각각 [e0,e1]·[e2,e3]로 유지된다. 두 score의 네 셀이 모두 충족하면 supported, 판정 가능한 셀 하나라도 다르면 falsified다. 최초 선택과 proof를 별도로 판정한다.
2. 동률 score 0.6: ON 후보 activation 차이가 동결 tolerance 2e-12 이내이고, 배열 교환이 후보 순서를 뒤집으며 최초 선택·proof는 각 배열의 첫 후보 경로를 따른다. 최초 선택과 proof의 실제 ID가 바뀌면 각각 supported다. 판정 가능한 동일 activation 조건에서 그렇지 않으면 falsified다. activation 동률이 사라지면 동률 정책 예측은 not_evaluable로 두고 상태의 순서 의존성을 기록한다.
3. OFF: 모든 score에서 실제 ID 최초 primitive 선택·최종 proof가 먼저 놓인 경로를 따라 바뀐다는 대조 예측이다. 최초 선택과 proof를 별도 판정한다. 비동률 ON의 유지와 동률/OFF의 전환을 한 통계로 합치지 않는다.

readout 없음·budget 종료·불안정 pool·두 완결 binding construct 미형성은 해당 비교의 not_evaluable이다. 입력/hash/journal 재생 불일치, host repair·추가 학습, coverage/집계 오류는 장치 실패다. 가설 반증은 장치 실패가 아니며 성공 예측을 만들기 위해 core를 수정하지 않는다. 최초 실행 실패·부분 evidence·traceback을 보존하고 자동 retry하지 않는다.

## 독립 검산과 측정

원클릭은 source와 조건·부모 evidence seal을 동결한 뒤 과거 R077 raw를 검산하고 synthetic/native-free grammar 검사, 실제 평가, raw 저장, 독립 journal·pool recurrence·경로 검산, 집계 변조 거부, 최종 core regression 1회, bundle/ZIP 봉인을 수행한다. 생산 과정은 private world·evaluator를 로드하지 않는다. 검산기는 producer를 import하지 않고 별도 process에서 기존 독립 규칙을 사용한다. source·memory·config·world hash와 slot→실제 edge ID를 검산하며 후보 membership·binding·activation·eligibility·prior/mismatch·양방향 inhibition·선택 순서·expansion·proof/readout/terminal adoption·개별 비용을 보존한다.

`D_DAG`, expansion, kernel ticks, selector/scheduler/binding 검사, wall time을 따로 기록한다. energy·peak memory는 null이다. ON의 expansion 감소를 tick·시간·전력 효율 개선으로 자동 일반화하지 않는다. 별도 연구자/독립 발견 표본은 없고, 동일 원자료의 검산은 새 독립 증거가 아니다.
