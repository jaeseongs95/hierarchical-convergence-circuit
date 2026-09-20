# R065 검증 기록과 도구의 한계

원클릭 실행은 합성 self-test, R064 원자료 수식 재생과 summary 일치, 12개 packet의 24건 참조 채점, 9건 변조 거부, core 회귀 599 pass / 기존 skip 3을 완료했다. source 12개 항목(자체 manifest 포함), 신규 bundle 29개 파일·ZIP, 부모 bundle 1,418개 파일의 무결성을 확인했다. 코드·계약·metric을 실행 뒤 바꾸거나 연구를 다시 실행하지 않았다.

`change-scope-guardian`의 working-tree 판정은 `BLOCKED`로 보존한다. 구현체는 excluded 검사를 preexisting-untouched보다 먼저 수행해 작업 전부터 있던 `HCR-Evidence/exp45/r064-20260920T024825Z-d995fcc733.zip`을 제외 경로 변경으로 분류했다. 해당 ZIP의 baseline/current SHA-256은 모두 `bdb80612141f759fc82e573795dd914fb1a8dca00001df586685084c4d487e02`다. 이 판정을 PASS로 고치지 않았다.

별도 [scope-evidence.json](../../HCR-Evidence/r065-validation/scope-evidence.json)은 초기 baseline에 있던 범위 밖 26,385개 파일의 실제 bytes가 모두 보존됐고, 당시 staged 62개 파일이 허용 범위 안이며 제외 경로 밖임을 검증했다. 이후 추가되는 완료 검증 기록도 최종 staged 목록에서 같은 범위 규칙으로 확인한다. 따라서 working-tree 스킬의 한계와 실제 커밋 대상의 범위 준수 근거를 분리한다. 계약의 범위·수용 기준과 baseline은 변경하지 않았다.

초기 저장소 profiler는 workspace 밖의 상위 AGENTS 참조 때문에 BLOCKED를 반환했다. 상위 지침은 instruction-scope-resolver가 별도로 확인한 상태였으므로 profiler에는 내부 대상만 전달했고 수정된 요청은 PASS였다. 최초 출력도 보존했다. 이 과정은 실험 결과나 native 실패가 아니다.

Windows 실행 로그의 CRLF는 원바이트로 보존했다. `git -c core.whitespace=cr-at-eol diff --cached --check`는 전체 및 직접 작성 파일 모두 통과했다. baseline은 원바이트를 복원할 수 있는 gzip으로 커밋하고 압축 전후 digest를 남겼다. 원본 JSON은 로컬에서 보존하며 Git에서는 중복 제외한다.
