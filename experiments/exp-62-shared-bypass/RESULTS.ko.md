# EXP-62 / r16 결과: 회로 내부 우회 출구는 보존됐지만 계산 tick은 늘었다

현재 learner로 표현 가능한 비중복 과제로 공유 줄기·내부 갈림길·재합류·공통 마지막 edge를 가진 graph를 선정하고, AI Research SSH 서버에서 작은 기술 확인을 완료했다. 세 번의 native 양성 학습으로 길이 2 pattern 하나가 형성됐고, 여섯 frozen 평가 모두 정답·proof validity·가정의 사실성·답 채택을 보존했다. 학습 ON은 expansion을 줄였지만 kernel tick은 두 경우 모두 증가했다. **안전한 구조 재사용의 기술 확인은 통과했고, 계산 효율 향상은 관측되지 않았다.**

## 관찰과 비용

학습 경험은 서로 다른 episode ID의 길이 2 양성 chain 세 개다. 각각 외부 reference 프로세스의 검증과 기존 native feedback을 거쳐 pending 증거 1→2→3 뒤 circuit 하나가 형성됐다. host가 pattern·strength·memory를 직접 작성하지 않았다. 학습한 것은 역할화된 양성 경로이며 세계 사실 교정이나 새 탐색 정책이 아니다. prior_gain=0, pattern_lengths=[2], route_only와 나머지 EXP58 설정을 형성 전부터 고정했다.

| 고정 과제 | 조건 | 채택 값 | expansion | kernel tick | raw inference wall(초) |
|---|---|---|---:|---:|---:|
| 열린 우회로 | 학습 ON | True | 4 | 168 | 0.034924 |
| 열린 우회로 | 같은 기억 OFF | True | 6 | 71 | 0.012999 |
| 열린 우회로 | 미학습 ON | True | 6 | 71 | 0.012629 |
| 모두 막힘 | 학습 ON | False | 5 | 156 | 0.034048 |
| 모두 막힘 | 같은 기억 OFF | False | 6 | 64 | 0.012357 |
| 모두 막힘 | 미학습 ON | False | 6 | 64 | 0.011936 |

False는 채택 거부가 아니라 실제 False 답의 채택이다. 여섯 조건 모두 accepted=True이며 외부 world의 정답과 일치했다. OFF와 미학습 ON의 정수 비용은 각 과제에서 동일했다. 이 표의 wall은 native inference 비용 필드이며 별도 프로세스 시작·reference·journal 저장·audit·봉인의 전체 시간과 다르다. 한 번의 고정 순서 실행이므로 속도 차이의 통계적 근거로 사용하지 않는다.

학습 ON의 첫 macro는 두 과제 모두 slot [0,1], 즉 S→A→B였고 첫 expansion의 추가 frontier에 [0,3], 즉 S→A→C가 실제 남았다. 먼저 탐색한 B→J가 막힌 뒤 negative_requires_dependency_coverage가 기록됐다. 열린 우회로에서는 최종 proof의 가정이 정확히 e0/e3/e4/e5였고 primitive dependency depth는 4였다. 모두 막힌 경우에는 두 공개 경로를 각각 차단하는 e2/e4를 근거로 False를 채택했으며 depth는 2였다. 경로 inventory를 최종 근거로 대신하지 않았다.

## 사전 예측 판정

- 첫 macro와 내부 side-exit 보존: 두 authored 조건에서 supported.
- 올바른 판단·truthful proof·채택 보존: 여섯 조건에서 supported.
- 잠정 False 뒤 coverage 유지 및 열린 우회 경로의 실제 최종 근거 연결: supported.
- expansion 감소: 열린 경우 6→4, 모두 막힌 경우 6→5로 supported.
- 계산 tick: 각각 71→168(+97), 64→156(+92). 감소는 관측되지 않았다. 학습 비용을 추가해도 tick 기준 이점은 이 조건에서 성립하지 않는다.

