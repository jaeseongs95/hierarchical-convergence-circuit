# EXP-70 / r24: 저장된 완전 입력 tick 전이의 정확 재사용 가능성

2026-10-19 KST, 실행 전 고정. 기준 main2175fb7b. 방향성 토론의 조건부 판정은 DIRECTION.ko.md에 보존한다. 이번에는 native cache나 새 AI 학습을 구현하지 않는다.

## 질문과 입력

r19가 기각한 경계 생략형 국소 대체와 달리, **전체 입력을 보존한 수치 전이의 정확한 반복이 저장 궤적에 남는가**를 묻는다. 기존18case JSON을 해시로 고정하고 corrected r19 audit_execution으로 다시 수식 검산한다. bottom_up/coupled 각6case의36settle·988tick을 분석하며 separate_algorithms6case에는 전이가 없다. 그것을988에 더하지 않는다. 원래 고정 case→arm 순서를 각 arm에 투영하고 kernel/tick 순서를 유지한다. 입력 목록·순서·hash는 frozen_spec/input_manifest에 고정한다.

원 r19 run은 프로그램 tuple/JSON 배열 비교 오류로 FAILED_AT_AUDIT였고 저장 재생 수정 뒤 검산했다. Windows 재생의 사후 허용오차1e-15 및 실행 후 전체 source 재해시 미수행 이력을 보존한다. r19의 수신된 source preflight manifest에 현재 dynamics·원 spec과 보존된 executed-probe bytes를 결속해 기록에 없는 top_down 기본값 등의 출처를 확인한다. 이는 실행 후 전체 source 재해시가 아니다. r24는 이 이력을 성공으로 바꾸는 재실행이 아니다. r24에는 별도로 PRE 절대오차1e-15·상대오차0을 고정한다. 이 오차는 수식 재생만의 허용치이고 key/next-state bit 비교에는 적용하지 않는다. 기존 입력과 native Cost·convergence는 불변이다.

## 완전 key와 시간 경계

key는 순서 있는 Program(groups/links 목록 순서 포함), Config 전체, 전체 current, drives, top_down=True와 동결 dynamics source SHA를 포함한다. key는 타입 tag가 있는 JSON bytes이며 float.hex로 signed zero와 모든 이진64 부동소수 값을 보존한다. dict key 순서는 정렬하되 list 순서는 바꾸지 않는다. bool/int/float를 서로 합치지 않는다. SHA는 기록용이고 조회는 key 원본 bytes를 비교하는 Python dict로 하여 hash 일치만으로 hit를 만들지 않는다. 같은 key에 저장 next-state bit가 다르면 ValueError로 중단하며 근사·새 key·재실행으로 전환하지 않는다. 단일 호스트·동결 source의 분석이며 플랫폼 간 exact 실행을 보증하지 않는다.

첫 current는 저장 initial, 이후는 직전 저장 tick state다. 해당 행의 state는 next-state이므로 key에 미래 출력처럼 넣지 않는다. miss 때 현재 저장 전이를 읽어 삽입하고 다음 항목부터만 조회한다. hit의 저장값은 먼저 들어온 과거 항목에서만 얻으며 현 next-state는 그 뒤 적중 검증에만 사용한다. 전체 trace를 미리 index하지 않는다. 파일 자체는 분석 프로세스가 미리 읽을 수 있으나 lookup index에 미래 항목을 넣지 않는다.

tick의 수치 출력만 후보다. residual·stable_steps·history·margin·진동·남은 budget·종료는 해당 controller의 책임으로 남으며 이 분석에서 건너뛰거나 cache에서 복사하지 않는다. Cost 증가와 trace 이벤트도 수치값만으로 대체했다고 주장하지 않는다. 원본 next-state·convergence·readout·Cost의 전체 일관성은 별도 scalar audit로 확인한다.

## cache 수명과 귀속

비교 arm별로 cold한 분석용 index를 새로 만들고 종료 뒤 폐기한다. 두 수명을 각각 분석한다.

- `case_local`: 원 r19의 case별 subprocess 수명에 맞춰 case마다 cold. 같은 case 내 kernel 사이에는 유지한다.
- `arm_stream`: arm 전체6case에 유지하는 가상 긴 process 수명. 원 실행에서 실제 제공된 process-local 기회와 다르며 추가 저장/공유 경로의 비용이 미해결이다.

