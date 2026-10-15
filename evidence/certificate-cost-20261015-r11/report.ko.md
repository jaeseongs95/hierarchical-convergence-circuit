# 동일 graph의 인증 비용 대조 — r11

## 결론

전체 wall 절감 목표는 이번 실행에서 실패했다. C1의 실제 wall은 C0 대비 +5.740%, F 대비 +11.453%였다. 인증 단계의 계산·시간은 줄었지만 전체 시간과 총 트리 CPU는 줄지 않았다. 원본 C0와 개선 C1은 같은 tick에서 종료했고 성공 인증 내용도 바이트 단위로 같았다. 이는 단회 실행의 비용 관측이며 보편적 속도 우위나 호스트 교란을 제거한 인과 추정은 아니다.

## 관찰

| 정책 | 종료 tick | wall(s) | tree CPU(s) | 후보/거리 |
|---|---:|---:|---:|---|
| F | 6144 | 1396.703 | 1296.031 | True / INSIDE |
| C0 | 5168 | 1472.172 | 1387.016 | True / INSIDE |
| C1 | 5168 | 1556.672 | 1393.969 | True / INSIDE |

원본 r10에서는 C가 F보다 976 tick 적으면서 wall 57.876초, tree CPU 53.609375초 더 걸렸다. Taylor 호출 수는 오히려 C가 적었다. 당시 내부 phase 시간을 측정하지 않았으므로 역사적 차이의 정확한 원인은 식별되지 않는다.

이번에는 전진 계산·인증·상태 저장·수치 초기화를 겹치지 않는 외부 타이머로 구분했다. 타이머 호출·ledger 작성·실행기 startup·최종 봉인·scheduler·diagnostic 및 감독 비용 중 별도 phase에 속하지 않은 것은 미귀속이다. 미귀속 시간을 파일 I/O나 인증에 임의 배분하지 않았다. 각 phase의 CPU 원값은 comparison.json에 있고 Job tree CPU와 합산하지 않는다.

| 정책 | 전진 wall(s) | 인증 wall(s) | 저장 wall(s) | 초기화 wall(s) | 미귀속 wall(s) |
|---|---:|---:|---:|---:|---:|
| F | 1309.746 | 0.000 | 85.678 | 0.062 | 1.217 |
| C0 | 1204.446 | 190.177 | 76.186 | 0.032 | 1.331 |
| C1 | 1382.832 | 87.531 | 84.876 | 0.047 | 1.386 |

이번 C0−F wall 차이는 +75.469초다. 전진·인증·저장·초기화·미귀속 차이를 더한 회계 항등식이 comparison.json에 있다. 이는 이번 실행의 추가 비용과 절약 비용을 나누며, r10의 57.876초를 소급 분해하지 않는다.

C1−C0에서는 인증 phase가 -102.646초였지만 같은 전진 계산 phase가 +178.386초, 저장 phase가 +8.690초였다. 두 C의 forward 코드·입력·전진 횟수는 같으므로 이 전진 시간 차이를 인증 필터가 줄인 계산량으로 설명하지 않는다. 부하·주파수·열·OS 대기 등은 가능한 대안이며 실제 원인은 식별하지 못했다. 전체 wall 개선은 관측되지 않았다. 절감된 인증 연산량과 인증 phase의 시간 감소만 확인한 것으로 한정한다.

| 정책 | 인증 시도 | residual | 실제 region proof | 음성 생략 | Taylor |
|---|---:|---:|---:|---:|---:|
| F | 0 | 0 | 0 | 0 | 86012 |
| C0 | 323 | 323 | 323 | 0 | 83653 |
| C1 | 323 | 323 | 1 | 322 | 76891 |

## 해석과 수학적 조건

기존 인증은 유효 영역에서 K≥0, qK<1, r≥0 및 v=(I−K)⁻¹r을 검사한다. v=r+Kv≥r이므로 max(r)>2ε이면 기존 component bound max(v)/2가 ε 이하일 수 없다. C1은 같은 현재 잔차를 먼저 구해 이 음성 조건에서만 영역 증명과 선형 소거를 생략한다. 등호는 원본 계산으로 넘긴다. 잔차는 상계 증명값이므로 이 음성 결과는 실제 거리 하한이나 OUTSIDE 판정이 아니다.

생략 결과는 SCREENED_NOT_CERTIFIABLE / proof NOT_EVALUATED이며 전체 음성 proof 전문까지 원본과 같은 것은 아니다. 나머지 경로는 동일 local_certificate와 동일 현재 residual witness를 사용한다. model/current whole7 box/radius/epsilon 외 과거 궤적·anchor·truth·최초 성공 tick·미래 상태는 숫자 API에 주어지지 않는다. 캐시는 없다. geometry·원자료 결속·비음수·whole7·eH 검사를 유지했다. 고정 모델의 모든 row에서 |b|+Σ|G|<49를 확인하여 degree96 Taylor 정의역 조건을 만족한다. 임의의 다른 모델에서 모든 예외 행동까지 동치라고 주장하지 않는다.

## 판별 검증

- 공통 full7 상태 15,507쌍이 정확히 같았다. 새 비선형 궤적 전체를 별도 구현으로 재생한 검사는 아니다.
- 개선 C의 모든 323개 cadence에 원본 인증을 다시 적용해 판정이 같음을 확인했다. 기록된 목록 길이뿐 아니라 tick//16·attempt 연속성·첫 성공과 종료 tick의 결속도 확인했다.
- 원본/개선의 최초 성공 tick과 성공 certificate canonical bytes가 같았다. evaluator는 정책 봉인 뒤 같은 world·accepted anchor를 읽고 원본 숫자 helper로 성공 인증을 다시 확인했다.
- analytic 경계 테스트 5개 PASS. 격리 사본에서 임계값 2ε를 ε로 바꾸자 동일 테스트가 equality 경계를 잡았다. 기존 r10 self-test의 24 PASS / .8초 timing 1실패는 수정하거나 25 PASS로 바꾸지 않았다.
- 평가 가능한 후보 3/3, 정답 3/3. 이것은 선택된 하나의 알려진 graph와 all-open authored synthetic world의 진단 후보 정확도다. adoption·full Engine 정확도는 측정하지 않았다.

