# EXP-64 / r18 결과: 사전 차단은 품질을 보존했지만 비용 우위 조건은 찾지 못했다

AI Research SSH에서 학습3회·평가16회와 별도 검산·봉인을 7.888484210초에 완료했다. 현재 관측만 읽는 사전 조건으로 네 case 중 세 case의 회로 검색을 차단했고, 16개 평가 모두 정답·증명·가정의 사실성·실제 답 채택을 보존했다. 그러나 허용한 단순 chain에서도 ON은 OFF보다 비쌌다. **필터는 항상 ON의 비용 일부를 줄였으나, 실제 K=1..4 모두에서 학습 없는 OFF의 비용을 회수하지 못했다.** 이번 조건은 기능 확인을 통과했으며 비용 우위 조건으로는 채택하지 않는다.

## 비용을 지불하기 전의 조건

r17의 pool overflow 복귀는 binding scan 뒤에 일어났다. 이번 비중복 개입은 기존 `use_circuits` 호출 경계 앞에서 전체 session의 회로 사용을 정하는 wrapper다. src·학습 규칙·기존 설정은 바꾸지 않았다. native memory 문서는 이미 읽으므로 그 비용은 남으며 recall/binding/pool을 시작하기 전에 차단한다.

compiled memory가 있고, public score가 모두 정확히 +1이며, 전체 edge가 하나의 단순 start→goal chain이고 길이가 motif 길이2의 두 배 이상이면 ON이다. 그 외에는 원래 primitive 추론으로 실행한다. 현재 고정 한도에서는 허용 chain 길이가4다. gate는 답을 반환하지 않으며 strength·case ID·외부 world·답·실행 후 비용을 읽지 않는다. chain 확인 자체는 O(E) 계산이고 무료로 취급하지 않았다.

학습은 서로 다른 양성 길이2 경험 세 번의 native inference→별도 reference→native feedback으로 회로 하나를 형성했다. 항상 ON, 사전 필터, 같은 학습 memory의 OFF, 빈 memory의 미학습 OFF를 네 case에 각각 실행했다. 실행 목록은 미리 고정했으며 case마다 arm 시작 순서를 회전했다. public score 부호와 truth가 일치하는 authored fixture이므로 잘못된 관측에 대한 보호를 입증하지 않는다.

## 품질과 실제 차단

| case | 사전 필터 | 이유 | OFF→필터 expansion | OFF→필터 kernel tick |
|---|---|---|---:|---:|
| chain4_open | 허용 | 단일 양성 chain, 두 macro 기회 | 4→2 | 38→108 |
| chain4_blocked | 거부 | 확실한 양성 측정 아님 | 4→4 | 34→34 |
| fan5_open | 거부 | branching | 7→7 | 36→36 |
| fan5_blocked | 거부 | branching | 7→7 | 32→32 |

각 case의 네 arm 모두 accepted=True이며 open은 True, blocked는 False를 실제 채택했다. 정답, proof validity, 가정의 사실성이 모두 통과했다. 서버의 별도 audit가 gate 기록과 public 입력을 다시 연결하고 독립 구조 판정식, native 생성 전의 시점, 실제 switch를 확인했다.

세 거부 case에서 recall_checks·binding_checks·pool_calls가 모두0이었다. 필터의 native 정수 비용은 허용 case에서 항상 ON, 거부 case에서 학습 OFF와 같았다. 두 OFF의 native 정수 비용도 모든 case에서 같았다. 이는 gate 검사 자체가 무료라는 뜻이 아니다. 네 case 합계 metadata read4, edge record read14, chain link4이며, gate 자체 CPU 약44.088µs·wall 약50.506µs가 별도로 관측됐다. 이 시간은 아래 프로세스 비용 안에 이미 포함돼 있다.

단순 chain의 두 macro는 expansion을 줄였지만 kernel tick은 38→108, group update는342→902, binding check는0→16이었다. **재사용할 구조가 있다는 조건과 총계산을 아낀다는 조건은 다르다.** 이 결과로 조건을 사후 수정하거나 재실행하지 않았다.

## 학습을 포함한 실제 비용

공통 init와 train/reference/feedback9단계를 관측해 세 학습 전략에 같은 학습 비용을 한 번씩 배분했다. 이는 세 개의 독립 학습 반복이 아니다. 미학습 OFF에는 init만 부과했다. 실제 실행한 case 순서의 prefix K=1..4만 비교하며 K>4 손익분기를 외삽하지 않는다.

학습 inference+feedback의 native 비용은 tick99, expansion6, group update495, signal transmission792, compilation item39, learning update3, memory write item7, storage byte7007이었다. storage byte는 feedback에 기록된 누적 비용이며 최종 디스크 점유량이 아니다. 외부 training reference의 verification check36도 별도 부과했다. 학습9단계의 child user+system CPU는1.423001초, stage wall은1.742903초였고 공통 init CPU0.117138초·wall0.165647초는 모든 전략에 추가했다.

| 전략 | K=4 tick | expansion | binding check | pool call | group update | child CPU(초) | stage wall(초) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 항상 ON | 437 | 20 | 151 | 6 | 3667 | 2.546508 | 3.123509 |
| 사전 필터 | 309 | 26 | 16 | 2 | 2451 | 2.466264 | 3.073081 |
| 학습 OFF | 239 | 28 | 0 | 0 | 1891 | 2.445859 | 3.073381 |
| 미학습 OFF | 140 | 22 | 0 | 0 | 1396 | 0.954774 | 1.230055 |

