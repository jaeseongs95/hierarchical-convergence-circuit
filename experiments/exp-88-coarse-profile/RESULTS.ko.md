# R42 / EXP-88: 큰 구간 계측이 정확성을 보존하고 부담 기준을 통과했다

**원래 계산 이력 288쌍을 정확히 보존하면서 native 계측 부담이 고정 10% 기준 안에 들었다.** joint 부담 중앙값은 +2.115%, factor는 +1.634%였다. 각 방식의 세 반복이 모두 통과했고, `settle` 전체 구간이 세 반복 모두 최대이며 30%를 넘었다. 이 유한 조건에서 수렴 전체 구간을 후속 조사 후보로 남긴다. 수렴 내부의 검증·산술·제어 비용이나 최적화 효과는 아직 판정하지 않았다.

## R41과 구분되는 질문

[R41](../exp-87-producer-profile/RESULTS.ko.md)은 매 tick·Program 검증·digest까지 관측했지만 joint 14.14%, factor 13.93% 부담으로 10% 기준을 넘었다. R42는 별도 계약에서 이 세 probe를 제거하고 Program 생성·수렴 전체·결과 구성 같은 큰 구간을 관측했다. R41의 결과나 기준을 바꾸지 않았다. R25의 고정점 산술 생략, R30의 공간 공유, R40의 표현별 총비용 비교도 대체하지 않는다. 이미 정한 진단 후속이므로 새 방향성 패널은 반복하지 않았다.

R40 q4의 8개 폐쇄 관계표×이름2×행순서2=32맥락, canonical XY00/01/10/11 네 질의, 세 방식×plain/profiled×3반복으로 576기록·2,304출력이다. 매 실행은 fresh producer/initial0.5이며 답 cache가 없다. 원천24개와 상위 수치34,560회, 전체34,584 settle을 실제 실행했다. 동일 kernel+Config bytes의 저장만 공유했고 계산은 생략하지 않았다. 학습·세계측정·동결 후 native 재실행·사후튜닝은0회다.

arm과 짝 mode 순서는 동결한 회전식으로 배치했다. 이 32맥락은 독립 통계표본이 아니다. 완전한 관계표는 외부 폐쇄계약이며 가상 assignment나 목록 부재를 세계 사실/부정증거로 확대하지 않는다. 일반CSP·큰domain·학습·최소표현·제품성능/운영채택을 검증한 연구가 아니다.

## 계측 방법과 보존 조건

plain은 원래 R40 실행 경로다. profiled는 원래 R33 kernel의 data-producing 행 주변만 측정한다. 연구 runtime 9개 binding을 프로세스 안에서 임시 교체하고 정상·예외 모두 finally로 복원한다. 중첩 observer를 거부한다. **Program.validate·Program.digest·dynamics.tick은 교체하지 않으며 원래 경로에서 모두 실행한다.** 엔진 소스·수식·설정·임계값·서비스·전역 설정은 바꾸지 않았다.

`settle`은 원래 validation·전체 tick·제어·trace 관찰/복사를 포함한다. `result_materialize`는 plain·digest·결과/cost 구성 전체다. 이 두 구간을 더 세분한 비중을 추정하지 않는다. process_time_ns 중첩 stack에서 exclusive=inclusive−측정자식이며, 각 기록의 exclusive합=root inclusive가 정수 ns로 정확히 맞았다. 전체 core stopwatch−root인 profile_support에는 설치·복원·snapshot이 남는다. 자식 timer 종료 뒤 집계는 부모 잔여에 남기고, 최종 metric 구성·저장·원천·감사·준비·봉인·launcher는 별도 비용으로 보존했다. clock 정보는 원자료에 있으며 분해능을 정확도/무교란 보장으로 해석하지 않는다.

288짝에서 mode와 원래 두 CPU 필드만 제외한 전체 반환 기록이 같았다. Program/Config/drives/initial/모든 tick state/residual/stable_steps/convergence/cost의 canonical bytes도 정확히 같았다. 같은 해시라도 전체 bytes를 검사했고, 65개 trace를 lossless 확장해 모든 물리 참조를 검산했다. scalar1e-14 허용오차는 별도 scalar 재계산에만 쓰며 짝비교를 완화하지 않았다.

## 고정 부담선과 coarse 비용 결과

