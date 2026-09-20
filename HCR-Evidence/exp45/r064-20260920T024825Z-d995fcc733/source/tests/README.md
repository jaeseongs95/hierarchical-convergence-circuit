# R0.1 검증

`python -X utf8 -B hcr.py check` 또는 `python -X utf8 -B scripts/selftest.py`로 실행한다. 표준 unittest만 사용하며 실제 네트워크 연결을 거부한다. source 밖 임시 폴더에서 저장/재로드, 통합 demo, 해시/trace/summary 위변조 거부를 검사한다.

같은 kernel의 두 A 수준, bounded update, 2-cycle, 명시적 초기 상태에 따른 다중안정, 공개 입력만의 inference, memory gate, frozen 평가 무변경, 반복 경험 threshold, 값이 달라지는 회로 재사용, 기존 오류 보존, 새로운 관측 이후 재확장, 학습 영속성을 검사한다.

PowerShell native parser가 없는 환경에서는 해당 한 시험을 skip으로 보고한다. Python 3.12 문법 검사는 실제 3.12 인터프리터 실행과 구분한다. 합성 calibration과 반복 검산은 별개의 연구 표본이 아니다.
