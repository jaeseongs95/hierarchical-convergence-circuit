# 무작위 반복 대조와 전진 시간 변동 — r13

## Executive Verdict

**전체 완료 비용 평균은 판정 보류(`ABSTAIN_INCOMPLETE_EVIDENCE`)다.** 첫 C1만5,168tick에서 인증을 완료했고 나머지3셀은1,575초 상한에서 미완료로 남았다. timeout 소비 시간을 성공 완료 비용으로 대체하거나 완료 셀만 평균내지 않았다.

같은4,176tick 전진 구간에서 C0의 후속 반복은178.737초 더 걸렸고, 주 스레드 CPU 증가175.000초와 나머지 경과 증가3.737초로 나뉜다. C1의 후속 반복도359.114초 증가하면서 CPU278.141초·나머지80.974초 증가를 동반했다. **대기 증가만으로 이번 변동을 설명할 수 없다.** 순수 산술 고유 비용·실주파수·cache 중 어느 원인인지는 미식별이며, 과거 r11의+178.386초를 소급 설명한 결과도 아니다.

## Consensus Proposal

설계 합의 상태는 `consensus`다. 실행·검산 최종 코드18핀과 배정·실패·집계 규칙을 먼저 동결했다. 그 뒤 `os.urandom(32)`를 한 번 호출하고 첫 바이트의 독립 bit 두 개로 인접 block별 순서를 정했다. 실제 순서는 **C1→C0 | C0→C1**이었다. 반대 순서를 강제한 것이 아니며 가능한 배정은4개다. 재추첨·결과를 보고 시작을 미루는 선택은 하지 않았다. 로컬 기록은 있지만 과거에 폐기된 난수까지 없었다는 외부 증명은 아니다.

## Strong Consensus

동일 graph/model/x0/grid30/cadence16/tickcap6144/epsilon1e-6/radius1e-5와 원 C0/C1 산술을 유지했다. 첫 C1 필터는t16이다. 각 셀은 별도 cold process로 실행했고 숫자 helper에는 현재 model·whole7 box·고정 반경·epsilon만 전달했다. 미래 궤적·world 정답·anchor·시계·호스트 관측은 숫자 입력으로 사용하지 않았다. 관측기 비용은 양 정책의 소비 시간에 포함했다.

예산은4×(정책1575+평가10+공유cleanup10)+setup30+검산450=6860초, 전체6900초와 미배정40초다. 추첨부터 draw 파일 close까지0.0128616초를 실제 outer deadline에서 차감했다. 미사용분 재배정·추가 셀·재시도·수치 probe·GC/affinity/priority/power 설정 변경은 없다. 준비·보고·Git 처리는 종전과 같이 실험 실행 구간 밖이다.

## Material Disagreements

사용자는 실험 뒤 이 PC를 여러 에이전트가 동시에 사용한다고 확인했다. 함께 제공한 작업 관리자 화면에는 메모리26.3/29.7GB(89%)·CPU64%가 표시된다. 이는 공유 호스트의 자원 경쟁을 주요 환경 교란으로 해석해야 한다는 맥락이며, 실험 전 구간의 부하를 계측한 기록은 아니다. 동시 부하는 대기뿐 아니라 cache·메모리·전력 등 실행 조건을 통해 CPU 사용시간에도 영향을 줄 수 있으므로, 아래 CPU 증가를 근거로 공유 호스트 간섭을 배제하지 않는다. 무작위 순서만으로 시간에 따라 변하는 부하가 통제됐다고 주장하지 않는다.

남은 쟁점은 CPU 회계 변동의 원인이다. 같은 숫자 궤적이 같은 기계 실행 비용을 보장하지 않는다. CPU 사용시간의 증가는 계산 구간의 실행 서비스시간 변동을 지지하지만, 그 자체로 작업량 증가·주파수 저하·cache·allocator 중 하나를 확정하지 않는다. 인증이 남긴 allocation/cache 효과와 실행 환경 변화도 구분되지 않았다. 전진 차이를 단순 호스트 교란으로 빼서 보정한 속도 향상은 계산하지 않았다.

## Decision by Axis

| 셀 | 상태 | 마지막 봉인 tick | 소비 QPC(초) | Job CPU(초) | 진단 후보 정오/거리 |
|---|---|---:|---:|---:|---|
| 01-C1 | COMPLETE | 5168 | 1,276.783 | 1,174.594 | True/INSIDE |
| 02-C0 | BUDGET_INCOMPLETE | 4900 | 1,575.012 | 1,429.406 | False/OUTSIDE |
| 03-C0 | BUDGET_INCOMPLETE | 4185 | 1,575.004 | 1,441.828 | False/OUTSIDE |
| 04-C1 | BUDGET_INCOMPLETE | 4759 | 1,575.003 | 1,395.062 | False/OUTSIDE |

