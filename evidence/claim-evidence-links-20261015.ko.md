# 최신 주장–증거 연결표 — 2026-10-15

기준 commit은 `5b2d5eabf2f10a90971803cdd0c625b9b6f9933f`다. 이 문서는 기존 결과를 연결한 새 해석이며 새 실험·증명 재검산이 아니다. 원문 `claims.yaml`의 2026-09-16 상태와 봉인 raw는 수정하지 않는다. 기존 LLM 관찰 HCC-C01~C05는 당시 source summary를 참조하는 관찰로 유지하며 이번 계산 모델 연구로 재검증하지 않았다.

## 판정 읽는 법

`observed`는 명시된 장치·조건의 관찰, `certified_model`은 기존 기록에 인증된 고정 실수 모델 명제다. `mixed_scoped`는 expansion 지지와 ticks 반증처럼 서로 다른 비용축의 판정을 함께 보존한다. 모두 전체 HCC/LLM 내부/인간 인지/생물학/물리 효율의 확정 상태가 아니다. `unsupported`는 현재 직접 증거가 없다는 뜻이며 전역 반증이 아니다.

## 조건별 연결

| 주장 ID | 질문 | 현재 상태 | 확인한 결과와 경계 | 근거 |
|---|---|---|---|---|
| `HCC-H01/H02` | 계층 공통 primitive·cross-A 승격 | `hypothesis` | 고정 수준의 동일 갱신식은 구현 선택이다. 수준별 baseline 대비 우위·승격 의미 보존의 직접 검증으로 올리지 않는다. | [theory](../theory/core-hypothesis.md) · [dynamics](../src/hcr/dynamics.py) |
| `HCC-H03/formation` | 반복 검증 → 회로 형성·재사용 | `observed` | EXP44의 사전 정의 motif/3회 임계 규칙에서 형성·새 분기 topology reuse 관찰. 자율 graph 구조 발견은 미입증. | [exp44](../experiments/exp-44-circuit-formation/RESULTS.ko.md) |
| `HCC-H03/cost` | 재사용 → 비용 감소 | `mixed_scoped` | EXP44 expansion 감소 지지, kernel ticks 감소 예측은 3쌍 모두 반증. EXP58에서도 expansion 감소/ticks 증가. 전체 가설의 전역 반증·walltime/에너지 우위로 확대하지 않는다. | [exp44](../experiments/exp-44-circuit-formation/RESULTS.ko.md) · [exp58](../experiments/exp-58-equal-binding/results.ko.md) |
| `HCC-H04/revision` | 오류 → 약화·재확장 → 지속 교정 | `partially-supported` | EXP45/50의 약화와 관측 교정은 분리된다. 같은 misleading 관측 재노출의 교정 유지 예측은 해당 조건에서 반증. | [exp45](../experiments/exp-45-error-retention/RESULTS.ko.md) · [exp46](../experiments/exp-46-information-boundary/RESULTS.ko.md) · [exp50](../experiments/exp-50-revision-factorization/RESULTS.ko.md) |
| `HCC-H04/information` | 재확장 → 새로운 구별 정보 | `observed` | EXP48은 동일 정보 baseline에서도 fresh 관측으로 세계를 구별했다. HCC 고유 이점·자율 관측 선택은 미입증. | [exp48](../experiments/exp-48-observation-refresh/RESULTS.ko.md) |
| `HCC-H05` | 직관·명시적 추론의 두 실행 양식 | `hypothesis` | native 회로 선택·proof 경로 변화는 확인했지만 인간 직관이나 일반 추론의 설명력을 확인한 것은 아니다. | [theory](../theory/core-hypothesis.md) · [exp58](../experiments/exp-58-equal-binding/results.ko.md) · [exp59](../experiments/exp-59-binding-order/results.ko.md) |
| `HCC-H06` | 안정 오답과 오수렴 | `partially-supported` | EXP45/52의 안정 오답은 toy 조건에서 관찰. 실수 low-stop은 평형에서 먼 조기 종료이므로 실제 안정 attractor 오답과 같은 원인으로 묶지 않는다. 착시·인간 오류의 공통 기제는 가설. | [exp45](../experiments/exp-45-error-retention/RESULTS.ko.md) · [exp52](../experiments/exp-52-native-selection-boundary/RESULTS.ko.md) · [real_stop](../experiments/exp-62-top-down/on-real-stop-certificates-20261014.json) |
| `HCC-H07` | 강한 attractor의 속도–수정성 tradeoff | `derived-prediction` | checkpoint 약화·선택 경계는 좁게 관찰했지만 순수 attractor 강도 개입/동일 총비용·정확도·수정성 tradeoff는 미입증. | [theory](../theory/core-hypothesis.md) · [exp50](../experiments/exp-50-revision-factorization/RESULTS.ko.md) · [exp52](../experiments/exp-52-native-selection-boundary/RESULTS.ko.md) |
| `HCC-H08` | 판단 생성과 설명 복원 분리 | `hypothesis` | 경로·proof·adoption 구별은 필요하지만 이 기록으로 판단 뒤 설명의 사후 생성이나 LLM 내부 경로를 확정하지 않는다. | [theory](../theory/core-hypothesis.md) · [exp59](../experiments/exp-59-binding-order/results.ko.md) |
| `DYN-FOLD` | 첫 ON family의 평형 소멸 | `certified_model` | score 임계 enclosure [0.036068708258,0.036068713259]. 정확 fold 전/점/후 서로 다른 평형 3/2/1. enclosure 내부 uniform count UNKNOWN; native 임계값·전체 동역학 분기 미입증. | [fold](../experiments/exp-62-top-down/on-critical-strip-certificates-20261013.json) |
| `STOP-REAL` | 작은 이동량 종료와 평형 근접성 분리 | `certified_model` | above_near 실수 궤적의 기존 확장 정책은 1848에서 low stop. 모든 평형까지 p∞ 거리 하한 0.873674578281281700994460954275. tick별 native 반올림은 이 low stop에 필수 아님. 원 cap160/native 종료 결과와 구별. | [real_stop](../experiments/exp-62-top-down/on-real-stop-certificates-20261014.json) |
| `LIMIT-REAL` | 동일 원 초기값의 장기 high 수렴 | `certified_model` | 조기 종료를 무시한 고정 실수 궤적은 6144까지 high basin 진입·이후 수렴 인증. 6144는 최초 탈출시각 아님. 외부 정답·fullEngine 정책 인증 아님. | [real_escape](../experiments/exp-62-top-down/on-real-escape-certificates-20261014.json) |
| `GATE-ONLINE` | 현재 입력 수렴 인증과 최초성 | `certified_model` | known orbit에서 eps_p=1e-6/1e-8 거리 최초 진입은 5156/5171. 반경1e-5·성분 상계는 그 tick에서 인증하여 기존 고정 gate 지연5/2를0으로 줄임. 최초성은 기존 모든 선행 OUTSIDE 증명을 결합한 사후 판정. | [distance](../experiments/exp-62-top-down/on-fixed-point-distance-entry-certificates-20261014.json) · [online](../experiments/exp-62-top-down/on-online-convergence-gate-certificates-20261014.json) |
| `GATE-UTILITY` | 인증 → 외부 판단·총비용 개선 | `unsupported` | streaming B 생성/native libm/fullEngine/미지 graph/총비용·외부정답 개선은 미입증. 다음 정책 대조의 목표이며 결과가 아니다. | [online](../experiments/exp-62-top-down/on-online-convergence-gate-certificates-20261014.json) · [runtime](../src/hcr/runtime.py) · [world](../experiments/exp-58-equal-binding/reference_world.json) |
| `R081-PARTIAL` | top_down 묶음 개입의 원 실행 경계 | `partially-supported` | 원 R081은 CLOSED_BY_USER_AT_CELL3/native3of4. 관측된 .03 paired 효과와 미관측 .04 OFF를 구별하며 두 점 모두라는 universal 결과는 UNKNOWN. 누락 셀 재개는 계획에 없다. | [r081_partial](../experiments/exp-62-top-down/partial-identifiability.json) · [exp62_design](../experiments/exp-62-top-down/design.ko.md) |