## 예산·중단과 원자료

각 정책은 새 프로세스의 x0에서 독립적으로 시작했다. 모델·관찰·processed graph·cadence16·tick cap6144·grid30·ε=1e−6·radius=1e−5는 동일하다. 순서는 실행 전 난수로 ['F', 'C0', 'C1']에 고정했다. 각 정책 cap1800, setup180, 평가120/셀, cleanup10/셀, 봉인 후 검산600, 전체 outer watchdog6900초다. 보수적 예약은 6570초이며 남은330초를 추가 실험에 재배정하지 않았다. 실제 전체 4803.860초, 전체 초과=False, 기록된 모든 Job active=0이다. outer CPU는 inner와 겹치므로 합산하면 안 된다. 메모리는 Job의 committed virtual peak이며 RSS·실제 에너지는 미측정이다. hard real-time 보장은 없다.

처음 서명한 실행기를 Git checkout이 LF→CRLF로 바꾸어 원격 raw-byte 검사가 실패했고 실행 전 code-pin 검사가 거부했다. 실제 cell은 0개였다. 새 .cmd 한 파일에만 LF 속성을 명시한 추가 GPG commit을 push한 뒤 실험을 한 번 시작했다. 실패와 pre-execution 계약 개정본은 raw bundle에 남겼다. .gitattributes는 기존 worktree CRLF를 유지하므로 원격 LF canonical bytes로만 비교한다. 새 .cmd와 다른 변경 파일은 raw bytes를 비교한다.

범위 확장 시 구 task baseline 결속 검사는 거부를 보존했다. 비용이 큰 commit별 전체 파일 스캔은 소유한 읽기 전용 프로세스만 중단했다. 원본 baseline의 6파일 PASS, custody 수정의 실제 Git diff 허용 경로 대조, 수정 뒤 clean 상태의 확장 working-tree baseline을 분리한다. 과거 baseline을 새 task에 재결속하지 않았다.

raw.zip과 raw-manifest.json은 실행·평가·검산·phase/counter·원실패·동결 개정·로컬 진단 근거를 바이트/해시 inventory로 보존한다. 나중의 최종 push·수용 영수증은 로컬 OP에 별도로 남기며 이미 만든 archive 안에 있다고 주장하지 않는다.

## 대안 설명과 주장 범위

실행 순서 난수화 1회는 균형 반복 설계가 아니다. 각 arm 1회라 시간 변동·불확실성 구간을 추정할 수 없고, CPU 부하·캐시·전력·스케줄러 차이는 통제하지 않았다. phase 차이는 관측된 메커니즘 근거이지만 보편적인 인과 효과 크기를 뜻하지 않는다. 정답·커버리지·시간·CPU·메모리·tick을 하나의 효율 점수로 합치지 않는다. 추가 graph의 일반화나 독립 discovery 표본은 0이다. 기존 accepted anchor와 공유 숫자 helper는 신뢰 경계다.

토론은 MEDIUM의 blind 관점 2개, 조건부 교차검토, Coordinator 통합으로 수행했고 보증은 partially_independent다. 구현 source 후속 검토와 결과 후속 검토는 기존 reviewer 재사용이며 fresh 독립 판정이 아니다. 실제 inherited 모델/추론은 UNKNOWN, Judge·reserve·specialist는 사용하지 않았다. dot 기존 답변은 최근 제한된 조회 범위에서 NOT_OBSERVED이며 원요청 status unknown은 부재 증명이 아니다. 새 답변을 확인하면 별도 dated amendment로 반영한다.

## 근거 연결과 전달 상태

실행 전 테스트 문서의 freeze hash는 LF 변환 문제를 수정하기 전 계약의 역사적 값이다. 원문을 고치지 않고 post-execution-verification.json으로 최종 유효 계약과 연결했다. 두 계약의 모든 code pin 집합이 같고 현재 파일도 그 집합과 정확히 일치한다. 바뀐 것은 새 실행기 한 파일의 LF 전달 규칙이다.

과학 실행이 모두 끝난 뒤 기존 동일 테스트·동일 후보를 별도 소유 사본에 고정해 canonical test-plan/check-proof도 수행했다. 잘못된 임계값의 red 다음 원본 후보의 green이 실제로 실행됐고 CONSISTENT였다. 이는 서명 없는 로컬 바이트·명령·근거 일관성 검사이며 독립 감사나 새 과학 표본이 아니다.

초기 prelaunch 오류는 당시 도구 출력에서 확인한 협조적 요약 기록이다. 별도 원본 stdout/stderr 영수증 파일이 있었다고 주장하지 않는다. raw-manifest.json에도 이 한계를 명시한다. 실제 세 과학 셀의 원자료·감독·평가·검산 로그는 원래 바이트로 보존한다.

총괄의 전달 경로 통지와 정정 두 건은 수신 처리 ACK만 남겼다. 이는 이번 연구 조언이나 새 사용자 권한이 아니다. 최근 실행 전 2turn·실행 후 1turn 조회 범위에서 연구 답변을 관측하지 못했으며 전체 과거 답변의 부재를 뜻하지 않는다. 새 외부 메시지·Google Drive 업로드·공유 변경은 하지 않았다.
