# EXP62 / R081: 두 점에서 top_down 신호 묶음 제거

## 질문과 사전 근거

R080의 같은 교환 배열·circuits OFF에서 e3=.03은 첫 stable_false(95 ticks, goal .03688332023268971) 뒤 coverage 전개로 e0/e1 proof에 도달했다. .04는 첫 stable_true(111 ticks, goal .9840687555064942)에서 e2/e3 proof를 채택했다. 이 두 상태는 readout .5 및 margin .3의 ambiguous 구간에서 이미 멀다. 단순 readout 경계를 동등한 원인으로 다시 놓지 않는다. 양수이면 첫 True라는 가설은 이전 결과에서 반증되었으며 이번 실험의 새 질문이 아니다.

이번 질문은 **모든 `kind=top_down` 링크의 전송을 제거하면 이 유한 두 점의 첫 수렴 상태와 coverage 경로가 바뀌는가**이다. 기존 `AdaptiveSession`의 bool 플래그만 조작한다. native source와 historical worker/auditor는 수정하지 않는다.

## 기존 연구와 비교한 이번 실험의 역할 (F1)

아래 문헌 비교는 2026-10-03에 원 논문의 공개 초록을 확인한 범위다. R081 결과나 포괄적인 신규성 검토를 대신하지 않는다. 공통점과 차이의 적용은 이 저장소의 설계 해석이다.

