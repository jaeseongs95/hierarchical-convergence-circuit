# R068: 기존 native 관측 요청의 진입 조건

## 질문과 사전 조사

R067 NEXT의 첫 단계는 기존 API가 과거 사실과 현재 관측의 conflict를 관측 요청으로 연결하는지 확인하는 것이다. 현재 Observation은 episode_id, revision, start, goal, edges만 받는다(`src/hcr/codec.py:62`). 과거 사실표와 valid_at은 native 입력에 없다. `src/hcr/runtime.py`의 AdaptiveEngine.request_revision은 외부 `correct=False` 피드백을 요구하고, ADAPT·재전개 허용·요청 예산을 검사한 뒤 abs(score)<0.9 또는 unknown인 모든 edge를 고른다. conflict 전용 trigger나 단일 edge 선택기가 아니다.

이 때문에 R067 controller와 동일 정보·단일 후보 조건에서 자율 conflict sensing을 직접 비교하는 것은 현재 표현 계약으로 측정 불가다. 이 결과를 능력 점수 0으로 바꾸지 않는다. 성공을 위해 native 입력이나 요청 edge를 보정하지 않는다.

## 동결 설계

R067의 observation(episode_id 포함), config, R064 after_correction memory와 계산 상한을 그대로 사용한다. mode(frozen_eval/adapt) × circuit(OFF/ON) 네 세션을 실행한다. native 최초 판단과 candidate readout/adoption을 저장하고 정확히 그 finish branch를 복원해 피드백 없이 request_revision을 한 번 호출한다. 거부·응답과 전후 packet을 저장한다. 추가 관측 상한은 1회이나 요청이 없으면 호출하지 않는다. 실제 센서 응답·학습·후속 revision은 연구 조건에서 제공하지 않는다.

두 세계 A(e1=False), B(e1=True)는 관측이 같은 참조 해석이다. 같은 native 판단을 각각 채점하며 세션이나 독립 표본 수를 두 배로 세지 않는다. R067 과거 사실·freshness는 controller 전용 정보였고 여기서도 native에 새로 주입하지 않는다.

예측은 자동 요청 0, 피드백 없는 명시적 API 호출 거부다. 다른 결과가 나오면 최초 packet과 오류를 보존하고 구현·검산 차이를 조사한다. 외부 오답 피드백은 세계에 관한 추가 정보이자 memory 갱신을 유발하므로 자율 관측의 공정한 대조군으로 취급하지 않는다.

## 별도 합성 검사

동결된 10개 API 조건은 연구 표본에 합산하지 않는다. frozen 피드백 거부, 올바른 피드백 이후 요청 거부, weak 두 edge 요청, strong 요청 없음, 요청 예산 0, 재전개 비활성, train mode 요청 없음, e0=1로 만든 단일 후보의 같은 세션 revision, 중복 pending 거부, 요청하지 않은 edge 변경 거부를 확인한다. 합성 incorrect feedback은 실세계 정답 평가가 아닌 API fixture다. 단일 후보 revision은 e1=-1인 합성 응답을 쓰고 최초와 후속 판단을 모두 보존한다.

## 검증과 비용

생산 코드와 분리된 프로세스에서 기존 수식 검산기로 packet·event·state·proof를 재계산하고, 별도 규칙으로 요청과 피드백 경계를 검사한다. 변조 거부, 원자료/부모/source hash, ZIP 바이트 일치와 최종 core 회귀 1회를 확인한다. 독립 연구자 감사는 아니다.

kernel ticks, expansion, reuse, binding, API 호출, 실제 observation request와 measurement를 분리한다. 시간·에너지·총 효율 우위를 주장하지 않는다. core와 기존 evidence는 수정하지 않으며 실패하면 새 run의 로그·traceback을 보존한다.

실행: 저장소 루트 `Run-HCR-R068.cmd`. 원클릭은 Git을 변경하거나 패키지를 설치하지 않는다.
