# EXP-71 / r25: 정확 고정점 이후 수치 산술 생략

2026-10-19 KST, 실행 전 고정. 기준 main `5f675b68f2e6d5d244567e6cade3c3eb2cccf08a`.

## 비중복 질문과 선택

R24 원수명에서 남은 재사용18회는 같은 settle의 정확 고정점 반복뿐이었다. 이번 질문은 **이 반복의 수치 산술만 생략하면 controller의 의미를 모두 보존하며 전체 실행 시간도 줄일 수 있는가**다. R24는 저장 전이의 반복을 센 분석이고, R25는 새 native baseline/후보를 실행하는 component 대조다. 전체 입력 cache·cross-case 공유·근사 종료·학습은 추가하지 않는다. R24 HIGH 방향성 토론과 결과를 근거로 좁혔으며 이번에 새 독립 토론 패널을 수행했다고 주장하지 않는다.

정책 대안은 (A) 그대로 종료, (B) tolerance로 조기 종료, (C) exact fixed point 이후 산술만 생략이다. B는 patience/history/trace 의미를 바꾸므로 제외한다. C는 종료 controller를 보존한 채 검출 비용과 절감량을 작은 비교로 반증할 수 있어 택한다. 결과를 보고 기준이나 반복 수를 바꾸지 않는다.

## 불변조건과 최소 구현

`src/hcr/dynamics.py`의 tick/settle은 수정하지 않는다. 연구 전용 wrapper가 원 settle의 전역 tick 호출만 단일 worker 안에서 일시 대체하고 finally로 복원한다. 한 invocation 안에서 프로그램은 tuple/frozen dataclass로 재구성, Config도 frozen, drive는 개인 dict의 read-only proxy, initial은 개인 복사다. 외부 callback은 받지 않고 자체 observer가 state를 복사해 기록한다. 공유 호출·동시성·공격적인 object.__setattr__·사용자 callback 변이는 지원하지 않는다. 이 경계를 범용 library API의 안전성으로 확대하지 않는다.

실제 native tick을 한 번 이상 계산한 뒤, 모든 state 값의 **타입 float 및 float.hex bit 동일성**으로 current==next를 확인한다. signed zero와 근접 float를 합치지 않는다. 다음 tick부터 불변 입력과 latched current의 bit를 확인하고 새 dict를 반환한다. 별도 tick/settle/case로 latch를 넘기지 않으며 input identity·top_down 변경이나 latched state 변이는 중단한다. hash cache나 미래 정답 preload는 없다.

수치 함수 F가 같은 binary64 state x에서 F(x)=x를 실제 계산했다면, 같은 고정 인자·연산·호스트에서 다음 입력 x의 출력도 x다. 이는 해당 폐쇄 입력 조건의 결정성에 대한 귀납 근거다. residual/stable_steps/observe/margin/oscillation/history/budget/종료는 원 settle이 매 논리 tick마다 그대로 실행한다. 조기 종료나 convergence 복사는 하지 않는다. native 호출 때 원 Cost가 증가하고, 산술 생략 때도 원래 증가할 logical Cost를 동일하게 기록한다. **논리 Cost의 불변은 물리 산술을 수행했다는 뜻이 아니다.** 별도 physical ledger에 실제 native 호출·생략·검출·group/link 산술을 기록한다.

CS 조건 `ALG-KEY-004`, `PERF-MEASURE-001`에서 도출한 3개 불변조건과 검증 의무는 별도 cs-request/constraints에 고정한다. READY는 설계·참조 구조 검사이며 구현 PASS나 독립 감사가 아니다. 준비 경계, 실제 의미 대조, 전체 비용 대조 결과를 이후 같은 조건에 대응시킨다.

## 입력과 의미 보존

R24가 고정한 기존 R19의18case·36kernels·988ticks 중 native kernel36개를 모두 사용한다. case→bottom_up/coupled→kernel의 고정 순서다. separate_algorithms는 전이가 없으므로 실행하지 않는다. 저장 program/config/initial/drives를 양 arm에 동일하게 넣고, 같은 interpreter에서 baseline과 후보의 state·전체 tick trace·residual·stable_steps·convergence·readout·논리 Cost를 타입 및 float bit까지 비교한다. 보존된 입력의 수식 재생은 기존 독립 scalar verifier로 절대오차1e-15·상대오차0을 사용하며 이 허용치를 양 arm 동등성 판정에 적용하지 않는다.