| 비교 대상 | 기존 메커니즘과 겹치는 점 | R081에서 구별할 수 있는 것과 한계 |
| --- | --- | --- |
| [Hopfield (1982)](https://pubmed.ncbi.nlm.nih.gov/6953413/), DOI 10.1073/pnas.79.8.2554 | 상태 동역학으로 내용 주소 기억을 회복하며 비동기 갱신을 사용한다. 반복 상태 갱신과 안정화 자체는 HCC만의 발상이 아니다. | R081은 고정한 authored graph의 동기 tick에서 top_down 전송 묶음만 제거한다. 첫 수렴, 후속 coverage, proof 채택을 분리하지만 기억 복원 성능 비교나 공통 에너지 함수의 존재를 시험하지 않는다. |
| [Rao·Ballard (1999)](https://www.nature.com/articles/nn0199_79), DOI 10.1038/4580 | 상위→하위 경로가 예측을, 하위→상위 경로가 예측 오차를 전달한다. 계층 간 feedback이라는 공통 구조가 있다. | R081의 kind=top_down과 centered link 입력을 곧 예측 오차 최소화라고 해석할 수 없다. 별도 prediction/error 역할·생성모형·학습을 비교하지 않으므로 predictive coding 대비 우월성이나 동등성은 판정하지 않는다. |
| R079→[R080 원관찰](../exp-61-small-positive/results.ko.md)→[R080 후속 후보](../exp-61-small-positive/NEXT.ko.md) | 같은 배열·OFF에서 작은 양수의 first False/True가 갈렸고, R080 NEXT는 내부점 세 개 추가를 후보로 남겼다. | R081은 임계값 정밀화 대신 기존 양끝 .03/.04에서 신호 묶음 제거의 효과를 구별한다. True 두 조건은 재현이며 새 지지로 더하지 않는다. R080의 미실행 내부점 후보는 실행하지 않는다. |

따라서 이번 기여 후보는 일반적인 수렴·feedback의 발명이 아니라, 이 구현에서 특정 신호 묶음이 첫 상태와 coverage 경로에 영향을 주는지를 고정 조건과 독립 원자료 검산으로 분리하는 것이다. False 조건에서도 상태가 유지되면 해당 두 점에서 그 묶음이 category 차이에 필수라는 설명은 약해진다. 상태가 바뀌어도 개별 링크의 원인, 학습된 circuit 형성 또는 인간 인지의 증거로 확대하지 않는다. 두 문헌의 구현을 추가 실험하는 계획은 이번 범위에 없다.

## 고정 조건과 조작

순서는 .03/True, .03/False, .04/True, .04/False의 정확히 네 셀이다. True 두 셀은 R080 재현, False 두 셀만 새 신호 개입이다. 새 독립 발견 표본·학습·feedback은 각각 0이다.

R077 봉인 memory/3.json, config signature, world, topology, public ID, episode `r077-probe`, 배열 `[e2,e3,e0,e1]`, e2=1/e0=1/e1=.6, `use_circuits=False`, `judgment_prior=route_only`를 고정한다. top_down_gain=.35, prior_gain=0, relation_gain=2, self_excitation=.25, inhibition=.20, damping=.45 및 모든 초기 상태 .5를 유지한다. max_ticks=160, session advances=16, session ticks=5120이다. 정확한 경로·해시·수치는 frozen_spec.json이 기준이다.

`runtime.py`는 플래그의 bool 타입을 검사하고 pending switches를 매 advance 대조한다. `sessions.py`→`state.restore_engine`은 switches를 복원하며 `capture_candidate`도 그 세션을 복원해 finish한다. `dynamics.tick`은 False일 때 해당 링크 전송만 건너뛴다. 저장된 Program/groups/links/weights/digest는 paired 첫 network에서 동일해야 한다. 동일 route가 자연히 재등장한 후속 network도 program/drive를 대조하지만, 경로·frontier·proof·비용을 강제로 같게 만들지 않는다.

## 수식과 예측

source의 한 tick에서 `positive-negative = 2*drive + (self_excitation+inhibition)*(2*p-1)`이다. 이를 temperature로 나눈 sigmoid 목표로 damping 갱신한다. 자기 상태 항은 제거되지 않는다. 따라서 이 조작을 전체 재귀·쌍안정의 제거로 해석하지 않는다. 작은 대수 identity 검사는 같은 source의 확인이며 새 native 표본이나 고정점·불안정성·유일성의 증명이 아니다.

피드백 제거 시 약한 e3가 아래 경로에서 오는 음의 입력을 받지 않고 양의 외부 drive를 유지한다는 source 구조로부터 다음 방향 가설을 세운다. 새로운 조건의 수치 pilot이나 solver로 예측을 맞추지 않았다.

| ID | literal 술어 | 평가 가능 조건 |
| --- | --- | --- |
| remove_bundle_s003_true | .03/False 첫 category=stable_true, candidate_value=True, ready=True, 같은 advance의 해당 network progress 없음 | 해당 첫 상태가 stable_true/false/ambiguous |
| remove_bundle_s004_true | .04/False에서 위와 같은 술어 | 동일 |
| category_change_exists | 두 paired 비교 중 적어도 하나에서 첫 category가 다름 | 증인 pair의 양쪽이 stable; 무증인 반증은 두 pair 모두 stable |
| numeric_difference_both | 각 pair의 첫 settled goal 절대차가 2e-12 초과 | 양쪽 settled goal 측정; 비수렴 수치 차이는 수렴 증거가 아님 |

stable 평가 가능한 literal 불충족은 반증이다. budget_exhausted/oscillating/unsupported/누락은 stable_false 증인이 아니다. category 무증인+미평가는 판정불가다. numeric 예측은 측정된 동일 pair 하나면 반증, 그런 반례가 없으면 두 pair 모두 측정되어야 지지한다. 이 네 판정은 같은 두 쌍의 서로 관련된 관찰이며 독립 지지 네 건으로 세지 않는다. 가설 반증도 실험 성공 조건과 양립한다.

## 측정과 독립 검산

첫 network는 journal상 최초 `r02_network(kind=decision)`이다. 생성 advance의 반열린 event 범위 안에서 matching settled/progress를 묶는다. pre-network progress와 이후 advance에서 반복된 progress를 첫 지표로 섞지 않는다. 모든 decision network의 category/status/goal/margin/residual/stable_steps/ticks, candidate/ready/pending value, graph completeness/frontier/route를 기록한다.

생산 kernel을 import하지 않는 기존 `hcr.evaluation` recurrence와 별도 규칙으로 모든 tick, flags, 비용, 후보, grounding/readout/adoption을 재계산한다. spec bool을 engine-created/document switches/모든 network/후보 및 각 progressive packet과 직접 대조한다. False에서는 support 링크만 active이며 tick 수×active link 수를 signal_transmissions와 대조한다.

링크별 `transmitted`, 실제 마지막 tick의 centered input(비활성 링크는 0), 전송했을 경우의 would-be centered term, terminal-centered term, uncentered weight×activation을 분리한다. 이전 R076~R079의 final_signed_input 명칭 정정과 역사적 봉인은 그대로 둔다. active goal ancestry는 provenance inventory이며 효과의 크기를 판정하는 지표가 아니다.

Proof.paths 전체 목록과 final parent closure를 구분하고 D_DAG를 독립 재계산한다. 최초 판단·최종 raw value·readout 승인·terminal adoption도 별개다. OFF pool metrics는 null/not_applicable, 관측 pool ticks는 0이다. 비용 단위를 더해 총 효율로 부르지 않는다. actual energy/peak memory는 null이다. UTC 시점과 monotonic duration을 함께 보존하고 pending wall_seconds=0을 실소요시간으로 쓰지 않는다.

원자료 mutation은 payload/engine/created flag, tick/state/status/cost 및 network-local progress를 조작한 뒤 event chain과 packet 해시를 다시 계산한다. 정상 rehash-only control이 통과하고 의미적 이유로 거부되는지 기록한다. hash 불일치만으로 semantic 검사를 통과했다고 하지 않는다. 요약은 원자료에서 재계산하고 paired delta·전송 지표·예측·proof 등을 변조해 대조한다.

## 실행과 중단

`Run-HCR-R081.cmd --writer-id <담당ID> --reviewer-id <검토자ID> --review-dir <검토파일폴더>`는 source·조건 동결과 selftest 후 외부 설계 검토에서 멈춘다. 검토자가 확정되지 않았으면 실행하지 않는다. 각 재개는 `--resume <출력된 동일 run 경로>`를 추가한다. 재개는 새로운 native 조건을 최대 하나만 실행하며 기존 조건을 반복하지 않는다.

F2 순서는 외부 설계 검토 PASS → 첫 조건 → 그 조건의 외부 검토 PASS → 다음 조건이다. 네 번째 조건도 외부 검토를 받아야 최종 raw manifest·독립 분석·요약 검산·core 회귀 한 번·bundle/ZIP으로 넘어간다. scientific ambiguous/oscillation/network budget/session budget 결과도 외부 검토를 마쳐야 다음 조건으로 진행한다. runtime/integrity/측정 실패 및 부분 출력은 보존하고 자동 재시도하지 않는다.

검토 요청은 run의 `review_requests/design.json` 또는 `<cell-id>.json`에 생성된다. 외부 검토자는 같은 이름의 JSON을 별도 검토파일폴더로 전달한다. receipt 필드는 `schema=hcc-r081-external-review-v1`, 요청 객체 그대로인 `request`, 지정한 `reviewer_id`, `verdict=PASS`, `blocking_findings=[]`, 실제 검토 근거를 가리키는 `evidence`, 검토 시각 `reviewed_at`이다. 요청의 run/source/plan/raw 해시가 일치해야 수용하며 승인된 기록은 run의 `external_reviews`에 보존한다. 해시는 내용 결속을 검증할 뿐 검토자의 신원을 인증하지 않는다. 담당자는 검증된 외부 파일 전달 경로로 받은 실제 검토 기록만 공급해야 하며 스스로 PASS를 만들어서는 안 된다. 내부 audit 결과·단순 ACK·파일 존재만으로 외부 검토를 대신하지 않는다.

외부 검토자는 동결 설계와 F1 비교의 적정성, 각 조건의 원자료 및 생산 코드와 분리된 재계산 결과, 실패 분류를 검토한다. 외부 검토 미수행은 연구 결과의 실패가 아니라 대기 상태다. 자기 검토, 다른 조건·run·소스의 결과, FAIL 또는 미해결 지적은 차단한다. 기존 결과 덮어쓰기·자동 retry·새 조건·예산 연장·학습은 없다.

## 주장 범위

한 authored native graph와 동일 memory의 유한 신호 묶음 개입이다. 개별 feedback edge, gain 또는 자기항의 효과를 분리하지 않았다. 정확 임계값·단조성·연속 bifurcation·고정점 유일성·LLM 내부·인간 인지·생물학·전력 또는 하드웨어 효율로 일반화하지 않는다. 결과 뒤에는 원관찰→가능 원인→paired 결과→현재 주장→다음 판별 후보 순서로 기록하며 조건을 추가하지 않는다.
