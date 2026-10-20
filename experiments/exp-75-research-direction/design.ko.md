# EXP-75 / R29 A-0 고정 설계

질문은 **같은 tick 안의 구조적 중복을 순서·feedback·입력 bit까지 보존하며 공유할 기회가 있는가**다. R25의 고정점 이후 시간 반복 생략, R28의 판정식 변환과 구별한다. 이번에는 native 추론·학습·세계측정·runtime benchmark를 실행하지 않는다.

Program은 기존 `make_program`의 chain2(edge2,path[0,1]), shared_bypass(edge6,paths[0,1,2,5]/[0,3,4,5]), 기존 R19 lower/upper 생성기로 고정한다. shared_bypass는 기존 생성기로 만든 명시적 전체 경로 Program이며, R16의 저장된 어느 최종 kernel 기록과 같다고 주장하지 않는다. Config는 R26의 frozen kernel 전체를 사용한다. 네 Program JSON과 전체 source SHA를 실행 전에 저장한다.

각 Program의 feature input은 spec에 명시한다. 동일 drive 조건은 +4/-4/+0/+0.4, 나머지 네 조건은 +4 배경에서 한 input만 +3.2/-4/nextafter(4,0)로 바꾸거나 그 input의 initial만0.25로 바꾼다. 기본 initial은 모든 group0.5, goal drive는0이다. 비대칭 대상은 chain2 e:0, shared_bypass e:1, lower f0, upper promoted로 미리 고정한다. 이는 구조 보호 대조이며 자연 입력 분포나 독립 정확도 표본이 아니다.8조건의 순서와 모든 bit 값은 frozen_spec.json에 고정했다.

4Program×8조건=32query를 각 Program별 한 case process에서 순차 분석한다. source/입력 확인, 정적 partition 생성, 별도 pair-elimination 검증, 결과 저장 뒤 audit로 전체32행을 다시 확인한다. 전체600초·stage60초·worker1·retry0, AS512MiB·parentfile32MiB/child16MiB·raw128MiB 종료 시 soft 합계 검사를 기존 R22 runner로 적용한다.

수용 기준은32조건 누락/중복 없이 frozen 입력과 결속되고, source 순서/중복/feedback/bit를 보존하는 충분조건·그 규칙 내 최대 class·투영 작업량을 검산하는 것이다. 기회가 전부0이면 이 경로를 종료한다. 적어도 한 조건에서2개 이상 node를 공유할 수 있으면 A-1 계약 심사의 준비 조건을 충족한다. 이는 실제 group 연산을 생략했다거나 빨라졌다는 뜻이 아니다. invalid proof·binding·coverage·작업량·범위 위반은 실패이고, 불명·상한 초과도 그대로 종료한다. Program/drive/initial/반복 수를 결과 후 바꾸지 않는다.

native tick/settle/recorded settle과 World.measure는 실행 시 금지 함수로 교체하고, 분석 코드는 이 함수를 호출하지 않는다. 학습 API도 호출하지 않는다. 준비 단계의 별도 합성 fixture는 동일/비대칭·중복 link·순서·signed zero와 false positive/false negative를 검사하며32census 결과를 로컬에서 미리 분석하지 않는다. 정적 검산·봉인의 CPU/wall은 연구 실행 비용으로만 기록한다.

다음 A-1은 최대64settles의 별도 프로토콜이 필요하다. 이 A-0 요청에는 native adapter, 수치 trace, 성능 판정, 학습·기억 갱신이 포함되지 않는다. 학습·실제 수명·총비용 연결 없는 양성 결과는 compiler의 기회 확인으로 한정한다.
