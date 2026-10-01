# R078 이후 판별 후보: zero-drive 경로와 readout threshold

R078은 R077 봉인 memory를 재사용해 두 edge 블록만 교환했다. ON의 score 0·1 선호는 실제 edge ID 기준으로 유지됐고, 동률 0.6에서는 같은 activation의 후보 order·최초 선택·final proof 지원이 함께 뒤집혔다. 후보 order 자체와 digest/internal identity 배치의 독립 인과 효과는 아직 분리하지 못했다.

이번 실험의 새로운 반증은 OFF 최종 proof가 항상 입력 첫 경로를 따른다는 가설이다. 교환 배열·e3 score 0은 [e2,e3]를 먼저 확장했지만 35 tick의 음성 goal 상태 뒤 `negative_requires_dependency_coverage`로 [e0,e1]을 추가 확장했다. 두 경로 network에서 81 tick을 더 쓰고 [e0,e1]을 final ancestry로 선택해 True를 채택했다. `proof.paths` inventory와 `Proof.final` 지원을 구분한 검산은 `HCR-Evidence/r078-validation/proof-support-audit.json`에 있다. ON 67 tick 대 OFF 116 tick인 이 셀은 이전의 일률적인 ON tick 증가 해석을 조건부로 수정한다.

개별 e3 score 0은 zero observation drive라는 뜻이며 전체 readout 중립을 뜻하지 않는다. 전체 UNSUPPORTED 규칙은 모든 edge가 0/None일 때 적용된다. 이번 첫 network는 다른 비영 edge가 있는 조건에서 goal 0.0190<0.5로 잠정 negative 상태에 도달했다. 작은 양수 입력도 이 readout 경계를 넘지 못하면 coverage가 유지될 수 있다. stable_decision의 margin은 goal 기준이며 후보 간 분리를 측정하지 않는다.

다음 최소 판별 후보는 같은 교환 배열·config·graph·공개 ID·world·memory에서 OFF의 e3 neutral 0과 작은 양수들을 비교하는 것이다. 원래 배열과 ON을 paired 대조로 유지하며 첫 network의 goal state·수렴 상태·progress reason·ready 경계·남은 frontier·후속 확장·final ancestry·readout/채택·분리된 비용을 기록한다. 방향성 경계와 연속적인 activation 변화가 coverage 전환에 각각 어떻게 연결되는지 구별한다. 구체적인 score·셀 수·예측·반증/판정불가 기준은 아직 동결하지 않았다.

예측은 0/양수라는 입력 구분과 goal 0.5 threshold를 나누어 동결해야 한다. 원래 배열 6셀은 기존 R077의 결정적 재현 확인이며 교환 배열 6셀이 이번 새로운 입력 개입이었다. R077의 OFF 경로 고정 관찰 역시 원래 배열에 제한됨을 후속 baseline 해석에 반영한다.

이는 후속 후보이며 새 실행·재학습·host correction을 이번 R078 evidence에 추가하지 않았다. 일반 순서 불변성, scheduling 최적성, inhibition의 독립 효과와 Graph↔Circuit 통합 가설의 지지 범위는 확대하지 않는다.
