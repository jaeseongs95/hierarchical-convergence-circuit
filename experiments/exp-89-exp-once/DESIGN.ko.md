# R43 / EXP-89: 음수 분기의 중복 exp 호출 한 번을 제거한다

HIGH 방향 토론(4개 blind 관점·비원저자 교차검토·별도 fresh Judge)은 동일 음수 exp(z)의 분기 내부 재사용 한 변경을 조건부로 선정했다. 이 연구로 미세최적화 계열을 닫고, 다음 방향 검토에서는 codebook coverage를 동결한 표현 불변성 검사를 우선 후보로 삼는다. R25의 고정점 tick 생략, R30의 공간 공유, R31의 learned macro 비교, R42의 관측 외피와 다른 개입이다. 이것을 H03의 학습·압축·회로 재사용 성공으로 세지 않는다.

원래 src/hcr/dynamics.py의 음수 sigmoid는 exp(z)/(1+exp(z))이다. 연구 외피는 동일 builtin math.exp를 한 번 호출해 ez/(1+ez)를 계산한다. 양수 분기, 다른 부동소수 연산 순서, 모든 guard·원래 settle·controller·history·observer·logical Cost를 보존한다. 같은 유한 float 입력과 같은 Python/libm의 결정적 exp가 전제이며, 실제 bytes와 비용은 새 실행에서 검증한다. 근사 exp·벡터화·검증 생략·답 cache·warm start를 추가하지 않는다. 공통 엔진을 수정하지 않고 프로세스 안의 dynamics.tick 하나만 finally로 복원하는 연구 경로다. 중첩과 foreign patch를 거부한다.

correctness는 R42의 고유65 upper kernel 입력을 두 방식으로 다시 실행한130 settle이다. 이때만 exp wrapper로 실제 호출을 센다. 저장된 이전 state로 독립 복원한 G/Nnegative와 baseline=G+N, exp_once=G가 맞아야 한다. 모든 기록은 원래 Program/Config/drives/initial/tick state/residual/stable_steps/convergence/readout/Cost와 정확 canonical bytes로 같아야 한다. state key 순서도 따로 맞춘다. scalar1e-14는 별도 수식 재생에만 쓰며 짝비교를 완화하지 않는다.

추가 control은 원래 controller의 stable_ambiguous와 budget_exhausted 두 조건×두 방식=4settle이다. direct tick은12개 유효조건(양수·0·negative-zero 입력·0 양쪽 작은 값·큰 음수/양수 underflow·초기0/1·중복link와top_down ON/OFF)과6개 오류조건(missing/extra state,NaN state,범위밖 state,inf drive,unknown drive)×두 방식=36호출이다. 오류의 타입·메시지·Cost와 정상 출력/계수도 비교한다. 직접 tick 입력은 frozen_spec의 direct_tests에 사전 기록하고, 비유한 값은 descriptor로만 표현해 runtime에서 생성한다. 이 외 새로운 native 시험을 추가하지 않는다.

시간 대조는 R40 q4의8폐쇄관계표×이름2×순서2=32맥락·3반복·5셀(joint baseline/exp_once,factor baseline/exp_once,동일정보 exact baseline)이다.480기록·1920질의·192native짝이다. 각 호출은 fresh producer/initial0.5이고 모든 수치·trace를 실행한다. timing의 exp계수 probe는0이다. 원천24회와 상위34560회, correctness130회, control4회로34718settle이다. max_ticks160의보수적5554880settleticks와 direct36회를 합쳐 최대5554916tick호출이다. 학습·세계측정은0회다. 반복과이름/순서변형은 독립 일반화 표본이 아니다.

5셀의 순서는 caseindex+rep 기반으로 회전하되 모든셀의 case순서는 같다. baseline/candidate×joint/factor 네 저장기는 독립 cache/seen 수명을 갖고 입력순서·저장정책이 같다. 참조 ID는 서로 다른 n0000/n1000/n2000/n3000 영역이며 짝비교는 참조이름이 아니라 확장한 kernel+Config bytes다. 같은 bytes의 저장만 공유하고 계산은 생략하지 않는다. 네 cache192MiB·raw128MiB는 합계 상한이며 각 cache에 따로 허용하지 않는다.

총CPU 주 판정은 각기록의 core(설치·export/guard·Program/검증·tick·trace·plain/digest 포함)+저장+개별audit를 합친다. 모든 준비·countedpass·source·work/audit 잔여·부모봉인·launcherCPU를 실제관측해15arm-rep그룹(각32맥락)에 동일 배분한다. 총wall은 completion 전체(bootstrap 이미 포함)에서 측정 core/storage/audit wall을 뺀 잔여를15등분한다. launcher wall을 다시 더하지 않는다. 구성 비용의 배분이며 각그룹의 독립OS process 전체실행으로 확대하지 않는다. 단위가 다른 counter를 한 연산 수로 합하지 않는다.

두 native표현 각각 세 반복 모두 candidate/baseline 총CPU<=0.95,wall<=1.05이며 모든 품질·bytes·원장·source/raw해시·복원 검사가 맞을 때만 이 유한 연구 후보의 비용 채택이다.5%/5%는 기술판별선이며 통계유의성·제품효율·H03 증거가 아니다. 한 조건이라도 미달하면 호출감소와 비용판정을 나누어 음성으로 닫는다. 입력·기준·반복·수명·상각·상한·후보를 사후 조정하거나 native를 재실행하지 않는다. R40/R41의 음성 결과도 바꾸지 않는다.
