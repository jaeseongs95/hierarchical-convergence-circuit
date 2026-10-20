# EXP-77 / R31 결과

**고정된 길이2 path motif와 네 toy 입력에서는 일반 verified macro가 학습 회로와 같은 확장을 골랐고, 수치 activation pool의 추가 이득은 관측되지 않았다.** 모든 평가12조건이 정답·유효 primitive proof·진실한 가정을 보존했다. macro는 primitive보다 expansion을 줄였지만 최종 판단의 수치 계산은 줄이지 못했다. 학습비를 포함한 실제4회 사용에서 두 재사용군의 총비용은 무학습 primitive보다 컸다. 단회 시간의 통계적 속도 판정은 하지 않는다.

## 토론에서 이번 과제로

전체 방향 HIGH 토론이 요구한 두 후보 표현·소비·경쟁 설명 gate를 [사전 설계](design.ko.md)에 기록했다. 현재 계층 상위 Program은 scalar를 소비하고, richer 객체/역할 의미 전달은 새 표현과 소비 계약이 필요하다. 지속적인 False 예외 교정도 현재 learner 표현에 없다. 반면 실제 learned path motif는 native workspace의 multi-edge 확장으로 소비되므로 같은 경험의 일반 macro 대조가 가능했다.

EXP-25/26과 R18은 ON/OFF 및 gate 비교였다. 이번에는 동일 학습 산출물에 **일반 macro 실행 대안**을 추가했다. R18의 학습3개·평가4개·Config를 재사용했으며 새 독립 데이터셋으로 세지 않는다. prior_gain=0, pattern_lengths=[2], route_only를 고정했다. 독립 학습 알고리즘의 비교가 아니라 동일 motif의 실행 방식 비교다.

학습3회는 실제 native 추론→외부 참조 채점→Feedback→native learner 전이를 수행했다. 올바른 True proof3개로 circuit1개가 형성됐고 episode provenance3개를 별도 dict 학습 전이식으로 검산했다. 두 learned arm은 같은 memory를 받았고 primitive는 empty memory를 받았다. 평가 중 기억 변경·추가 측정·사후 임계값 조정·재시도는 없다.

## 품질과 실제 계산

| 방식 | strict 정답 | expansion 합 | 수치 ticks | group/normalization | link | 학습 포함 K4 CPU / wall(초) |
|---|---:|---:|---:|---:|---:|---:|
| hcr | 4/4 | 14 | 338 | 3172 | 3948 | 1.605399 / 1.881600 |
| macro | 4/4 | 14 | 140 | 1396 | 1968 | 1.566166 / 1.681195 |
| primitive | 4/4 | 22 | 140 | 1396 | 1968 | 0.928257 / 1.032375 |

strict 정답은 채택값이 외부 정답이며 primitive proof가 유효하고 모든 가정이 실제 참조 세계와 맞는 경우다. 모든 군이 네 입력에서 같은 품질을 보존했다. HCR와 macro는 네 입력 모두 같은 expansion edge 순서를 택했다. 두 군의 실제 재사용 확장은 각각4회다. macro의 native schema `circuit_reuses`는 인증된 multi-edge 경로 적용을 표시하며 recurrent pool 실행 횟수를 뜻하지 않는다.

입력별 hcr/macro/primitive ticks는 chain4_open 108/38/38, chain4_blocked 98/34/34, fan5_open 71/36/36, fan5_blocked 61/32/32였다. expansion은 각각2/2/4, 3/3/4, 2/2/7, 7/7/7이었다. fan5에서 초기 후보가5개라 공통 cap4로 primitive fallback한 기록도 유지했다. 이후 현재 frontier에서 허용되는 motif만 다시 검사했고 불완전 후보 목록을 승자로 쓰지 않았다.

HCR는 수치 pool6회를 추가해 macro보다198ticks·1776group/normalization·1980link 계산이 더 많았다. macro와 primitive는 최종 decision 계산량이 같았다. 이 차이는 네 조건에서 동일한 확장 순서를 선택한 정책의 비용 대조이며, 모든 입력에서 두 선택 정책이 동등하다는 증거가 아니다. 일반 macro의 >0 sign 규칙과 native activation 규칙은 서로 다른 적용 정책이다.

macro는 공짜가 아니다. hcr와 macro 모두 binding operation151회·recall10회·candidate16개를 검사했고, macro는 공개 점수12개를 별도로 검사했다. primitive에는 binding/recall/pool이 없다. topology edge 검사는 hcr/macro157회, primitive204회다. topology·binding·score·kernel 작업은 단위가 달라 하나의 연산 합계로 더하지 않는다. 현재 macro도 최종 native primitive 판단·수렴·증명을 재실행한다.

## 학습을 포함한 실제 사용 비용

| 실제 사용 K | hcr CPU(초) | macro CPU(초) | primitive CPU(초) |
|---|---:|---:|---:|
| 1 | 0.954815 | 0.941172 | 0.344809 |
| 2 | 1.170858 | 1.144014 | 0.537841 |
| 3 | 1.386609 | 1.353786 | 0.732444 |
| 4 | 1.605399 | 1.566166 | 0.928257 |

부모가 관측한 각 자식 process의 CPU와 wall을 합산했다. 모듈 import·source 검사·입력/memory 구성·회로/macro 준비·탐색/수치 계산/증명·trace/JSON/디스크 쓰기를 포함한다. learned arm에는 공통 실제 init+학습3회(외부 채점·피드백·컴파일·저장 포함)를 각각 한 번 부과했고 primitive에는 init만 부과했다. 실제 학습은 한 번 공유한 paired 회계이며 두 군을 독립 재학습한 복제가 아니다. session 부분 시간과 reference/learning 부분 시간은 부모 단계 비용에 다시 더하지 않는다.