소비 시간은 감독을 포함한 실제 QPC 구간이다. 미완료3셀의 nominal cap 대비 감독 구간 초과는 약0.003~0.012초이며, legacy 시계에서는 최대0.016초였다. 정리·기록이 포함된 관측값으로 남기며 hard realtime 보장을 뜻하지 않는다. 각 셀의 공유cleanup10초와 전체6900초 안에서 종료·평가했고 잔존 프로세스는0이다.

| 정책 | 계획/실행 | 인증 완료 | 평가 가능 | 진단 후보 정답 | 거리 INSIDE |
|---|---:|---:|---:|---:|---:|
| C0 | 2/2 | 0/2 | 2/2 | 0/2 | 0/2 |
| C1 | 2/2 | 1/2 | 2/2 | 1/2 | 1/2 |

정답·거리 열은 알려진 authored synthetic world의 **진단 후보** 평가다. 미인증 후보를 실제 채택·성공 종료로 바꾸지 않았다. fullEngine 정확도·후속 coverage 완료는 미측정이다. 두 pair의 완료 비용 차이와 평균은 모두 미확정이며 비용 우위를 선언하지 않는다.

네 셀에 연속으로 남은 마지막 공통 닫힌 전진 경계는4176tick이다. 각 셀에서261개 창을 비교했다.

| 셀 | 공통 tick | 닫힌 전진 창 | 경과(초) | 주 스레드 CPU(초) | 경과−CPU(초) |
|---|---:|---:|---:|---:|---:|
| 01-C1 | 4176 | 261 | 968.304 | 889.219 | 79.085 |
| 02-C0 | 4176 | 261 | 1,186.581 | 1,069.141 | 117.440 |
| 03-C0 | 4176 | 261 | 1,365.318 | 1,244.141 | 121.177 |
| 04-C1 | 4176 | 261 | 1,327.418 | 1,167.359 | 160.059 |

| 동일 정책 반복 | 후속−이전 경과 | CPU 차이 | 나머지 경과 차이 |
|---|---:|---:|---:|
| C0: 02-C0→03-C0 | 178.737 | 175.000 | 3.737 |
| C1: 01-C1→04-C1 | 359.114 | 278.141 | 80.974 |

단위는 초다. 같은 정책 내 비교도 시간 순서·실행 상태가 섞인 관측이며 무작위 처리 효과로 부르지 않는다. C0의 CPU 증가175초는 user 증가179.297초와 kernel 감소4.297초를 합친 값이다. 단순 kernel I/O 증가만으로도 설명되지 않지만, 사용자 모드의 어느 연산이 느려졌는지는 분리하지 못했다.

| 공통 전진 구간 C1−C0(초) | pair1 | pair2 | 평균 |
|---|---:|---:|---:|
| 경과 | -218.277 | -37.899 | -128.088 |
| 주 스레드 CPU | -179.922 | -76.781 | -128.352 |
| 경과−CPU | -38.355 | 38.882 | 0.263 |

이 표는 **전진 구간 진단**이며 완료 정책 비용이 아니다. 전진 창은 초기 상태 저장 뒤 첫 advance 직전,128tick 블록 쓰기보다 앞에서 시작해 현재16tick 상태 저장 뒤 certificate 호출 직전에 끝난다. 수치 계산·상태 저장·history·wrapper·일부 관측을 포함하고 인증과 이후 gate 기록은 제외한다. 창은 독립 표본이 아니며 무작위 배정 단위는 네 셀이다.

## Evidence

고정450초 검산 결과는 **PASS_INTEGRITY_ONLY**다. 공통 기준 full7 상태 비교13,847건과 완료 C1의 fresh 원본 predicate323건을 대조했다. 원본 함수의 동일 전체 payload·helper핀·canonical bytes에 결속한 검산이며 과거 답변 캐시는 아니다. 부분 C1에는 최종 `timings.json`이 없으므로 그 정책의 실제 gate 기록까지 모두 검산했다고 주장하지 않는다.

완료 셀의 성공 certificate는 원본과 대조됐다. 원장의 `successful_certificate_bytes_and_first_tick_equal=false`는 네 완료 조건이 성립하지 않았다는 표시이며, 관측된 성공 certificate의 불일치를 뜻하지 않는다. 공유 pinned helper와 accepted old anchor를 신뢰하며 별도 비선형 전체 prefix 재생은 하지 않았다.

