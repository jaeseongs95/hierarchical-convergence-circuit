# R0.2 원시 실행 기준선 분석

새 추론 없이 기존 run을 읽어 만든 집계다. 수치 tick 재연산 감사와는 구분한다.

## Familiarity — warm − cold

| 사례 | 정답 cold/warm | primitive D | 확장 Δ | binding Δ | 신호 Δ | tick Δ | infer wall Δ(s) |
|---|---|---|---:|---:|---:|---:|---:|
| counterfactual | True/True | 2/2 | -1 | 27 | 1210 | 68 | 0.010292300 |
| renamed_reordered | True/True | 3/3 | -1 | 18 | 872 | 33 | 0.007018400 |
| same_structure | True/True | 3/3 | -1 | 18 | 872 | 33 | 0.007036800 |

음수는 해당 항목 감소다. 이 표만으로 end-to-end 가속을 주장하지 않는다.

## 저장 전후 회로 상태

| 회로 | 강도 전/후 | 실패 전/후 | 활성 전/후 |
|---|---|---|---|
| pattern-ac8909863fce4682a84bf769 | 0.81015625/0.16203125000000002 | 0/1 | True/True |
| pattern-d7053e8a62ed20d50b15444c | 0.81015625/0.81015625 | 0/0 | True/True |

## 해석 경계

retention/reload의 재오답은 그대로 보존한다. candidate_trace.json의 후보·선택·prior와 learning_patches를 연결해 읽는다. 동반된 상태 변화는 관측이며, 원인 분리는 별도 paired probe가 필요하다.

비용은 costs.csv의 판단별 카운터, analysis.json의 learning_by_decision으로 분리된다. training3/9은 해당 arm의 최초 판단·수정 판단·feedback 비용을 각각 비교한다.

원 실행에서 측정하지 않은 항목:
- 원 실행의 엔진 생성/메모리 load wall time
- 원 실행의 전체 실험 end-to-end wall time
- 개별 입력 측정의 실제 자원 비용
- 원 실행 당시 RAM memory와 save/load memory의 행동 동등성