학습 inference는 총99ticks·495group·792link였고 feedback의 compilation_items39·learning_updates3·memory_write_items7·storage_bytes7007을 별도로 기록했다. K4에서 hcr/macro/primitive의 학습 포함 ticks는437/239/140, group은3667/1891/1396, link는4740/2760/1968이다. storage_bytes는 해당 native 저장 계수이며 실제 전체 evidence 크기와 다르다. 별칭(signal_events 등)을 중복 합산하지 않는다.

K=1..4 어느 실제 prefix에서도 학습 포함 process CPU 비용 회수는 관측되지 않았다. macro의 평가만 보아도 process CPU 합계가 primitive보다 컸다. 고정4회보다 긴 수명·상각·손익분기점을 외삽하지 않는다. 짧은 단회 process 시간에는 import·계측·저장과 타이머 분해능이 포함되므로 통계적인 시간 우위를 채택하지 않는다. 준비·별도 audit·봉인·호스트 orchestration은 위 군별 사용 비용과 분리한다.

## 실행과 검증

AI Research SSH 요청81072e1d… 하나를 사용했다. 이번에는 owner-reviewed command_set 정책이 python3 명령을 자동 허용했다. 별도 소유자 승인 대기는 없었고, 이전 회차의 high_risk/disclosure 오류를 이번 실행 사유로 재사용하지 않았다. Linux Python3.12.3에서18단계 모두 exit0, 학습3회·평가12회·실제21settles·717ticks, 봉인 포함4.400064초(상한600초), 최대 단계 wall0.316984초(상한60초)였다. worker1/retry0, World.measure0, AS512MiB·parentfile32MiB/child16MiB·raw 단계 peak956940bytes를 확인했다.

준비 구조 검사40개가 통과했다. 초기 합성 fixture에서 AdaptiveConfig를 Config용 make_pattern에 전달해 `AttributeError: 'AdaptiveConfig' object has no attribute 'relation_gain'`가 발생했으며 cfg.kernel로 수정한 뒤 통과했다. 당시 native 추론·settle·학습은0회였다. 실제 서버 실험을 결과 후 수정/재실행하지 않았다.

수신15session의 hash chain·입력/기억/역할·독립 DFS matching·Program/drive 문법·side branch 보존·scalar/controller·최종 readout/proof·실제 작업량·학습 전이를 재생했다. 서버/로컬 최대 수치 오차는0(허용1e-14)이었고, 입력 revision·memory version·tick·cost/decision binding·후보 정렬·역할/분기·macro eligibility의 재봉인 변조7종이 모두 거부됐다. 로컬 native 추론·학습은0회다. 작성자 CS3의무 및 bundle check43개 raw 결속은 PASS이며 독립 감사나 호스트 인증이 아니다.

269개 고정 source의 로컬 bytes는 불변이다. 수신 manifest 대상 JSON23개 중22개는 정확한 SHA-256이 일치했다. source-postcheck 하나에서는 전송 adapter가 이미 고정된 문서 경로 theory/source/HCC_habit_fixed_schema_20260917.md를 `[REDACTED:entropy:45].md`로 바꿨다. 수신 원문을 수정하지 않았고,269개 모두 True인 응답과 고정 source 목록의 유일한 key 대응으로 만든 **별도 canonical reconstruction**의 SHA가 manifest의 원본 SHA와 일치했다. 이를 원본 파일을 그대로 수신했다고 표시하지 않는다. [수신 검증](../../evidence/macro-control-20261020-r31/receipt-verification.json)과 별도 재구성 파일에 구별해 보존했다.

same-channel manifest와 원자료의 내부 일관성 확인이다. upstream SSH 완전성은 unknown이며 독립 host attestation은 없다. 서버 evidence ZIP205778bytes 자체와36개 stdout/stderr는 수신하지 않았다. 실패·원자료를 숨기지 않았으며 [분석](../../evidence/macro-control-20261020-r31/analysis.json)과 [로컬 검산](../../evidence/macro-control-20261020-r31/local-verification.json)에 비용/검증을 연결했다.

## 연구 방향에 반영

이번 고정 path2 범위에서는 회로의 확장 감소를 일반 verified macro로 설명할 수 있다. 현재 수치 activation pool이 같은 확장을 더 적은 계산으로 수행한다는 추가 이득 예측은 지지되지 않았다. 무학습 primitive보다 학습 포함 총비용이 줄었다는 주장도 닫는다. 새로운 threshold/gate 튜닝으로 이 음성 결과를 구제하지 않고 연구용 pool 치환을 production이나 core에 도입하지 않는다.

프로젝트의 공통 primitive·Graph↔Circuit·수정 가능성이라는 큰 방향은 유지한다. 다만 다음 효율 주장에는 일반 macro를 필수 경쟁 설명으로 두고, 실제로 생략되는 판단 계산과 준비/학습비를 입증해야 한다. 다음 작은 연구를 고르기 전에는 richer 객체/역할 의미가 상위 계산에서 어떻게 소비되는지, 동일 confidence·다른 역할·미학습 조합에서 어떤 예측이 갈리는지 먼저 표현/소비 계약으로 고정한다. EXP-27의 typed proof memo와 동등한 packet 전달만으로 H02를 새로 검증했다고 부르지 않는다. 지속 예외 교정은 저장할 조건과 실제 소비 경로가 생기기 전까지 이론 반증 실험으로 실행하지 않는다.

이 결과는 고정 authored path 문법·단일 공유 학습·재사용된 네 toy 관측의 실행 비교다. 일반 학습 이론, 임의 DAG 학습, 계층 의미 일반화, 생물학적 회로, LLM·하드웨어·에너지 또는 범용 AI의 증거로 확대하지 않는다.
