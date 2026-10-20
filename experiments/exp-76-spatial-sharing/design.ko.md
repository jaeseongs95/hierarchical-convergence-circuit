# EXP-76 / R30 A-1 고정 설계

질문은 R29의 공간 공유 충분조건을 실제 대표 갱신·전체 상태 복원으로 구현했을 때 원본의 모든 관측을 보존하면서 group/link/normalization 연산을 줄이는가다. R29는 기회 분석이었고 이번에는 runtime을 대조한다. 외부 정답률·학습된 회로 효율·일반 AI 성능의 검증이 아니다.

R29의 chain2/shared_bypass/lower/upper와 동일8drive/initial 조건, Config, top_down=True를 그대로 고정한다. Program별8조건을 기존 순서대로 나열한32query에서 원본과 공유판을 각1회 실행한다. query index 짝수는 native→shared, 홀수는 shared→native다. query마다 새 process를 만들고, 공유 계획은 매 query 생성·별도 검증하며 다른 query로 재사용하지 않는다. 실제 통계적 반복은 없으므로 cold CPU/wall은 기술 관측으로만 보고하고 속도 우위 판정은 하지 않는다.

native arm은 고정 SHA의 tick을 호출한다. shared arm은 R29의 source/input/binary64 label·ordered incoming 충분조건으로 partition을 생성하고 별도 pair-elimination으로 검증한다. 실제 Program/Config/drive/initial/native source 결속을 확인한 후 대표 node에 도착하는 link만 원래 순서로 누적한다. 대표의 bias/drive·자기 state와 원본과 같은 식으로 갱신하고 모든 node를 원래 group 순서로 복원한다. source state는 복원된 전체 상태에서 읽는다. 중복 link·feedback을 없애거나 weight를 합치지 않는다. 공유가 없는 query도 같은 경로로 실행해 준비 비용과 음성 대조를 남긴다.

기존 dynamics.settle은 수정하지 않는다. 연구 process 안에서 tick만 일시 교체하고 finally로 복원한다. controller의 residual·history·stable·termination·goal readout는 원본 코드 그대로다. 실제 core 파일·기억·학습기·이전 실험은 수정하지 않는다. 동시 실행·callback 변이·실행 중 source/config/input 변경은 이 고정 단일 process 계약에 없다. 이 실험용 임시 tick 교체를 공유 서버의 서비스나 일반 병렬 runtime으로 배포하지 않는다.

수용 기준은32쌍의 매 tick 전체 state 값과 순서·residual·stable_steps·종료 status/ticks/residual/margin/stable_steps·최종 state·readout가 타입/float bit까지 동일한 것이다. 별도 scalar/controller 검산은 전체 원본 수학식을 재생하고 실제 Cost는 원본 group/link와 대표 row 수×tick으로 따로 확인한다. scalar tolerance는1e-14이고 직접 두 arm의 비교는 tolerance 없이 bit 단위다. 원본과 같은 결과가 외부 세계의 올바른 답을 뜻하지는 않는다.

실제 group update/normalization/link 전송은 실행 loop의 Cost로 기록한다. 전체 state 출력 slot과 alias copy slot도 계수한다. 각 query의 생략량을 R29의 가상 한 tick 합계와 혼동하지 않는다. scalar 검산은 연구 검증 비용이며 native 호출 수와 분리한다.

cold CPU/wall 경계는 arm 진입 직후부터 입력 deepcopy, Program/Config 구성·검증, native source SHA와 입력 binding, 공유판의 partition 생성·독립 검증·실행 index 구성, settle·전체 복원·trace/readout/result 구성과 payload JSON 직렬화1회까지다. payload 크기는 이 직렬화값의 크기다. 최종 case 파일의 재직렬화·디스크 쓰기, process import, 공통 전체 source 검사, 별도 pair/scalar 검산은 pair process 단계 비용에 포함하고 cold arm 비용에는 넣지 않는다. pair process 비용은 두 arm과 검산의 합이므로 개별 arm의 process 비용으로 나누어 주장하지 않는다. 준비 비용은 cold 내부 부분집합으로 기록한다. cache 저장·load·학습·미래 query 수명을 무료로 가정하지 않는다.

최대64settles·10240ticks, 전체600초·stage60초·worker1·retry0·학습0·World.measure0을 고정한다. AS512MiB·parentfile32MiB/child16MiB·raw128MiB 종료 시 soft 합계 검사를 기존 R22 runner로 적용한다. 준비 단계는 구조·binding 검사만 수행하며 native 추론은0회다. 새64settle은 AI Research SSH에서만 실행하고 로컬은 준비 검사·수신 raw 검산만 한다.

다른 쌍의 결과를 보기 전에 두 arm을 완료한 query는 파일로 보존하고, 오류·한도 초과·bit 불일치는 즉시 실험을 중단해 failure와 가용 로그를 남긴다. native까지 실패를 숨기는 자동 fallback·재시도는 없다. 준비 검사에는 R29의11개 구조 대조와 실제 Program/Config/source 결속 대조를 포함한다. raw audit에는 입력·trace·순서·비용·복원·timing·readout·partition·누락 query 변조9종을 고정한다.

동치 실패는 현재 shared runtime을 미채택으로 닫는다. 동치와 실제 연산 절감이 양성이어도 학습/속도/production 채택을 선언하지 않는다. 다음 단계는 실제 learner 산출물과 query 수명, 준비 비용을 회수할 사용 조건을 먼저 정의해야 한다. 결과 후 query·초기값·반복·비용 경계를 바꿔 구제하지 않는다.
