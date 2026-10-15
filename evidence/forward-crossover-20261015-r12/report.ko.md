# 동일 전진 시간과 C 전체 비용의 교차 대조 — r12

## Executive Verdict

**C1의 전체 비용 절감은 확인되지 않았다.** C0 평균 1,341.422초, C1 평균 1,352.384초로 C1이 0.817% 느렸다. 사전 판정 규칙의 결과는 NO_WHOLECOST_WIN이다. C1−C0 정책 전체 비용의 두 인접 pair는 [163.57963649999988, -141.65562010000008]초, 평균은 10.962초다. 음수는 C1이 빠르다는 뜻이다. 전체 비용 판정 자격=True, 두 pair 모두 C1이 빠름=False. 기존 +178.386초의 원인은 여전히 NOT_IDENTIFIED다. 새 실행의 수치·나머지·GC·시계 차이를 나누지만 과거 실행을 복원하지 않는다.

## Consensus Proposal

같은 graph, x0, 정보, C0/C1 코드와 수치 helper를 유지하고 C0→C1→C1→C0로 실행했다. 순서는 실행 전 ABBA/BAAB 중 seed로 고정했다. 네 셀은 각각 새 프로세스·고유 디렉터리이며 정책 cap1575, evaluator10, 공유 cleanup10초다. setup30, 검산450, 예약합6860, 전체6900, 여유40초를 추가 실험에 재배정하지 않았다. F는 이번에 실행하지 않았다.

## Strong Consensus

동일 코드·상태·호출 횟수는 동일 runtime 비용을 보장하지 않는다. 이전 단일 F→C0→C1 순서는 정책과 시간 순서가 섞였다. 이번 정책은 같은 현재 model/whole7 box/radius/epsilon만 사용하며 과거 궤적·정답·anchor·시계·호스트 수치는 숫자 helper에 입력하지 않았다. C1의 음성 잔차 필터와 성공 인증은 r11과 같다. 기본 GC 설정을 바꾸거나 수치 probe·캐시·반복 재시도를 추가하지 않았다.

## Material Disagreements

이전178.386초를 특정 원인에 소급 배분할 근거는 없다. 실제 Python의 monotonic 구현은 GetTickCount64, 공시 해상도15.625ms였고, QPC는 QueryPerformanceCounter였다. 20만회 clock-only 사전 관측의 최소 양의 변화는 고정 계약에 있다. 이 관측은 엄밀한 오차 상한이 아니다. 이전 callback별 CPU 합계의 +111.9375초 역시 실제 수치 CPU 증가의 독립 증거로 쓰지 않는다. 서로 반대인 pair 부호가 나오면 평균과 함께 공개하며 단일 승리로 숨기지 않는다.

## Decision by Axis

| 순서/정책 | 상태 | 봉인 tick | 정책 전체 QPC(s) | Job CPU(s) | 평가 |
|---|---|---:|---:|---:|---|
| 01-C0 | COMPLETE | 5168 | 1246.943 | 1167.734 | True / INSIDE |
| 02-C1 | COMPLETE | 5168 | 1410.523 | 1326.484 | True / INSIDE |
| 03-C1 | COMPLETE | 5168 | 1294.246 | 1167.625 | True / INSIDE |
| 04-C0 | COMPLETE | 5168 | 1435.901 | 1315.156 | True / INSIDE |

| 셀 | 전진 부모 | 수치 하위 | 전진 나머지 | 수치 내 GC 하위 | 인증 | 저장 | 미귀속 | 전진 legacy−QPC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 01-C0 | 1013.609 | 1001.099 | 12.510 | 0.000 | 160.885 | 71.199 | 1.208 | 0.333 |
| 02-C1 | 1253.200 | 1237.819 | 15.380 | 0.000 | 80.017 | 75.789 | 1.475 | 0.200 |
| 03-C1 | 1141.463 | 1127.365 | 14.099 | 0.000 | 72.303 | 78.882 | 1.558 | 0.170 |
| 04-C0 | 1173.974 | 1159.478 | 14.497 | 0.000 | 183.086 | 77.199 | 1.606 | 0.420 |

전진 부모 = 수치 하위 + 부모와 하위의 차이다. GC는 수치/인증/저장 등에 이미 포함된 하위 wall이므로 부모와 합산하지 않는다. 전진 나머지는 box 파싱·모델 변환·outward 검증·관측 및 계측 overhead가 섞인 값이며 순수 I/O나 순수 산술로 부르지 않는다. 미귀속에는 startup·gate ledger·observer block 쓰기·최종 trace·프로세스 종료·감독 등이 포함된다. trace 최종 직렬화는 phase 합계 밖이지만 전체 정책 시간 안에 있다.

