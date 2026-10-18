# EXP-63 / r17 결과: 후보 상한 초과 시 복귀는 보존됐고 tick 이점은 없었다

r16에서 내부 출구 보존은 확인됐지만 tick이 늘어난 결과를 반영해, 다음 비중복 과제로 **학습 회로 후보 풀의 수용 상한 4/5 경계**를 선정했다. AI Research SSH의 새 전용 폴더에서 학습 3회·평가 12회·별도 검산·봉인을 6.470097581초에 완료했다. 후보 5개일 때 root의 부분 후보를 활성화하거나 승자로 쓰지 않고 primitive 확장으로 돌아갔으며, 마지막 분기와 최종 답의 근거가 보존됐다. **네 조건 모두 학습 ON의 kernel tick이 대조군보다 컸다.**

## 실제 동작과 품질

현재 기본 설정과 r16의 config 전체를 유지했다. 서로 다른 세 양성 길이2 chain을 native inference→별도 reference→native feedback으로 처리해 pending 증거 1→2→3 뒤 회로 하나를 형성했다. host가 memory·strength를 작성하지 않았고 src·learner·binding 순서·상한을 변경하지 않았다. prior_gain=0이므로 strength에 의한 답 교정 실험도 아니다.

입력은 S→A 뒤 A→B1..Bn으로 갈라지고 마지막 Bn→G만 연결되는 fanout이다. n=4/5 각각 마지막 edge가 열린/막힌 world를 고정했다. 각 case에서 learned_on, 같은 memory의 learned_off, 빈 memory의 unlearned_on을 실행했다. 12개 모두 raw 정답·proof validity·가정의 사실성·실제 답 채택이 통과했다. 막힌 경우의 False는 abstention이 아니라 accepted=True인 실제 False 답이다. 두 OFF/빈 기억 대조의 판단과 정수 비용은 case별로 같았다.

후보 4개에서는 root scan complete=True, 네 binding 전부를 가진 pool network/result가 각각 하나 생성됐고 첫 macro는 [0,1]이었다. 후보 5개에서는 다섯 번째 match에서 complete=False/fallback_reason=pool_capacity였고 root pool network/result는 0개, 첫 확장은 primitive [0]이었다. 부분 match 목록은 기록만 남았으며 root의 활성화·승자 선택에 쓰이지 않았다.

이 복귀는 해당 root에서의 행동이다. 그 다음 A에서는 완결 길이2 binding이 하나만 남아 pool이 한 번 실행됐다. 5개·open은 A→B5→G macro로 답에 도달했고, 5개·blocked에서는 음성 측정으로 macro가 부적격이 되어 primitive 확장을 계속했다. 이를 전체 실행에서 circuit이 꺼졌다고 해석하지 않는다.

모든 learned_on에서 [e0,ei] 분기 prefix가 실제 expansion의 added path에 보존됐다. open의 최종 primitive 근거는 각각 e0/e4/e5와 e0/e5/e6, depth=3이었다. blocked는 유일한 목표 연결 edge e5/e6를 차단 근거로 사용했고 proof depth=2였다. 분기 inventory 자체를 최종 정당화로 대신하지 않았다. source-bound journal replay는 이 각 확장의 adjacency·visited·후보·coverage와 finish/readout 연결도 검산했다.

## 비용: expansion 감소와 tick 증가는 함께 관측됐다

| case | expansion OFF→ON | kernel tick OFF→ON | ON binding checks | ON pool calls |
|---|---:|---:|---:|---:|
| 후보4·open | 6→5 | 36→68 | 18 | 1 |
| 후보4·blocked | 6→5 | 32→64 | 18 | 1 |
| 후보5·open | 7→2 | 36→71 | 56 | 1 |
| 후보5·blocked | 7→7 | 32→61 | 63 | 1 |

초과 시 root pool을 만들지 않았어도 이미 수행한 binding scan 비용과 뒤 단계의 pool 비용이 남는다. 5개·open의 expansion 감소를 전체 계산 절감으로 바꿔 주장할 수 없다. 세 feedback 단계만 합쳐도 compilation_items=39, memory_write_items=7, storage_bytes=7007이 추가됐다. 이는 training inference·외부 reference·프로세스·저장·검산 비용 전체를 합친 수치가 아니며, 전체 학습 비용 회수를 입증하지 않는다. 세부 비용 원문은 summary와 서버 raw에 남겼다.

