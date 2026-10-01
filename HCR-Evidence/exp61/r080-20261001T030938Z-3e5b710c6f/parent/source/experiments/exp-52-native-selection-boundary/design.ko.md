# R071: native 선택 경계의 민감도

R070에서 회로 약화는 pool 계산에 전달됐지만 기존 threshold에서는 선택이 같았다. 이번에는 threshold별 빈 memory에서 동일한 native 형성·약화 절차를 수행하고, 유효한 대응 checkpoint에서 선택이 달라지는지 검사한다. core와 기존 evidence는 보존한다.

## 실행 전 동결한 조건

threshold는 기본값 0.55와 R070의 두 activation 사이 중간값 0.9940565651611166이다. 이 경계는 기존 자료를 본 뒤 정한 설계 입력이다. 독립 사전 발견의 성공으로 세지 않는다. threshold가 전체 config signature에 포함되므로 기존 memory를 재서명하지 않는다.

각 config의 empty memory에서 R063의 서로 다른 positive training 세 개를 실행한다. 이어 같은 topology·score(e0=1.0,e1=0.8)를 가진 donor 두 개에 별도 authored world(e0=True,e1=False)로 산출한 피드백을 각각 한 번 적용한다. donor episode ID는 r071-donor-1/2로 서로 다르게 동결한다. 첫 약화 뒤 M0, 두 번째 뒤 M1을 저장한다. R064 correction/revision은 생략하며 R069 전체 memory의 재현을 주장하지 않는다.

예상 circuit strength는 0.55→0.11→0.022, evidence episodes는 세 개, balance는 0.75다. 두 donor의 실제 reuse·오답·weaken과 native feedback binding을 검산한다. config별 같은 단계의 pattern/program·strength·episodes·active·version·failures·pending 상태를 비교한다. config signature, memory/patch hash와 전체 provenance의 동일성을 강제하지 않는다.

네 평가에는 동일한 revision=1 observation을 새 세션에 전달한다. route_only, circuit gate ON, top_down, 예산과 kernel은 같다. 평가 뒤 feedback은 적용하지 않는다. 기본 threshold에서는 M0/M1 모두 circuit, midpoint에서는 M0 circuit/M1 primitive가 예측이다. 네 판단은 True 오답을 유지할 것으로 예측한다. midpoint-M1 expansions는 2, 나머지는 1이다. 정수 비용과 wall time의 단위는 분리한다.

## 검산과 실패 경계

생산 worker는 authored world를 읽지 않는다. 별도 evaluator process가 후보의 외부 평가를 산출하고 exact finish packet에 피드백을 소비한다. 모든 생성·전이·학습을 independent session formula로 재생하고 pool과 decision을 각각 재계산한다. 별도 process는 원자료의 선택·readout·비용과 summary를 대조한다.

형성·donor reuse·약화가 없으면 checkpoint_construct_not_engaged로 기록해 선택 가설을 판정 불가로 둔다. 대응 checkpoint·stable pool·동일 계산 입력과 mismatch 조건이 유효한데 예상 선택이 없으면 선택 예측을 falsified로 기록한다. 가설 지지는 구현 수용의 필수 조건이 아니다. runtime, budget, schema, binding 실패는 별도로 보존하고 threshold 조정·추가 학습·retry로 숨기지 않는다.

원클릭 Run-HCR-R071.cmd는 조건/source 동결→계약 selftest→native 형성 및 네 평가→독립 검산과 변조 거부→기존 core 회귀 1회→bundle 봉인을 수행한다. 각 결과는 새 폴더에 저장하며 실패와 traceback을 보존한다. 새 native 준비 실행 10개와 평가 4개, 연구 피드백 10회가 계획이다. 네 평가를 독립 표본 네 개로 세지 않는다. 실제 에너지와 peak memory는 측정하지 않는다.
