# EXP-79 / R33 결과

**후보별 상위 역할 신호가 native 하위 선택을 바꾸고, 그 변경이 별도 native T 계산에 전달되는 경로는 확인했다. 하지만 현재 numeric 선택기는 모호·모순에서 안전하게 보류하지 못하므로 일반 채택을 거부한다.** 정보동일 일반 exact solver는 전체288조건에서 정확했다.

## 방향과 비교

[방향 토론](direction.ko.md)은 MEDIUM 독립2관점·각1회 교차검토 후 Coordinator가 통합했다. 보증은 partially_independent이며 fresh Judge/최종 독립 감사가 아니다. R19와 같은 한 왕복 host 스케줄임을 인정하고, 새 측정은 실제 native 원천이 지지한 typed 대안 후보의 역할별 compatibility→native lower 선택→첫 C를 받지 않는 별도 T 소비로 한정했다. native5/10group compatibility·3group selector·5group T는 기존 tick/settle을 수정하지 않는다. 자세한 입력·판정은 [동결 설계](design.ko.md), [명세](frozen_spec.json)에 있다.

288입력×full/frozen/exact의864평가다. 맥락4종×soft prior3종×T2종×이름2종×후보순서2종×초기상태3종을 교차했다. 이름/초기 상태를 독립 표본으로 세지 않는다. 두 R 후보는 완결된 대안 가설이며 두 경로의 primitive proof가 각각 유효하다는 사실을 세계에서 동시에 참이라는 주장으로 승격하지 않았다. C는 공개 hard constraint, local prior는 soft preference이고 hidden truth가 아니다. 학습과 세계 측정은0회다.

| 방식 | strict:값·사유·결속 | query 값 | 결속 | 원천 포함 native tick | 배분 CPU초 |
|---|---:|---:|---:|---:|---:|
| 왕복 full | 144/288 | 160/288 | 160/288 | 46764 | 3.792385 |
| 피드백 제거 frozen | 64/288 | 80/288 | 80/288 | 45660 | 3.752143 |
| 일반 exact solver | 288/288 | 288/288 | 288/288 | 396 | 2.290840 |

strict와 query값은 다르다. None을 내도 hard ambiguity/inconsistency의 사유를 구분하지 못하면 strict 실패다. frozen은 피드백 기여를 보는 인과 제거군이고 충분한 최적화 경쟁 알고리즘은 아니다.

## 성공 경로와 음성 결과

one0/one1의 유일한 해144조건에서 full은144/144, frozen은64/144, exact는144/144였다. 같은 lower 증거·prior·T·초기 상태에서 C만 바꾼72쌍 모두 full의 lower 선택과 최종 T 값이 바뀌었다. frozen에서는 두 변화가 모두0쌍이었다. 최종 consume_t는 binding/T/vocabulary/config/Program/initial만 받으며 C나 compatibility trace를 직접 읽지 않는다. 이는 단순 상위 activation 변화와 실제 후속 소비를 구분하는 근거다.

either(두 후보 허용)72조건과 both(허용 후보 없음)72조건에서 full과 frozen 모두 strict0/144였다. 각 방식에서128/144조건은 bool 값을 확정했고,16조건은 None으로 보류했으나 사유는 abstain_dynamic이라 hard ambiguous/inconsistent 구분에 실패했다. 정확한 집합 의미를 푸는 exact는 이144조건도 모두 맞혔다. 검사기가 native 선택·출력·사유를 수정하지 않았고, 실패 후 입력·threshold·코드 재조정이나 native 재실행은 하지 않았다.

코드상 selector는 두 compatibility를 차이 하나로 줄인다. 대수적으로 [u,u]와 [v,v]는 같은 차이0이므로, 이 표현만으로 모든 후보 허용과 아무 후보도 허용되지 않음을 일반적으로 구분할 수 없다. 이는 코드에 대한 구조 분석이며 모든 실제 native trace가 완전히 같았다는 측정 주장은 아니다.

