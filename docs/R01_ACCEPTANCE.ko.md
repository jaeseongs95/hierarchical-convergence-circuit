# 구현 인수 기준과 한계

실행한 증거와 최종 test 수는 배포의 validation 영수증이 기준이다. 이 파일은 합격 기준을 기술하며 기능 구현만으로 가설의 Claim 상태를 올리지 않는다.

| 기준 | 현재 코드의 확인 방법 |
|---|---|
| 동일 primitive at A0/A1 | dynamics의 동일 tick 함수, 수준이 같은 값인 단위시험, top_down 비활성 대조 |
| cold graph construction | 빈 memory→search/group/link 계수 증가 |
| graph→circuit | 세 episode의 검증 뒤 compiler 등록과 memory provenance |
| 구조 재사용 | 새 이름/입력 edge 순서에서도 role binding, current activation 초기화 |
| 답 캐시 아님 | 동일 회로에 명확한 반대 사실을 입력하면 다른 답 |
| 회로화가 primitive D를 감추지 않음 | warm/cold proof depth 동일 기준, tick와 signal을 별도 집계 |
| stable≠correct | learned positive prior와 약한 반대 증거의 실제 오수렴 |
| reality 이후 수정 | feedback 이후 특정 edge만 측정→새 attempt→graph execution |
| 지속적인 재학습 | 저장/재로드 후 같은 약한 증거와 정상 입력의 새 판단 |
| 무보정 기록 | 첫 판단 readout→proof reconstruction→decision→feedback 순서 보존 |
| frozen evaluation | checksum 무변경, feedback API 거부 |
| 근거 없는 정답 생성 금지 | 추가 정보 없으면 보류/기존 판단 유지. reference 접근 sentinel |

범용 인지 학습, sparse spiking dynamics, distributed identity, 실제 감각 encoder, 신규 A의 자율 형성, 임의 D/M 탐색, 일반 부분그래프 mining은 구현하지 않았다. R0.1의 graph expansion은 제한된 공개 topology의 후보 경로 열거와 새로운 측정 후 재전개다. 모든 경로가 이미 있고 새 정보가 없으면 unsupported/ambiguous로 보류한다.

개발 데이터에서 full이 graph_only보다 모든 조건에서 우월하도록 만들지 않았다. prior로 더 잘 완성하는 경우와 잘못 안정되는 경우를 함께 보존한다. 그러므로 '정확도 손실 없는 전체 계산 감소'는 이 배포만으로 확인된 주장이 아니다.