988전이를 두 가정에 분석해 analytical row1,976개를 얻는다. 원전이·표본을1,976개로 늘려 세지 않고 수명별 결과도 합산하지 않는다. 각 hit는 **첫 삽입된 원 항목**으로 동일settle/동일case 다른settle/교차case를 나눈다. 새 invocation인데 프로그램·config·initial·drive·flags·source SHA 전체가 같으면 repeated_kernel_invocation으로 표시한다. 같은 invocation의 반복 state는 이 항목으로 세지 않는다. 공개 measurement/context 동일 여부도 교차 집계한다. ID만 다른 paired fixture와 전체 kernel 반복의 기여를 숨기지 않는다. first-origin 집계이므로 arm_stream에서 과거 case가 원점인 hit가 case_local의 내부 반복과 다른 분류를 받을 수 있다.

index 최대2,048항목, logical payload16MiB다. payload는 key bytes·next-state 직렬화 bytes·origin locator bytes·kernel header bytes·공개 숫자 signature bytes의 합으로 정의한다. 공유 객체와 Python allocator·dict overhead·원자료/이벤트 목록·시스템 RSS를 포함한 실제 RAM이 아니다. OS AS512MiB 제한과도 구별한다. 상한 초과면 중단하며 eviction 정책을 사후 도입하지 않는다.

## 비용과 판정

hit/miss·국소성·반복 귀속·key 생성 bytes·key SHA 횟수·next-value binding SHA 횟수·조회·복사 값 수·삽입 수·payload peak를 기록한다. key/hash/lookup/copy-store/저장값 검증의 구간 wall과 분석 전체 CPU/wall을 나눈다. 값의 복사는 float가 불변인 shallow dict 복사다. 부분 구간 합은 모든 Python 비용의 전수 계수가 아니다. origin/보고서 구성·case reset/종료·추가 직렬화·파일 I/O는 전체 분석/단계 시간에 남는다. stored-value 검증은 알려진 저장 결과를 대조하는 연구 비용이며 실제 online cache에 정답 채널이 있다고 가정하지 않는다.

hit의 group 수·활성 link 수·normalization 수는 **생략 가능한 수치 산술의 상한**이다. native tick 호출 자체와 Cost 부작용·trace·수렴 제어까지 생략했다는 뜻이 아니다. 원988tick과 비용을 수정하거나 상한을 CPU·금액·에너지로 환산하지 않는다. 신규 측정·label·학습0이다. r19 원 학습도0이며 학습 포함 비용 회수·현실 반복률·일반화는 미판정이다.

동일 key 출력 bit 충돌·입력 provenance 불명확은 후보 실패다. hit가 없거나 전부 의도된 전체 kernel 재실행/가상 cross-process 수명뿐이면 선별로 종료한다. case_local에서 repeated_kernel_invocation을 제외한 기회가 남아도 즉시 효율 성공으로 세지 않고, 관리 부담을 고려할 가치가 있을 때만 별도 소규모 native 대조의 후보로 둔다. 고정점 주변 몇 번의 반복만 남으면 그 좁은 성격도 공개한다.

## 검산·자원·추적

새 native tick/settle/World.measure와 원 settle_one을 실행 시작부터 금지한다. pure preparation은 합성4전이로 완전 key6필드·signed zero·근접float·타입·case reset·cross-arm cold·출력충돌·수명/귀속·상한과 변조 거부를 검사하며 실제988전이 census를 하지 않는다. 서버 census 한 단계 뒤 별도 audit가 다른 tuple/IEEE754 표현 index로 적중·원점·bit 출력·귀속·비용식을 대조한다. hit decision/key/origin/산술상한/합계 변조5종은 정확한 거부 사유까지 검사한다. 이 검산도 실제 native 실행이나 독립 연구 표본이 아니다.

기존 r22 bounded runner를 새 spec/entry로 재사용해 준비→census→audit3단계를 실행한다. worker1·retry0·전체600초·stage60초, 부모 AS512MiB/개별파일32MiB, 자식 AS512MiB/개별파일16MiB, stage 종료 raw128MiB soft 검사다. hard disk quota·peak RSS·SIGKILL/디스크 정지시 봉인을 보증하지 않는다. 부모와 준비 child의 getrlimit을 확인하며 모든 child의 개별 측정을 주장하지 않는다.

전송 전 ZIP/source/spec/design/입력 hash를 고정하고 새 전용 폴더를 사용한다. 소유자 승인된 정확한 요청을 한 번 조회해 이어가며 재요청하지 않는다. 도구에 없는 approvedAt/actor는 만들지 않는다. 원자료/source 전후 SHA·수신 JSON과 미수신 로그/ZIP 범위를 구별한다. 결과를 보고 입력·기준·코드를 바꾸거나 재실행하지 않는다. 방향 토론은 구현 최종 감사나 포털 승인을 대신하지 않는다.
