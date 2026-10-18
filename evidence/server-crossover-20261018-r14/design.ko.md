# r14 서버 C0/C1 후속 대조 설계

## Executive Verdict
같은 그래프의 Linux 서버 내부 전체 비용을 새로 관측한다. 기존 r13은 종료 상태로 보존한다.

## Consensus Proposal
conditional_consensus. 네 cold process를 인접 두 쌍으로 배정하고 사전 동결 뒤 독립 fair bit 두 개를 한 번만 뽑는다. 조건은 Linux 종료 smoke 통과·핀 일치·초기 available 메모리 1GiB 이상이다.

## Strong Consensus
수치 helper/model과 매 tick fsync·ack를 재사용한다. timeout·누락을 분모 4에 유지하고 완료 셀만 평균내지 않는다. VM·SMT 간섭을 배제했다고 주장하지 않는다.

## Material Disagreements
미해결 반대는 없다. 512MiB 가상 주소 공간 상한은 Windows Job committed memory와 다르다. 관측기 자체 부하와 Linux 저장 비용을 측정 비용에 포함한다.

## Decision by Axis
범위: 새 r14만. 비용: 인접 C1−C0 두 차이와 평균, 전체 완료·품질·검산이 없으면 보류. 환경: 관측 신호·미관측·관측 불가를 구분하고 데이터 제외·재실행은 하지 않는다.

## Evidence
r13은 1/4 완료, ABSTAIN_INCOMPLETE_EVIDENCE였다. 지정 서버 조회에서 Ubuntu/AWS VM, Python3.12.3, 2logical CPU가 같은 1physical core의 SMT, 메모리7816MiB, root ext4와 가용140GiB를 확인했다. 상위 user.slice 및 user-1001.slice cpu.max는 max 100000, memory.max는 max였다. 단시점 load0은 전체 부하 보장이 아니다.

## Required Actions
정식 실행 전 synthetic 감독·부모소멸·메모리 제한 확인과 기존 필터 경계검사를 수행한다. 총13100초 = 정책4×3000 + 평가4×15 + 정리4×10 + 검산900 + 고정관측30 + 여유70. 준비·전송·smoke는 별도 기록하며 정식 배정에 합치지 않는다. 이 예산은 완료 보장이 아니다. fresh 검산은 실제 모든 gate의 전체 payload를 helper pins와 함께 canonical dedup한 뒤 원본 predicate를 호출한다. 323개·tick5168은 예상 불변조건이며 누락을 숫자로 메우지 않는다.

## Optional Optimizations
수치 pilot·새 캐시·새 의존성·설치·sudo·전역 설정·타 프로세스 중단 없음.

## Unresolved
VM의 hypervisor/SMT/cache/전력/다른 작업 간섭은 완전 통제·식별 불가다. PSI·steal·throttling 무신호도 무간섭 인증이 아니다. Windows r11~r13 원인이나 가상 완료 시간을 소급 교정하지 않는다.

## Method / Run Summary
독립 토론 MEDIUM/degraded_ok, fresh fork_turns:none reviewer2명(계측/간섭 및 통계/예산), 각1회 교차검토, Coordinator 통합. 재위임·Judge·reserve·specialist 없음. 요청 모델/effort override 없음, 실제 모델/effort UNKNOWN. 두 리뷰어는 로컬 원자료만 확인했으며 서버 사양은 Coordinator가 SSH 조회로 확인했다. 구현·시험은 토론과 별도 단계다. 이는 새 독립 최종 감사가 아니다.

공식 자료: [Python resource](https://docs.python.org/3.12/library/resource.html), [Python subprocess](https://docs.python.org/3.12/library/subprocess.html), [Kernel PSI](https://docs.kernel.org/accounting/psi.html), [Kernel cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html).