| 지표 | pair1 C1−C0(s) | pair2 C1−C0(s) | 평균(s) |
|---|---:|---:|---:|
| whole_policy | 163.580 | -141.656 | 10.962 |
| Job_tree_CPU | 158.750 | -147.531 | 5.609 |
| advance | 239.591 | -32.511 | 103.540 |
| certificate | -80.868 | -110.782 | -95.825 |
| state_persistence | 4.590 | 1.683 | 3.136 |
| numeric_advance | 236.720 | -32.113 | 102.303 |
| advance_rest | 2.871 | -0.398 | 1.236 |
| numeric_GC | 0.000 | 0.000 | 0.000 |
| unattributed | 0.267 | -0.049 | 0.109 |
| arithmetic_init | 0.000 | 0.004 | 0.002 |

위 차이는 관측된 회계 분해다. 수치−관측 GC도 GC를 제거한 반사실 실행 시간이 아니다. GC는 정책의 allocation 차이가 비용으로 이어지는 경로일 수 있으므로 단순한 호스트 교란으로 빼지 않는다. GC CPU는 측정하지 않았다.

완료 pair 1의 C1−C0 전진 차이 +239.591초는 수치 함수 +236.720초와 나머지 +2.871초로 나뉜다. 관측 수치 GC 차이는 +0.0000400초, 전진 legacy−QPC 차이의 차이는 -0.133초다.
완료 pair 2의 C1−C0 전진 차이 -32.511초는 수치 함수 -32.113초와 나머지 -0.398초로 나뉜다. 관측 수치 GC 차이는 +0.0000368초, 전진 legacy−QPC 차이의 차이는 -0.250초다.

| 셀 | 공통 tick | 전진 QPC | 수치 QPC | 전진 나머지 | 수치 내 GC | 전진 legacy−QPC |
|---|---:|---:|---:|---:|---:|---:|
| 01-C0 | 5168 | 1013.609 | 1001.099 | 12.510 | 0.0000301 | 0.333 |
| 02-C1 | 5168 | 1253.200 | 1237.819 | 15.380 | 0.0000701 | 0.200 |
| 03-C1 | 5168 | 1141.463 | 1127.365 | 14.099 | 0.0000628 | 0.170 |
| 04-C0 | 5168 | 1173.974 | 1159.478 | 14.497 | 0.0000260 | 0.420 |

공통 prefix는 네 셀 모두가 보존한 마지막 공통 불변 블록 경계 5168 tick에서 선택했다. 특정 arm의 빠른 구간을 골라낸 값이 아니며, 완료 정책 전체 비용으로 승격하지 않는다. GC·시계 차이가 작더라도 수치 함수가 왜 느려졌는지까지 식별한 것은 아니다. 이번 실행의 QPC 차이로 이전178.386초를 보정하지 않는다.

## Evidence

이번 실행에서 전진 시간 차이의 대부분은 수치 함수 호출을 감싼 elapsed 구간에서 관측됐다. 그 구간의 실행 시간이 달라진 원인은 식별하지 못했으며, 수치 연산 자체의 고유 비용 증가나 과거 +178.386초의 원인을 확정한 것은 아니다. 직접 관측한 GC collection 정지시간이 작다는 사실로 refcount·allocator·cache의 간접 효과 전체를 배제하지 않는다. 네 셀의 전진 legacy−QPC 차이는 약 0.170~0.420초이며, 모두0.4초 미만인 것은 아니다.

| 셀 | 호스트 집계 busy(%) | 블록 CPU 단일 차 합(s) | 블록 wall 합(s) | 관측 GC 전체(s) |
|---|---:|---:|---:|---:|
| 01-C0 | 41.89 | 1167.625 | 1246.662 | 0.0035610 |
| 02-C1 | 37.39 | 1326.359 | 1410.198 | 0.0048675 |
| 03-C1 | 60.69 | 1167.531 | 1293.792 | 0.0042847 |
| 04-C0 | 59.12 | 1315.000 | 1435.469 | 0.0037195 |

같은 C1의 두 실행은 호스트 집계 busy가 약37.39%와60.69%일 때 전체시간이 각각1,410.523초와1,294.246초였다. 집계 busy가 큰 쪽이 더 빨랐으므로 단순한 ‘호스트 전체 부하 증가가 느려짐을 설명한다’는 주장을 하지 않는다. 이 지표는 해당 코어의 가용성·주파수·전력·온도·스케줄링을 측정하지 않으며, 상관이나 인과 효과를 추정하기에도 표본이 작다.

C0의 region proof는 셀당323회, C1은1회였다. residual323회는 유지되고 C1은322회의 음성 필터를 기록했다. Taylor는 C0 83,653회, C1 76,891회였다. 같은 정보·상태·횟수의 전진과 인증 연산 절감을 구분했다. 평균 전체 Job CPU는 C1−C0 +5.609375초였으며 phase별 callback CPU 합계로 이를 재배분하지 않는다.

outer kill-only Job flags8192, memory limit0, committed virtual peak68,620,288 bytes였고 inner Job은512MiB 상한이었다. 검산 자체349.646초, 감독 포함350.099초로450초 이내다. 이 메모리는 RSS가 아니며 실제 에너지는 미측정이다. 모든 기록된 Job active0과 종료코드0을 확인했다. hard real-time 보장은 없다.