## 기술 수용과 검증

Python 3.12.3, host ip-172-26-4-106에서 준비·학습·평가·독립 검산·봉인까지 4.813768674초가 관측돼 600초 상한 안에 완료했다. train 3회, feedback 3회, evaluation 6회, 자동 retry 0회, 순차 numeric worker 1개다. 17개 stage가 모두 exit 0이며 실행 후 launcher PID 8625가 없음을 확인했다. 하위 프로세스 주소 공간 상한은 512MiB였으며 peak RSS·에너지는 측정하지 않았다.

기존 packet_states와 verify_candidate로 training/evaluation journal과 finish branch, 학습 feedback의 정확한 연장, memory chain, 설정·관측·mode·switch·예산·source binding을 별도 audit 프로세스에서 검산했다. 외부 BFS 및 proof checker로 정답·근거·가정의 사실성을 재검사했다. 답과 proof depth를 바꾼 두 변조를 거부했다. 서버 시작·종료 source 불변성 검사와 로컬의 72개 source hash 대조가 통과했다. 로컬로 가져온 summary/result는 서버 raw manifest의 SHA-256과 일치했다. 로컬에서는 native inference를 실행하지 않았다.

원자료 전량을 로컬에서 다시 재생한 것은 아니다. 서버의 전체 raw ZIP은 `/home/mcpops/hcc-native-bypass-20261018-r16/evidence.zip`이며 SHA-256은 `6e792abf0e4f2b3cf89c2f2441b4fd0cdeae45e41bd7dfa5ffe1ce8624e9849c`, 크기는 1,317,533 bytes다. 다운로드 준비 카드는 생성됐지만 파일을 기기에 저장한 상태로 보고하지 않는다. 로컬 보존한 선택 결과·실행 시간·source/raw manifest·검사 기록은 [evidence 폴더](../../evidence/native-bypass-20261018-r16/)에 있다. 원자료 재검산 진입점은 동결 source의 `PYTHONPATH=src:. python3 -B tools/r16_shared_bypass/probe.py --phase verify --out runs/technical`이다. 이 명령은 native inference 없이 원자료에서 집계를 다시 계산한다.

실행 전 로컬 검사에서 sys.path 우선순위 때문에 루트의 hcr.py가 package를 가려 import가 한 번 실패했다. src 우선순위로 고친 뒤 typed config·두 경로·외부 BFS 정답·학습 episode 구분·구문 검사를 통과했다. 이때 native 실행은 없었으며 서버 연구 코드·조건의 사후 수정이나 재실행은 없다. 엔진은 변경하지 않았고 전체 core 회귀는 이번에 실행하지 않았다.

## 해석과 다음 결정

EXP44의 dead-end 분기나 EXP58~61의 분리된 완결 경로와 달리, 이번에는 macro 내부 노드의 대체 출구와 재합류가 최종 행동에 연결됐다. 다만 원래 workspace의 출구 보존 규칙을 기존 learner와 결합한 한 구조적 family의 기술 확인이다. 학습 ON/OFF는 binding·pool·macro 전체의 개입이며, strength 효과·inhibition 단독 효과·새 정책 발견을 분리하지 않는다. 정확도가 대조군보다 높아진 것도 아니다.

두 world와 여섯 실행을 여섯 독립 일반화 표본으로 세지 않는다. 정식 holdout, 학습 비용 회수, 물리 효율, 범용 AI 우위는 미확립이다. 기술적 표현 가능성과 검사 경로는 확보됐지만 **효율 우위 확인을 목적으로 같은 조건의 반복을 확대할 근거는 없다.** 후속 확인을 진행한다면 먼저 목적을 구조 다양성에서의 출구 보존·실패 경계로 한정하고, 이를 검사할 다른 family와 자원 배정을 고정해야 한다. 이번 요청에서는 큰 확인 배치나 새 최적화 기능을 실행하지 않았다.
