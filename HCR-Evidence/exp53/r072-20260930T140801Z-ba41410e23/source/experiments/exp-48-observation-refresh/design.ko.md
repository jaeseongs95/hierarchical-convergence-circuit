# R067: 충돌 이후 e1 추가 관측의 효과

R066에서는 사실 저장과 조회가 달랐고, 같은 scope 안의 미통지 변화에서 오래된 사실 조회가 오류를 만들었다. e0와 e1 score가 함께 바뀌었으므로 e1 정보 하나의 효과는 분리되지 않았다.

이번에는 v0→v1→v2의 e0 score를 +0.8로 고정한다. 최초 e1 score도 +0.8이며 과거 e1=False와 충돌한다. context·epoch·memory·config·topology·관측 ID와 revision은 모두 동일하다. 비공개 세계 A는 e0=True/e1=False, B는 e0=True/e1=True다. 세계 label은 증거의 조건 식별자이며 native observation에는 주지 않는다.

## 동결된 비교

| 군 | 후속 e1 입력 | 추가 관측 예산 | 실제 호출 | 유효 시점 |
| --- | --- | ---: | ---: | --- |
| history | 과거 사실 -1 | 1 | 0 | -1 |
| stale | 원래의 낡은 +0.8 | 1 | 1 | 0 |
| fresh | 현재 측정 ±1 | 1 | 1 | 1 |

2개 세계 × 3개 군 × 회로 ON/OFF의 12조건에서 각각 최초·후속 native 판단을 실행한다. 총 24회는 대응 조건 수이며 독립 표본 수가 아니다. 새 학습은 없다. 양성 회로가 있는 동일한 R064 after_correction memory를 사용한다.

요청 edge e1과 한 번의 예산은 실행 전에 정한다. 명시적 baseline controller가 요청하고 별도 이상적 toy 관측 서비스가 답한다. private truth는 서비스와 검산기에만 전달한다. 관측 서비스는 결과를 미리 파일로 만들어 두지만 worker는 최초 판단 저장 뒤 요청을 기록하고 응답을 읽는다. 온라인 자율 관측·실제 센서 지연·능동적 edge 선택을 측정하는 장치는 아니다.

후속 판단은 수정 입력으로 만든 fresh session이다. 최초 세션 내부에서 계속 진행하는 native revision 경로의 효과와 구분한다. timestamp/provenance는 외부 기록이며 native가 freshness를 추론했다고 보지 않는다. 모든 군에서 observation ID/revision과 e0를 유지하고 e1 score만 바꾼다.

## 측정과 예측

최초 판단·후속 판단의 packet, proof, readout, terminal adoption과 모든 advance를 보존한다. 새 사실은 별도 표에 기록하지만 이번 판단은 응답에서 만든 입력을 직접 사용하며, 저장 뒤 다음 에피소드에서의 유지 효과는 측정하지 않는다.

동일한 두 edge score를 받는 단순 AND/sign baseline을 둔다. 하나라도 음수면 False, 모두 양수면 True, 그 외는 unknown으로 판정한다. 검산기는 이 baseline의 결과를 별도로 계산하며 private world는 채점에만 쓴다. 비용은 두 edge 검사로 기록하고 native ticks와 합하지 않는다.

- 과거 사실과 stale 관측은 두 세계를 구분하지 못한다.
- fresh e1 관측은 두 세계에서 모두 올바른 채택으로 이어진다.
- 최초 conflict는 두 세계 모두에서 발생하므로 세계 변화의 충분한 신호가 아니다.
- 동일 정보를 받은 단순 baseline도 두 세계를 맞춘다. 성공을 HCC의 고유 이점으로 해석하지 않는다.

예측 실패는 실험 결과로 남기며 조건을 변경해 성공을 만들지 않는다. False·unknown·conflict·거부·측정 불가는 각각 보존한다. unknown/conflict 응답은 합성 경계 검사로만 확인하며 연구 12조건에 합산하지 않는다.

## 실행과 한계

`Run-HCR-R067.cmd`는 source/조건/부모 입력 동결 → 합성 경계 검사 → 관측 서비스 → native 실행 → 별도 프로세스 입력 재구성·수식 replay → 최종 core 회귀 1회 → bundle/ZIP 순서로 실행한다. 자동 retry·설치·Git 작업을 하지 않고 첫 실패 로그를 보존한다.

이상적인 sensor가 제공한 관측의 유용성을 검증하는 좁은 toy 실험이다. sensor 정확성·trust 판단·일반화·native 자율 정보 획득·기억 유지·실제 에너지·총 계산 효율을 입증하지 않는다.
