# R064 source에서 확인한 정보 흐름

기준은 R064 bundle의 `source/`와 일치하는 현재 source다. 실행기가 원본 source manifest와 현재 `src/`, `tools/`의 바이트를 CRLF→LF만 정규화해 대조한다. 다음은 정적 source 해석이며 runtime 필드 ablation 실험으로 표현하지 않는다.

| 단계 | source | 다음 단계로 전달되는 것과 경계 |
|---|---|---|
| 관측 → 판단 | `src/hcr/runtime.py:179`의 `AdaptiveEngine.begin`, `:251`의 `advance` | public observation과 memory를 받고 workspace를 형성한다. 참조 세계 truth는 입력받지 않는다. |
| 회로 검색·활성화 | `src/hcr/activation.py:23`, `:69`; `src/hcr/expansion.py:22` | active·pattern·strength와 evidence episode 수에서 얻는 balance, 현재 관측 score가 계산에 쓰인다. 저장된 open_edge는 역할 관계이며 특정 episode의 e1=True라는 사실표가 아니다. |
| 외부 판정 | `tools/r064_retention/audit.py:23`의 `reference` | native 판단 후 private truth로 correctness와 proof/assumption 정합성을 계산해 Feedback을 만든다. 잘못된 True에 대한 feedback과 e1=False 관측은 정보량이 다르다. |
| feedback → patch | `src/hcr/runtime.py:347`, `src/hcr/learning.py:73`의 `update_adaptive` | 오류는 사용 회로를 약화한다. 올바른 판단의 구조 학습 분기는 `feedback.correct is True and feedback.proof_valid and decision.value is True`다. False에는 이 분기가 없다. |
| persistent memory | `src/hcr/circuits.py:159`의 `AdaptiveMemory` | circuits, pending, consumed_feedback, patches, version, config_signature 및 schema를 저장한다. feedback/decision ID와 proof digest는 값·관측을 복원하는 사실 조회표가 아니다. |
| session·trace 이력 | `src/hcr/state.py:53`; `src/hcr/runtime.py:368`; R064 corrected learning packet | full session에는 held observation·decision과 feedback, trace가 남는다. 보존 자료에 교정 정보가 없다는 주장은 틀리다. |
| fresh frozen 평가 | `tools/r064_retention/worker.py:83`; `tools/r063_formation/worker.py`의 `execute` | memory snapshot으로 새 AdaptiveSession을 만든다. 이전 full session의 held/feedback/requests를 넘기지 않는다. 같은 episode_id를 사용해도 사실 조회는 생기지 않는다. |
| 무결성·중복 방지 | `src/hcr/circuits.py:191`; `src/hcr/runtime.py:224`, `:347` | 전체 memory hash/version은 guard·feedback binding에, consumed_feedback/patch는 이력 검증과 재소비 방지에 쓰인다. “읽지 않는 이력”이 아니라 “현재 판단 내용의 사실 근거로 조회하지 않는 이력”이다. |

pending은 학습 후보이며 activation pool은 compiled circuits를 순회한다. circuit의 feedback_ids와 proof_digests는 출처 확인에 쓰인다. evidence_episodes는 출처 기능뿐 아니라 balance 계산에도 영향을 주므로 순수 감사 metadata로 분류하지 않는다. circuit version은 출력 provenance에 포함된다. 이 구분은 현재 adaptive 경로에 한정하며 R0.1 learner나 일반 HCC 전체로 확장하지 않는다.

재분석 출력의 `memory_flow.json`은 raw 값의 대조다. 이 표의 source 해석은 별도로 사람이 읽을 수 있는 경계 설명이며, 코드에서 문자열이 검색됐다는 이유만으로 인과성이 증명됐다고 주장하지 않는다.