후보의 첫 exact fixed-point tick은 생략하지 않는다. 별도 검산이 저장 trace를 따라 최초 exact 고정점 위치를 구하고 이후 생략 수·물리 ledger를 대조한다. state·Cost·stable_steps·ledger 변조4종과 timing workload 변조1종이 정해진 사유로 거부되어야 한다. 준비 검사는 합성 tick stub만 사용하며 서버 자료 native 실행과 timing은 로컬에서 하지 않는다.

여기서는 저장된 각 kernel의 입력을 재실행한다. 새 category/context 정책이나 coupling drive를 끝에서 끝까지 다시 생성하는 전체 AI task 시험이 아니다. 기존 R19의 FAILED_AT_AUDIT와 수정 재생 이력·실행 후 전체 source 재해시 미완료는 그대로 보존한다. 새 양 arm 의미 보존을 과거 run 성공·일반화·센서 신뢰성으로 바꾸지 않는다.

## 비교 비용과 채택 기준

별도 correctness pass에서36kernel×2arm을 한 번 실행한 뒤 같은 process에서 timing7쌍을 수행한다. 각 block은36kernel을4번 반복한다. 짝수 block은 baseline→후보, 홀수 block은 후보→baseline이다. 순서·반복은 고정하며 결과에 따른 추가 반복·선택적 제외·재실행은 없다. 소규모 같은 process 반복 부하이고 cold-start나 현실 반복률의 독립 표본이 아니다.

timed boundary는 입력 재구성·개인 drive/initial 복사·검출기 설치/복원·모든 tick·state bit 검출·trace 복사·수렴 controller·logical charging·결과 구성·공통 counter/checksum을 포함한다. imports·입력 file I/O·최종 감사는 밖이며 각 단계 wall/child CPU로 별도 남긴다. 실제 native baseline에는 검출 wrapper가 없고 후보의 추가 부담을 차감하지 않는다. 원시 block별 process_time CPU와 perf_counter wall·순서·실제 부하·환경을 보존한다. 계측 오차/OS scheduling·작은 표본을 인정하며 통계적 유의성이나 제품 성능을 주장하지 않는다.

지역 component 채택 조건은 (1) 모든 의미/ledger 검증 통과, (2)7개 paired CPU ratio의 median≤0.95, (3)wall ratio median≤0.95, (4)CPU 개선 pair≥6/7이다. 미충족도 유효한 음성 연구 결과다. 충족해도 이 호스트·고정 부하의 후속 검토 후보이며 src 자동 편입·제품 배포·학습 포함 효율 성공은 아니다. 이번 학습/새 측정은0이며 기존 학습 비용의 상각을 새로 측정하지 않는다.

## 자원·실패·출처

correctness72 + timing2,016 = 새 native settle2,088회다. 원 입력과 같은 종료라면 총 logical tick57,304회이며 각 settle의 max_ticks160으로 도출한 보수적 상한334,080회를 고정한다. 실제 native tick은 생략만큼 적다. stage timeout60초·전체600초·worker1·retry0·학습0·World.measure0이다. 새로운 클라우드 리소스·sudo·서비스/네트워크 변경은 없다.

기존 R22 실행기를 재사용해 준비→single native matrix→audit3단계를 실행한다. 부모 AS512MiB/개별파일32MiB, child AS512MiB/개별파일16MiB, stage 종료 raw128MiB soft 검사다. 부모·준비 child limit을 기록하며 모든 child 개별 계측·hard disk quota·RSS peak·OS 실패 봉인을 보증하지 않는다. 실패면 증거를 남기고 중단하며 재실행하지 않는다.

ZIP/source/spec/design/입력 hash를 실행 전에 고정하고 새 전용 서버 폴더를 쓴다. 실제 소유자 승인된 새 R25 요청만 실행하며 R24 승인을 재사용하지 않는다. 원자료 수신 해시·remote source가 가려진 경우의 한계·미수신 로그/ZIP을 구별한다. 이 문서는 실행 전 계획이며 결과는 실행 후 별도 RESULTS와 receipts에 기록한다.
