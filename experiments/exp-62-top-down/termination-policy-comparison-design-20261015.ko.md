# 같은 graph의 종료정책 대조 설계 — 2026-10-15

상태: `DESIGN_ONLY_NOT_EXECUTED`. 기준은 `5b2d5ea`다. 이 문서는 실행 계약 후보이며 새 실험·native 실행·Engine 변경을 수행하지 않는다. 원 R081의 `CLOSED_BY_USER_AT_CELL3/native3of4`는 유지한다.

## 질문과 이전 결과

같은 first graph와 같은 현재 정보, 공통 총예산에서 종료정책이 평형 근접성·잠정 후보·실제 비용을 어떻게 바꾸는지 비교한다. 기존 실수 분석의 1848 low stop, 거리 최초 진입 5156/5171과 지역 인증 지연0은 개발 근거다. 같은 사례를 다시 확인해도 독립 발견·일반화 표본이 아니다. 실제 streaming, native 산술 또는 총비용 우위를 이미 확보했다고 전제하지 않는다.

## 두 비교의 경계

주대조는 `network-8`의 첫 ON graph를 고정한 실수 모델 분석이다. graph·drive·초기 상태를 실행 중 바꾸지 않는다. 종료시점과 같은 연구 readout으로 얻은 잠정 후보를 비교한다. 실제 native `stable_decision`·공개 readout·terminal adoption 결과와 구별한다.

부분 graph의 False 후보는 전체 dependency coverage가 필요하다. 주대조에서 이를 최종 오답이나 채택된 False로 처리하지 않는다. `coverage_required=True`, adoption=`NOT_MEASURED`를 남긴다. 후속 coverage 비용을0으로 쓰거나 총문제 해결 비용에서 제외하지 않는다. 그 비용을 요구하는 fullEngine 비교는 아래 별도 확장 계약이며 주대조의 효율 주장 범위에 포함되지 않는다.

## 고정 입력과 동일 정보

raw `swapped-s003-td1-off`의 첫 ON program/ordered7을 사용하고 `e:1` drive만 `above_near`의 `0x1.277babda5a221p-3`를 정확 유리수로 올린 값으로 선언한다. score는 `0x1.277babda5a221p-5`, 초기 p는 모두 `1/2`다. raw 이름의 `off`는 circuits OFF이며 top_down은 True다. graph 생성 시점의 processed paths·frontier·completeness와 observation/model digest를 동결한다.

세 arm은 같은 public observation/topology/config/model, 순차 생성된 현재 whole7 구간과 공개 과거 prefix, 자원 원장에 접근할 수 있다. 접근 가능한 public 정보가 같다는 뜻이며 처리된 dependency가 완전하다고 가정하지 않는다. 새 관측·feedback·학습·restart는0이다.

정책은 미래 상태·6144 anchor·root census·실제 최초시점·선행 outside proof·hidden world·다른 arm 출력에 접근할 수 없다. 지역 인증의 수치 함수에는 model/currentB/radius/epsilon만 전달한다. 기존 저장 B를 무료로 읽는 replay는 별도 사후 진단이며 주대조의 실제 비용 결과가 아니다.

## 세 정책

| arm | 종료규칙 | 경계 |
|---|---|---|
| L | 전체7 잔차·patience4·reset·진동 검사·margin의 현행 순서를 실수 구간 비교로 이식 | tick 상한6144·검사cadence16의 실수 heuristic이며 원 native cap160/매tick 종료와 다르다. 비교가 겹치면 `INCONCLUSIVE` |
| F | 공통 자원 상한 또는 tick6144까지 계속 | wall 경계 또는 tick6144 중 먼저 도달한 시점의 마지막 완성 구간을 사용한다. tick6144 도달을 요구하는 endpoint baseline은 아니며 stable status를 만들지 않는다 |
| C | tick16의 배수에서 current-only 성분별 인증, 반경_x=`1e-5`, epsilon_p=`1e-6` | selfmap/진입/수축/전체B 잔차/positive comparison 증명을 통과하면 종료. 비인증은 계속하며 비수렴으로 판정하지 않는다 |

