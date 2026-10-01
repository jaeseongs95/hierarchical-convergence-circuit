# EXP-37 / R056 사전 동결 설계

## 질문과 근거

R055에서 고정총량 배분의 내부 세 점은 full/drop_P_prefix 모두 high였다.
하지만 약한 drive 증가와 강한 drive 감소가 함께 일어나 기여를 분리하지 못했다.
이번에는 각 orientation에서 strong {4, 3.02} × weak {.08, 1.06}을 비교한다.
start에서는 strong=e:0, goal에서는 strong=e:1이다. 구조적으로 교환 가능한 방향이
아니므로 두 orientation을 평균하거나 대칭성 검정으로 합치지 않는다.

## 조건과 보존 범위

| orientation | strong | weak | id | 실제 (e:0,e:1) drive |
|---|---:|---:|---|---|
| start | 4 | .08 | startstrong | (4,.08) |
| start | 4 | 1.06 | start_raise_weak | (4,1.06) |
| start | 3.02 | .08 | start_lower_strong | (3.02,.08) |
| start | 3.02 | 1.06 | startlean | (3.02,1.06) |
| goal | 4 | .08 | goalstrong | (.08,4) |
| goal | 4 | 1.06 | goal_raise_weak | (1.06,4) |
| goal | 3.02 | .08 | goal_lower_strong | (.08,3.02) |
| goal | 3.02 | 1.06 | goallean | (1.06,3.02) |

각 입력에 full/drop_P_prefix 두 mask를 적용해 16행을 만든다.
R055 대각선 8행은 재현 control이며 off-diagonal 8행만 새 대조다.
입력 표기는 drive/4이며 goal drive=0이다. 원본 drive와 덮어쓴 drive를 구분한다.
총 drive는 대각선 4.08, off-diagonal 5.06 또는 3.10이다. 고정총량 실험이 아니다.
한 drive를 고정한 다른 drive의 개입 효과는 측정하지만 총량의 별도 독립 효과를
동시에 분해했다고 주장하지 않는다.

R052 c001/start_edge program, group/bias/support/link 순서·weight, initial=.5,
default config, 동기 갱신, 종료 규칙 및 160 tick 예산을 보존한다.
P_prefix(p:0:1→p:0:0) 삭제 이외의 program 변경은 없다. 각 분기는 fresh start다.
기존 core/tests/manifest/evidence와 기본 dispatcher EXP-30은 변경하지 않는다.

## 사전 측정과 판정

각 셀에서 delta_goal=drop_P_prefix−full을 primary로 보고한다.
full_goal, dropout_goal도 함께 보고하고 e:0/e:1 delta·전체 tick·상태·counter를 보존한다.
각 orientation에서 행은 strong [4,3.02], 열은 weak [.08,1.06]인 2×2 표다.
각 measure(full_goal, dropout_goal, delta_goal)의 표를 [[a,b],[c,d]]라 할 때:

- weak 증가: strong=4에서 b−a, strong=3.02에서 d−c.
- strong 감소: weak=.08에서 c−a, weak=1.06에서 d−b.
- interaction: (d−c)−(b−a). 방향을 바꾸거나 결과를 본 뒤 contrast를 추가하지 않는다.

대조는 비방향 기술량이다. 특정 부호·high 전환·영향 부재를 성공 조건으로 두지 않는다.
weak 변화만으로 full endpoint가 low→high면 해당 국소 조건에서 strong 감소 없이도
전환이 관찰된 것으로 해석한다. strong 변화만의 전환도 같은 방식으로 구분한다.
둘 다 필요해 보이는 패턴도 일반적 충분성·필요성으로 확장하지 않는다.

stable_decision/stable_ambiguous이면서 goal<.5−1e-6이면 low,
goal>.5+1e-6이면 high, 나머지는 inconclusive다.
full=low/drop=high일 때 low 술어에 대한 삭제 링크의 맥락적 필요성 true,
둘 다 low면 false, 나머지는 null이다. 1e-6은 오차 보증이나 통계 한계가 아니다.
비안정 종료에서도 연속값은 보고한다. 종료 tick이 다르므로 동일 시간 효과가 아니다.

## 출처·검증·실행 계약

spec에 R052 원본 10파일과 R055 anchor 12파일의 SHA-256을 동결한다.
R055 anchor는 plan/source_manifest/raw_manifest/audit 및 대각선 8 raw다.
R052 native provenance replay와 R055 8 trajectory replay는 새 표본이 아니다.
bridge는 drive·모든 tick/state/residual/stable·최종 상태·종료·counter를 비교한다.
수치 비교는 abs/rel 1e-12다. 생성기와 별도 프로세스의 검산기가 independent_step으로
전 궤적·최초 종료·비용을 재계산하며 producer/runtime/session/dynamics import를 금지한다.

Run-HCR-R056.cmd: 기준선·source/spec/parents/anchors 동결 → synthetic self-test →
별도 smoke 8행/8bridge → 최종 core regression 1회 → 연구 16행 → 독립 수치 audit →
summary/bundle/ZIP. smoke와 연구·출처 검증 비용을 합치지 않는다.
본 연구는 한 번 실행하며 자동 retry·덮어쓰기·결과에 따른 조건 추가는 없다.
구현 중 synthetic 검사와 결함 수정은 허용하되 실제 연구 재시작은 하지 않는다.
실패하면 최초 log·traceback·부분 evidence를 보존한다.
검증 완료 후 커밋·로컬 main 병합·작업 브랜치 정리·origin/main push·원격 확인한다.

## 주장 범위

이 결과는 고정 program의 수치 반응이다. native packet/proof/support/raw decision/
adoption/실제 에너지는 null이다. 새로운 native 또는 LLM 실험으로 표현하지 않는다.
독립 표본, basin/다중 attractor, hysteresis, 연속적 전환점, bias/topology의 원인 분리,
인간 인지·모델 내부 또는 HCC 전체 가설에 대한 직접 증거로 일반화하지 않는다.