따라서 새 기능은 **유일한 hard 제약 아래의 authored typed 왕복 소비 충분성**을 지지한다. 일반 CSP, 안전한 모호성 해소, 학습·의미 자동 형성·더 큰 객체 일반화·독자적 primitive 필요성·효율 우위를 지지하지 않는다. activation은 보정 확률이 아니며 compatibility는 lower posterior를 읽지 않는 외생 역할 신호로 계산했다. 한 번의 replacement feedback을 독립 evidence나 반복 검증으로 세지 않았다.

## 실제 비용과 검증

AI Research SSH 요청374816ca503583deaba47c7465d360d6e1b7418251bc0e82는 실제 command_set 정책으로 자동 허용돼 실행됐다. source12회와 각 numeric 방식1440회씩, 총2892settle/92028tick이다. 서버15단계 모두exit0, 원천98개 파일 불변, 봉인까지13.493890546초로1800초 상한 내였다. worker1/retry0이며 parent512MiB/child256MiB, parent file32MiB/child file16MiB/raw128MiB 설정을 사용했다. 308구조 검사와7표적 변조 거부, 전체 저장 tick의 별도 scalar/controller/count replay 및 source proof/역할/메시지/revision/T 결속 검산을 수행했다. 서버 scalar 최대오차0.0, Windows host 최대오차2.220446049250313e-16로 동결1e-14 이내다. 이는 구현자 별도 계산 검산이며 독립 감사가 아니다.

위 CPU는 실제 record별 source export·guard·그래프 생성·인코딩·수렴·메시지·선택·논증·직렬화·파일쓰기 시간을 합산하고, 각 arm에 같은 실제 source process CPU 0.131675초를 한 번씩 더했다. batch 공통 import/입력 로드/metrics/종료 overhead 1.311169초는 각 arm에1/3씩 배분했다. 이 배분은 명시적 회계 가정이며 각 arm을 따로 실행한 독립 시간 측정이 아니다. 물리 source는 한 번만 생성해 공유했다. 준비/검산/봉인·host 수신은 별도이며, 상세한 native group/link·원천 포함량과 CPU 분해는 [analysis.json](../../evidence/typed-feedback-20261020-r33/analysis.json)에 있다. 짧은 단일 실행으로 통계적 속도나 비용 회수 우위는 주장하지 않는다.

JSON882개를 로컬로 받았고 manifest 자체를 제외한881개 bytes SHA가 서버 manifest와 정확히 일치했다. 모든 native tick record가 포함된다. 나머지30 stdout/stderr는 manifest에서 empty SHA인 것을 확인했으나 파일 자체는 받지 않았다. 서버 ZIP 다운로드 요청 완료는 파일 준비를 뜻한다. ZIP6564504bytes/SHA6bcffdbeccd89d67d81017beff8451c4eb6e8dc2c4020471e340e270448116c1은 로컬 미수신이다. text archive transfer는 entropy 마스킹·upstream cap으로 사용하지 않았고, 대신 정상 JSON을 수신·검산했다. SSH completeness는 unknown, 같은 채널 hash는 외부 host attestation이 아니다.

## 다음 방향과 채택 조건

다음은 객체 수 확대보다 **가능한 결속 집합의 상태를 표현하고 보류를 보존하는 조건**을 먼저 설계해야 한다. 최소 조건은 유일해/복수해/해없음을 구분하고, 복수해라도 후속 query의 참·거짓이 모든 해에서 같을 때만 답하며, 순서·이름·초기 상태 때문에 임의 후보를 확정하지 않는 것이다. 일반 exact solver를 충분한 대조로 유지한다. 그 조건을 만족하기 전에는 이 numeric selector를 채택하지 않는다. 이번 연구의 source/input/threshold를 고쳐 같은 결과로 재평가하지 않고 새 계약에서 시험한다.