각 arm의 32맥락 coreCPU합 profiled/plain<=1.10이 세 반복 모두 맞고 모든 품질·짝·원장이 통과해야 내부 비중을 해석한다. 같은 최대 exclusive 범주가 세 반복 모두 전체 계측 core의30%이상이면 후속 조사 후보만 부여한다. 사전 10%/30%는 기술판별선이며 통계적 유의성·신뢰구간·효율 채택선이 아니다. 표의 CPU는 세 그룹의 중앙값, 부담은 같은 반복의 짝비율 중앙값이다.

| 방식 | plain core CPU(s) | profiled core CPU(s) | 부담 중앙값 | 부담 범위 | 조건을 만족한 후보·비중 범위 |
|---|---:|---:|---:|---:|---|
| native_joint | 3.420496 | 3.492829 | 2.115% | 1.881–2.384% | settle (65.763–65.961%) |
| native_factor | 3.425516 | 3.482505 | 1.634% | 1.475–2.762% | settle (65.777–66.106%) |
| exact_joint | 0.110458 | 0.111897 | 1.085% | 1.014–1.668% | source_export_guard (96.969–97.004%) |

다음은 profiled 환경의 coarse exclusive 비중 중앙값이다. 각 열의 중앙값 합이 정확히100%일 필요는 없고, 원장 합은 개별 기록과 그룹에서 확인했다. producer/consumer inclusive anchor는 analysis에 별도 보존했으며 이 표와 겹치므로 더하지 않는다. 전체 q4 core의 분해이고 producer만의 원인기여도가 아니다.

| 구간 | joint | factor | exact |
|---|---:|---:|---:|
| 원천 export/guard | 3.108% | 3.128% | 96.970% |
| 회로 문서 생성 | 0.297% | 0.296% | 0.000% |
| Program 생성 | 3.181% | 3.116% | 0.000% |
| 수렴 전체 | 65.823% | 65.976% | 0.000% |
| plain·digest·결과 구성 전체 | 24.785% | 24.513% | 0.000% |
| membership 외피 잔여 | 0.475% | 0.476% | 0.000% |
| 필드 encoding | 0.285% | 0.283% | 0.000% |
| producer 외피 잔여 | 0.147% | 0.104% | 0.000% |
| consumer 외피 잔여 | 0.077% | 0.136% | 0.000% |
| 입력 계약 검사 | 0.052% | 0.053% | 0.975% |
| kernel 외피 잔여 | 1.353% | 1.357% | 0.000% |
| core 잔여 | 0.440% | 0.475% | 1.296% |
| 설치·복원·snapshot | 0.027% | 0.029% | 0.747% |

모든 native arm에서 후속 후보는 `settle`이며, exact는 `source_export_guard`다. source guard 제거·출처계약 완화의 근거로 쓰지 않는다. R41과 이번 실행의 부담 수치는 서로 다른 실행의 기술적 관측이다. 경계 변경의 일반적인 인과효과/통계적 속도 우위나 비계측 시간의 정확한 분해를 입증한 것은 아니다. **R40의5% 총비용 채택 음성 결과는 그대로다.** 이번에는 회로 최적화를 수행하지 않았다.

## 정확성과 자원 검산

모든 arm-mode에서 strict 질의384/384, Z eligibility768/768과 모든 role/pair/membership/triple/queryinput 중간층이 맞았다. arm-mode마다 이름/순서 정규화72기록쌍·288질의쌍, 반복0 대비 이후64기록쌍이 불변이었다. 독립 full8triple oracle, 원천24개의 proof, 모든 scalar/controller/cost를 검산했다. 288개의 계측 배타 원장과 kernel/build/settle/materialize 호출 수·9개 복원도 확인했다. tick 수는 저수준 timer 대신 전체 이력/counter에서 확인했다. 최대 scalar 오차는 1.7347234759768071e-18다. semantic12·계측5·짝 kernelref1의 변조를 모두 거부했다.

AI Research SSH의 전용 폴더에서 34,584 settle·1,044,216 tick을 실행했고 봉인 포함 **67.360543초**였다. 세 단계 exit0, 소스162개/input129pin 불변이다.

| 단계 | wall(s) | process CPU(s) | exit | ru_maxrss_raw |
|---|---:|---:|---:|---:|
| preparation | 0.366259 | 0.316492 | 0 | 23792 |
| work | 58.316061 | 58.280556 | 0 | 29956 |
| audit | 8.481092 | 8.436290 | 0 | 36176 |