후보 4/5는 topology·후속 탐색 순서도 달라진다. 따라서 두 topology 사이의 비용 차이를 pool 상한만의 순수 인과 효과로 해석하지 않는다. ON/OFF는 binding·pool·macro 전체 개입이다. 각 cell 한 번의 고정 순서 실행이며 raw wall을 속도 우위의 통계 근거로 쓰지 않는다.

## 검증과 보존

host ip-172-26-4-106, Python 3.12.3에서 준비~봉인 6.470097581초로 600초 상한을 지켰다. init1 + train/reference/learn 각3 + eval12 + audit1, 총23 stage가 모두 exit0이다. 순차 numeric worker1, retry0이며 launcher PID8788은 실행 뒤 없음을 확인했다. child 주소공간 한도512MiB, raw128MiB의 stage 종료 후 검사, 검산·봉인 시간 예약을 유지했다. peak RSS·실제 에너지는 측정하지 않았다.

별도 서버 audit 프로세스가 기존 packet_states/verify_candidate와 외부 BFS/proof checker로 정확한 journal, candidate/finish branch, feedback 연장, memory chain, 설정·관측·switch·예산을 검산했다. 답 값과 proof depth를 바꾼 두 변조를 거부했다. source 시작/종료 불변성 및 로컬72개 source hash 대조가 통과했다. 로컬 선택 summary/result의 SHA-256은 서버 raw manifest와 일치했고 네 비용 차이도 다시 계산했다. 로컬에서는 native inference를 실행하지 않았다. src가 바뀌지 않아 이번 요청에서 전체 core 회귀는 실행하지 않았다.

실행 전 synthetic trace 검사3개와 7개 입력의 typed topology/설정 및 네 BFS 정답 검사가 통과했다. 첫 stdin 사전 검사에서 루트 hcr.py가 package를 가린 import 실패, 두 번째 검사에서 존재하지 않는 Observation.validate 호출 실패가 있었다. src-first 경로와 실제 Topology.validate API로 사전 검사만 고쳤으며, native 실행 전이었다. 원 연구 source·입력의 사후 수정이나 재실행은 없다.

전체 raw ZIP은 서버 `/home/mcpops/hcc-pool-capacity-20261018-r17/evidence.zip`에 보존돼 있다. 크기1,687,405 bytes, SHA-256 `e7aa421f540b0695288d777277f0d56d13cded566f23680bd640fcc6a546c34e`다. 다운로드 준비 카드는 생성됐지만 전체 ZIP을 로컬로 받거나 로컬에서 전량 재생한 상태는 아니다. 로컬 선택 결과·manifest·검사 기록은 [evidence 폴더](../../evidence/pool-capacity-20261018-r17/)에 있다. full raw의 읽기 전용 재검산 진입점은 `PYTHONPATH=src:. python3 -B tools/r17_pool_capacity/probe.py --phase verify --out runs/technical`이며 추가 native inference를 하지 않는다.

## 판정과 다음 방향

사전 예측한 4/5 경계 동작, 마지막 분기 보존, 올바른 최종 근거·채택과 OFF/빈 기억 대조 일치는 네 authored 조건에서 모두 supported다. 기본 경계에서의 품질 보존은 확인했고 tick 우위는 관측하지 못했다. 하나의 fanout family 안의 네 조건·세 arm이며 12개 독립 일반화 표본이 아니다. 일반 graph 학습·새 탐색 정책·억제 단독 효과·실세계 효율 우위를 입증하지 않는다.

다음 단계는 성공 조건을 찾는 반복 확대가 아니라 **recall/binding/pool 비용을 지불하기 전에 재사용을 허용할지 정할 정보가 현재 관측에 있는가**라는 별도 의사결정 문제로 좁히는 것이 타당하다. gate를 제안한다면 품질 손실 없는 primitive 복귀, 선택 시점에 사용 가능한 정보, training+K회 사용 총비용을 사전에 고정해야 한다. 이번에는 새 gate·최적화·상한 조정이나 큰 확인 배치를 구현·실행하지 않았다.
