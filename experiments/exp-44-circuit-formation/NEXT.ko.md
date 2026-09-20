# 다음 판별 질문: 오류 뒤 변화가 memory에서 행동까지 유지되는가

이 문서는 후속 설계 제안이며 다음 실험의 동결 계약이 아니다. R063의 형성 후 memory를 출발점으로 검토하되, 다음 실행 전에 정확한 입력·외부 truth·feedback·예산·예측을 따로 동결한다.

## 필요한 구분

R063은 형성과 새 topology에서의 reuse를 연결했다. 그러나 닫힌 입력도 처음부터 올바르게 False를 채택했으므로 외부 오류 feedback, ADAPT 재개, memory 약화와 수정의 유지는 측정하지 않았다. 닫힌 입력에서 circuit 후보가 부적격해 primitive를 사용한 것과, 잘못 채택한 판단을 외부 feedback 이후 수정한 것은 다른 사건이다.

다음 질문은 **동일하게 형성된 회로가 잘못된 판단에 사용된 뒤, native 약화·재개 규칙이 이후 행동을 바꾸는가**다. 단순히 memory strength가 낮아졌다는 사실로 수정 성공을 선언하지 않는다.

## 최소 실험 경계

R063 memory/3.json과 원본 소스의 출처를 연결한다. 기존 ADAPT·feedback·request_revision API와 historical retention fixture부터 확인하고 새 learning 메커니즘을 추가하지 않는다. 사전 지정한 오해를 유발하는 관측과 독립 world truth를 분리한다. 정확한 오류 입력은 연구 시작 전에 정하며, 원하는 오답이나 correction이 나올 때까지 학습·입력을 바꾸지 않는다.

처음 판단, 잘못된 판단에 실제 쓰인 circuit, 외부 평가, native negative feedback의 patch, 허용된 observation request, 수정 관측, 재개 판단, 재개 뒤 memory를 순서대로 기록한다. 조건에 따라 원래 판단이 맞거나 circuit 사용이 없거나 revision 요청이 나오지 않으면 그 사실을 그대로 남기고, 나머지 경로를 host가 만들어 주지 않는다.

수정 전과 후의 frozen memory snapshot을 같은 평가 입력에 적용한다. misleading 관측 재노출과 올바른 관측 입력을 구분하고, snapshot 사이의 ON/OFF 대조에서도 source·config·scheduler·readout·budget을 고정한다. 입력 교정 효과와 memory 변화 효과를 섞지 않는다. 필요하다면 주 실험은 memory 효과 하나로 좁히고 장기 유지·새 instance 전이는 뒤로 분리한다.

## 판정

오류 발견, 사용 circuit 약화, revision 요청, 수정 관측 적용, 수정된 raw 판단, 관측 지지·채택, 이후 frozen 재노출에서의 행동 변화를 각각 판정한다. 이전 상태를 직접 복사하거나 정답을 바꿔 끼우지 않는다. strength 변화만 있고 행동이 같다면 구조 상태 변경과 행동 수정의 연결은 확인되지 않은 것이다.

R063에서 kernel ticks 감소는 반증됐으므로 후속 실험에서도 expansion과 pool/decision ticks를 나눈다. 오류 수정이 더 많은 계산을 요구해도 숨기지 않는다. 이 단계가 끝난 뒤에야 latent connectivity와 동적 edge 생성의 비교가 구별할 새 질문이 있는지 판단한다.
