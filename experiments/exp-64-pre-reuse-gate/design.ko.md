# EXP-64 / r18: recall 이전 사전 필터와 학습 포함 비용

## 설계와 비중복 질문

r16/r17은 품질 보존과 expansion 감소를 확인했지만 kernel tick 이점은 없었다. r17의 pool overflow fallback은 이미 binding 비용을 지불한 뒤다. 이번에는 **기존 use_circuits 호출 경계에서 session을 만들기 전에** 현재 관측으로 회로 사용 여부를 결정한다. 엔진이나 학습 규칙은 바꾸지 않는다. 이것은 학습된 gate나 검증된 비용 최적화가 아니라, 비용을 아낄 가능성이 있는 보수적 사전 필터의 작은 기술 실험이다.

허용 조건은 compiled memory가 있고, 모든 score가 정확히 +1이며, 전체 edge가 하나의 단순 start→goal chain이고 길이가 motif 길이2의 두 배 이상인 경우다. 그 외는 원래 primitive 경로로 실행한다. 현재 제한에서 허용 chain 길이는4다. 해당 조건은 두 macro를 사용할 기회와 branching/mismatch 배제를 뜻하며 tick 절감 보증은 아니다. strength·case ID·외부 world·답·실행 결과·미래 비용은 읽지 않는다. public score 부호가 truth와 같은 authored fixture이므로 현실의 관측 오류에 대한 보호를 입증하지 않는다. 조건 검사에 쓰는 edge 순회·chain 확인은 유료 계산이며 따로 센다.

gate는 전체 session의 ON/OFF를 정한다. 중간 frontier마다 다시 평가하거나 policy를 학습하지 않는다. memory 문서를 읽는 비용은 session stage에 남고, recall/binding/pool만 차단한다. 거부할 때 답을 직접 내거나 정답 solver 결과를 반환하지 않고 기존 native primitive 추론·proof·readout을 그대로 실행한다.

## 고정 입력과 대조

길이4 chain의 마지막 edge open/blocked와 r17 fan5의 open/blocked, 네 case다. 최초 세 양성 길이2 경험에서 native inference→별도 reference→feedback으로 회로 하나를 형성한다. config 전체는 r17과 같다. 항상 ON, 사전 필터(pregated), 같은 학습 memory의 OFF, 학습 없는 OFF를 비교한다. case-major이며 case마다 arm 시작 순서를 한 칸 회전한 실행 목록을 동결한다. train3/feedback3/eval16, 순차1이며 반복 timing 벤치마크가 아니다.

quality는 raw 정답, proof validity, 가정의 사실성, 실제 답 채택을 따로 검사한다. 사전 예상은 chain4_open만 gate=True이며 거부 case에서 recall/binding/pool이 0인 것이다. 허용 시 native 정수 비용은 always_on, 거부 시 learned_off와 같을 것으로 예측한다. OFF와 미학습 OFF도 비교한다. 이 동일성은 gate 자체의 비용이 0이라는 뜻이 아니다. 단순 chain에서 유효한 회로라도 학습 비용을 회수하지 못할 수 있으며 그 결과를 그대로 보고한다.

## 학습 포함 비용의 정의

실제로 실행한 공통 init와 train/reference/feedback 9개 stage를 학습 비용 T로 관측한다. 세 학습 전략에 동일한 T를 한 번씩 부과하고 미학습 OFF에는 init만 부과한다. 각 전략이 실제로 실행한 네 case의 순서상 앞 K=1..4개 비용을 더한다. 이는 공통 학습 결과의 비교용 비용 배분이며 세 개의 독립 학습 실행이 아니다. K>4의 반복·손익분기 외삽은 하지 않는다.

native 단위별 총량은 training inference의 finish decision 비용 + feedback 비용 + 평가 finish decision 비용이다. 별칭 카운터는 중복 합산하지 않고 tick·group update·binding·학습 write·byte를 하나의 숫자로 섞지 않는다. training 외부 reference의 검증 checks도 별도 포함한다. gate는 edge_records_read/chain_links_followed/metadata_reads와 CPU/wall을 기록한다. 이것은 모든 CPU 명령 수가 아니다.

프로세스 stage wall과 child user+system CPU의 T+평가 합도 별도로 비교한다. 여기에는 import·memory load·gate·native 실행·packet 저장이 포함되므로 gate 시간을 다시 더하지 않는다. source 준비, stage 밖 orchestration, 평가용 독립 audit와 ZIP 봉인은 연구 수행의 공통 비용으로 따로 공개한다. 한 번의 작은 측정으로 실행 속도나 물리 에너지 우위를 주장하지 않는다.

## 예산과 검증

서버 새 전용 폴더, 준비~검산~봉인600초, session16advances/5120ticks, worker1, stage60초/audit90초, audit+seal110초 및 seal20초 예약, child 주소공간512MiB, stage 후 raw128MiB, retry0. 이전 run·src/tests를 고치지 않는다. 로컬에서는 policy 경계·입력·원자료 집계 self-check만 하며 native 실행을 하지 않는다.

별도 audit는 기존 journal/candidate/proof/feedback/memory 검산에 더해 gate 입력·시점·실제 switch 일치와 독립적인 구조 조건, gate 거부 시 native 비용0, 비용 합과 K 누적을 검사한다. 값·proof·gate 기록 변조를 거부한다. 모든 결과를 보존하고 입력·조건을 성공에 맞춰 바꾸지 않는다. 기술 수용과 가설 성공은 별도다. 이번 범위는 이 작은 비교까지이며 production gate로 편입하지 않는다.