첫 세 행에는 학습 비용과 외부 reference36 checks가 포함된다. 미학습 OFF에는 학습 비용이 없다. native 비용 벡터를 서로 다른 단위의 단일 점수로 합치지 않았으며 gate 순회 카운터도 native tick으로 변환하지 않았다. 나머지 비용 항목과 gate 시간은 summary의 prefix_totals에 있다.

| 실제 prefix K | 항상 ON tick | 필터 tick | 학습 OFF tick | 미학습 OFF tick | 항상 ON CPU(초) | 필터 CPU(초) | 학습 OFF CPU(초) | 미학습 OFF CPU(초) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 207 | 207 | 137 | 38 | 1.790664 | 1.780995 | 1.756104 | 0.318879 |
| 2 | 305 | 241 | 171 | 72 | 2.035785 | 1.994578 | 1.970073 | 0.519710 |
| 3 | 376 | 277 | 207 | 108 | 2.275913 | 2.231184 | 2.205666 | 0.738548 |
| 4 | 437 | 309 | 239 | 140 | 2.546508 | 2.466264 | 2.445859 | 0.954774 |

K=4에서 필터는 항상 ON보다 tick128·binding135·pool4를 줄였지만 expansion6·topology edge check39가 늘었다. 학습 OFF와 비교하면 tick70·binding16이 추가되고 expansion2를 줄였다. 미학습 OFF와 비교하면 학습 부담까지 남는다. 동일 품질에서 비용 일부가 줄었다는 관측을 총비용 우위로 바꾸지 않는다.

stage 시간은 import·memory load·gate·native·packet 저장을 포함한 별도 프로세스 시간이다. parent의 child 대기 polling 지연도 wall에 포함된다. cell마다 한 번 측정했으므로 작은 CPU/wall 차이는 통계적 속도 우위나 물리 에너지 절감 근거가 아니다. 평가 품질을 판정하는 별도 audit는0.967219초, source 준비는0.015288초였고 그 밖의 orchestration과 ZIP 봉인도 전체7.888484초에 포함된다. 이러한 공통 연구 비용은 각 전략의 배포 시 사용 비용에 중복 부과하지 않았다.

## 검증과 보존

host ip-172-26-4-106, Python3.12.3에서 init1+train/reference/learn 각3+eval16+audit1, 총27 stage가 모두 exit0이었다. 준비~봉인600초, 순차 worker1, child 주소공간512MiB, stage 후 raw128MiB 검사, 재시도0을 지켰다. 종료 후 launcher PID8852가 없음을 확인했다. peak RSS와 실제 에너지는 측정하지 않았다.

서버의 별도 audit 프로세스가 journal/candidate/proof/feedback/memory chain, 원 설정·관측·switch·예산, gate 시점과 독립 구조 판정, 학습 포함 누적 비용을 검사했다. 답 값·proof depth·gate 기록 변조 세 종류를 거부했다. 로컬에서는73개 frozen source의 SHA-256, 선택 summary/result/ledger의 raw manifest 해시, 16개 품질 행, 16개 prefix 비용식과 CPU/wall·gate 합을 재검산했다. training 비용을 각 raw journal에서 재구성한 검사는 서버에서 수행했으며 로컬은 기록된 training 합계에 기반한 비용식을 확인했다.

실행 전 로컬 policy 경계12개, 비용 별칭1개, synthetic prefix accounting80개, 입력·구조·설정·BFS 검사는 통과했다. 로컬 native inference나 전체 core 회귀는 실행하지 않았다. 엔진 source는 변경하지 않았다.

전체 raw ZIP은 서버 `/home/mcpops/hcc-pre-reuse-gate-20261018-r18/evidence.zip`에 보존돼 있다. 크기2,005,651 bytes, SHA-256 `2e5efef0f55c76f0db49ce090f1dba6d39c563b08395c1a2491ddcde24399759`다. 다운로드 준비는 완료됐지만 전체 ZIP을 로컬로 받거나 로컬에서 전량 재생한 상태는 아니다. 선택 결과와 source/raw manifest, stage ledger, 검산 기록은 [evidence 폴더](../../evidence/pre-reuse-gate-20261018-r18/)에 보존했다.

raw를 받은 뒤의 재검산 진입점은 `PYTHONPATH=src:. python3 -B tools/r18_pre_reuse_gate/probe.py --phase verify --out runs/technical`이며 추가 native inference를 하지 않는다. 이번 실행에서는 별도 audit를 수행했고 이 verify 명령을 추가 실행하지 않았다.

## 판정과 다음 방향

현재 구현에서 session 생성 전에 회로를 차단하고 원래 추론으로 복귀할 수 있다는 기술 조건은 네 authored case에서 확인했다. 두 topology family의 고정 네 case이며 16개 독립 일반화 표본이 아니다. 이번 필터를 production 기본값으로 편입하지 않는다.

현재 설정에서 비용을 우선한다면 OFF가 기준선이다. 다음 연구의 판단 조건은 단순한 macro 존재가 아니라 **같은 품질에서 primitive 비용보다 재사용의 binding·pool·동역학·gate 비용이 작고, 관측된 사용 횟수 안에서 학습 부담까지 회수하는가**여야 한다. 이 실험에는 그 조건을 만족한 case가 없다. 대규모 반복이나 서버 증설에 앞서 고정된 작은 입력에서 회로 ON의 실제 내부 비용이 왜 늘어나는지 분해하고, 실행 전에 얻을 수 있는 정보로 비용 차이의 부호를 예측할 수 있는지 먼저 검토하는 것이 타당하다. 다음 최적화·새 실험은 이번 결과에 포함하지 않았다.