고정 검산기의 native 창 검사는 COMPLETE셀에 한정됐다. 네 셀 공통 전진 창1,044개는 별도 보고 집계에서 원시 CPU/cycle 차분·동일PID/TID·QPC 순서·끝 상태 digest를 대조했다. 추가 궤적·predicate 계산은 없다. 비수치 집계 시간은9.970초이며 정책 비용이나 고정 검산 시간에 합치지 않았다. 읽기 전후 bracket과 부호 있는 경과−CPU를 보존했고 음수를0으로 자르지 않았다.

[Microsoft GetThreadTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getthreadtimes)의100ns는 표현 단위이며 갱신 정확도 보장이 아니다. 짧은 reject의 CPU0은 무비용을 뜻하지 않는다. [QueryThreadCycleTime 문서](https://learn.microsoft.com/en-us/windows/win32/api/realtimeapiset/nf-realtimeapiset-querythreadcycletime)가 경고하듯 raw cycle을 elapsed나GHz로 변환하지 않았다. CPU와 cycle의 일치를 독립적인 정밀도 증명으로 세지 않는다. 경과−CPU에는 대기·선점·읽기 경계·회계 오차가 섞이므로 순수 호스트 간섭 시간이 아니다.

원 필터5개와 최종 경계 테스트14개(기존7+새7)가 통과했다. 격리 사본에서 같은 테스트·명령으로 signed residual clipping mutation의 실제 실패와 원본 복구 후 성공을 확인했고 canonical proof는CONSISTENT다. 최초13개 proof는 결속 보완 전 이력으로 보존했다. 기존 r10의24PASS/시간민감1실패는 재실행하거나25PASS로 바꾸지 않았다.

## Required Actions

실행·부분 결과·보류 판정을 봉인한다. 전체 실험은 추첨 비용 포함 **6,418.007초<6,900초**, 검산 본체410.961초·감독 포함411.587초<450초였다. 기록된11개 Job은 모두 잔존0으로 종료했다. outer/inner CPU는 겹치므로 합산하지 않으며 Job committed memory를RSS로 부르지 않는다. 최종 범위·서명·원격 반영은 실제 별도 영수증에 결속한다.

## Optional Optimizations

이번 작업은 현재 대조·검산·보고·서명 push로 마무리한다. 추가 최적화·실험·재검산은 수행하지 않는다.

## Unresolved

과거+178.386초와 이번 CPU 서비스시간 변동의 단일 원인은 미식별이다. 실주파수·열·retired instruction·cache·allocator/refcount·코어 residency·ETW는 측정하지 않았다. GC callback은 collection wall만 관측하며 간접 효과 전체를 배제하지 않는다. 부분 셀에는 최종 trace/GC-after 기록도 없으므로 모든 셀의 종료 후 GC 상태를 관측했다고 표현하지 않는다.

n2/arm, 배정 공간4다. 무작위화가 실제 period 균형·비선형 drift·carryover·간섭 제거를 보장하지 않으며, 통상5% 유의성이나 일반적 우위를 주장하지 않는다. 독립 graph/world 발견 표본은0이다. 결과는 같은 알려진 graph의 실수 모델에 한정한다.

## Method / Run Summary

토론스킬을 먼저 적용했다. 두 fresh `fork_turns:none` 읽기 전용 관점(performance/measurement, randomization/budget), 각1회 조건부 교차검토 뒤 Coordinator가 통합했다. MEDIUM/degraded_ok, partially_independent이며 Judge/reserve/specialist는 없다. inherited 실제 모델·추론 수준은UNKNOWN이다. 같은 reviewer를 재사용한 소스·결과 기록 점검은 새 독립 감사가 아니다. 추첨 전에 debit과 predraw 코드 핀 결속, 부분 파일 수 표기, 전체 검산 시간 표시를 보완했다.

진행 확인용 파일 조회는 root Job 밖에서 대략35초 간격으로 수행했다. 갱신 중인 state ack는 읽지 않았고 파일명은 완료 증명으로 쓰지 않았다. 이 외부 관리 부하의 CPU/RSS는 별도 계측하지 않았으며, 그 동시 실행 영향은 관측된 경과 시간의 환경에 포함된다. 호스트 정규화로 제거하지 않았다.

dot 연구 조언은 제한된 최근1turn(hasMore=true) 조회에서 확인되지 않았고, 전역 부재·미전달의 증거는 아니다. 원질의를 중복 전송하지 않았다. 사용자의 마무리 지시에 따라 후속 연구는 시작하지 않는다.

raw.zip/inventory에는 작성 시점의 실행·창·상태·봉인·평가·검산·테스트·준비·source snapshot을 보존한다. 이후 acceptance/delivery·최종 context 저장 영수증은 로컬 OP의 별도 자료이며 이미 봉인한 zip 안에 있다고 주장하지 않는다.
