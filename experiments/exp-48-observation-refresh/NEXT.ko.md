# R067 이후: conflict에서 실제 관측 요청으로 이어지는 경로

이번에는 host가 미리 정한 e1을 요청했다. 다음 최소 질문은 **같은 관측 예산과 노출 정보에서 기존 native 경로가 필요한 관측을 요청하는가**다. 요청이 없으면 그 경계를 결과로 남기며 성공을 위해 native에 정답이나 요청 edge를 주입하지 않는다.

1. 기존 request/observation/revision API, 요청 trigger, pending state와 replay 규칙을 읽기 전용으로 조사한다. 과거 사실·freshness metadata가 native 입력에 실제로 노출되는지 먼저 확인한다. 노출되지 않는 정보를 안다고 가정하지 않는다.
2. native 요청과 R067 명시적 controller 요청을 분리한다. 동일 edge 후보·추가 관측 상한 1·동일 sensor 응답을 사용하고, host가 native 요청을 교정하거나 자동 retry하지 않는다. native에 필요한 정보 표현이 없어 직접 비교가 불가능하면 측정 불가로 남긴다.
3. 최초 판단→요청 발생/미발생→측정 응답→기존 세션 revision→후속 readout/adoption을 각각 보존한다. 새 session 재실행과 native revision의 차이를 혼합하지 않는다.
4. 요청 trigger 부재, 정보 미노출, 잘못된 edge 요청, 응답 unknown/conflict, 판단 수정 실패, 외부 예산 종료를 구분한다. 실패 이후 구현 확장은 새 계약으로 다루고 이번 조건을 바꾸지 않는다.
5. 먼저 두-edge·단일 후보의 최소 경로만 확인한다. 이 조건의 성공은 유용한 edge의 일반적 선택이나 장기 기억 유지의 증거가 아니다. 여러 후보에서의 관측 선택은 별도 후속 질문이다.

이는 아직 실행하지 않은 후속 방향이다. 센서 신뢰도나 장기 기억까지 한 번에 추가하지 않는다.