검산 감독 상태=COMPLETE, 결과=PASS. 전체 기준 상태와 각 셀 공통 full7 비교 수=15507, 새 원본 predicate 고유 입력=323, C1 발생 건수=646. 중복 제거는 봉인 후 전체 payload(model/current box/radius/epsilon/helper pins)의 canonical bytes가 정확히 같은 경우만 허용했다. SHA는 인덱스이며 bytes도 대조했다. 과거 r11 판정값을 재사용하지 않았다. 독립 비선형 전체 prefix 재생 검사는 아니며 공유 고정 수치 helper와 accepted old anchor를 신뢰한다.

원본 경계 테스트5개와 새 계측/교차/중도절단 테스트7개가 통과했다. 격리 사본에서 primary QPC 시간을 legacy로 치환하자 같은 테스트가 실패하고 복구 후 통과했다. 최종 canonical proof는 CONSISTENT다. 이전 r10 전체 suite의 24 PASS/시간민감1실패를 다시 실행하거나25 PASS로 바꾸지 않았다.

새 phase 주 시계는 perf_counter_ns다. legacy는 같은 callback을 포함하지만 CPU 시계 읽기 등 더 넓은 경계를 갖는다. legacy−QPC 전부를 양자화 오차라고 단정하지 않고 clock_bracket_seconds를 함께 보존한다. [Python3.12 time 문서](https://docs.python.org/3.12/library/time.html)는 시계 구현·해상도와 process CPU/elapsed의 의미를 설명한다.

128tick마다 누적·차분 phase/GC·Taylor/카운터·상태 hash·block CPU 단일 차와 GetSystemTimes 원값을 보존했다. kernel에는 idle이 포함된다. 집계 busy 비율은 호스트 전체의 상관 관측이며 해당 단일 코어의 가용성이나 주파수·열·특정 background 원인을 뜻하지 않는다. [Microsoft GetSystemTimes 문서](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getsystemtimes)와 같은 정의로 집계했다. callback CPU 합계는 해상도/갱신/경계 alias 한계가 있어 Job CPU 및 block 단일 차와 구분했다. outer Job CPU는 inner와 겹치므로 합산하지 않는다.

## Required Actions

이번 bounded 연구 결과와 미측정을 보존한다. 전체 물리 QPC 시간은 5743.031초, 상한6900, 초과=False, outer active=0다. 각 불완전·실패·NOT_RUN은 계획 분모4에 남긴다. 전체 검산/네 셀 품질이 빠지면 전체 비용 우위를 판정하지 않는다. 최종 scope·GPG 작업단위 commit·push·원격 바이트 대조는 별도 로컬 영수증에 보존한다.

## Optional Optimizations

이 연구에서는 추가 최적화 코드를 도입하지 않았다. 같은 관측기를 두 arm에 적용한 결과이며 계측 전 비용을 직접 복원하지 않는다. 이 네 번에서의 기술적 평균 효과 외 보편적·통계적 성능 우월성이나 F보다 빠르다는 새 주장은 하지 않는다.

## Unresolved

이전178.386초의 단일 원인, 주파수·온도·코어별 부하·background culprit·cache 상태·RSS·에너지는 미확인이다. ABBA는 선형 period 추세의 평균 위치를 맞추지만 U자형/비선형 drift·carryover를 제거하지 않는다. arm당2회이며 독립 graph/world 표본0이다. 정확도·커버리지는 알려진 단일 authored synthetic world의 진단 후보이며 adoption/full Engine 정확도는 미측정이다. 1575초는 이전 C1보다18.328초만 길어 완료 보장 예산이 아니었다.

## Method / Run Summary

토론스킬은 두 fresh blind 관점과 각1회 조건부 교차검토 뒤 Coordinator가 통합했다. MEDIUM/degraded_ok, assurance partially_independent이며 Judge/reserve/specialist는 없었다. inherited 실제 모델·추론 수준은 UNKNOWN이다. 구현 뒤 같은 reviewer를 재사용한 source follow-up은 새 독립 감사가 아니다. 중도절단 성공 callback의 final 강제와 평가 누락 PASS 표시 두 문제를 실행 전에 고쳤다. dot 연구 답변은 제한된 최근 조회 범위에서 확인되지 않았으며 기존 질의가 없거나 미전달됐다는 뜻이 아니다. 새 답을 받으면 날짜를 붙여 반영한다.

원자료 zip/inventory는 실행·봉인·clock·phase·GC·host·평가·검산·테스트·최초 후보 영수증을 보존한다. archive 작성 뒤 delivery/acceptance 영수증은 로컬 OP에 있고 이미 봉인한 archive 안에 있다고 주장하지 않는다. .gitattributes는 기존 CRLF를 유지하며 원격 대조에서 이 한 파일만 LF canonicalization을 적용하고, 새 launcher와 다른 파일은 raw bytes를 비교한다.