L/C의 수락 검사는 같은 tick16 배수에서만 한다. L의 잔차·patience·reset·history는 매tick 갱신하고 검사시점의 stable 우선·진동 다음 순서를 유지한다. 이전 tick의 성공 조건을 latch하지 않는다. 따라서 기존 매tick1848 stop은 새 L의 종료시점 예측이 아니다. 자원 만료는 검사격자 밖에서도 중단하며 마지막 완성 상태만 남긴다. 예측 가능한 cadence를 전 구간에 사용한다. 알려진 최초 tick 주변만 검사하지 않는다. 따라서 C의5156 종료나 zero-delay 재현을 예측하지 않는다. 이번 설계에서 scalar/vector 또는 반경을 다시 최적화하지 않는다.

공통 순차 구간 생성은 x0에서 시작하며 outward grid30/Taylor96/proposal precision80을 후보로 고정한다. 완성된 supplier·검산기 코드의 hash와 soundness는 실행 전 별도로 확정해야 한다. 어떤 arm도 다른 arm이 계산한 미래 prefix를 이어받지 않는다.

## 총예산과 비용 귀속

한 known input × 세 정책 × 공통 wall 상한180/1800초의6셀이다. 새 독립 발견 표본은0이다. 각 셀에 봉인 후 evaluator120초와 종료·부분 기록 grace10초를 똑같이 배정하고, 공통 준비180초를 둔다. 180초는 짧은 예산의 완료·오종료·미완료,1800초는 긴 예산에서의 같은 지표를 판별한다. 두 예산의 모든 셀은 독립 cold start이며 짧은 실패에서 긴 셀로 resume하지 않는다. 예산별3셀과 전체6셀 분모를 함께 보고한다. 순차 전체 상한은 `180 + 3×(180+120+10) + 3×(1800+120+10) = 6900초`다. 실행 순서는 `180/L,F,C` 뒤 `1800/C,F,L`로 고정한다. concurrency1·같은 host·single-thread이며 process-tree 외부 watchdog은 실행 전 검증 의무다.

정책 wall에는 input 인수/graph 구성, x0부터의 모든 상태·구간 생성, 잔차·scheduler·인증 검사, 연구 readout과 출력 봉인이 들어간다. C의 추가 증명 비용은 C에 귀속한다. 공통 공급기라도 각 arm의 독립 실행에는 그 비용을 모두 부과한다. 별도 shared replay를 수행하면 실제 인프라 생성1회 비용과 arm별 배부 비용을 따로 기록한다.

과거 선택 상태 인증9.172초는 전체 궤적 생성 비용이 아니다. 큰 상한도 완료 보장이 아니며,180초에서 모두 미완료될 가능성을 그대로 둔다. 예산을 채우기 위해 조기 종료 arm을 억지로 계속하지 않는다. wall 상한과 실제 사용량을 구별하고 CPU seconds도 별도 계측한다. tick/binding/Taylor/Fraction 원장은 서로 다른 단위로 유지하며 임의 가중합으로 총계산량을 만들지 않는다. energy·peak memory가 미계측이면 null이다. 미래 실행에서는 memory 상한도 결과를 보기 전에 동결해야 한다.

봉인 후 world/거리 채점은 evaluator120초에서 수행하고, 정책 비용과 평가 포함 연구 비용을 각각 보고한다. 실행 중 평가 결과를 정책으로 돌려보내지 않는다. grace에서는 과학 계산을 하지 않으며 logging/termination 초과도 실제 경계 위반으로 기록한다. 예산 미완료나 채점 미완료를 성공 분모에서 빼지 않는다.

## 외부 정답과 공통 연구 readout

`above_near`는 합성 score 질의이므로 과거 world truth를 자동 승계하지 않는다. 실행 전 새로운 합성 context에서 같은 public edge IDs/topology를 유지하고 `e0=e1=e2=e3=True`의 all-open world를 독립 evaluator 파일로 선언·pin한다. 이는 설계한 toy truth이며 현실 관측의 정답이 아니다. edge coverage·세계 reachability·첫 처리 경로 reachability·observation 연결을 사전 검증하며 score나 평형을 truth 생성 규칙으로 사용하지 않는다.

모든 arm의 공통 연구 readout은 현재 Bgoal 전체가1/2 이상이면 True, 전체가1/2 미만이면 False이며 겹치면 None이다. margin 하한이 binary64 `.30`의 정확 lifted 값 미만이면 None이다. 이는 status와 독립적인 진단 후보다. L에만 또는 C에만 추가 readout gate를 붙이지 않는다. partial False의 잠정 후보 correctness와 실제 채택된 판단의 correctness는 별도다. 실제 adoption은 주대조에서 미측정이다.