core CPU합 42.172105초, 저장 15.883458초, 원천 0.041942초, work 잔여 0.183051초이며 합계가 work process CPU와 맞는다. audit 잔여 0.598954초, 준비·봉인·launcher를 포함한 관측 process CPU합은 67.318240초다. 네트워크/로컬문서작업이나 OS전체·standalone제품비용 측정은 아니다. 비용을 무료로 제외하거나 임의 상각하지 않았다.

R41 work CPU×계획1.25, 다른 phase 잔여 유지, 안전계수3·60초올림으로 단계240초/전체300초를 동결했다. raw128MiB/cache192MiB/건당128KiB/AS각512MiB/파일130·8MiB/LRU18/고유trace<=34,560은 운영 중단선이며 완료·미래 CPU/RSS 보장이 아니다. 계획1.25와 해석허용선1.10은 별개다. RSS와 서버 메모리는 원시 점관측으로 보존했다.

로컬 준비503Boolean·9합성 외피 대조·정상/예외복원·중첩차단·저수준 함수 미교체·metadata8·joint격리10·factor격리12·저장/상한9·codec2·LRU18·Python5 AST/UTF8/LF가 통과했다. 합성 settle/tick은 fake이며 실제 수치정확성 증거와 구분한다. 준비 중 private 생성기 namespace 충돌과 입력 파일 생성 전 의존 검사 실행을 수정한 뒤 통과했으며 native실행은0회였다.

## 수신 한계와 다음 후보

JSON 88개/2,518,952 bytes를 받았고 manifest 대상87개 JSON의 원본 크기·SHA가 모두 직접 맞았다. manifest는 자기 해시 밖이다. 이번에는 adapter 마스킹/복원이 없었다. 첫 완료 조회는 실행 중이라 파일이 아직 없었고, 첫 큰 다중파일 조회는 상위 adapter에서 잘렸다. 완전한6파일을 보존하고 나머지 파일은 최대240,000bytes 단위로 나누어 받았다. native 재실행이나 기대 해시 변경은 없었다. 전송 실패 기록을 보존했다. 서버 ZIP과 빈 stdout/stderr6개는 받지 않았지만 모든 수치/판단/계측 JSON을 받았다. upstream 완전성은unknown이며 동일채널 해시는 독립 host attestation이 아니다.

검산·CS검토는 작성자의 자료 재계산이며 독립감사가 아니다. CS bundle의 PASS는 결속과 원시 해시의 일관성을 확인하며 실호스트 신뢰/정확성/권한/무교란을 자동증명하지 않는다.

다음 후보는 수렴 전체 구간 안에서 **원래 검증·tick·제어·trace 관찰을 보존하는 한 가지 변경**을 별도 계약으로 비교하는 것이다. 비용 상각/캐시 없이 fresh 실행에서 전체 이력과 학습 포함 총비용을 확인해야 한다. 어느 내부 항목이 낭비인지 아직 확정하지 않았으므로 먼저 원래 구현을 검토해 계산을 실제로 줄일 수 있는 변경을 고른다. 이번 R42에서는 최적화나 다음 실험을 실행하지 않았다.

## 근거

- [설계](DESIGN.ko.md), [결과별 판단](OUTCOMES.ko.md), [상한](BUDGET.ko.md), [동결 입력](frozen_spec.json)
- [비용·해석](../../evidence/coarse-profile-20261020-r42/analysis.json), [로컬 검산](../../evidence/coarse-profile-20261020-r42/local-verification.json), [수신 검산](../../evidence/coarse-profile-20261020-r42/receipt-verification.json)
- [서버 결과](../../evidence/coarse-profile-20261020-r42/raw/result.json), [원본 manifest](../../evidence/coarse-profile-20261020-r42/raw/manifest.json), [호출 원장](../../evidence/coarse-profile-20261020-r42/raw/work-ledger.json)
- [계측 외피](../../tools/r42_coarse_profile/runtime.py), [검산](../../tools/r42_coarse_profile/verify.py), [실행](../../tools/r42_coarse_profile/probe.py)
- [CS검토](../../evidence/coarse-profile-20261020-r42/cs/review.json), [bundle 검사](../../evidence/coarse-profile-20261020-r42/cs/bundle-check.json), [비중복](../../evidence/coarse-profile-20261020-r42/nonduplication.json)
