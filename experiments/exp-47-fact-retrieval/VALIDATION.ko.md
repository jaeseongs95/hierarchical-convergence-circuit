# R066 검증 기록

연구 조건·worker·사실 조회 로직·검산 metric은 실행 뒤 바꾸지 않았다. 최초 60개 native 평가, 독립 수식 replay, 사실 join 검산과 13개 변조 거부는 완료됐다. 합성 경계 self-test 10개는 연구 표본에 합산하지 않는다.

최초 core 회귀는 `python -m` 실행의 import 우선순위 때문에 루트 `hcr.py`가 `src/hcr`를 가렸다. `test_contracts_dynamics` 모듈이 불러와지지 않아 579개 항목 중 error 1개·기존 skip 3개였고, 이 실행은 실패로 보존했다. [failure.json](../../HCR-Evidence/exp47/r066-20260920T060557Z-c4b48b19a6/failure.json)을 성공으로 바꾸지 않는다.

수정은 pipeline의 subprocess bootstrap에서 `src/`를 import 검색 경로 맨 앞에 넣는 부분과 해당 source manifest hash다. 기존 core·tests와 최초 source snapshot은 수정하지 않았다. 먼저 실패한 테스트 모듈을 같은 방식으로 import해 경로가 해결됐음을 확인하고, [recover-regression.py](../../HCR-Evidence/r066-validation/recover-regression.py)로 원래 run 전체 hash와 수정 두 파일을 동결한 뒤 회귀만 다시 실행한다. native 평가와 독립 표본은 추가하지 않는다. 이 복구 스크립트는 같은 출력 폴더가 있으면 실행을 거부한다.

최초 시도 전체와 실패 기록은 원바이트 ZIP으로 묶고, 수정 source·회귀 결과·복구 plan은 별도 [regression-recovery](../../HCR-Evidence/r066-validation/regression-recovery/result.json)에 저장한다. 따라서 회귀 시도 총수는 2회이며 최종 성공 회귀는 1회다. 정상 신규 실행용 원클릭은 수정된 bootstrap을 사용한다. 이미 얻은 연구 결과를 유리하게 바꾸기 위한 재실행은 없다.

작업 기준선은 첫 구현 전에 저장했다. workspace profiler는 지침 참조를 입력받지 않아 열린 질문 하나를 남겼고, 적용 지침은 별도 instruction-scope-resolver 결과와 원문으로 확인했다. 모델/추론 설정을 추정하거나 MCP guarded workflow 완료를 주장하지 않는다. 지침 분석 JSON의 필드 이름을 canonical schema에 맞춰 정리했으며 연구 계약은 바꾸지 않았다.

최종 성공 수치, source/입력/ZIP 무결성, 범위 밖 기존 파일 보존 및 색인 검사 결과는 [delivery-verification.json](../../HCR-Evidence/r066-validation/delivery-verification.json)을 따른다. 관측하지 않은 항목이나 기존 skip을 pass로 세지 않는다.

최종 회귀는 602개 중 599개 통과, 기존 Windows 환경 skip 3개였다. 전체 diff 공백 검사는 봉인 source의 기존 Markdown hard break 9개와 기존 테스트의 끝 빈 줄 1개를 발견했다. 해당 두 파일이 기존 source와 원바이트로 같음을 확인했으며 공백을 고쳐 재봉인하지 않았다. 직접 작성·수정 파일의 공백 검사는 통과했다. 전체 검사 exit 2와 개별 근거는 별도로 보존한다.