## 현재 연구 방향

root→basin→fold→종료 분석은 평형 존재, 원 초기값의 목적지, 평형 소멸, 유한 종료를 구별했다. 이제 같은 known orbit의 인증 지연·반경 최적화는 보류한다. 새로 구별할 대안이 있거나 사전 목표를 충족하지 못할 때만 다시 연다.

다음 질문은 같은 graph에서 종료정책이 외부 판단과 실제 자원 사용을 어떻게 바꾸는가다. 먼저 실수 모델에서 정보·총예산을 맞춘 대조를 설계한다. 실제 native streaming/전체 Engine 적용에는 산술·구간 생성·coverage 연결의 별도 계약이 필요하다. 계층 공통성·학습된 압축·수정 유지의 전체 순환은 그 결과와도 별도로 검증한다.

수렴, 외부 정답, proof, readout, terminal adoption과 비용은 별도 축이다. 높은 goal이나 인증 지연0만으로 정답·실행시간·총효율 개선을 선언하지 않는다. 동일 raw의 여러 재분석·결정적 반복·mutation control을 새 독립 발견 표본으로 세지 않는다.

## 출처와 미해결 사항

[기계 판독 연결표](claim-evidence-links-20261015.json)의 `source_pins`는 경로·바이트 수·SHA-256을 고정한다. 결과 원문에 포함된 raw/source/검산 provenance를 따라가며, 이 연결표 작성에서 이전 proof를 새로 검산했다고 보고하지 않는다.

dot의 AI 연구 원질문에 대한 답변은 아직 `NOT_OBSERVED`다. 총괄의 다른 프로젝트 답변이나 전달 ACK는 연구 조언으로 취급하지 않는다. 실제 답변이 오면 원질문·출처를 확인하고 날짜별 보완 기록으로 반영한다.