## 결과 열과 판별 예측

각 행에 stop reason/tick/native-style status, 후보/sign/margin, synthetic-world candidate correctness, answer coverage, 실제 거리 INSIDE/OUTSIDE/AMBIGUOUS/NOT_EVALUATED, 인증 상태, processed coverage/frontier, 평가 가능한 proof/support/D_DAG, 시간·비용 원장을 남긴다. 새 proof를 host가 만들어 채우지 않는다. conditional accuracy는 후보가 있는 평가 가능 셀 분모를 함께 표시하고, 전체 사전6셀의 완료·보류·예산·측정 실패 분포도 반드시 보고한다.

| 예측 | 지지/반증 조건 |
|---|---|
| 작은 이동량은 충분한 근접성 조건이다 | L의 stop 거리 하한이 epsilon보다 크면 이 입력에서 반증. 기존1848 증인은 개발 근거 |
| C 인증은 sound proximity를 준다 | 모든 CERTIFIED 출력에 독립 거리 상계≤epsilon. 반례는 soundness 실패, 미채점은 UNKNOWN |
| C는 같은 예산에서 잠정 판단을 개선한다 | C가 맞고 대응 L/F가 틀리거나 보류하는지 확인. 대조가 없으면 개선 미지지 |
| C는 품질을 보존하며 정책 시간을 줄인다 | 후보·품질이 대응군보다 나쁘지 않고 실제 정책 wall이 작아야 지지. ticks 감소만으로 지지하지 않음 |

상한 부족, 구간 threshold 겹침, 채점 미완료는 각각 명시한다. `NOT_CERTIFIED`를 OUTSIDE·divergence로 바꾸지 않는다. source/contract/runtime 실패는 측정 실패이며 가설 반증과 구별한다. 결과 뒤 반경·precision·cadence·예산·입력을 변경하거나 자동 retry하지 않는다.

## fullEngine coverage와 native 확장 계약

전체 판단 비교는 같은 첫 graph/public observation/memory/config/초기 상태/정보 접근 가능성에서 시작한다. 이후 route·frontier·proof·새 graph가 자연스럽게 달라지는 것은 결과로 보존한다. 처리 prefix를 강제로 같게 만드는 host correction은 금지한다. 공통 총예산에는 모든 새 graph 구성·구간/상태 생성·binding/pool/scheduler·재인증·coverage·proof/readout/adoption·봉인이 포함된다. graph/model/drive가 바뀌면 이전 인증을 폐기하고 새로 인증한다.

이 확장은 controller adapter·evaluator·각 산술 코드 pin, 전 단계 비용 경계, 구체적인 전체 budget, watchdog, actual native 적용 시 floatingpoint/libm을 포괄하는 B 공급 계약이 없어 `DESIGNED_EXTENSION_NOT_EXECUTION_READY`다. 현재 실수 증명을 native 출력 칸으로 복사하지 않는다. 본 주대조의 잠정 후보 결과로 fullEngine 정답·재확장 회복·총문제 해결 효율을 주장하지 않는다.

## 실행 선행 조건과 중단선

실행 전 supplier/각 정책/evaluator 구현·source pin, model/world/observation/processed graph 결속, 미래·truth 누출 검사, 공통 계측·process-tree hard deadline·부분 기록 보존을 검증해야 한다. 새 bounded 실행 요청과 별도 동결 계약이 있어야 과학 실행에 들어간다. 이번 commit은 이 작업들을 수행했다는 증빙이나 실행 승인으로 사용하지 않는다.

같은 known orbit의 미세 지연 개선은 여기서 보류한다. 실제 총비용·잠정 판단 연결이 판별된 뒤 fullEngine 또는 held-out graph의 어떤 불확실성을 줄일지 별도 선택한다. dot 원답은 현재 `NOT_OBSERVED`이며, 실제 답변의 원질문·출처를 확인한 뒤 날짜별 보완으로 반영한다.

[기계 판독 설계](termination-policy-comparison-plan-20261015.json) · [최신 주장–증거 연결표](../../evidence/claim-evidence-links-20261015.ko.md)
