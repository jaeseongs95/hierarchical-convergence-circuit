# R42 / EXP-88: 큰 구간으로 계측 부담을 검증한다

R41은 전체 반환 기록과 kernel 바이트 288쌍의 정확 동치를 확인했지만, native 계측 부담이 joint 14.14%, factor 13.93%로 고정 10% 기준을 넘었다. 이번 과제는 별도 계약에서 probe 수를 줄여 같은 기준을 만족하는지 확인하는 관측 연구다. R41의 실패 자료와 결론은 그대로 보존한다. R25의 산술 생략, R30의 공간 공유, R40의 표현별 총비용 비교와도 구분된다. 이미 정한 진단 후속이므로 새 방향성 패널은 반복하지 않는다.

R40 q4의 8개 폐쇄 관계표 × 이름 2 × 행순서 2 = 32맥락을 사용한다. canonical XY00/01/10/11 네 질의, 세 방식(native_joint/native_factor/same-information exact_joint), plain/profiled 두 mode, 세 반복으로 576기록·2,304출력이다. 매번 fresh producer/initial0.5이며 답 cache가 없다. arm 순서는 (caseindex+rep)%3, mode 짝 순서는 (caseindex+rep+arm순번)%2로 회전한다. 원천24개를 한 번 fresh native로 만들고 상위34,560회를 모두 계산한다. 전체34,584 settle/최대5,533,440 tick이며 학습·세계측정은0회다.

R41 외피를 재사용하되 Program.validate·Program.digest·dynamics.tick에는 probe를 설치하지 않는다. 이 함수들은 원래 settle·결과구성 경로에서 항상 실행한다. 연구 runtime의 validate/documents/produce/membership/consume/encode_role와 kernel alias3개, 총9개 binding만 프로세스 안에서 임시 교체하고 정상·예외 모두 finally로 정확히 복원한다. 중첩 observer를 거부하며 worker는1이다. 엔진 소스·수식·설정·임계값은 바꾸지 않는다.

coarse 범주는 source_export_guard/contract_validate/document_build/producer/membership/encode_role/consumer/kernel/program_build/settle/result_materialize/core잔여다. settle은 원래 validation·전체tick·제어·trace관찰/복사를 함께 포함한다. result_materialize는 codec.plain·Program.digest·결과와cost 구성 전체다. 이 구간 안의 비용을 다시 분해하거나 순수 신경 산술의 비중이라고 부르지 않는다.

process_time_ns stack으로 exclusive=inclusive−측정자식 시간을 계산한다. 모든 exclusive 합은 root inclusive와 정수 ns로 같아야 한다. 전체 core stopwatch−root를 profile_support로 보존해 설치·복원·snapshot을 포함한다. 자식 timer 종료 뒤의 집계는 부모 잔여에 남는다. 최종 metric 필드 구성/저장/원천/감사/준비/봉인/launcher는 별도 phase 비용에 남긴다. producer/consumer inclusive anchor는 세부 exclusive와 겹치므로 합하지 않는다. 세부 합계는 q4 core 전체이며 producer만의 원인기여도로 간주하지 않는다.

두 mode의 288짝에서 mode와 원래 두 CPU필드만 제외한 전체 반환 기록이 같아야 한다. 모든 kernel의 Program/Config/drives/initial/tick state/residual/stable_steps/convergence/cost canonical bytes도 정확히 같아야 한다. 같은 해시도 전체 bytes를 대조한 뒤 저장만 공유하고, 계산은 생략하지 않는다. scalar1e-14 허용오차는 별도 재계산에만 쓰며 짝비교를 완화하지 않는다. 독립 full8triple oracle·모든중간층·출처·봉인·역할·물리참조와 source proof/controller를 검산한다.

R41과 동일하게 각 arm의32맥락 coreCPU합 profiled/plain<=1.10이 세 반복 모두 맞고 품질/짝/원장/복원이 통과해야 내부 비중을 해석한다. 그때 같은 최대 exclusive 범주가 세 반복 모두30%이상이면 이 유한 경로의 후속 조사 후보로만 남긴다. 10%/30%는 기술판별선이며 통계적 유의성·제품효율·최적화 채택선이 아니다. 통과해도 plain 시간의 정확한 분해를 복원하거나 최적화 효과를 입증한 것은 아니다. R40의5%총비용 음성 결론은 변하지 않는다.

부담 초과·동치 실패·상한 중단·원자료 부족은 음성/제한 결과로 보존한다. 동결 후 재튜닝·native 재실행·상한 증가는 하지 않는다. 고정32맥락/폐쇄2값관계/q4/3반복/LinuxPython에 한정하며 일반CSP·큰domain·학습·최소표현·운영채택으로 확대하지 않는다. 관계표 완전성은 외부 폐쇄계약이고 가상assignment나 목록 부재를 세계의 사실/부정 증거로 바꾸지 않는다.
